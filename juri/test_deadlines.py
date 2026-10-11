import json
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app import adicionar_dias_uteis, calcular_dias_uteis_entre, listar_vencimentos_dashboard, salvar_aviso_processo, app


class DeadlinesTest(unittest.TestCase):
    def test_adicionar_dias_uteis_skips_weekend(self):
        base = datetime(2026, 10, 5)
        self.assertEqual(adicionar_dias_uteis(base, 2), datetime(2026, 10, 7))

    def test_calcular_dias_uteis_entre(self):
        inicio = datetime(2026, 10, 5)
        fim = datetime(2026, 10, 9)
        self.assertEqual(calcular_dias_uteis_entre(inicio, fim), 3)

    def test_manual_processo_aviso_appears_in_dashboard(self):
        arquivo = Path(__file__).with_name('avisos.json')
        backup = arquivo.read_text(encoding='utf-8') if arquivo.exists() else None
        data_id = (datetime.now().date() + timedelta(days=3)).isoformat()
        try:
            with arquivo.open('w', encoding='utf-8') as f:
                json.dump({
                    data_id: [{
                        'cliente': 'Cliente Teste',
                        'numeroProcesso': '1234567-89.2024.8.26.0000',
                        'processo': '1234567-89.2024.8.26.0000',
                        'tipo': 'processo_manual',
                        'dateKey': data_id,
                    }]
                }, f, ensure_ascii=False)

            itens = listar_vencimentos_dashboard()
            self.assertTrue(any(
                item.get('tipo') == 'processo_manual' and item.get('numeroProcesso') == '1234567-89.2024.8.26.0000'
                for item in itens
            ))
        finally:
            if backup is None:
                if arquivo.exists():
                    arquivo.unlink()
            else:
                with arquivo.open('w', encoding='utf-8') as f:
                    f.write(backup)

    def test_salvar_aviso_processo_registra_no_calendario(self):
        arquivo = Path(__file__).with_name('avisos.json')
        backup = arquivo.read_text(encoding='utf-8') if arquivo.exists() else None
        try:
            if arquivo.exists():
                arquivo.unlink()

            cliente = {
                'nome': 'Cliente Calendario',
                'numeroProcesso': '1234567-89.2024.8.26.0001',
                'dataVencimentoProcesso': '2026-10-15',
                'prazoDiasUteis': 10,
                'observacoes': 'Acompanhamento do processo'
            }

            salvar_aviso_processo(cliente)

            with arquivo.open('r', encoding='utf-8') as f:
                avisos = json.load(f)

            self.assertIn('2026-10-15', avisos)
            self.assertTrue(any(
                item.get('numeroProcesso') == '1234567-89.2024.8.26.0001'
                for item in avisos['2026-10-15']
            ))
        finally:
            if backup is None:
                if arquivo.exists():
                    arquivo.unlink()
            else:
                with arquivo.open('w', encoding='utf-8') as f:
                    f.write(backup)

    def test_registrar_acompanhamento_normaliza_data_para_iso(self):
        arquivo = Path(__file__).with_name('avisos.json')
        backup = arquivo.read_text(encoding='utf-8') if arquivo.exists() else None
        try:
            if arquivo.exists():
                arquivo.unlink()

            cliente = app.test_client()
            response = cliente.post('/registrar_acompanhamento', json={
                'numero': '333333-33.2024.8.26.0000',
                'assunto': 'Teste de consulta',
                'partes': 'Cliente Teste',
                'ultima_movimentacao': 'Sem info',
                'prazo': '15',
                'data_final': '31/12/2026'
            })

            self.assertEqual(response.status_code, 200)
            with arquivo.open('r', encoding='utf-8') as f:
                avisos = json.load(f)
            self.assertIn('2026-12-31', avisos)
            self.assertTrue(any(item.get('numero') == '333333-33.2024.8.26.0000' for item in avisos['2026-12-31']))
        finally:
            if backup is None:
                if arquivo.exists():
                    arquivo.unlink()
            else:
                with arquivo.open('w', encoding='utf-8') as f:
                    f.write(backup)


if __name__ == '__main__':
    unittest.main()
