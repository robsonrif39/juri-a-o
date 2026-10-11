from celery import Celery
from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from bs4 import BeautifulSoup
import requests
from datetime import datetime, timedelta
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'juri-acao-secret-key'
ADVOGADOS_FILE = 'advogados.json'
CLIENTES_FILE = 'clientes.json'


def parse_date(value):
    if value is None:
        return None
    if hasattr(value, 'date') and not isinstance(value, str):
        try:
            return value.date()
        except Exception:
            pass
    if hasattr(value, 'year') and hasattr(value, 'month') and hasattr(value, 'day'):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M:%S'):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def normalizar_data_calendario(value):
    data = parse_date(value)
    if data is None:
        return None
    return data.isoformat()


def formatar_data_breve(data):
    if data is None:
        return 'Sem data'
    meses = {
        1: 'jan', 2: 'fev', 3: 'mar', 4: 'abr', 5: 'mai', 6: 'jun',
        7: 'jul', 8: 'ago', 9: 'set', 10: 'out', 11: 'nov', 12: 'dez'
    }
    return f"{data.day:02d} {meses.get(data.month, data.strftime('%b')).lower()}"


def feriados_anuais(ano=None):
    ano = ano or datetime.now().year
    return {
        f'{ano}-01-01',
        f'{ano}-04-21',
        f'{ano}-05-01',
        f'{ano}-09-07',
        f'{ano}-10-12',
        f'{ano}-11-02',
        f'{ano}-11-15',
        f'{ano}-12-25',
    }


def adicionar_dias_uteis(data_base, quantidade, feriados=None):
    data_tipo = type(data_base)
    if quantidade <= 0:
        resultado = parse_date(data_base) or datetime.now().date()
        return resultado if data_tipo is datetime else resultado

    base = parse_date(data_base)
    if base is None:
        base = datetime.now().date()

    feriados_set = set(feriados or [])
    data = base
    cont = 0
    while cont < quantidade:
        data += timedelta(days=1)
        if data.weekday() < 5 and data.isoformat() not in feriados_set:
            cont += 1

    if isinstance(data_base, datetime):
        return datetime.combine(data, datetime.min.time())
    return data


def calcular_dias_uteis_entre(data_inicial, data_final, feriados=None):
    inicio = parse_date(data_inicial)
    fim = parse_date(data_final)
    if inicio is None or fim is None:
        return 0
    if fim <= inicio:
        return 0

    feriados_set = set(feriados or [])
    total = 0
    cursor = inicio + timedelta(days=1)
    while cursor < fim:
        if cursor.weekday() < 5 and cursor.isoformat() not in feriados_set:
            total += 1
        cursor += timedelta(days=1)
    return total


def carregar_advogados():
    try:
        with open(ADVOGADOS_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            if isinstance(dados, list):
                return dados
    except FileNotFoundError:
        pass

    advogado_padrao = [{
        'id': 1,
        'nome': 'Dra. Renata Silva',
        'oab': '123456',
        'login': 'renata',
        'senha_hash': generate_password_hash('123456')
    }]
    salvar_advogados(advogado_padrao)
    return advogado_padrao


def salvar_advogados(lista):
    with open(ADVOGADOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend='redis://localhost:6379/0',
        broker='redis://localhost:6379/0'
    )
    celery.conf.update(app.config)
    return celery


celery = make_celery(app)
advogados = carregar_advogados()


def carregar_clientes():
    try:
        with open(CLIENTES_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            if isinstance(dados, list):
                return dados
    except FileNotFoundError:
        pass
    return []


def salvar_clientes(lista):
    with open(CLIENTES_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)


def salvar_aviso_processo(cliente):
    if not isinstance(cliente, dict):
        return None

    nome = (cliente.get('nome') or cliente.get('cliente') or 'Cliente').strip()
    numero = (cliente.get('numeroProcesso') or cliente.get('numero') or '').strip()
    data_vencimento = parse_date(cliente.get('dataVencimentoProcesso') or cliente.get('data_vencimento'))
    prazo_dias = cliente.get('prazoDiasUteis')

    if data_vencimento is None:
        try:
            prazo_dias = int(prazo_dias) if prazo_dias not in (None, '') else 0
        except (TypeError, ValueError):
            return None
        if prazo_dias <= 0:
            return None
        feriados = set()
        for ano in {datetime.now().year, datetime.now().year + 1}:
            feriados |= feriados_anuais(ano)
        data_vencimento = adicionar_dias_uteis(datetime.now().date(), prazo_dias, feriados)

    if data_vencimento is None:
        return None

    aviso = {
        'cliente': nome,
        'nome': nome,
        'numeroProcesso': numero,
        'numero': numero,
        'tipo': 'processo',
        'prazo': f"{prazo_dias} dias úteis" if prazo_dias not in (None, '', 0) else 'Prazo informado',
        'data_final': data_vencimento.isoformat(),
        'dateKey': data_vencimento.isoformat(),
        'assunto': f"Processo de {nome}",
        'observacao': cliente.get('observacoes') or 'Prazo de processo registrado no cadastro',
        'processo': numero,
    }

    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        avisos = {}

    if not isinstance(avisos, dict):
        avisos = {}

    chave = data_vencimento.isoformat()
    lista = avisos.setdefault(chave, [])
    if any(
        item.get('numeroProcesso') == numero and item.get('cliente') == nome and item.get('dateKey') == chave
        for item in lista
    ):
        return aviso

    lista.append(aviso)
    with open('avisos.json', 'w', encoding='utf-8') as f:
        json.dump(avisos, f, ensure_ascii=False, indent=2)

    return aviso


clientes = carregar_clientes()
eventos = []


def parse_moeda(value):
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    texto = str(value).strip().replace('R$', '').replace(' ', '')
    if not texto:
        return 0.0
    texto = texto.replace('.', '').replace(',', '.')
    try:
        return float(texto)
    except ValueError:
        return 0.0


def listar_honorarios_receber(data_inicio=None, data_fim=None):
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        return []

    registros = []
    if isinstance(avisos, dict):
        for data_key, lista in avisos.items():
            for idx, item in enumerate(lista):
                if not isinstance(item, dict):
                    continue
                if item.get('tipo') == 'processo_manual':
                    continue
                valor = parse_moeda(item.get('valorParcela') or item.get('valorTotal') or item.get('valor'))
                if valor <= 0:
                    continue
                data_item = item.get('dateKey') or data_key
                if data_inicio and data_item < data_inicio:
                    continue
                if data_fim and data_item > data_fim:
                    continue
                registros.append({
                    'cliente': item.get('cliente') or 'Cliente',
                    'data': data_item,
                    'parcela': item.get('parcela') or '—',
                    'valor': valor,
                    'valor_formatado': f'R$ {valor:,.2f}',
                    'observacao': item.get('observacao') or 'Cobrança registrada no calendário',
                    'status': item.get('status') or 'pendente',
                    'index': idx,
                    'dateKey': data_key,
                })
    elif isinstance(avisos, list):
        for idx, item in enumerate(avisos):
            if not isinstance(item, dict):
                continue
            if item.get('tipo') == 'processo_manual':
                continue
            valor = parse_moeda(item.get('valorParcela') or item.get('valorTotal') or item.get('valor'))
            if valor <= 0:
                continue
            data_item = item.get('dateKey') or item.get('data_final') or 'Sem data'
            if data_inicio and data_item < data_inicio:
                continue
            if data_fim and data_item > data_fim:
                continue
            registros.append({
                'cliente': item.get('cliente') or 'Cliente',
                'data': data_item,
                'parcela': item.get('parcela') or '—',
                'valor': valor,
                'valor_formatado': f'R$ {valor:,.2f}',
                'observacao': item.get('observacao') or 'Cobrança registrada no calendário',
                'status': item.get('status') or 'pendente',
                'index': idx,
                'dateKey': data_item,
            })

    return sorted(registros, key=lambda item: (item['data'], item['cliente']))


def montar_grafico_honorarios(registros):
    soma_por_mes = {}
    for item in registros:
        try:
            data_ref = datetime.strptime(item['data'], '%Y-%m-%d').date()
        except ValueError:
            continue
        chave = data_ref.strftime('%b/%Y')
        soma_por_mes[chave] = soma_por_mes.get(chave, 0) + item['valor']

    grafico = []
    for mes, total in sorted(soma_por_mes.items(), key=lambda pair: datetime.strptime(pair[0], '%b/%Y')):
        grafico.append({
            'label': mes,
            'valor': total,
            'valor_formatado': f'R$ {total:,.2f}',
            'altura': max(18, min(100, int((total / max(1.0, max(soma_por_mes.values()))) * 100))),
        })
    return grafico


def listar_proximo_evento():
    hoje = datetime.now().date()
    eventos = []

    for arquivo in ('avisos.json', 'acompanhamento.json'):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except FileNotFoundError:
            continue

        if isinstance(dados, dict):
            for data_key, lista in dados.items():
                for item in lista:
                    if not isinstance(item, dict):
                        continue
                    data_evento = parse_date(item.get('dateKey') or item.get('data_final') or data_key)
                    if data_evento is None or data_evento < hoje:
                        continue
                    if item.get('tipo') == 'processo_manual' and not (item.get('numeroProcesso') or item.get('processo')):
                        continue
                    titulo = (
                        item.get('assunto')
                        or item.get('cliente')
                        or item.get('nome')
                        or item.get('observacao')
                        or item.get('numeroProcesso')
                        or item.get('processo')
                        or 'Evento do calendário'
                    )
                    resumo = item.get('observacao') or item.get('prazo') or item.get('parcela') or 'Evento agendado'
                    eventos.append({
                        'data': data_evento,
                        'data_breve': formatar_data_breve(data_evento),
                        'titulo': titulo,
                        'resumo': resumo,
                    })
        elif isinstance(dados, list):
            for item in dados:
                if not isinstance(item, dict):
                    continue
                data_evento = parse_date(item.get('dateKey') or item.get('data_final'))
                if data_evento is None or data_evento < hoje:
                    continue
                titulo = (
                    item.get('assunto')
                    or item.get('cliente')
                    or item.get('nome')
                    or item.get('observacao')
                    or item.get('numeroProcesso')
                    or item.get('processo')
                    or 'Evento do calendário'
                )
                resumo = item.get('observacao') or item.get('prazo') or item.get('partes') or 'Evento agendado'
                eventos.append({
                    'data': data_evento,
                    'data_breve': formatar_data_breve(data_evento),
                    'titulo': titulo,
                    'resumo': resumo,
                })

    if not eventos:
        return {'data': None, 'data_breve': 'Sem data', 'titulo': 'Sem eventos', 'resumo': 'Cadastre um aviso no calendário'}

    proximo = min(eventos, key=lambda item: item['data'])
    return proximo


@app.context_processor
def injeta_proximo_evento():
    return {'proximo_evento': listar_proximo_evento()}


def listar_vencimentos_dashboard():
    hoje = datetime.now().date()
    feriados = set()
    for ano in {hoje.year, hoje.year + 1}:
        feriados |= feriados_anuais(ano)

    itens = []
    for cliente in clientes:
        data_vencimento = parse_date(cliente.get('dataVencimentoProcesso') or cliente.get('data_vencimento'))
        prazo = cliente.get('prazoDiasUteis')
        if data_vencimento is None and prazo:
            try:
                data_vencimento = adicionar_dias_uteis(hoje, int(prazo), feriados)
            except (TypeError, ValueError):
                continue

        if data_vencimento is None:
            continue

        dias_restantes = calcular_dias_uteis_entre(hoje, data_vencimento, feriados)
        itens.append({
            'cliente': cliente.get('nome'),
            'numeroProcesso': cliente.get('numeroProcesso'),
            'data_vencimento': data_vencimento.isoformat(),
            'dias_restantes': dias_restantes,
            'tipo': 'processo'
        })

    for arquivo in ('avisos.json', 'acompanhamento.json'):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except FileNotFoundError:
            continue

        if isinstance(dados, dict):
            for data_key, lista in dados.items():
                for item in lista:
                    if not isinstance(item, dict):
                        continue
                    data_str = item.get('dateKey') or item.get('data_final') or data_key
                    data_vencimento = parse_date(data_str)
                    if data_vencimento is None:
                        continue
                    dias_restantes = calcular_dias_uteis_entre(hoje, data_vencimento, feriados)
                    if dias_restantes <= 10:
                        itens.append({
                            'cliente': item.get('cliente') or item.get('nome') or 'Aviso',
                            'numeroProcesso': item.get('numeroProcesso') or item.get('numero') or item.get('processo') or '',
                            'data_vencimento': data_vencimento.isoformat(),
                            'dias_restantes': dias_restantes,
                            'tipo': item.get('tipo') or 'aviso'
                        })
        elif isinstance(dados, list):
            for item in dados:
                if not isinstance(item, dict):
                    continue
                data_vencimento = parse_date(item.get('data_final') or item.get('dataVencimento') or item.get('dateKey'))
                if data_vencimento is None:
                    continue
                dias_restantes = calcular_dias_uteis_entre(hoje, data_vencimento, feriados)
                if dias_restantes <= 10:
                    itens.append({
                        'cliente': item.get('cliente') or item.get('nome') or 'Aviso',
                        'numeroProcesso': item.get('numeroProcesso') or item.get('numero') or item.get('processo') or '',
                        'data_vencimento': data_vencimento.isoformat(),
                        'dias_restantes': dias_restantes,
                        'tipo': item.get('tipo') or 'aviso'
                    })

    itens = sorted(itens, key=lambda x: (x['dias_restantes'], x['cliente']))
    return itens[:8]


def listar_casos_recentes_dashboard(limit=3):
    itens = []

    for cliente in clientes:
        data_ref = parse_date(cliente.get('dataCadastro')) or parse_date(cliente.get('dataVencimentoProcesso'))
        if data_ref is None:
            continue

        tipo = (cliente.get('tipoCaso') or 'Civil').strip()
        titulo = cliente.get('nome') or 'Cliente sem nome'
        descricao = cliente.get('numeroProcesso') or 'Processo em andamento'
        itens.append({
            'titulo': titulo,
            'descricao': descricao,
            'data': data_ref,
            'tag': tipo,
            'tag_class': 'tag-blue',
            'progress': 60,
            'tipo': 'cliente'
        })

    for arquivo in ('acompanhamento.json', 'avisos.json'):
        try:
            with open(arquivo, 'r', encoding='utf-8') as f:
                dados = json.load(f)
        except FileNotFoundError:
            continue

        if isinstance(dados, dict):
            for date_key, lista in dados.items():
                for item in lista:
                    if not isinstance(item, dict):
                        continue
                    data_ref = parse_date(item.get('dateKey') or item.get('data_final') or date_key)
                    if data_ref is None:
                        continue

                    titulo = item.get('assunto') or item.get('cliente') or item.get('nome') or item.get('numeroProcesso') or item.get('numero') or 'Caso recente'
                    descricao = item.get('observacao') or item.get('ultima_movimentacao') or item.get('prazo') or 'Evento do escritório'
                    tipo = item.get('tipoCaso') or item.get('tipo') or 'Civil'
                    if tipo == 'processo_manual':
                        tipo = 'Processo'
                    elif tipo == 'processo':
                        tipo = 'Processo'

                    itens.append({
                        'titulo': titulo,
                        'descricao': descricao,
                        'data': data_ref,
                        'tag': str(tipo).title(),
                        'tag_class': 'tag-green' if 'trabalhista' in str(tipo).lower() else 'tag-blue' if 'civil' in str(tipo).lower() else 'tag-red',
                        'progress': 70,
                        'tipo': 'processo'
                    })
        elif isinstance(dados, list):
            for item in dados:
                if not isinstance(item, dict):
                    continue
                data_ref = parse_date(item.get('data_final') or item.get('dateKey'))
                if data_ref is None:
                    continue

                titulo = item.get('assunto') or item.get('cliente') or item.get('nome') or item.get('numeroProcesso') or item.get('numero') or 'Caso recente'
                descricao = item.get('partes') or item.get('ultima_movimentacao') or item.get('observacao') or 'Evento do escritório'
                tipo = item.get('tipoCaso') or item.get('tipo') or 'Civil'
                itens.append({
                    'titulo': titulo,
                    'descricao': descricao,
                    'data': data_ref,
                    'tag': str(tipo).title(),
                    'tag_class': 'tag-green' if 'trabalhista' in str(tipo).lower() else 'tag-blue' if 'civil' in str(tipo).lower() else 'tag-red',
                    'progress': 72,
                    'tipo': 'processo'
                })

    itens = sorted(itens, key=lambda x: x['data'], reverse=True)
    return itens[:limit]


@app.route('/')
def home():
    alertas_vencimento = listar_vencimentos_dashboard()
    casos_recentes = listar_casos_recentes_dashboard()

    grupos = {
        'criticos': [],
        'pendentes': [],
        'novos_alertas': []
    }

    for item in alertas_vencimento:
        nome = (item.get('cliente') or '').strip()
        if not nome:
            continue

        dias = int(item.get('dias_restantes', 0) or 0)
        registro = {
            'nome': nome,
            'data': item.get('data_vencimento'),
            'dias': dias,
            'numero': item.get('numeroProcesso') or ''
        }

        if dias <= 3:
            grupos['criticos'].append(registro)
        elif dias <= 7:
            grupos['pendentes'].append(registro)
        else:
            grupos['novos_alertas'].append(registro)

    for chave in grupos:
        grupos[chave] = sorted(grupos[chave], key=lambda r: (r['data'] or '9999-12-31', r['nome']))

    resumo_grupos = [
        {'key': 'criticos', 'label': 'críticos', 'color': 'gold', 'itens': grupos['criticos']},
        {'key': 'pendentes', 'label': 'pendentes', 'color': 'amber', 'itens': grupos['pendentes']},
        {'key': 'novos_alertas', 'label': 'novos alertas', 'color': 'blue', 'itens': grupos['novos_alertas']}
    ]

    clientes_lista = sorted(clientes, key=lambda item: (item.get('nome') or '').lower())

    return render_template(
        'menu.html',
        advogado_nome=session.get('advogado_nome'),
        alertas_vencimento=alertas_vencimento,
        casos_recentes=casos_recentes,
        total_clientes=len(clientes),
        clientes_vencendo_hoje=sum(1 for item in alertas_vencimento if item['dias_restantes'] <= 0),
        processos_vencendo_hoje=sum(1 for item in alertas_vencimento if item['tipo'] == 'processo' and item['dias_restantes'] <= 0),
        resumo_grupos=resumo_grupos,
        clientes_lista=clientes_lista,
    )


@app.route('/home')
def home_legacy():
    return redirect(url_for('home'))


@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        data_vencimento = request.form.get('dataVencimentoProcesso', '').strip()
        prazo_dias = request.form.get('prazoDiasUteis', '').strip()
        cliente = {
            'nome': request.form['nome'],
            'cpf': request.form['cpf'],
            'rg': request.form['rg'],
            'telefone': request.form['telefone'],
            'cep': request.form['cep'],
            'endereco': request.form['endereco'],
            'bairro': request.form['bairro'],
            'cidade': request.form['cidade'],
            'email': request.form['email'],
            'tipoCaso': request.form['tipoCaso'],
            'numeroProcesso': request.form['numeroProcesso'],
            'observacoes': request.form['observacoes'],
            'dataVencimentoProcesso': data_vencimento,
            'prazoDiasUteis': int(prazo_dias) if prazo_dias else '',
            'dataCadastro': datetime.now().date().isoformat()
        }
        clientes.append(cliente)
        salvar_clientes(clientes)
        salvar_aviso_processo(cliente)
        return redirect(url_for('lista'))
    return render_template('cadastro.html')


@app.route('/cadastro_legacy')
def cadastro_legacy():
    return redirect(url_for('cadastro'))


@app.route('/lista')
def lista():
    return render_template('lista.html', clientes=clientes)


@app.route('/consulta', methods=['GET', 'POST'])
def consulta():
    resultado = []
    if request.method == 'POST':
        termo = (request.form.get('termo') or '').strip()
        resultado = [
            c for c in clientes
            if termo.lower() in (c.get('nome', '') or '').lower() or termo in (c.get('cpf', '') or '')
        ]
    return render_template('consulta.html', resultado=resultado, clientes=clientes)


@app.route('/calendario', methods=['GET', 'POST'])
def calendario():
    if request.method == 'POST':
        pass
    return render_template('calendario.html', eventos=eventos, clientes=clientes)


@app.route('/honorarios')
def honorarios():
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()
    registros = listar_honorarios_receber(data_inicio or None, data_fim or None)
    total_honorarios = sum(item['valor'] for item in registros)
    chart_data = montar_grafico_honorarios(registros)
    return render_template(
        'honorarios.html',
        honorarios=registros,
        total_honorarios=total_honorarios,
        total_honorarios_formatado=f'R$ {total_honorarios:,.2f}',
        total_clientes=len({item['cliente'] for item in registros}),
        chart_data=chart_data,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@app.route('/toggle_honorario_status', methods=['POST'])
def toggle_honorario_status():
    dados = request.get_json() or {}
    date_key = dados.get('dateKey')
    index = dados.get('index')
    novo_status = dados.get('status')

    if not date_key or index is None or not novo_status:
        return {'status': 'erro', 'mensagem': 'Dados insuficientes'}, 400

    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        return {'status': 'erro', 'mensagem': 'Calendário não encontrado'}, 404

    if isinstance(avisos, dict):
        lista = avisos.get(date_key, [])
        if isinstance(index, int) and 0 <= index < len(lista):
            lista[index]['status'] = novo_status
            avisos[date_key] = lista
            with open('avisos.json', 'w', encoding='utf-8') as f:
                json.dump(avisos, f, ensure_ascii=False, indent=2)
            return {'status': 'ok'}
    elif isinstance(avisos, list):
        if isinstance(index, int) and 0 <= index < len(avisos):
            avisos[index]['status'] = novo_status
            with open('avisos.json', 'w', encoding='utf-8') as f:
                json.dump(avisos, f, ensure_ascii=False, indent=2)
            return {'status': 'ok'}

    return {'status': 'erro', 'mensagem': 'Registro não encontrado'}, 404


@app.route('/editar/<int:idx>', methods=['GET', 'POST'])
def editar_cliente(idx):
    if idx < 0 or idx >= len(clientes):
        return 'Cliente não encontrado', 404
    if request.method == 'POST':
        clientes[idx]['nome'] = request.form['nome']
        clientes[idx]['cpf'] = request.form['cpf']
        clientes[idx]['rg'] = request.form['rg']
        clientes[idx]['telefone'] = request.form['telefone']
        clientes[idx]['cep'] = request.form['cep']
        clientes[idx]['endereco'] = request.form['endereco']
        clientes[idx]['bairro'] = request.form['bairro']
        clientes[idx]['cidade'] = request.form['cidade']
        clientes[idx]['email'] = request.form['email']
        clientes[idx]['tipoCaso'] = request.form['tipoCaso']
        clientes[idx]['numeroProcesso'] = request.form['numeroProcesso']
        clientes[idx]['observacoes'] = request.form['observacoes']
        clientes[idx]['dataVencimentoProcesso'] = request.form.get('dataVencimentoProcesso', '')
        prazo = request.form.get('prazoDiasUteis', '').strip()
        clientes[idx]['prazoDiasUteis'] = int(prazo) if prazo else ''
        salvar_clientes(clientes)
        salvar_aviso_processo(clientes[idx])
        return redirect(url_for('lista'))
    return render_template('editar.html', cliente=clientes[idx], idx=idx)


@app.route('/excluir/<int:idx>', methods=['POST'])
def excluir_cliente(idx):
    if idx < 0 or idx >= len(clientes):
        return 'Cliente não encontrado', 404
    clientes.pop(idx)
    salvar_clientes(clientes)
    return redirect(url_for('lista'))


@app.route('/registrar_acompanhamento', methods=['POST'])
def registrar_acompanhamento():
    novo = request.get_json()
    if not isinstance(novo, dict):
        return {'status': 'erro', 'mensagem': 'Payload inválido'}, 400
    try:
        with open('acompanhamento.json', 'r', encoding='utf-8') as f:
            lista = json.load(f)
    except FileNotFoundError:
        lista = []
    lista.append(novo)
    with open('acompanhamento.json', 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

    data_final = novo.get('data_final')
    data_final_iso = normalizar_data_calendario(data_final)
    if data_final_iso:
        aviso = {
            'cliente': novo.get('partes') or novo.get('assunto') or 'Processo',
            'numeroProcesso': novo.get('numero'),
            'numero': novo.get('numero'),
            'data_final': data_final_iso,
            'dateKey': data_final_iso,
            'prazo': novo.get('prazo'),
            'tipo': 'processo',
            'assunto': novo.get('assunto'),
            'partes': novo.get('partes'),
            'ultima_movimentacao': novo.get('ultima_movimentacao'),
            'observacao': 'Prazo de processo registrado'
        }
        try:
            with open('avisos.json', 'r', encoding='utf-8') as f:
                avisos = json.load(f)
        except FileNotFoundError:
            avisos = {}
        avisos.setdefault(data_final_iso, []).append(aviso)
        with open('avisos.json', 'w', encoding='utf-8') as f:
            json.dump(avisos, f, ensure_ascii=False, indent=2)
    return {'status': 'ok'}


@app.route('/avisos', methods=['GET'])
def mostrar_avisos():
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        avisos = {}
    return render_template('avisos.html', avisos=avisos)


@app.route('/avisos/<data>', methods=['GET'])
def mostrar_avisos_por_data(data):
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        avisos = {}
    return jsonify(avisos.get(data, []))


@app.route('/add_aviso', methods=['POST'])
def add_aviso():
    data = request.get_json() or {}
    dateKey = data.get('dateKey')
    aviso = data.get('aviso')
    if not dateKey or not aviso:
        return {'status': 'erro', 'mensagem': 'Dados de aviso inválidos'}, 400
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        avisos = {}
    avisos.setdefault(dateKey, []).append(aviso)
    with open('avisos.json', 'w', encoding='utf-8') as f:
        json.dump(avisos, f, ensure_ascii=False, indent=2)
    return {'status': 'ok'}


@app.route('/get_avisos')
def get_avisos():
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
    except FileNotFoundError:
        avisos = {}
    return jsonify(avisos)


@app.route('/editar_aviso', methods=['POST'])
def editar_aviso():
    data = request.get_json() or {}
    dateKey = data.get('dateKey')
    idx = data.get('idx')
    novo_aviso = data.get('aviso')
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
        if dateKey in avisos and isinstance(idx, int) and 0 <= idx < len(avisos[dateKey]):
            avisos[dateKey][idx] = novo_aviso
            with open('avisos.json', 'w', encoding='utf-8') as f:
                json.dump(avisos, f, ensure_ascii=False, indent=2)
            return {'status': 'ok'}
        return {'status': 'erro', 'msg': 'Aviso não encontrado'}, 404
    except Exception as e:
        return {'status': 'erro', 'msg': str(e)}, 500


@app.route('/excluir_aviso', methods=['POST'])
def excluir_aviso():
    data = request.get_json() or {}
    dateKey = data.get('dateKey')
    idx = data.get('idx')
    try:
        with open('avisos.json', 'r', encoding='utf-8') as f:
            avisos = json.load(f)
        if dateKey in avisos and isinstance(idx, int) and 0 <= idx < len(avisos[dateKey]):
            avisos[dateKey].pop(idx)
            if not avisos[dateKey]:
                avisos.pop(dateKey)
            with open('avisos.json', 'w', encoding='utf-8') as f:
                json.dump(avisos, f, ensure_ascii=False, indent=2)
            return {'status': 'ok'}
        return {'status': 'erro', 'msg': 'Aviso não encontrado'}, 404
    except Exception as e:
        return {'status': 'erro', 'msg': str(e)}, 500


@app.route('/listar_acompanhamento')
def listar_acompanhamento():
    try:
        with open('acompanhamento.json', 'r', encoding='utf-8') as f:
            lista = json.load(f)
    except FileNotFoundError:
        lista = []
    return jsonify(lista)


@app.route('/excluir_acompanhamento', methods=['POST'])
def excluir_acompanhamento():
    data = request.get_json() or {}
    try:
        with open('acompanhamento.json', 'r', encoding='utf-8') as f:
            lista = json.load(f)
        lista = [proc for proc in lista if proc.get('numero') != data.get('numero')]
        with open('acompanhamento.json', 'w', encoding='utf-8') as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'erro', 'erro': str(e)}, 500


@app.route('/editar_acompanhamento', methods=['POST'])
def editar_acompanhamento():
    novo = request.get_json() or {}
    try:
        with open('acompanhamento.json', 'r', encoding='utf-8') as f:
            lista = json.load(f)
        for i, proc in enumerate(lista):
            if proc.get('numero') == novo.get('numero'):
                lista[i].update(novo)
                break
        with open('acompanhamento.json', 'w', encoding='utf-8') as f:
            json.dump(lista, f, ensure_ascii=False, indent=2)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'erro', 'erro': str(e)}, 500


@app.route('/consulta_oab', methods=['POST'])
def consulta_oab():
    dados = request.get_json() or {}
    oab = (dados.get('oab') or '').strip()
    if not oab:
        return jsonify([])
    processos = buscar_processos_oab_esaj(oab)
    return jsonify(processos)


@app.route('/consulta_oab_async', methods=['POST'])
def consulta_oab_async():
    dados = request.get_json() or {}
    oab = (dados.get('oab') or '').strip()
    if not oab:
        return jsonify({'status': 'erro', 'mensagem': 'OAB obrigatória'})
    return jsonify({'status': 'ok', 'task_id': 'simulado'})


@app.route('/consulta_resultado/<task_id>')
def consulta_resultado(task_id):
    return jsonify({'status': 'ok', 'task_id': task_id, 'processos': []})


@app.route('/consulta_resultado_oab/<oab>')
def consulta_resultado_oab(oab):
    return jsonify([])


@app.before_request
def require_login():
    public_endpoints = {'login', 'cadastro_advogado', 'static'}
    if request.endpoint in public_endpoints:
        return None
    if not session.get('advogado_id'):
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    erro = None
    if request.method == 'POST':
        login_digitado = request.form.get('login', '').strip()
        senha = request.form.get('senha', '')
        advogado = next((a for a in advogados if a['login'].lower() == login_digitado.lower()), None)

        if advogado and check_password_hash(advogado['senha_hash'], senha):
            session.clear()
            session['advogado_id'] = advogado['id']
            session['advogado_nome'] = advogado['nome']
            session['advogado_oab'] = advogado['oab']
            return redirect(url_for('home'))

        erro = 'Login ou senha inválidos.'

    return render_template('login.html', erro=erro)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/cadastro_advogado', methods=['GET', 'POST'])
def cadastro_advogado():
    erro = None
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        oab = request.form.get('oab', '').strip()
        login = request.form.get('login', '').strip()
        senha = request.form.get('senha', '').strip()

        if not nome or not oab or not login or not senha:
            erro = 'Preencha nome, OAB, login e senha.'
        elif any(a['oab'].upper() == oab.upper() for a in advogados):
            erro = 'Já existe um advogado cadastrado com esta OAB.'
        elif any(a['login'].lower() == login.lower() for a in advogados):
            erro = 'Este login já está em uso.'
        else:
            advogados.append({
                'id': len(advogados) + 1,
                'nome': nome,
                'oab': oab,
                'login': login,
                'senha_hash': generate_password_hash(senha)
            })
            salvar_advogados(advogados)
            return redirect(url_for('login'))

    return render_template('cadastro_advogado.html', erro=erro)


@celery.task
def consulta_esaj_oab_task(oab):
    url = f"https://esaj.tjsp.jus.br/cpopg/search.do?conversationId=&cbPesquisa=OAB&numeroOAB={oab}&pesquisar=Pesquisar"
    session_req = requests.Session()
    resp = session_req.get(url)
    soup = BeautifulSoup(resp.text, 'html.parser')
    processos = []
    for link in soup.select('.linkProcesso'):
        processo_url = 'https://esaj.tjsp.jus.br' + link['href']
        processo_resp = session_req.get(processo_url)
        processo_soup = BeautifulSoup(processo_resp.text, 'html.parser')
        movimentacoes = []
        for mov in processo_soup.select('.containerMovimentacoes .movimentacao'):
            data_tag = mov.select_one('.dataMovimentacao')
            desc_tag = mov.select_one('.descricaoMovimentacao')
            if not data_tag or not desc_tag:
                continue
            movimentacoes.append({
                'data': data_tag.text.strip(),
                'descricao': desc_tag.text.strip(),
            })
        processos.append({
            'numero': link.text.strip(),
            'ultima_movimentacao': movimentacoes[0] if movimentacoes else {},
            'movimentacoes': movimentacoes,
        })
    with open(f'dados_oab_{oab}.json', 'w', encoding='utf-8') as f:
        json.dump(processos, f, ensure_ascii=False, indent=2)
    return processos


def extrair_movimentacoes_esaj(driver):
    titulos = [
        'Petições diversas',
        'Incidentes, ações incidentais, recursos e execuções de sentenças',
        'Audiências',
        'Apensos, Entranhados e Unificados',
    ]
    movimentacoes = []
    for titulo in titulos:
        try:
            h2 = driver.find_element(By.XPATH, f"//h2[contains(@class, 'tituloDoBloco') and contains(text(), '{titulo}')]")
            tabela = h2.find_element(By.XPATH, "following-sibling::table[1]")
            linhas = tabela.find_elements(By.XPATH, './/tr')
            for linha in linhas:
                tds = linha.find_elements(By.TAG_NAME, 'td')
                if len(tds) >= 2:
                    data = tds[0].text.strip()
                    descricao = tds[1].text.strip()
                    if data or descricao:
                        movimentacoes.append({'bloco': titulo, 'data': data, 'descricao': descricao})
        except Exception:
            continue
    return movimentacoes


def buscar_processos_oab_esaj(oab):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--log-level=3')
    try:
        driver = webdriver.Chrome(options=options)
    except Exception:
        return []

    url = f"https://esaj.tjsp.jus.br/cpopg/search.do?conversationId=&cbPesquisa=NUMOAB&dadosConsulta.valorConsulta={oab}&cdForo=-1"
    driver.get(url)
    time.sleep(2)

    processos = []
    try:
        cards = driver.find_elements(By.CSS_SELECTOR, 'div.row.unj-ai-c.home__lista-de-processos')
        for div in cards:
            numero = div.find_element(By.CSS_SELECTOR, 'a.linkProcesso').text.strip()
            link = div.find_element(By.CSS_SELECTOR, 'a.linkProcesso').get_attribute('href')
            if not link:
                continue
            driver.execute_script('window.open(arguments[0]);', link)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(1)
            try:
                assunto = driver.find_element(By.ID, 'assuntoProcesso').text.strip()
            except Exception:
                assunto = ''
            partes = []
            try:
                linhas = driver.find_elements(By.CSS_SELECTOR, '#tablePartesPrincipais tbody tr')
                for linha in linhas:
                    nome = linha.find_element(By.CSS_SELECTOR, '.nomeParteEAdvogado').text.strip()
                    tipo = linha.find_element(By.CSS_SELECTOR, '.label').text.strip()
                    partes.append(f'{tipo}: {nome}')
            except Exception:
                partes = []
            try:
                linha = driver.find_element(By.CSS_SELECTOR, '#tabelaUltimasMovimentacoes tr')
                data = linha.find_element(By.CSS_SELECTOR, '.dataMovimentacao').text.strip()
                descricao = linha.find_element(By.CSS_SELECTOR, '.descricaoMovimentacao').text.strip()
                ultima_mov = f'{data} - {descricao}'
            except Exception:
                ultima_mov = ''
            movimentacoes = extrair_movimentacoes_esaj(driver)
            peticoes = [m['descricao'] for m in movimentacoes if 'Petições' in m['bloco']]
            incidentes = [m['descricao'] for m in movimentacoes if 'Incidentes' in m['bloco']]
            apenso = [m['descricao'] for m in movimentacoes if 'Apensos' in m['bloco']]
            audiencia = [m['descricao'] for m in movimentacoes if 'Audiências' in m['bloco']]
            processos.append({
                'numero': numero,
                'assunto': assunto,
                'partes': ' | '.join(partes),
                'ultima_movimentacao': ultima_mov,
                'peticoes': ' | '.join(peticoes),
                'incidentes_recursos_sentenca': ' | '.join(incidentes),
                'apenso': ' | '.join(apenso),
                'audiencia': ' | '.join(audiencia),
            })
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
    except Exception:
        pass
    driver.quit()
    return processos


if __name__ == '__main__':
    app.run(debug=True)
