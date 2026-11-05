"""Testes: python -m unittest -v test_pipeline.py

Não exige a base original da DIO para executar.
"""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from pipeline_tratamento import (
    MASK, carregar_contrato, ler_xlsx_padrao, ler_entrada, normalizar_data,
    normalizar_milhas, normalizar_preco, normalizar_ano, normalizar_entrega,
    transformar, executar,
)

ROOT = Path(__file__).resolve().parent
HEADERS = ['sale_id','sale_date','customer_name','porsche_model','model_year','sale_price',
           'vehicle_mileage','payment_method','city','state','salesperson','delivery_status']
SAMPLE = [
 [6,'2024-02-30','Cliente Ficticio Alpha','718 Cayman',2022,'$79,500.00','9,800 miles','Credit card','boston','ma','Vendedor Ficticio R','delivered'],
 [7,'03/14/2024','Cliente Ficticio Beta','911 Turbo S','twenty twenty four','235000 USD','16093.44 km','wire transfer','Seattle','Washington','Vendedor Ficticio Q','DELIVERD'],
 [8,'2027-05-27','Cliente Ficticio Alpha','Taycan 4S',2024,'$121k',9.5,'bank-transfer','los angeles','ca','Vendedor Ficticio R','delivered!!!'],
]

class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = carregar_contrato(ROOT/'schema.md')

    def test_preco(self):
        self.assertEqual(normalizar_preco('$121k')[0], 121000.0)
        self.assertEqual(normalizar_preco('USD 112.750')[0], 112750.0)
        self.assertEqual(normalizar_preco('89.750,00')[0], 89750.0)

    def test_datas(self):
        self.assertEqual(normalizar_data('2024-02-30'), (None,'DATA_INVALIDA'))
        self.assertEqual(normalizar_data('03/14/2024')[0], '2024-03-14')
        self.assertEqual(normalizar_data(45434)[0], '2024-05-22')

    def test_ano_status_milhas(self):
        self.assertEqual(normalizar_ano('twenty twenty four')[0], 2024)
        self.assertEqual(normalizar_entrega('DELIVERD')[0], 'Delivered')
        self.assertEqual(normalizar_milhas(9.5)[0], 9.5)
        self.assertEqual(normalizar_milhas('16.09344 km')[0], 10.0)

    @unittest.skipUnless((ROOT/'exedio.xlsx').is_file(), 'Base bruta privada não incluída no GitHub')
    def test_leitura_xlsx_local_opcional(self):
        headers, rows = ler_entrada(ROOT/'exedio.xlsx')
        fallback = ler_xlsx_padrao(ROOT/'exedio.xlsx', 0)
        self.assertEqual(fallback[0], headers)
        self.assertEqual(len(fallback)-1, len(rows))

    def test_intercalacao_integridade_privacidade(self):
        names, public, audit, m = transformar(HEADERS, SAMPLE, self.contract)
        self.assertEqual(len(public), 3)
        self.assertEqual(len(names), 27)
        self.assertEqual(m['datas_invalidas'], 1)
        self.assertEqual(m['datas_futuras'], 1)
        self.assertEqual(m['km_convertidos'], 1)
        self.assertEqual(m['linhas_revisar'], 1)
        for i, h in enumerate(HEADERS):
            self.assertEqual(names[2*i], h+'_fonte')
            self.assertEqual(names[2*i+1], h+'_tratado')
        for row in public:
            for h in ('sale_id','customer_name','salesperson'):
                self.assertEqual(row[names.index(h+'_fonte')], MASK)
        self.assertEqual(public[2][names.index('sale_price_tratado')], 121000.0)
        self.assertEqual(public[2][names.index('vehicle_mileage_tratado')], 9.5)
        self.assertEqual(public[0][names.index('customer_name_tratado')],
                         public[2][names.index('customer_name_tratado')])
        serialized = json.dumps([public,audit],ensure_ascii=False)
        for forbidden in ['Cliente Ficticio Alpha','Cliente Ficticio Beta','Vendedor Ficticio Q','Vendedor Ficticio R']:
            self.assertNotIn(forbidden, serialized)

    def test_saida_csv_e_arquivos(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)/'origem.csv'
            out = Path(tmp)/'publico'
            with raw.open('w',encoding='utf-8',newline='') as f:
                w = csv.writer(f)
                w.writerow(HEADERS)
                w.writerows(SAMPLE)
            m = executar(raw, ROOT/'schema.md', out)
            self.assertEqual(m['registros'], 3)
            with (out/'dados_intercalados_publicos.csv').open(encoding='utf-8-sig',newline='') as f:
                r = list(csv.DictReader(f))
            self.assertEqual(len(r), 3)
            self.assertEqual(r[0]['customer_name_fonte'], MASK)
            self.assertTrue((out/'metricas_qualidade.json').exists())

    def test_esquema_nao_autoriza_divulgar_pessoas(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'schema.md'
            s = (ROOT/'schema.md').read_text(encoding='utf8')
            p.write_text(s.replace('"source":"customer_name","normalizer":"person_customer","privacy":"suppress"',
                                   '"source":"customer_name","normalizer":"person_customer","privacy":"public"'),encoding='utf8')
            with self.assertRaises(ValueError):
                carregar_contrato(p)

if __name__ == '__main__':
    unittest.main()
