from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import os
#from celery import Celery
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

app = Flask(__name__, template_folder='../templates', static_folder='../static')


# Configurações do banco de dados
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///acompanhamento.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

ACOMP_FILE = 'acompanhamento.json'
CALENDARIO_FILE = 'calendario_avisos.json'

class Processo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    descricao = db.Column(db.String(200))
    prazo_final = db.Column(db.String(20))  # ou Date

    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'descricao': self.descricao,
            'prazo_final': self.prazo_final
        }

class Aviso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.String(10), nullable=False)  # formato 'YYYY-MM-DD'
    cliente = db.Column(db.String(100), nullable=False)
    parcela = db.Column(db.String(10), nullable=False)
    valor_parcela = db.Column(db.String(20), nullable=False)
    valor_total = db.Column(db.String(20), nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'data': self.data,
            'cliente': self.cliente,
            'parcela': self.parcela,
            'valorParcela': self.valor_parcela,
            'valorTotal': self.valor_total
        }

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    rg = db.Column(db.String(20), nullable=False)
    telefone = db.Column(db.String(20))
    cep = db.Column(db.String(20))
    endereco = db.Column(db.String(200))
    bairro = db.Column(db.String(100))
    cidade = db.Column(db.String(100))
    email = db.Column(db.String(100))
    tipoCaso = db.Column(db.String(50))
    numeroProcesso = db.Column(db.String(50))
    observacoes = db.Column(db.Text)

def carregar_acompanhamento():
    if os.path.exists(ACOMP_FILE):
        with open(ACOMP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def salvar_acompanhamento(lista):
    with open(ACOMP_FILE, 'w', encoding='utf-8') as f:
        json.dump(lista, f, ensure_ascii=False, indent=2)

clientes = []

eventos = []
processos = []  # Adicionado para armazenar processos

@app.route('/')
def home():
    total_clientes = len(clientes)
    clientes_vencendo_hoje = [c for c in clientes if c.get('vencimento') == datetime.today().date()]
    qtd_clientes_vencendo_hoje = len(clientes_vencendo_hoje)
    valor_dia = sum(c.get('valor', 0) for c in clientes_vencendo_hoje)
    valor_total_clientes = sum(c.get('valor', 0) for c in clientes)
    processos_vencendo_hoje = [p for p in processos if p.get('prazo_final') == datetime.today().date()]
    qtd_processos_vencendo_hoje = len(processos_vencendo_hoje)
    total_processos = len(processos)
    return render_template(
        'menu.html',
        total_clientes=total_clientes,
        qtd_clientes_vencendo_hoje=qtd_clientes_vencendo_hoje,
        valor_dia=valor_dia,
        valor_total_clientes=valor_total_clientes,
        qtd_processos_vencendo_hoje=qtd_processos_vencendo_hoje,
        total_processos=total_processos
    )

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        cliente = Cliente(
            nome=request.form['nome'],
            cpf=request.form['cpf'],
            rg=request.form['rg'],
            telefone=request.form['telefone'],
            cep=request.form['cep'],
            endereco=request.form['endereco'],
            bairro=request.form['bairro'],
            cidade=request.form['cidade'],
            email=request.form['email'],
            tipoCaso=request.form['tipoCaso'],
            numeroProcesso=request.form['numeroProcesso'],
            observacoes=request.form['observacoes']
        )
        db.session.add(cliente)
        db.session.commit()
        return redirect(url_for('lista'))
    return render_template('cadastro.html')

@app.route('/consulta', methods=['GET', 'POST'])
def consulta():
    try:
        with open('processos.json', 'r', encoding='utf-8') as f:
            processos = json.load(f)
    except FileNotFoundError:
        processos = []
    return render_template('consulta.html', processos=processos)

@app.route('/calendario', methods=['GET', 'POST'])
def calendario():
    clientes = Cliente.query.all()
    return render_template('calendario.html', clientes=clientes)

@app.route('/lista')
def lista():
    clientes = Cliente.query.all()
    return render_template('lista.html', clientes=clientes)

@app.route('/menu')
def menu():
    return render_template('menu.html')

@app.route('/totais')
def totais():
    total_clientes = len(clientes)
    clientes_vencendo_hoje = [c for c in clientes if c.get('vencimento') == datetime.today().date()]
    qtd_clientes_vencendo_hoje = len(clientes_vencendo_hoje)
    valor_dia = sum(c.get('valor', 0) for c in clientes_vencendo_hoje)
    valor_total_clientes = sum(c.get('valor', 0) for c in clientes)
    processos_vencendo_hoje = [p for p in processos if p.get('prazo_final') == datetime.today().date()]
    qtd_processos_vencendo_hoje = len(processos_vencendo_hoje)
    total_processos = len(processos)
    return jsonify({
        'total_clientes': total_clientes,
        'qtd_clientes_vencendo_hoje': qtd_clientes_vencendo_hoje,
        'valor_dia': valor_dia,
        'valor_total_clientes': valor_total_clientes,
        'qtd_processos_vencendo_hoje': qtd_processos_vencendo_hoje,
        'total_processos': total_processos
    })

@app.route('/registrar_acompanhamento', methods=['POST'])
def registrar_acompanhamento():
    data = request.get_json()
    proc = Processo(
        numero=data['numero'],
        descricao=data.get('descricao', ''),
        prazo_final=data.get('prazo_final', '')
    )
    db.session.add(proc)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/listar_acompanhamento')
def listar_acompanhamento():
    processos = Processo.query.all()
    return jsonify([p.to_dict() for p in processos])

@app.route('/excluir_acompanhamento', methods=['POST'])
def excluir_acompanhamento():
    data = request.get_json()
    proc = Processo.query.filter_by(numero=data['numero']).first()
    if proc:
        db.session.delete(proc)
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/editar_acompanhamento', methods=['POST'])
def editar_acompanhamento():
    data = request.get_json()
    proc = Processo.query.filter_by(numero=data['numero']).first()
    if proc:
        proc.descricao = data.get('descricao', proc.descricao)
        proc.prazo_final = data.get('prazo_final', proc.prazo_final)
        db.session.commit()
    return jsonify({'ok': True})

@app.route('/get_avisos')
def get_avisos():
    avisos = Aviso.query.all()
    resultado = {}
    for aviso in avisos:
        if aviso.data not in resultado:
            resultado[aviso.data] = []
        resultado[aviso.data].append(aviso.to_dict())
    return jsonify(resultado)

@app.route('/add_aviso', methods=['POST'])
def add_aviso():
    data = request.get_json()
    dateKey = data['dateKey']
    aviso = data['aviso']
    novo_aviso = Aviso(
        data=dateKey,
        cliente=aviso['cliente'],
        parcela=aviso['parcela'],
        valor_parcela=aviso['valorParcela'],
        valor_total=aviso['valorTotal']
    )
    db.session.add(novo_aviso)
    db.session.commit()
    return jsonify({'ok': True})

@app.route('/editar_cliente/<int:idx>', methods=['GET', 'POST'])
def editar_cliente(idx):
    cliente = Cliente.query.get_or_404(idx)
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.cpf = request.form['cpf']
        cliente.rg = request.form['rg']
        cliente.telefone = request.form['telefone']
        cliente.cep = request.form['cep']
        cliente.endereco = request.form['endereco']
        cliente.bairro = request.form['bairro']
        cliente.cidade = request.form['cidade']
        cliente.email = request.form['email']
        cliente.tipoCaso = request.form['tipoCaso']
        cliente.numeroProcesso = request.form['numeroProcesso']
        cliente.observacoes = request.form['observacoes']
        db.session.commit()
        return redirect(url_for('lista'))
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/excluir_cliente/<int:idx>', methods=['POST'])
def excluir_cliente(idx):
    cliente = Cliente.query.get_or_404(idx)
    db.session.delete(cliente)
    db.session.commit()
    return redirect(url_for('lista'))

@app.route('/consulta_oab', methods=['POST'])
def consulta_oab():
    data = request.get_json()
    oab = data.get('oab')
    processos = []

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        url = "https://esaj.tjsp.jus.br/cpopg/open.do"
        driver.get(url)
        print("Página carregada")
        time.sleep(2)

        driver.find_element(By.ID, "cbPesquisa").send_keys("OAB")
        print("Selecionou OAB")
        time.sleep(1)

        campo_oab = driver.find_element(By.ID, "campo_NUMOAB")
        print("Campo OAB encontrado")
        campo_oab.clear()
        campo_oab.send_keys(oab)
        time.sleep(1)

        driver.find_element(By.ID, "botaoConsultarProcessos").click()
        print("Clicou em consultar")

        # Aguarda os resultados
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".home__lista-de-processos"))
        )
        print("Resultados carregados")

        processos_rows = driver.find_elements(By.CSS_SELECTOR, ".home__lista-de-processos")
        for row in processos_rows:
            numero = row.find_element(By.CSS_SELECTOR, ".nuProcesso .linkProcesso").text.strip()
            classe = row.find_element(By.CSS_SELECTOR, ".classeProcesso").text.strip()
            assunto = row.find_element(By.CSS_SELECTOR, ".assuntoPrincipalProcesso").text.strip()
            recebido_em = row.find_element(By.CSS_SELECTOR, ".dataLocalDistribuicaoProcesso").text.strip()
            try:
                advogado = row.find_element(By.CSS_SELECTOR, ".nomeParte").text.strip()
            except:
                advogado = ""

            # Pega o link do processo (URL absoluta)
            link_rel = row.find_element(By.CSS_SELECTOR, ".nuProcesso .linkProcesso").get_attribute("href")
            if link_rel.startswith("http"):
                link = link_rel
            else:
                link = "https://esaj.tjsp.jus.br" + link_rel

            # Abre o link em uma nova aba e aguarda o carregamento
            driver.execute_script("window.open(arguments[0]);", link)
            driver.switch_to.window(driver.window_handles[1])
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".tituloDoBloco"))
            )
            time.sleep(1)  # Pequeno delay extra

            # --- PARTES DO PROCESSO ---
            try:
                partes = []
                linhas_partes = driver.find_elements(By.CSS_SELECTOR, "#tabelaPartesPrincipais tbody tr")
                for linha in linhas_partes:
                    try:
                        tipo = linha.find_element(By.CSS_SELECTOR, ".tipoDeParticipacao").text.strip()
                    except:
                        tipo = ""
                    try:
                        label = linha.find_element(By.CSS_SELECTOR, ".nomeParteAdvogado").text.strip()
                    except:
                        label = ""
                    if tipo or label:
                        partes.append(f"{tipo} {label}".strip())
                partes_texto = " | ".join([p for p in partes if p])
            except Exception as e:
                print("Erro ao buscar partes:", e)
                partes_texto = ""

            # --- ÚLTIMA MOVIMENTAÇÃO ---
            try:
                # Tenta pelo ID padrão
                try:
                    linha_mov = driver.find_element(By.CSS_SELECTOR, "#tabelaTodasMovimentacoes tbody tr")
                except:
                    # Busca qualquer tr que tenha .dataMovimentacao
                    linha_mov = driver.find_element(By.XPATH, "//tr[td[contains(@class, 'dataMovimentacao')]]")
                data_ultima = linha_mov.find_element(By.CSS_SELECTOR, ".dataMovimentacao").text.strip()
                try:
                    descricao_ultima = linha_mov.find_element(By.CSS_SELECTOR, ".descricaoMovimentacao").text.strip()
                    # Corrige se vier undefined ou vazio
                    if not descricao_ultima or descricao_ultima.lower() == "undefined":
                        descricao_ultima = ""
                except:
                    # Se não houver classe, pega o texto da última célula
                    descricao_ultima = linha_mov.find_elements(By.TAG_NAME, "td")[-1].text.strip()
                    if not descricao_ultima or descricao_ultima.lower() == "undefined":
                        descricao_ultima = ""
                # Monta a string final corretamente
                if descricao_ultima:
                    ultima_movimentacao = f"{data_ultima} - {descricao_ultima}"
                else:
                    ultima_movimentacao = data_ultima
            except Exception as e:
                print("Erro ao buscar última movimentação:", e)
                ultima_movimentacao = ""

            # --- PETIÇÕES ---
            try:
                peticoes = []
                tabelas = driver.find_elements(By.XPATH, "//h2[contains(text(),'petições') or contains(text(),'Petição')]/following-sibling::table[1]")
                for tabela in tabelas:
                    linhas_pet = tabela.find_elements(By.TAG_NAME, "tr")
                    for linha in linhas_pet:
                        texto = linha.text.strip()
                        if texto:
                            peticoes.append(texto)
                peticoes_texto = " | ".join(peticoes)
            except Exception as e:
                peticoes_texto = ""

            # --- INCIDENTES, RECURSOS, SENTENÇA ---
            try:
                incidentes = ""
                try:
                    incidentes = driver.find_element(By.ID, "processoSemIncidentes").text.strip()
                except:
                    # Se não existir o ID, tente buscar por texto
                    incidentes = driver.find_element(By.XPATH, "//td[contains(text(),'incidentes')]").text.strip()
            except:
                incidentes = ""
            try:
                sentenca = driver.find_element(By.XPATH, "//td[contains(text(),'sentenças vinculados')]").text.strip()
            except:
                sentenca = ""

            # --- APENSO ---
            try:
                apenso = driver.find_element(By.XPATH, "//td[contains(text(),'apensados')]").text.strip()
            except:
                apenso = ""

            # --- AUDIÊNCIA ---
            try:
                audiencia = driver.find_element(By.ID, "processoSemAudiencias").text.strip()
            except:
                audiencia = ""

            # --- FECHA A ABA E VOLTA ---
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

            # --- ADICIONA AO RESULTADO ---
            processos.append({
                "numero": numero,
                "classe": classe,
                "assunto": assunto,
                "recebido_em": recebido_em,
                "advogado": advogado,
                "partes": partes_texto,
                "ultima_movimentacao": ultima_movimentacao,
                "peticoes": peticoes_texto,
                "incidentes_recursos_sentenca": incidentes or sentenca,
                "apenso": apenso,
                "audiencia": audiencia
            })
        print("Processos coletados:", len(processos))
    except Exception as e:
        print("Erro ao buscar processos:", e)
    finally:
        driver.quit()

    with open('processos.json', 'w', encoding='utf-8') as f:
        json.dump(processos, f, ensure_ascii=False, indent=2)
    return jsonify(processos)

if __name__ == '__main__':
    app.run(debug=True)