# Mini Projeto Avaliativo - Módulo 1: Pipeline de Sanitização da Olist

## Descrição do Projeto

Este projeto, desenvolvido como parte do Módulo 1 (Fundamentos de Programação, Dados e Machine Learning) do curso **Machine Learning e Visão Computacional** do programa **SCTEC** 2026, implementa um pipeline de sanitização de dados usando apenas bibliotecas nativas do Python (`csv`, `re`, `datetime`, `pathlib`). O objetivo principal é realizar a sanitização e validação dos datasets `olist_products_dataset.csv` e `olist_orders_dataset.csv`, corrigindo inconsistências que impediam a geração de relatórios automatizados na infraestrutura da Olist.

O processamento é feito de forma modular com funções reutilizáveis em `functions.py` e a orquestração principal do fluxo em `main.py`.

## Estrutura do Projeto

- `src/`: Diretório local destinado ao armazenamento dos arquivos principais para execução do pipeline:
    - `main.py`: Script principal que orquestra o pipeline, carrega os dados brutos, invoca as transformações, gera o relatório estatístico no console e salva os resultados limpos.
    - `functions.py`: Módulo contendo as funções customizadas de leitura de CSV, normalização por Expressões Regulares (Regex), preenchimento de nulos, validação de regras de negócio e escrita de arquivos.
- `data/`: Diretório local destinado ao armazenamento dos arquivos CSV de entrada e saída.

## Guia de Execução

1. Certifique-se de que os arquivos `olist_products_dataset.csv` e `olist_orders_dataset.csv` estejam localizados dentro da pasta `data/`.
2. Abra o terminal na raiz do projeto (`sctec-projeto-I-etl`).
3. Entre no diretório `src/`:
```bash
cd src
```
4. Execute o comando:
```bash
python main.py
```

O script irá ler os arquivos em `data/`, limpar os dados conforme as regras definidas, imprimir um resumo de métricas no terminal e criar os arquivos resultantes `olist_products_cleaned.csv` e `olist_orders_cleaned.csv` na pasta `data/`.

## Decisões de Tratamento de Dados e Regras de Negócio

### 1. Leitura nativa de CSV
A leitura dos dados é feita via `csv.DictReader` em conjunto com blocos gerenciadores de contexto (`with open()`) para garantir eficiência de memória. Para mitigar falhas comuns em ambiente de produção, a função de leitura foi blindada com estruturas de `try/except` capturando `Exception`, garantindo que o pipeline reporte o erro de infraestrutura de forma clara sem sofrer uma interrupção abrupta.

### 2. Preenchimento de `product_category_name`
Campos vazios na categoria do produto são preenchidos com a string padrão `sem categoria`. Isso evita problemas de valores nulos em operações futuras de agrupamento e joins, mantendo a interpretabilidade do negócio.

### 3. Padronização de texto e Regex
Para evitar duplicidade de categorias por formatação (ex: "Eletro", "eletro ", "ELETRO"), os nomes passam por um processo de padronização:
- Conversão estrita para minúsculas com `.lower()`. 
- Remoção de espaços sobressalentes nas pontas com `.strip()`. 
- Limpeza de caracteres especiais e pontuações indevidas utilizando Expressões Regulares através do módulo `re`.

### 4. Tratamento de Valores Ausentes Numéricos (Produtos)
Observação inicial: os valores nulos acontecem exatamente nas mesmas 609 linhas para quase todas as colunas de características do produto. Isso indica que a ausência de informação é consistente por registro (provavelmente registros com pouca ou nenhuma descrição cadastral).

Valores nulos nas colunas `product_name_length`, `product_description_length` e `product_photos_qty` foram sistematicamente substituídos por 0:

- `product_name_length`: quando não há nome do produto, faz sentido que o comprimento seja `0`. Preencher com `0` preserva a propriedade numérica e evita inserir valores artificiais.
- `product_description_length`: ausência de descrição representa, na prática, um produto sem texto — portanto `0` é a representação mais fiel. Usar média/mediana seria estatisticamente incorreto e pode introduzir viés artificial.
- `product_photos_qty`: a falta de valor normalmente significa que não há fotos publicadas no anúncio; preencher com `0` é coerente com o significado do campo.

Justificativa técnica e de negócio:
- Preencher com `0` mantém consistência sem distorcer distribuições numéricas com valores inventados.
- Como os nulos ocorrem nas mesmas linhas, trata-se muito provavelmente de registros incompletos extraídos do mesmo lote ou etapa de cadastro; descartar todos esses registros poderia remover informações úteis (se ao menos dimensões físicas existirem), por isso só descartamos quando todas as dimensões físicas estão ausentes.
- Para colunas categóricas (como `product_category_name`) usar uma string explícita `sem categoria` mantém a interpretabilidade e evita problemas em agregações e joins.

### 5. Regra de Corte por Dimensões Físicas
Registros que possuem as colunas `product_weight_g`, `product_length_cm`, `product_height_cm` e `product_width_cm` simultaneamente vazias são descartados do dataset de produtos.

Justificativa técnica:
- Sem qualquer informação dimensional, esses registros perdem completamente a utilidade para análises de frete, cubagem logística e planejamento de transporte, tornando-se ruído descartável para os modelos de IA da empresa.

### 6. Validação da Hipótese de Pedidos Cancelados
O pipeline isola e audita os registros que contém a data de entrega (`order_delivered_customer_date`) ausente para confrontar com a hipótese de negócio da Olist: *estas datas estão nulas obrigatoriamente porque o status do pedido consta como cancelado?*

Para validar essa premissa, o script mapeou a distribuição real de status para os pedidos sem data de entrega, revelando o seguinte cenário estatístico:

* **Contagem de status (order_delivered_customer_date ausente):** `{'shipped': 1107, 'canceled': 619, 'unavailable': 609, 'invoiced': 314, 'processing': 301, 'delivered': 8, 'created': 5, 'approved': 2}`

#### Análise Crítica dos Dados e Justificativas:
A análise quantitativa prova que **a hipótese de negócio da Olist está incorreta**. O cancelamento (`canceled`: 619) representa apenas uma fração (aproximadamente 20.8%) dos casos com data de entrega ausente. A ausência desse metadado decorre, na verdade, de três fenômenos distintos na esteira de e-commerce:

1. *Pedidos em Fluxo Logístico Ativo:* Os status `shipped` (1107), `invoiced` (314), `processing` (301), `approved` (2) e `created` (5) somam a maior parte dos dados nulos. Tecnicamente, a data de entrega está ausente não por uma falha ou cancelamento, mas porque **o evento futuro ainda não aconteceu**. O produto está se movendo na esteira transacional. Preencher esses campos artificialmente destruiria a integridade temporal do pipeline.
2. *Interrupções de Fluxo Esperadas:* Os status `canceled` (619) e `unavailable` (609) justificam regras de negócio onde o produto nunca chegará ao cliente (seja por desistência ou quebra de estoque do parceiro/seller). Nestes cenários, o valor nulo é semanticamente correto e deve permanecer vazio, operando como um forte indicativo de churn ou falha operacional para modelos preditivos.
3. *Anomalias Críticas de Sistema:* A existência de 8 pedidos com o status `delivered` (entregue), mas com a data de entrega nula, aponta para um **bug sistêmico** (ex: falha na integração entre sistemas). 

#### Conclusão:
Diante do cenário acima apresentado, é rejeitada a hipótese da Olist de que "data de entrega nula significa pedido cancelado". Tratar o campo `order_delivered_customer_date` de forma generalista enviesaria qualquer modelo de Machine Learning a ser construído. 

### 7. Formatação Temporal
A coluna `order_approved_at` é convertida de seu formato original de string (`YYYY-MM-DD HH:MM:SS`) para o padrão simplificado de data brasileiro (`DD/MM/YYYY`) por meio do módulo nativo `datetime`, facilitando a plotagem em relatórios gerenciais e análises temporais baseadas em dias.

### 8. Etapa de Carga (Load) do Pipeline
Ao final da execução, uma nova função customizada `write_csv` extrai dinamicamente as novas chaves dos dicionários em memória e persiste os dados higienizados de volta no disco. Isso fecha o ciclo completo do pipeline de engenharia de dados.

## Reflexão teórica sobre Machine Learning

A qualidade dos dados que alimentam um ecossistema preditivo é o principal fator determinante para o sucesso ou fracasso de um modelo de Machine Learning. No cenário do mundo real, dados brutos são frequentemente corrompidos ou incompletos. Se metadados e tabelas transacionais forem injetados diretamente em um algoritmo de aprendizado supervisionado sem o devido processo de ETL e sanitização , enfrentaremos o fenômeno do Garbage In, Garbage Out (Lixo Entra, Lixo Sai). Dados incoerentes atuam como ruídos que forçam o modelo a aprender padrões estatísticos inexistentes, resultando em graves problemas de Overfitting (onde o modelo decora o ruído do treino e perde a capacidade de generalização) ou viés algorítmico. 

Ao aplicarmos uma lógica estruturada e consciente de programação na limpeza dos dados — como preencher categorias vazias de forma semântica , padronizar textos com Regex para evitar redundâncias e criar regras de corte logísticas claras  —, eliminamos sistematicamente as ambiguidades do dataset. Reduzir as inconsistências garante que os algoritmos matemáticos foquem puramente nos sinais e correlações legítimas do negócio. Como consequência direta, os modelos futuros de Inteligência Artificial tornam-se mais estáveis, justos em suas previsões e altamente confiáveis para a tomada de decisões automatizadas.
