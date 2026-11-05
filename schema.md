# schema.md — Porsche Sales Intelligence

> Versão 1.1 | Projeto de portfólio de Engenharia e Análise de Dados (base de treinamento) | Referência temporal: 04/11/2026.

## Finalidade e granularidade

Uma linha representa **um registro de venda/pedido de veículo**, não uma transação financeira liquidada. A chave pública `codigo_registro` é um código substituto gerado para esta versão; a chave original não é publicada. O conjunto tratado contém **100 registros**, dos quais **24 têm data inválida ou ambígua**. Esses registros permanecem na base, mas ficam fora de recortes mensais.

A coluna `preco_usd` é o valor registrado do veículo, **não** lucro, receita reconhecida ou caixa efetivamente recebido. O status `Delivered` sinaliza entrega, mas não prova recebimento de pagamento. Não existem colunas com custo de aquisição do veículo, margem ou despesa operacional na fonte.

## Colunas da tabela DadosTratados

| Coluna | Tipo | Nulável | Definição/regra |
|---|---|---|---|
| `codigo_registro` | string | Não | Identificador substituto sequencial: `REG-001` etc. |
| `data_venda` | date (`YYYY-MM-DD`) | Sim | Data validada. Datas impossíveis/ambíguas: nulo, sem imputação. |
| `mes_referencia` | string (`YYYY-MM`) | Sim | Derivado de `data_venda`; usado para os filtros. |
| `ano` | integer | Sim | Ano da data válida. |
| `mes_num` | integer | Sim | Mês (1–12) da data válida. |
| `modelo_porsche` | string | Não | Modelo de veículo conforme origem. |
| `ano_modelo` | integer | Não | Ano do veículo normalizado, inclusive quando escrito por extenso. |
| `preco_usd` | decimal(14,2) | Não | Valor informado da venda em dólares norte-americanos. |
| `quilometragem_mi` | decimal(12,2) | Não | Rodagem em milhas; `km ÷ 1,609344`, quando a unidade original era km. |
| `metodo_pagamento` | categoria | Não | Forma de pagamento com sinônimos padronizados. |
| `cidade` | string | Não | Cidade, com capitalização corrigida. |
| `estado_uf` | string(2) | Não | Sigla postal estadual americana. |
| `vendedor_codigo` | string | Não | Pseudônimo por vendedor (`VEN-001` etc.); mapeamento com nomes omitido. |
| `status_entrega` | categoria | Não | Categoria normalizada do estágio de entrega. |
| `situacao_temporal` | categoria | Não | `Histórica`, `Futura (simulada)` ou `Data inválida`. |
| `qualidade_linha` | categoria | Não | `OK` ou `Revisar`. |
| `observacoes_tratamento` | string | Sim | Flags de normalização, qualidade e conversão (sem nomes). |

## Vocabulários de domínio

- `status_entrega`: Delivered; Cancelled; In Transit; Shipped; Awaiting Pickup; Awaiting Delivery; Awaiting Review; Pending Approval; Pending Review; Pending.
- `metodo_pagamento`: Wire Transfer; Credit Card; Financing; Cash; Bank Transfer; Lease; Crypto Payment; Debit Card; ACH Payment.
- `situacao_temporal`: Histórica; Futura (simulada); Data inválida.

## Regras e critérios de tratamento

1. **Imutabilidade da origem:** os arquivos fornecidos não são alterados. A versão tratada é um artefato novo.
2. **Datas:** números seriados de Excel convertidos usando origem `1899-12-30`; datas textuais interpretadas em formatos explícitos `AAAA-MM-DD`, `MM/DD/AAAA` e nomes de meses em inglês. Datas inválidas (ex.: `2024-02-30`) são registradas como nulas; não se presume correção.
3. **Datas futuras:** datas depois de **2026-11-04** recebem flag `Futura (simulada)`. Não devem ser descritas como vendas realizadas até essa data.
4. **Preços:** normalização de `USD`, `$`, abreviação `k`, separadores de milhares e decimal, além de dois exemplos por extenso. Moeda de referência é **USD**, sem conversão cambial.
5. **Quilometragem:** texto por extenso ou `new`/`zero` normalizado; `KM` explicitamente convertido para **milhas** com fator exato `1.609344`. Valores numéricos sem unidade são presumidos como milhas. Valores fracionários, como `9.5`, são preservados.
6. **Categorizações:** normalização de caixa, pontuação e sinônimos de status e pagamento; estados convertidos à abreviação postal.
7. **Registros e IDs:** nenhuma linha é excluída automaticamente; nenhuma chave original de venda, nome de cliente ou nome de vendedor é exportado.
8. **Auditoria:** alterações e exceções acessíveis nas abas `DataReview` e `Dicionario`, e no relatório `data_review.md`.
9. **Custos:** nenhuma despesa foi imputada. A aba `Custos` contém campos vazios destinados a futura coleta validada.

## Indicadores e suas definições

| Indicador | Fórmula | Observações |
|---|---|---|
| Registros | Contagem de `codigo_registro` | Inclui todos os status no recorte. |
| Valor registrado | Soma de `preco_usd` | **Não representa receita nem lucro.** |
| Ticket médio registrado | Soma de `preco_usd` / número de registros | Sem inferência de margem. |
| Entregues | Contagem com `status_entrega = Delivered` | Não equivale a pagamento confirmado. |
| Valor de entregues | Soma de `preco_usd` onde `Delivered` | Indicador operacional, não receita reconhecida. |
| Cancelados | Contagem com `status_entrega = Cancelled` | Mantidos no conjunto, sinalizados. |
| Datas a revisar | Contagem `qualidade_linha = Revisar` | No recorte `Todos`, inclui datas inválidas. |
| Série temporal mensal | Agrupamento por `mes_referencia` | Exclui 24 registros sem data válida. |
| Custos do projeto | Soma de lançamentos inseridos manualmente no painel local | Não é custo de produto nem custo de venda. |

## Privacidade e LGPD

Os nomes originais (`customer_name`, `salesperson`) e o identificador comercial original não estão presentes nos arquivos públicos. Os vendedores possuem **pseudônimos**, o que não equivale necessariamente a anonimização irreversível. Cidade, data e estado podem funcionar como quase identificadores quando combinados com outras informações; se a base for real, conduza avaliação jurídica e de risco de reidentificação antes de publicar. Este material deve ser entendido como dado **didático** e não comprova autorização para publicar registros reais do Santander, Porsche, da DIO ou clientes.

Não inserir credenciais, segredos de API, dados de clientes, planilhas brutas ou mapas de correspondência entre pseudônimo e pessoa em repositórios públicos. Se houver dúvida sobre a origem/licença dos dados, publicar apenas agregados e exemplos sintéticos.

## Limitações conhecidas

- 24 datas inválidas, que restringem séries temporais.
- 18 datas posteriores a 04/11/2026, interpretadas como cenário futuro/didático.
- Não há dados sobre margem, despesas, desconto, imposto ou valor efetivamente liquidado.
- O registro `Delivered` não comprova pagamento.
- Os 100 registros de exemplo não devem ser interpretados como estatística de vendas reais da Porsche.

## Versão e rastreabilidade

- Origem: `exedio.xlsx` (12 colunas) e `exedio1.xlsx` (tentativa anterior de normalização, 21 colunas), **não incluídos no pacote público**.
- Produto: `porsche_dados_tratados.xlsx`, `dados_tratados_publicos.json`, `index.html`, `data_review.md`, `README.md`.
- Data da revisão: **04/11/2026**, fuso horário de São Paulo.


---

## Pipeline Python e contrato executável (versão 1.1)

O arquivo `pipeline_tratamento.py` lê **este** documento e interpreta o bloco JSON abaixo como contrato dos campos: `source` indica a coluna de origem, `normalizer` seleciona a regra em Python e `privacy` determina se o valor original pode aparecer na coluna `_fonte` do produto público. As colunas são criadas na ordem **fonte → tratado, imediatamente adjacentes**, para todos os 12 campos.

**Exceção LGPD:** a coluna `_fonte` de `sale_id`, `customer_name` e `salesperson` mostra `[SUPRIMIDO_LGPD]`; a coluna `_tratado` recebe identificadores substitutos (REG/CLI/VEN). Nenhum nome, chave de venda original ou tabela de correspondência é exportado. Os pseudônimos permitem correlacionar linhas, mas não são garantia de anonimização irreversível.

O arquivo `porsche_dados_intercalados.xlsx` terá **27 colunas**: 12 pares `*_fonte`/`*_tratado` e 3 indicadores extras (`situacao_temporal`, `qualidade_linha`, `observacoes_tratamento`). Datas inválidas tornam-se valores nulos na coluna tratada, preservados na coluna fonte quando não pessoais. O processo conserva todas as linhas e produz uma auditoria sem dados pessoais de origem.

<!-- PIPELINE_RULES_BEGIN -->
```json
{
  "schema_version": "1.1",
  "reference_date": "2026-11-04",
  "input_sheet": 0,
  "fields": [
    {"source":"sale_id","normalizer":"row_code","privacy":"suppress","description":"Identificador comercial suprimido e substituído por REG-xxx"},
    {"source":"sale_date","normalizer":"date","privacy":"public","description":"ISO 8601; sem inventar datas impossíveis"},
    {"source":"customer_name","normalizer":"person_customer","privacy":"suppress","description":"Nome suprimido; código CLI-xxx em memória"},
    {"source":"porsche_model","normalizer":"text","privacy":"public","description":"Trim de texto do modelo"},
    {"source":"model_year","normalizer":"model_year","privacy":"public","description":"Ano modelo numérico, inclusive quando escrito por extenso"},
    {"source":"sale_price","normalizer":"price_usd","privacy":"public","description":"Normalização monetária para número em USD"},
    {"source":"vehicle_mileage","normalizer":"mileage_mi","privacy":"public","description":"Milhas; conversão de km por 1,609344; preservação de frações"},
    {"source":"payment_method","normalizer":"payment","privacy":"public","description":"Vocabulário controlado de pagamento"},
    {"source":"city","normalizer":"city","privacy":"public","description":"Capitalização de cidades"},
    {"source":"state","normalizer":"us_state","privacy":"public","description":"Sigla postal de estados dos EUA"},
    {"source":"salesperson","normalizer":"person_seller","privacy":"suppress","description":"Nome suprimido; código VEN-xxx em memória"},
    {"source":"delivery_status","normalizer":"delivery_status","privacy":"public","description":"Status padronizado de entrega"}
  ]
}
```
<!-- PIPELINE_RULES_END -->

### Agentes de tratamento e validação

Este exercício chama as etapas de **agentes**, por analogia ao conteúdo da DIO, mas **as regras são funções Python determinísticas**, não agentes de IA com autonomia ou acesso a modelos externos. Nenhuma API paga é utilizada.

1. **Agente de contrato:** lê e valida as regras neste arquivo, rejeitando campos inesperados.
2. **Agente de ingestão:** lê o CSV/XLSX bruto sem alterá-lo.
3. **Agente de tratamento:** aplica conversões e padronização campo a campo.
4. **Agente de privacidade:** suprime identificadores diretos e atribui códigos internos.
5. **Agente de auditoria/qualidade:** registra mudanças e exceções sem expor nomes.
6. **Agente de exportação:** produz Excel/CSV e métricas JSON para o relatório e dashboard.

### Execução local

```bash
python pipeline_tratamento.py --entrada dados_brutos/exedio.xlsx --schema schema.md --saida saida
```

A exportação XLSX utiliza `artifact_tool` quando disponível no ambiente. O CSV/JSON também é produzido para facilitar integração e auditoria. A pasta `dados_brutos/` deve ficar fora do repositório Git. O arquivo `.gitignore` deste projeto previne inclusão acidental desses arquivos; revise manualmente cada commit.

**Validade:** estas regras são específicas da base didática Porsche; não são um mecanismo genérico que garanta conformidade com a LGPD. Base real exige avaliação de finalidade, necessidade, base legal, acesso, retenção e risco de reidentificação.