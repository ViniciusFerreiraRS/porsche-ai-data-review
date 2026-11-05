#!/usr/bin/env python3
"""Pipeline didático Santander/DIO - Porsche AI Data Review.

Lê dados brutos CSV ou XLSX, interpreta as regras executáveis de schema.md,
normaliza cada campo e insere a coluna _tratado imediatamente após _fonte.

SEGURANÇA: o resultado é uma versão para portfólio; nomes e IDs de origem
NUNCA são exportados, nem para auditoria. Códigos são pseudônimos, não anonimização.

Exemplos:
  python pipeline_tratamento.py --entrada dados_brutos/exedio.xlsx --schema schema.md --saida saida
  python pipeline_tratamento.py --entrada dados_brutos/exedio.csv --schema schema.md --saida saida

CSV e JSON são gerados com a biblioteca padrão. Leitura XLSX também possui fallback
via ZIP/XML padrão. A exportação XLSX requer artifact_tool, se instalado.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

SCHEMA_BEGIN = "<!-- PIPELINE_RULES_BEGIN -->"
SCHEMA_END = "<!-- PIPELINE_RULES_END -->"
MASK = "[SUPRIMIDO_LGPD]"

# Tabela postal americana usada como dicionário de domínio.
STATES = {
 'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO',
 'Connecticut':'CT','Delaware':'DE','Florida':'FL','Georgia':'GA','Hawaii':'HI',
 'Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY',
 'Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI',
 'Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE',
 'Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY',
 'North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR',
 'Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD',
 'Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA',
 'West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY','District of Columbia':'DC'
}
STATE_CODES = {k.casefold():v for k,v in STATES.items()}
STATE_CODES.update({v.casefold():v for v in STATES.values()})
WORDS = {'zero':0,'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,
'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'thirteen':13,'fourteen':14,
'fifteen':15,'sixteen':16,'seventeen':17,'eighteen':18,'nineteen':19,'twenty':20,
 'thirty':30,'forty':40,'fifty':50,'sixty':60,'seventy':70,'eighty':80,'ninety':90}


def carregar_contrato(path: Path) -> dict:
    """Agente de contrato: carrega e VALIDA regras declaradas no schema.md."""
    text = path.read_text(encoding='utf-8')
    if SCHEMA_BEGIN not in text or SCHEMA_END not in text:
        raise ValueError('schema.md não contém bloco PIPELINE_RULES_BEGIN/END.')
    body = text.split(SCHEMA_BEGIN,1)[1].split(SCHEMA_END,1)[0]
    match = re.search(r'```json\s*(\{.*?\})\s*```', body, re.S)
    if not match: raise ValueError('Não foi encontrado contrato JSON dentro do schema.md.')
    contract = json.loads(match.group(1))
    rules = contract.get('fields', [])
    if not rules or len({f['source'] for f in rules}) != len(rules):
        raise ValueError('Contrato vazio ou contém nomes de colunas duplicados.')
    known = {'row_code','date','person_customer','text','model_year','price_usd',
             'mileage_mi','payment','city','us_state','person_seller','delivery_status'}
    for rule in rules:
        if rule['normalizer'] not in known: raise ValueError('Regra desconhecida: '+rule['normalizer'])
        if rule.get('privacy') not in ('public','suppress'):
            raise ValueError('Privacidade deve ser public ou suppress: '+rule['source'])
        if rule['source'] in {'sale_id','customer_name','salesperson'} and rule['privacy']!='suppress':
            raise ValueError('Campo protegido não pode ser exportado: '+rule['source'])
    return contract


def ler_xlsx_padrao(path: Path, index_aba: int) -> list[list]:
    """Fallback somente LEITURA de XLSX com biblioteca padrão; não altera o arquivo.

    Lê células de texto/número do formato OOXML (suficiente para a base didática).
    Para formatos avançados de Excel, use artifact_tool.
    """
    ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
        'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
        'p':'http://schemas.openxmlformats.org/package/2006/relationships'}
    with zipfile.ZipFile(path) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            ss=ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in ss.findall('m:si',ns):
                shared.append(''.join(t.text or '' for t in si.findall('.//m:t',ns)))
        root=ET.fromstring(z.read('xl/workbook.xml'))
        sheet_nodes=root.findall('m:sheets/m:sheet',ns)
        if index_aba>=len(sheet_nodes):raise ValueError('Índice de aba inválido no schema.md')
        rid=sheet_nodes[index_aba].get('{'+ns['r']+'}id')
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target=None
        for node in rels:
            if node.get('Id')==rid:target=node.get('Target');break
        if target is None:raise ValueError('Relacionamento da aba não encontrado.')
        sheetpath=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        sheetpath=sheetpath.replace('xl/xl/','xl/')
        root=ET.fromstring(z.read(sheetpath))
        output=[]
        def colindex(colref):
            a=0
            for c in re.match(r'[A-Z]+',colref).group():a=a*26+ord(c)-64
            return a-1
        for row in root.findall('.//m:sheetData/m:row',ns):
            cells={}
            for c in row.findall('m:c',ns):
                ref=c.get('r')
                if not ref:continue
                typ=c.get('t','n');v=c.find('m:v',ns)
                raw=v.text if v is not None else None
                if typ=='inlineStr':
                    inline=c.find('m:is',ns)
                    val=''.join(n.text or '' for n in inline.findall('.//m:t',ns)) if inline is not None else ''
                elif typ=='s' and raw is not None:val=shared[int(raw)]
                elif typ=='b' and raw is not None:val=raw=='1'
                elif raw is not None and typ not in ('str','e'):
                    try:val=float(raw) if '.' in raw or 'E' in raw.upper() else int(raw)
                    except ValueError:val=raw
                else:val=raw
                cells[colindex(ref)]=val
            if cells:
                output.append([cells.get(i) for i in range(max(cells)+1)])
        return output


def ler_entrada(path: Path, index_aba: int = 0) -> tuple[list[str], list[list]]:
    """Agente de ingestão: arquivo original lido, nunca sobrescrito."""
    if path.suffix.lower()=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.reader(f))
    elif path.suffix.lower()=='.xlsx':
        try:
            from artifact_tool import Blob, SpreadsheetFile
        except ImportError:
            rows=ler_xlsx_padrao(path,index_aba)
        else:
            wb=SpreadsheetFile.import_xlsx(Blob.load(str(path)))
            rows=wb.worksheets.get_item_at(index_aba).get_range('A1').get_current_region().values
    else:
        raise ValueError('Use arquivos .xlsx ou .csv.')
    if len(rows)<2:raise ValueError('Fonte não possui dados.')
    header=[str(v).strip() for v in rows[0]]
    if len(set(header))!=len(header):raise ValueError('Há colunas de origem com nomes duplicados.')
    return header,rows[1:]


def english_number(s):
    tokens=[t for t in s.lower().replace('-',' ').split() if t not in
            ('and','dollars','usd','miles','mile','mi')]
    total=cur=0
    if not tokens:return None
    for tok in tokens:
        if tok in WORDS:cur+=WORDS[tok]
        elif tok=='hundred':cur*=100
        elif tok=='thousand':total+=cur*1000;cur=0
        else:return None
    return total+cur


def numeric_text(value):
    s=re.sub(r'\s+','',str(value))
    if not re.fullmatch(r'\d[\d.,]*',s):return None
    if ',' in s and '.' in s:
        s=s.replace('.','').replace(',','.') if s.rfind(',')>s.rfind('.') else s.replace(',','')
    elif ',' in s:
        p=s.split(',')
        s=s.replace(',','.') if len(p)==2 and len(p[-1]) in (1,2) else s.replace(',','')
    elif '.' in s:
        p=s.split('.')
        if len(p)>=2 and len(p[-1])==3:s=s.replace('.','')
    try:return Decimal(s)
    except InvalidOperation:return None


def normalizar_data(value):
    if isinstance(value,datetime):return value.date().isoformat(),''
    if isinstance(value,date):return value.isoformat(),''
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        if 43000<=value<=50000:return (date(1899,12,30)+timedelta(days=int(value))).isoformat(),''
        return None,'DATA_INVALIDA'
    s=str(value or '').strip()
    s=re.sub(r'(?i)(\d+)(st|nd|rd|th)\b',r'\1',s)
    formats=['%Y-%m-%d','%Y.%m.%d','%Y/%m/%d','%m/%d/%Y','%m/%d/%y',
             '%m-%d-%y','%m-%d-%Y','%B %d, %Y','%b %d %Y','%b %d, %Y']
    for fmt in formats:
        try:return datetime.strptime(s,fmt).date().isoformat(),''
        except ValueError:pass
    return None,'DATA_INVALIDA'


def normalizar_preco(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool):return float(value),''
    s=str(value or '').strip().lower()
    if any(token in s for token in ('hundred','thousand')):
        n=english_number(s)
        return (float(n),'') if n is not None else (None,'PRECO_INVALIDO')
    is_k=bool(re.search(r'\d\s*k\b',s))
    cleaned=re.sub(r'(?i)usd|dollars?|\$','',s).replace(' ','').strip()
    if is_k:cleaned=re.sub(r'(?i)k$', '', cleaned)
    val=numeric_text(cleaned)
    if val is None:return None,'PRECO_INVALIDO'
    return float(val*(1000 if is_k else 1)),''


def normalizar_milhas(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool):
        return float(value),''
    s=str(value or '').strip().lower()
    if s in ('new','new car','zero','zero miles','0 miles','0 mi','brand new'):
        return 0.0,''
    if 'thousand' in s:
        n=english_number(s)
        return (float(n),'') if n is not None else (None,'QUILOMETRAGEM_INVALIDA')
    km=bool(re.search(r'\bkm\b|kilomet',s))
    cleaned=re.sub(r'(?i)miles?|mi\.?|km|kilometers?|[: ]','',s)
    val=numeric_text(cleaned)
    if val is None:return None,'QUILOMETRAGEM_INVALIDA'
    return (round(float(val)/1.609344,2),'KM_CONVERTIDO_MI') if km else (float(val),'')


def normalizar_ano(value):
    if isinstance(value,(int,float)) and not isinstance(value,bool) and float(value).is_integer():return int(value),''
    s=str(value or '').lower().strip().replace('-',' ').replace('_',' ')
    if re.fullmatch(r'\d{4}',s):return int(s),''
    if re.fullmatch(r'20\s+\d{2}',s):return int(s.replace(' ','')),''
    tok=s.split()
    if len(tok)==3 and tok[:2]==['twenty','twenty'] and tok[2] in WORDS:
        return 2020+WORDS[tok[2]],''
    if s.startswith('two thousand'):
        n=english_number(s[len('two thousand'):].strip())
        if n is not None:return 2000+n,''
    return None,'ANO_MODELO_INVALIDO'


def normalizar_pagamento(value):
    s=str(value or '').lower().strip().replace('-',' ').replace('_',' ')
    for clue,label in [('crypto','Crypto Payment'),('credit','Credit Card'),('debit','Debit Card'),
        ('ach','ACH Payment'),('leas','Lease'),('financ','Financing'),('cash','Cash'),
        ('wire','Wire Transfer'),('bank','Bank Transfer')]:
        if clue in s:return label,''
    return None,'PAGAMENTO_INVALIDO'


def normalizar_entrega(value):
    s=str(value or '').lower().strip().replace('-',' ')
    s=re.sub(r'[^a-z ]','',s).strip()
    if s.startswith('deliv') or s=='deliverd':return 'Delivered',''
    if s.startswith('cancel'):return 'Cancelled',''
    cat={'in transit':'In Transit','shipped':'Shipped','awaiting pickup':'Awaiting Pickup',
         'awaiting delivery':'Awaiting Delivery','awaiting review':'Awaiting Review',
         'pending approval':'Pending Approval','pending review':'Pending Review','pending':'Pending'}
    return (cat[s],'') if s in cat else (None,'STATUS_INVALIDO')


def safe_value(value):
    """Proteção adicional contra injeção de fórmula em saídas tabulares."""
    if isinstance(value,str) and value and value.lstrip().startswith(('=','+','-','@')):
        return "'"+value
    return value


class AgenteTratamento:
    """Normalizadores determinísticos (não são agentes LLM autônomos)."""
    def __init__(self,contrato):
        self.contrato=contrato
        self.customers={}
        self.sellers={}

    def pseudonimo(self,value,person):
        key=re.sub(r'\s+',' ',unicodedata.normalize('NFKC',str(value or '')).casefold().strip())
        if not key:return None,'PESSOA_AUSENTE'
        mapping=self.customers if person=='customer' else self.sellers
        if key not in mapping:
            mapping[key]=('CLI' if person=='customer' else 'VEN')+f'-{len(mapping)+1:03d}'
        return mapping[key],''

    def executar(self,normalizer,value,number):
        if normalizer=='row_code':return f'REG-{number:03d}',''
        if normalizer=='date':return normalizar_data(value)
        if normalizer=='person_customer':return self.pseudonimo(value,'customer')
        if normalizer=='person_seller':return self.pseudonimo(value,'seller')
        if normalizer=='text':return str(value or '').strip(),''
        if normalizer=='city':return str(value or '').strip().title(),''
        if normalizer=='us_state':
            val=STATE_CODES.get(str(value or '').strip().casefold())
            return (val,'') if val else (None,'ESTADO_INVALIDO')
        if normalizer=='model_year':return normalizar_ano(value)
        if normalizer=='price_usd':return normalizar_preco(value)
        if normalizer=='mileage_mi':return normalizar_milhas(value)
        if normalizer=='payment':return normalizar_pagamento(value)
        if normalizer=='delivery_status':return normalizar_entrega(value)
        raise ValueError('Normalizador inválido: '+normalizer)


def transformar(headers, data, contract):
    """Agente de privacidade + qualidade + auditoria: não elimina nenhuma linha."""
    fields=contract['fields']
    names=[f['source'] for f in fields]
    if not all(s in headers for s in names):
        raise ValueError('Colunas ausentes: '+str(sorted(set(names)-set(headers))))
    if len(headers)!=len(names):
        raise ValueError('Entrada possui colunas não previstas no schema; revise o contrato para evitar vazamento.')
    # Preserva a ordem ORIGINAL dos campos, não a ordem de declaração no contrato.
    fmap={f['source']:f for f in fields}
    rules=[fmap[h] for h in headers]
    public_headers=[x for f in rules for x in (f['source']+'_fonte',f['source']+'_tratado')]
    public_headers+=['situacao_temporal','qualidade_linha','observacoes_tratamento']
    agent=AgenteTratamento(contract)
    ref=date.fromisoformat(contract['reference_date'])
    output=[]; audit=[]; problems=Counter(); modified=Counter()
    seen_source_ids=set(); duplicates=0
    for seq,values in enumerate(data,1):
        if len(values)!=len(headers):raise ValueError(f'Linha {seq+1} está com {len(values)} campos; esperado {len(headers)}')
        record=dict(zip(headers,values))
        if record['sale_id'] in seen_source_ids:duplicates+=1
        seen_source_ids.add(record['sale_id'])
        out=[];flags=[];mapped={}
        for f in rules:
            source=f['source'];raw=record[source]
            treated,flag=agent.executar(f['normalizer'],raw,seq)
            # Identificadores diretos nunca são exportados; nem mesmo na coluna fonte.
            source_view=MASK if f['privacy']=='suppress' else safe_value(raw)
            out.extend([source_view,safe_value(treated)])
            mapped[source]=treated
            if flag:
                flags.append(flag);problems[flag]+=1
            if f['privacy']=='suppress':
                reason='SUPRESSAO_LGPD'
                if treated is not None:
                    modified[source]+=1
            elif str(raw).strip()!=str(treated).strip():
                reason='NORMALIZADO' if not flag else flag
                modified[source]+=1
            else:reason=''
            if reason:
                audit.append([f'REG-{seq:03d}',source,reason,
                              'VALOR_RESTRITO' if f['privacy']=='suppress' else safe_value(raw),
                              safe_value(treated)])
        dt=mapped['sale_date']
        if not dt:temporal='Data inválida'
        elif date.fromisoformat(dt)>ref:
            temporal='Futura (simulada)';flags.append('DATA_FUTURA_REFERENCIA');problems['DATA_FUTURA_REFERENCIA']+=1
        else:temporal='Histórica'
        # Qualidade: uma data futura recebe alerta temporal, mas não é data inválida.
        serious=any(flag not in ('KM_CONVERTIDO_MI','DATA_FUTURA_REFERENCIA') for flag in flags)
        quality='Revisar' if serious else 'OK'
        output.append(out+[temporal,quality,'; '.join(flags)])
    metrics={
      'registros':len(data),'colunas_origem':len(headers),
      'colunas_intercaladas':len(public_headers),
      'datas_invalidas':problems['DATA_INVALIDA'],
      'datas_futuras':problems['DATA_FUTURA_REFERENCIA'],
      'km_convertidos':problems['KM_CONVERTIDO_MI'],
      'linhas_revisar':sum(x[-2]=='Revisar' for x in output),
      'duplicidades_id_origem':duplicates,
      'clientes_pseudonimos':len(agent.customers),
      'vendedores_pseudonimos':len(agent.sellers),
      'auditorias':len(audit),
      'ocorrencias':dict(problems),
      'colunas_modificadas':dict(modified),
      'data_referencia':ref.isoformat(),
      'aviso_financeiro':'Soma de preços registrados não equivale a lucro nem receita reconhecida.',
      'aviso_lgpd':'Nomes e IDs fonte suprimidos. Pseudonimização não garante anonimização.'
    }
    # Verificação de política - nenhuma origem pessoal deve sair para as colunas fonte.
    for i,f in enumerate(rules):
        if f['privacy']=='suppress':
            assert all(row[2*i]==MASK for row in output)
    return public_headers,output,audit,metrics


def escrever_csv(path, headers, values):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(headers)
        writer.writerows([[safe_value(v) if v is not None else '' for v in row] for row in values])


def excel_column(index):
    out=''
    while index:
        index,remainder=divmod(index-1,26)
        out=chr(65+remainder)+out
    return out


def escrever_xlsx(dest, headers, rows, audit, metrics, contract):
    from artifact_tool import Workbook, SpreadsheetFile
    wb=Workbook.create()
    sheet=wb.worksheets.add('Fonte_e_Tratado')
    report=wb.worksheets.add('DataReview')
    aud=wb.worksheets.add('Auditoria')
    dic=wb.worksheets.add('Dicionario')
    n=len(headers); last=excel_column(n);lastrow=5+len(rows)
    sheet.merge_cells(f'A1:{last}1')
    sheet.get_range('A1').values=[['PORSCHE | TRATAMENTO E PRIVACIDADE — EXERCÍCIO DIO']]
    sheet.merge_cells(f'A2:{last}2')
    sheet.get_range('A2').values=[['Fonte (campos não sensíveis) ↔ Tratado | Nomes e IDs originais suprimidos (LGPD) | Nenhuma linha excluída']]
    sheet.get_range_by_indexes(3,0,1,n).values=[headers]
    if rows:sheet.get_range_by_indexes(4,0,len(rows),n).values=[
        [safe_value(x) if x is not None else None for x in row] for row in rows]
    sheet.get_range(f'A1:{last}1').format={'fill':'#11283A','font':{'bold':True,'color':'#FFFFFF','size':17},'row_height':35}
    sheet.get_range(f'A2:{last}2').format={'fill':'#E9F3F5','font':{'color':'#364956','size':10},'row_height':24}
    sheet.get_range_by_indexes(3,0,1,n).format.row_height=31
    for idx,col in enumerate(headers):
        c=excel_column(idx+1)
        if col.endswith('_tratado'):
            color='#0B6C75'; font='#FFFFFF'
        elif col.endswith('_fonte'):
            color='#304F68';font='#FFFFFF'
        else:color='#916622';font='#FFFFFF'
        sheet.get_range(f'{c}4').format={'fill':color,'font':{'bold':True,'color':font},'row_height':31}
        sheet.get_range(f'{c}:{c}').format.column_width=18 if col.endswith('_tratado') else 23
        if col in ('sale_date_tratado','sale_price_tratado','vehicle_mileage_tratado'):
            sheet.get_range(f'{c}:{c}').format.column_width=20
        if col=='observacoes_tratamento':sheet.get_range(f'{c}:{c}').format.column_width=42
    sheet.freeze_panes.freeze_rows(4)
    if len(rows):
        quality_col=excel_column(headers.index('qualidade_linha')+1)
        sheet.get_range(f'{quality_col}5:{quality_col}{lastrow-1}').conditional_formats.add_custom(
            f'=${quality_col}5="Revisar"',{'fill':'#FEF3C7'})
        sheet.tables.add(f'A4:{last}{lastrow-1}',True,'ParesOrigemTratado')
    summary=[['Métrica','Valor'],['Registros preservados',metrics['registros']],
      ['Campos da origem',metrics['colunas_origem']],['Campos públicos incluindo pares',metrics['colunas_intercaladas']],
      ['Datas inválidas',metrics['datas_invalidas']],['Datas futuras de referência',metrics['datas_futuras']],
      ['Conversões km -> mi',metrics['km_convertidos']],['Linhas para revisar',metrics['linhas_revisar']],
      ['IDs duplicados na origem',metrics['duplicidades_id_origem']],
      ['Clientes pseudonimizados',metrics['clientes_pseudonimos']],
      ['Vendedores pseudonimizados',metrics['vendedores_pseudonimos']],
      ['Eventos de auditoria',metrics['auditorias']],['Data referência',metrics['data_referencia']]]
    report.get_range(f'A1:B{len(summary)}').values=summary
    report.get_range('A1:B1').format={'fill':'#102A43','font':{'bold':True,'color':'#FFFFFF'},'row_height':30}
    report.get_range('A:A').format.column_width=37
    report.get_range('B:B').format.column_width=28
    report.get_range('A15').values=[['IMPORTANTE: números de pedidos não são receita recebida, nem lucro.']]
    report.get_range('A16').values=[['LGPD: pseudônimos não garantem anonimização completa.']]
    audit_headers=['registro_publico','campo','tipo_alteracao','valor_fonte_seguro','valor_tratado']
    aud.get_range('A1:E1').values=[audit_headers]
    if audit: aud.get_range_by_indexes(1,0,len(audit),5).values=audit
    aud.get_range('A1:E1').format={'fill':'#102A43','font':{'bold':True,'color':'#FFFFFF'},'row_height':30}
    for c,w in [('A',21),('B',27),('C',27),('D',35),('E',31)]:aud.get_range(f'{c}:{c}').format.column_width=w
    aud.freeze_panes.freeze_rows(1)
    dheaders=['coluna_fonte','coluna_tratada','regra','privacidade','observacao']
    dr=[[f['source']+'_fonte',f['source']+'_tratado',f['normalizer'],f['privacy'],f.get('description','')] for f in contract['fields']]
    dic.get_range('A1:E1').values=[dheaders]
    dic.get_range_by_indexes(1,0,len(dr),5).values=dr
    dic.get_range('A1:E1').format={'fill':'#102A43','font':{'bold':True,'color':'#FFFFFF'},'row_height':30}
    for c,w in [('A',29),('B',29),('C',24),('D',18),('E',65)]:dic.get_range(f'{c}:{c}').format.column_width=w
    dic.freeze_panes.freeze_rows(1)
    SpreadsheetFile.export_xlsx(wb).save(str(dest))


def executar(entrada:Path,schema:Path,saida:Path):
    if not entrada.is_file():raise FileNotFoundError(f'Entrada não encontrada: {entrada}')
    if not schema.is_file():raise FileNotFoundError(f'schema.md não encontrado: {schema}')
    if entrada.resolve().parent==saida.resolve():
        raise ValueError('Saída não pode ser a mesma pasta do arquivo bruto. Use pasta separada.')
    contract=carregar_contrato(schema)
    headers,records=ler_entrada(entrada,int(contract.get('input_sheet',0)))
    names,treated,audit,stats=transformar(headers,records,contract)
    saida.mkdir(parents=True,exist_ok=True)
    escrever_csv(saida/'dados_intercalados_publicos.csv',names,treated)
    escrever_csv(saida/'auditoria_publica.csv',
       ['registro_publico','campo','tipo_alteracao','valor_fonte_seguro','valor_tratado'], audit)
    (saida/'metricas_qualidade.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        escrever_xlsx(saida/'porsche_dados_intercalados.xlsx',names,treated,audit,stats,contract)
        stats['xlsx_gerado']=True
    except ImportError:
        stats['xlsx_gerado']=False
        print('Aviso: artifact_tool ausente. CSV e JSON foram produzidos; XLSX não gerado.',file=sys.stderr)
    return stats


def main():
    p=argparse.ArgumentParser(description='Agentes determinísticos de Data Review e sanitização — exercício DIO')
    p.add_argument('--entrada',type=Path,required=True,help='Planilha original .xlsx ou .csv')
    p.add_argument('--schema',type=Path,default=Path('schema.md'),help='Contrato de regras em Markdown')
    p.add_argument('--saida',type=Path,default=Path('saida'),help='Pasta diferente da origem')
    args=p.parse_args()
    stats=executar(args.entrada,args.schema,args.saida)
    print(json.dumps(stats,indent=2,ensure_ascii=False))

if __name__=='__main__':main()