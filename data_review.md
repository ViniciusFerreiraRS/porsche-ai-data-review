# Data Review — Porsche Sales Intelligence

**Projeto Vinicius Dev | 04/11/2026 | Análise de base didática**

## Resumo executivo

A base original contém **100 registros** e **12 campos**, enquanto o segundo arquivo representa um tratamento inicial com **21 colunas**. Após padronização independente, foram preservados os **100 registros**, sem excluir linhas e sem inventar datas ou preços. A base pública gerada omite identificadores pessoais diretos.

| Indicador | Resultado |
|---|---:|
| Registros analisados | 100 |
| Datas impossíveis/ambíguas | **24** (24%) |
| Datas futuras em relação a 04/11/2026 | **18** |
| Conversões explícitas km → mi | **4** |
| Quilometragem fracionária preservada | 1 |
| IDs de venda duplicados na origem | 0 |
| Entregas registradas | **41** |
| Cancelamentos registrados | **7** |
| Soma dos preços registrados | **US$ 12,827,800.50** |
| Soma dos preços de pedidos entregues | **US$ 5,078,800.50** |

> As duas somas acima não são lucro, faturamento líquido nem caixa reconhecido. A primeira inclui pedidos pendentes e cancelados; a segunda depende apenas do status logístico `Delivered`.

## Diagnóstico e decisões de tratamento

1. **Calendário:** 24 datas sem interpretação válida, incluindo dias inexistentes e campos ambíguos. Não houve imputação: as linhas ficaram com `data_venda` nula e `qualidade_linha = Revisar`.
2. **Datas futuras:** 18 registros posteriores a 04/11/2026; classificados como `Futura (simulada)` e mantidos para fins didáticos. Dados não podem ser usados como volume histórico realizado até hoje.
3. **Preço:** USD padronizado a número decimal, inclusive valores como `$121k`, `68.900 dollars`, `89.750,00` e preços escritos por extenso.
4. **Distância:** valores com sufixo `KM` convertidos para milhas com fator exato `1.609344`; 4 conversões. O valor numérico de `9.5` foi preservado como 9,5 milhas, corrigindo arredondamento presente na primeira planilha tratada.
5. **Estados, status e formas de pagamento:** normalizados a vocabulários controlados, preservando a granularidade útil para análise comercial e operacional.
6. **Dados pessoais:** `customer_name` e `salesperson` foram retirados da exportação pública. Foram criados identificadores substitutos de registro e pseudônimos de vendedor, sem publicar o mapeamento.
7. **Custos:** os arquivos não incluem custo de aquisição, publicidade, hospedagem, tokens de IA ou margem. O modelo de custos foi criado vazio para preenchimento posterior, sem números fictícios.

## Insights iniciais (descrição exploratória, não causal)

- **Distribuição de status:** 41 entregas, 7 cancelamentos e 52 registros em outros estados logísticos. **Conclusão:** a análise de valores de pedido deve ser separada da análise de entregas.
- **Concentração geográfica por número de registros:** CA (16), TX (14), AZ (7), FL (6), NC (5). **Conclusão:** examinar estados individualmente em vez de inferir distribuição uniforme.
- **Modelos com maior soma de preços registrados:** 911 Dakar (US$ 810,600.00), 911 Turbo S (US$ 726,300.00), 911 GT3 (US$ 697,500.00). **Conclusão:** valor agregado alto pode refletir preço unitário elevado, não necessariamente maior volume.
- **Cobertura temporal:** dos 100 pedidos, apenas 76 possuem data válida para indicadores mensais; **24 não devem ser distribuídos arbitrariamente ao longo do calendário**.
- **Revisão anterior:** há 5 divergências de precisão em quilometragem na planilha inicialmente tratada, principalmente por arredondamento de conversões km→mi.

## Riscos e prioridades

- **Alto:** datas inválidas tornam incompletos os indicadores de evolução mensal. Priorizar validação contra fonte legítima antes de projeções e comparativos executivos.
- **Alto:** a presença de dados futuros impede tratar toda a base como histórico realizado em novembro de 2026.
- **Alto:** o valor de pedido não deve ser apresentado como lucro ou receita reconhecida.
- **Médio:** cidade e estado combinados com data podem permitir reidentificação em bases reais; fazer revisão antes de publicar.
- **Médio:** o controle de custos depende de alimentação real, classificação e unidade monetária consistente.

## Próximos passos

1. Revisar 24 datas com a fonte original autorizada (sem inventar valores).
2. Validar com a pessoa responsável se a fonte é inteiramente sintética ou se há licença para divulgação pública.
3. Alimentar custos com comprovantes/documentação, caso existam.
4. Refinar indicadores com regras de negócio: valor de pedidos, entregas, cancelamentos, pagamentos liquidados, margem (apenas quando existir custo real).
5. Versionar `schema.md`, este review, o Excel tratado e `index.html` no repositório apropriado.

## Metodologia

Análise exploratória, normalização de dados, validação de tipos e datas, classificação de qualidade, pseudonimização, agregações descritivas e documentação de limitações. Não foram realizadas inferências causais ou previsões. A base de ensino não comprova números reais de vendas Porsche.

## Complemento — pipeline de colunas lado a lado

Foi criado um **segundo arquivo tratado** (`porsche_dados_intercalados.xlsx`) sem
substituir a tabela analítica anterior. Cada uma das 12 colunas da fonte agora vem
seguida imediatamente da respectiva coluna de tratamento. Acrescentam-se três
campos de contexto/qualidade, totalizando 27 colunas por registro. Os identificadores
diretos de clientes, vendedores e vendas são suprimidos nas colunas de origem
exportadas. Nenhuma linha é eliminada.

O código `pipeline_tratamento.py` lê o contrato executável presente em `schema.md`.
Uma auditoria pública lista regras, alteração e valores de origem apenas quando
não protegidos. Foram mantidos 100 registros, 24 datas inválidas, 18 datas futuras
em relação à data de referência e quatro conversões de quilômetros para milhas.
A precisão das milhas fracionárias foi preservada.