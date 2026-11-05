# Porsche Sales Intelligence — AI Reports

**Exercício prático da aceleração Santander/DIO — AI Reports com Excel, GPT Agents e Claude Code.**

Projeto educacional desenvolvido no contexto do **Projeto Vinicius Dev**, com tratamento e validação de dados em Python, documentação `schema.md`, medidas de proteção de dados pessoais e dashboard interativo para análise de vendas Porsche. A construção contou com assistência de IA, revisão das regras e testes automatizados. Não é um produto ou projeto oficial da DIO, do Santander ou da Porsche.


## Visão geral

Dashboard interativo de vendas/pedidos de veículos com filtros de período, estado, modelo e situação de entrega. Inclui Data Review, dicionário de dados, rastreabilidade de regras e modelo de acompanhamento de custos operacionais do **projeto analítico**.

## Prévia do dashboard e Big Cards

**Dashboard interativo:** arquivo [index.html](index.html). Para visualizá-lo como site, ative o GitHub Pages em Settings → Pages.

| Big Card / Indicador | Base de demonstração |
|---|---:|
| Registros preservados | 100 |
| Entregas registradas | 41 |
| Datas inválidas sinalizadas | 24 |
| Datas futuras sinalizadas | 18 |

A prévia abaixo apresenta o dashboard criado para o exercício. Os cards e filtros funcionais estão implementados em [`index.html`](index.html).

![Prévia do dashboard Porsche com Big Cards e gráficos](./preview_dashboard%20%281%29.png)

Os **Big Cards/KPIs** no topo exibem registros, valor total registrado (não faturamento), ticket médio, entregas e datas a revisar. Cada card é atualizado pelos filtros de ano, mês, modelo, estado e situação da entrega. A interpretação do conjunto é complementada pelos gráficos, insights e relatório de qualidade.

**Experimento educacional:** os indicadores podem ser reproduzidos a partir da base tratada; os registros inconsistentes são sinalizados, sem esconder limitações ou inferir lucro.

> **Aviso:** base utilizada para fins de ensino. Não é publicação oficial de Porsche, Santander ou DIO. Pedidos e valores registrados não representam necessariamente receita reconhecida. Há datas futuras em relação a 04/11/2026.

## Como acessar

1. Abra [`index.html`](index.html) em qualquer navegador moderno — funciona sem servidor e sem bibliotecas externas.
2. Use os filtros de ano, mês, modelo, estado e entrega. Os cards, gráficos e insights se atualizam.
3. Consulte [`dados_intercalados_publicos.csv`](dados_intercalados_publicos.csv) para conferir a base com colunas fonte/tratada, sem identificadores pessoais diretos. A versão Excel já está disponível em [`planilha_porsche_tratada.xlsx`](planilha_porsche_tratada.xlsx).
4. Leia [`data_review.md`](data_review.md) para entender problemas encontrados e critérios de limpeza.
5. Consulte [`schema.md`](schema.md) para os tipos, métricas, regras, segurança e limitações.

## Arquitetura do projeto

```text
Arquivos recebidos (privados, não publicados)
    ↓ validação + inspeção
Data Review → regras de tratamento → conversão de unidades
    ↓
Pseudonimização + checagem de qualidade
    ↓
Dados tratados (Excel / JSON público sob avaliação)
    ↓
Dashboard HTML + relatórios + schema.md
```

## Funcionalidades

- Cards: registros, valor registrado, ticket médio, entregas e datas a revisar.
- Recortes: ano, mês, modelo de veículo, estado e status.
- Comparação com mês anterior quando aplicável e com base comparável.
- Tendência mensal baseada somente em registros com datas válidas.
- Composição de entregas, cancelamentos, principais modelos e estados.
- Modelo de gastos do **projeto de IA/dados** com registro local no navegador; não mede lucro na venda dos veículos.
- Avisos sobre qualidade, dados futuros e limites de interpretação.

## Estrutura

- `index.html` — dashboard funcional com dados públicos incorporados para operação offline.
- `dados_intercalados_publicos.csv` — resultado do pipeline com valores de origem permitidos e suas versões tratadas; `auditoria_publica.csv` e `metricas_qualidade.json` documentam o tratamento.
- `dados_tratados_publicos.json` — dados transformados sem nomes diretos.
- `schema.md` — contrato e dicionário de dados.
- `data_review.md` — achados e decisões técnicas.

## Segurança e privacidade

Nomes de clientes, nomes de vendedores e IDs comerciais originais foram **excluídos** dos arquivos produzidos. Os códigos de vendedores são pseudônimos, não garantia de anonimização. Para uma base real, endereço aproximado, datas e modelos também podem tornar pessoas identificáveis quando combinados.

## Sobre os custos

O controle local de custos do dashboard destina-se a despesas para **criar e manter o próprio projeto** (hospedagem, APIs, ferramentas). Dados ficam no armazenamento local do navegador, com opção de exportar CSV; não são enviados para servidor. Custos de compra dos carros e lucro não podem ser calculados com as fontes atuais.

## Publicação no GitHub Pages

1. Crie um repositório novo (recomendado: `porsche-ai-data-review`).
2. O projeto já contém os scripts, JSON, CSV, auditoria e documentação. Arquivos Excel e imagem de captura podem ser adicionados manualmente após revisão.
3. Em *Settings → Pages*, selecione *Deploy from a branch*, a branch principal e diretório `/ (root)`.
4. A página `index.html` será a tela inicial do dashboard.

*Nota de autoria:* a construção deste protótipo foi assistida por IA; descreva com transparência no portfólio as etapas revisadas e as decisões técnicas que você compreendeu ou modificou.

## Novo: exercício da DIO — agentes de tratamento de dados em Python

Adicionamos um pipeline didático inspirado na aceleração **Santander/DIO — AI Reports**.
Ele implementa etapas com nomes de "agentes" (*ingestão, contrato, normalização,
privacidade, auditoria e exportação*), porém são **funções determinísticas em Python,
não agentes LLM autônomos**. Não utiliza API paga.

### Fluxo de dados e regras

```text
base bruta local (.xlsx ou .csv) [não publicar]
    ↓ Agente de ingestão
schema.md [contrato JSON validado]
    ↓ Agente de tratamento
fonte permitida → tratado | fonte permitida → tratado | ...
    ↓ Agente de privacidade
supressão de IDs, nomes de clientes e nomes de vendedores
    ↓ Agente de qualidade e auditoria
planilha_porsche_tratada.xlsx + CSV público + auditoria + JSON de métricas
    ↓ Analista valida → Dashboard e documentação
```

**Cada coluna tratada fica imediatamente à direita da coluna fonte**. Para os
3 identificadores protegidos (`sale_id`, `customer_name` e `salesperson`),
a coluna fonte contém `[SUPRIMIDO_LGPD]` e a tratada recebe um pseudônimo.
A base pública possui **27 campos** (12 pares e 3 campos de qualidade).

### Executar no VS Code / terminal

1. Coloque a base original na pasta local `dados_brutos/exedio.xlsx` (esta pasta é ignorada pelo Git).
2. Execute na pasta do projeto:

```bash
python pipeline_tratamento.py --entrada dados_brutos/exedio.xlsx --schema schema.md --saida saida
```

O script sempre gera `saida/dados_intercalados_publicos.csv`, `saida/auditoria_publica.csv`
e `saida/metricas_qualidade.json`, usando apenas a biblioteca padrão do Python
para o tratamento. O Excel de saída (`saida/planilha_porsche_tratada.xlsx`) é gerado
quando a biblioteca `artifact_tool` está disponível. A leitura de XLSX tem
uma alternativa nativa baseada em ZIP/XML para planilhas simples como a do exercício.
Se estiver em um ambiente sem `artifact_tool`, use o CSV gerado (abre no Excel).

### Testes

```bash
python -m unittest -v test_pipeline.py
```

Verificam conversão monetária, datas impossíveis, quilometragem, intercalamento das
colunas, preservação de registros e supressão dos identificadores protegidos.

### Arquivos adicionados

- `pipeline_tratamento.py` — código-fonte reproduzível dos agentes.
- `test_pipeline.py` — testes automatizados.
- `planilha_porsche_tratada.xlsx` — saída demonstrativa pronta para inspeção.
- `dados_intercalados_publicos.csv` — saída pública lado a lado.
- `auditoria_publica.csv` — valores antes/depois para campos não sensíveis.
- `metricas_qualidade.json` — indicadores do Data Review.
- `schema.md` — documentação e **bloco de regras executáveis em JSON**.
- `.gitignore` — proteção contra inclusão acidental de arquivos brutos.

**Cuidado LGPD:** esta base foi informada como didática e autorizada para divulgação,
mas as regras demonstram **minimização e pseudonimização**, não garantia de
anonimização completa. Em bases reais, revisar riscos de reidentificação, finalidade,
base legal, acesso e retenção. O dashboard HTML original usa uma base normalizada
preparada na etapa anterior; o script disponibiliza os mesmos conceitos de
normalização com colunas fonte/tratada para auditoria reproduzível.
