# AGROGADO — Gestão Inteligente de Insumos Rurais & Manejo Bovino

> **Desafio Oficial:** *Gestão inteligente de insumos em uma propriedade rural*  
> **Instituição:** Instituto Federal de Educação, Ciência e Tecnologia de Rondônia (IFRO) — *Campus* Ariquemes  
> **Evento:** Semana Nacional de Ciência e Tecnologia (SNCT 2026) — 29 de Outubro de 2026  
> **Stack Tecnológica:** Python 3.14 (compatível 3.12+) • Django 5.2 LTS • SQLite 3 • HTML5 / CSS3 Puro • Chart.js  
> **Suíte de Testes:** 15 Testes Automatizados Integrados • 100% Aprovados (`OK`)  

---

## 1. Identificação da Equipe

A equipe é multidisciplinar, integrando competências de Tecnologia da Informação (Análise e Desenvolvimento de Sistemas) e Ciências Agrárias (Medicina Veterinária) para garantir total aderência zootécnica às rotinas reais da pecuária e da agricultura no Vale do Jamari / Rondônia:

| Integrante | Curso / Matrícula | Função no Projeto | Responsabilidades Principais |
|---|---|---|---|
| **Ian Pelentir Ramos** | ADS — 4º período<br>`2022105100001` | **Líder de Projeto & Arquiteto Back-end** | **Integrante Responsável**; arquitetura Django, modelagem relacional, conformidade regulamentar e integração de módulos |
| **Bruna Pereira da Silva** | Medicina Veterinária — 2º período<br>`2026105210042` | **Consultora de Domínio Rural & Zootecnia** | Regras de nutrição animal na seca, cálculo de ECC, controle sanitário de vacinas/medicamentos, carência e validação de campo |
| **Alan Menezes de Araújo** | ADS — 4º período<br>`2024105100044` | **Engenheiro de Dados & Motor Analítico** | Algoritmos determinísticos da To-Do List semafórica, projeção de cobertura, simulação de estiagem e suíte de testes |
| **Marco Antonio de Oliveira Medeiros** | ADS — 4º período<br>`2024105100014` | **Desenvolvedor Front-end & Usabilidade** | Interface voltada ao produtor rural, To-Do List acessível, painel de lotes bovinos, alternador de visualização e responsividade |

* **Integrante Responsável:** Ian Pelentir Ramos (`ianpelentir7@gmail.com`)  
* **IFRO — Campus Ariquemes** — Rodovia RO-257, Km 13, Sentido Machadinho D'Oeste, Ariquemes - RO  

---

## 2. Contexto do Problema e Motivação Regional

### O Desafio no Vale do Jamari (Ariquemes / Rondônia)
Ariquemes é um dos maiores polos da pecuária de corte e leite do estado de Rondônia. Nas fazendas da região, o manejo do gado e o controle do barracão de insumos costumam operar de forma desarticulada:
1. **Desconexão entre Rebanho e Depósito:** O produtor sabe quantas cabeças possui, mas não cruza o consumo diário do lote com os sacos de sal mineral ou ração restantes no galpão. O sal acaba de surpresa, interrompendo o ciclo de engorda e derrubando o ganho de peso diário (GMD).
2. **A Sazonalidade Amazônica (Período das Águas vs. Período da Seca):** Entre os meses de maio e outubro, a precipitação cai drasticamente em Rondônia. O capim (*Brachiaria brizantha*) perde teor de proteína bruta (PB cai para menos de 6%), exigindo que o gado dobre o consumo de suplementos minerais proteicos e ureados para evitar perda de Escore de Condição Corporal (ECC). Sem simulação preditiva, a propriedade enfrenta desabastecimento em massa.
3. **Perdas Financeiras com Perecíveis e Insumos Críticos:** Medicamentos veterinários caros (vacinas, antibióticos, carrapaticidas) vencem esquecidos na geladeira da fazenda, enquanto defensivos essenciais faltam no dia da aplicação.

### O Que o AGROGADO Resolve
O **AGROGADO** une o controle de **Estoque de Insumos** ao **Manejo de Lotes Bovinos** através de um **Motor Analítico Semafórico**. O produtor não precisa decifrar relatórios complexos: ao abrir o sistema, a **To-Do List Rural** diz exatamente o que deve ser comprado, vacinado ou ajustado hoje para evitar perdas financeiras.

---

## 3. Arquitetura e Funcionalidades do Sistema

```
                  ┌──────────────────────────────────────────────┐
                  │          PAINEL PRINCIPAL AGROGADO           │
                  │   Cotação @ Ariquemes/RO • Rebanho • Estoque │
                  └──────────────────────┬───────────────────────┘
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
   ┌───────────────────────────┐                   ┌───────────────────────────┐
   │    MOTOR ANALÍTICO        │                   │     MANEJO BOVINO         │
   │  To-Do List Semafórica    │                   │   Controle de Lotes       │
   │  🔴 Alta | 🟡 Média | 🟢  │                   │   ECC 1-5 • Pasto • Cabeças│
   └─────────────┬─────────────┘                   └─────────────┬─────────────┘
                 │                                               │
                 ├───────────────────────┬───────────────────────┤
                 ▼                       ▼                       ▼
   ┌───────────────────────────┐ ┌────────────────┐ ┌───────────────────────────┐
   │   SIMULAÇÃO DE SECA       │ │  RASTREAMENTO  │ │   VALIDAÇÕES RESTRITAS    │
   │ Consumo Mineral Dobrado   │ │  Lotes/Validade│ │  Sem Estoque Negativo     │
   │ Cobertura em Dias de Risco│ │  Entrada/Saída │ │  13 Campos do Regulamento │
   └───────────────────────────┘ └────────────────┘ └───────────────────────────┘
```

### 3.1 Módulos Principais

1. **To-Do List Rural Semafórica (RF02 / RF03):**
   * **🔴 Crítico (Alta Prioridade):** Ruptura de estoque iminente ($\le \text{Estoque Mínimo}$), cobertura de suplemento insuficiente para o rebanho ($< 7$ dias) ou lotes com vencimento próximo e risco de perda.
   * **🟡 Atenção (Média Prioridade):** Estoque em faixa de alerta ($\le 1.5 \times \text{Estoque Mínimo}$), consumo atípico detectado ($> 2\sigma$) ou carência sanitária próxima.
   * **🟢 Normal (Baixa Prioridade):** Itens com estoque seguro e consumo regular.
   * **Linguagem Amigável:** Justificativas diretas ao produtor (ex.: *"Estoque cobre apenas 4 dias de consumo para 180 garrotes Nelore no Pasto 04"*).

2. **Gestão de Lotes de Animais & Rebanho:**
   * Cadastro completo com Nome do Lote, Categoria Zootécnica, Cabeças, Pasto/Localização, Escore de Condição Corporal (ECC de 1 a 5), Peso Médio Estimado e Consumo Diário/Cabeça.
   * Vinculação direta ao insumo suplementar (sal mineral, ração, suplemento proteico).
   * **Cálculo de Autonomia:** Projeção automática de quantos dias o estoque restante sustentará o lote.
   * **Interface Dupla:** Alternância dinâmica entre visualização em **Cards Visuais** e **Tabela Completa**, com barra de busca instantânea.
   * Operações completas de criação, edição e exclusão de lotes com modais integrados.

3. **Simulador Sazonal de Seca (Vale do Jamari / RO):**
   * Botão alternador no cabeçalho e suporte a parâmetro de URL (`/?seca=1`).
   * Simula o comportamento real do inverno amazônico: dobra o consumo diário de sal mineral/proteico por cabeça (ex.: 120g $\to$ 240g/dia), recalculando a velocidade de exaustão do estoque e antecipando compras antes do gado emagrecer.

4. **Painel de Indicadores Regionais:**
   * Cotação da arroba (@) do Boi Gordo em **Ariquemes / RO** (R$ 228,50 / @ — base de mercado Rondônia).
   * Total de cabeças de gado ativas no sistema.
   * Valor financeiro total imobilizado em estoque (R$).

5. **Movimentações e Validações Rigorosas (RN01 / RN02 / RN03):**
   * Suporte integral aos **13 campos oficiais do regulamento**.
   * Bloqueio rigoroso de estoque negativo (impede saídas maiores que o saldo em depósito).
   * Rastreabilidade por número de lote do fabricante e data de validade.
   * Importação CSV com prévia antes da confirmação e transação atômica (`transaction.atomic`).
   * **Reanálise em Tempo Real (RF01.3):** Ao salvar qualquer movimentação, o motor analítico recalcula imediatamente todos os alertas sem necessidade de intervenção manual.

---

## 4. Guia Rápido de Instalação e Execução

O sistema foi concebido para ser 100% reprodutível em ambientes Linux, macOS e Windows (PowerShell/CMD).

### Pré-requisitos
* **Python:** 3.12 ou superior (homologado no Python 3.14).
* **Git:** instalado e configurado.

### 4.1 Passo a Passo

```bash
# 1. Clonar o repositório
git clone https://github.com/IanPelentir/agrohack.git
cd agrohack

# 2. Criar o ambiente virtual (Linux / macOS)
python3 -m venv venv
source venv/bin/activate

# No Windows (PowerShell):
# python -m venv venv
# .\venv\Scripts\Activate.ps1

# 3. Instalar as dependências do projeto
pip install -r requirements.txt

# 4. Aplicar as migrações no banco de dados SQLite
python manage.py migrate

# 5. Popular o banco com a massa de dados de demonstração (Gado + Insumos)
python manage.py shell -c "from estoque.seed import popular_dados_demonstracao; popular_dados_demonstracao()"

# 6. Executar a suíte de testes automatizados
python manage.py test

# 7. Iniciar o servidor de desenvolvimento
python manage.py runserver
```

Após iniciar o servidor, abra no navegador:
* 🌐 **Painel Principal:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
* ☀️ **Simulação do Modo Seca:** [http://127.0.0.1:8000/?seca=1](http://127.0.0.1:8000/?seca=1)
* 📋 **Produtos e Lotes:** [http://127.0.0.1:8000/produtos/](http://127.0.0.1:8000/produtos/)
* ➕ **Nova Movimentação:** [http://127.0.0.1:8000/movimentacoes/nova/](http://127.0.0.1:8000/movimentacoes/nova/)
* 📊 **Análise de Consumo:** [http://127.0.0.1:8000/consumo/](http://127.0.0.1:8000/consumo/)

---

## 5. Critérios Analíticos e Regras de Negócio

### 5.1 Fórmulas Matemáticas do Motor Analítico

| Critério | Fórmula / Regra Lógica | Ação Disparada |
|---|---|---|
| **Saldo Atual** | $\text{Saldo} = \sum \text{Entradas} - \sum \text{Saídas}$ | Se saldo $\le \text{Estoque Mínimo} \implies$ 🔴 Alerta Crítico |
| **Cobertura Geral** | $\text{Dias de Cobertura} = \frac{\text{Saldo Atual}}{\text{Consumo Médio Diário (30 dias)}}$ | Se dias $< 7 \implies$ 🔴 Alerta Crítico de Ruptura |
| **Suplementação por Lote** | $\text{Consumo Diário Total} = \text{Cabeças} \times \text{Consumo/Cab.}$ | Compara com o saldo do insumo vinculado |
| **Simulação de Seca** | $\text{Consumo Seca} = \text{Consumo Normal} \times 2.0$ | Antecipa esgotamento do sal mineral/proteico |
| **Risco de Validade** | $\text{Dias para Vencer} \le 30 \text{ e } \text{Saldo} > \text{Consumo Projetado}$ | 🔴 Alerta de Perda Financeira de Medicamento |
| **Anomalia de Consumo** | $\|x - \mu\| > 2\sigma$ com base mínima de 5 saídas | 🟡 Alerta de Saída Atípica |

### 5.2 Tratamento Rigoroso de Dados (RN01, RN02, RN03)
* **RN01 / RN01.1 — Integridade de Estoque e Unidades:** Unidades incompatíveis (ex.: litros e sacas) nunca são somadas. Tentativas de retirar quantidade superior ao saldo em depósito são sumariamente bloqueadas com mensagem clara de erro.
* **RN02 — Preservação de Dados Ausentes:** Preços e datas de validade não informados são mantidos como nulos (`None`). O algoritmo **não converte ausência de custo em R$ 0,00**, evitando mascarar o valor patrimonial da fazenda.
* **RN03 — Comunicação Explícita de Incerteza:** Produtos com histórico menor que 5 movimentações exibem explicitamente: *"Não estimado: histórico insuficiente de movimentações"*, repudiando extrapolações levianas.
* **RN04 — Transparência e Explicabilidade:** Zero algoritmos "caixa preta". 100% das decisões são lógicas, determinísticas e auditáveis.

---

## 6. Validação Zootécnica e Veterinária

A modelagem de domínio contou com a validação contínua da integrante **Bruna Pereira da Silva** (Medicina Veterinária — IFRO):
1. **Escore de Condição Corporal (ECC):**
   * Escala de 1 a 5 para bovinos de corte e leite.
   * Lotes com ECC $\le 2.5$ em período seco demandam suplementação proteica/energética imediata para estancar a perda de musculatura.
2. **Nutrição de Ruminantes na Seca de Rondônia:**
   * No período das chuvas, o sal mineral comum (consumo médio de 80g a 120g/cab/dia) atende às necessidades básicas de fósforo e microminerais.
   * Na seca, o declínio da digestibilidade da forrageira exige a transição para sal proteinado (200g a 300g/cab/dia), gerando pico de demanda no barracão. O simulador traduz essa realidade com precisão.
3. **Manejo Sanitário:**
   * Controle de validade e lotes de vacinas (febre aftosa, brucelose, clostridioses) e antibióticos para garantir eficácia biológica e evitar resíduos químicos proibidos no leite e na carne.

---

## 7. Suíte de Testes Automatizados

O sistema conta com **15 testes automatizados** cobrindo todas as rotas e regras de negócio essenciais:

```bash
$ python manage.py test
Found 15 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
...............
----------------------------------------------------------------------
Ran 15 tests in 1.028s

OK
Destroying test database for alias 'default'...
```

### Matriz de Testes
| Caso de Teste | Escopo | Requisito Validado |
|---|---|---|
| `test_painel_renderiza_com_sucesso` | HTTP / View | RF02 (To-Do List carregada com HTTP 200) |
| `test_lista_produtos_renderiza` | HTTP / View | Listagem de insumos e categorias |
| `test_detalhe_produto_renderiza` | HTTP / View | Rastreabilidade de lotes e saldo |
| `test_analise_consumo_renderiza` | HTTP / View | Gráficos temporais de consumo (Chart.js) |
| `test_tela_importar_renderiza` | HTTP / View | RF01.1 (Importação de planilhas CSV) |
| `test_tela_movimentacoes_renderiza` | HTTP / View | RF01.2 (Registro dos 13 campos) |
| `test_saldo_e_alerta_critico` | Motor Analítico | RF03.1 (Estoque mínimo e prioridade ALTA) |
| `test_estimativa_duracao_estoque` | Motor Analítico | RF03.3 (Cálculo determinístico de cobertura em dias) |
| `test_alerta_validade_proxima` | Motor Analítico | RF03.2 (Vencimento $\le 30$ dias e risco de perda) |
| `test_bloqueio_estoque_negativo` | Regra de Negócio | RN01.1 (Rejeição de saída superior ao saldo) |
| `test_reanalise_imediata_ao_salvar_movimentacao` | Fluxo Completo | RF01.3 (Atualização imediata da To-Do List) |
| `test_lote_animais_calculo_consumo_diario` | Manejo Bovino | Consumo total diário do lote em kg |
| `test_lote_animais_crud_views` | Manejo Bovino | Criação, edição e exclusão de lotes de gado |
| `test_painel_exibe_metricas_regionais_e_gado` | Usabilidade | Cotação da @ Ariquemes e total de cabeças |
| `test_simulador_modo_seca` | Sazonalidade | Duplicação de consumo na estiagem e alerta crítico |

---

## 8. Estrutura do Repositório

```
agrohack/
├── manage.py                          # Utilitário de comando Django
├── requirements.txt                   # Dependências oficiais (Django 5.2 LTS)
├── README.md                          # Documentação técnica completa
├── agrohack/                          # Configurações globais do projeto Django
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py                    # Configuração de banco, static e apps
│   ├── urls.py                        # Roteamento global
│   └── wsgi.py
├── estoque/                           # Aplicação principal (AGROGADO)
│   ├── admin.py                       # Registro no Django Admin
│   ├── analises.py                    # Motor analítico, To-Do List e simulação de seca
│   ├── forms.py                       # Formulários com validação e integridade
│   ├── models.py                      # Modelos: Insumo, Movimentacao, Lote, LoteAnimais
│   ├── seed.py                        # Carga de dados de demonstração (gado e insumos)
│   ├── tests.py                       # Suíte com 15 testes automatizados
│   ├── urls.py                        # Rotas: painel, lotes, produtos, movimentações
│   ├── views.py                       # Controladores e renderização
│   └── migrations/                    # Histórico de migrações SQLite
├── templates/                         # Templates HTML5 Semânticos
│   ├── base.html                      # Layout base com seletor Modo Seca e navegação
│   └── estoque/
│       ├── painel.html                # Painel principal: To-Do List, KPIs e Rebanho
│       ├── lote_form.html             # Formulário de criação/edição de lotes
│       ├── produtos.html              # Catálogo de insumos e saldos
│       ├── detalhe_produto.html       # Ficha técnica e lotes por validade
│       ├── movimentacao_form.html     # Registro de entradas e saídas
│       ├── analise_consumo.html       # Visualização temporal de consumo
│       └── importar.html              # Ingestão de CSV com prévia de dados
├── static/                            # Arquivos estáticos
│   └── css/
│       └── style.css                  # Design System Vanilla CSS (alto contraste rural)
└── docs/                              # Documentos e referências do evento
    ├── regulamento-agrohack.pdf       # Regulamento oficial do AgroHack 2026/2
    ├── especificacao_de_requisitos.md # Mapeamento completo dos requisitos
    └── antigravity-agrohack-python-django-sqlite.md
```

---

## 9. Declaração de Uso Ético e Responsável de IA (RN04)

Em estrita consonância com o item 5 do regulamento do AgroHack 2026/2 e o requisito **RN04**:

1. **Escopo do Auxílio:** Ferramentas de Inteligência Artificial generativa (Google Antigravity e modelos de assistência) foram utilizadas exclusivamente como suporte técnico na geração inicial de esqueletos sintáticos e agilização de estilização CSS.
2. **Soberania do Domínio Rural:** Nenhuma regra zootécnica de nutrição animal, fórmula de semaforização ou critério de cálculo de estoques foi produzido de maneira autônoma ou opaca.
3. **Determinismo e Auditabilidade:** Todo o motor analítico opera por **algoritmos matemáticos explícitos e auditáveis**, viabilizando a comprovação passo a passo de cada alerta perante a comissão avaliadora do IFRO.
4. **Revisão e Homologação:** A integridade de código, segurança e funcionalidade foram integralmente auditadas, testadas e aprovadas pelos quatro integrantes da equipe.

---

## 10. Licença e Versão de Entrega

* **Evento de Avaliação:** AGROHACK 2026/2 — Semana Nacional de Ciência e Tecnologia (SNCT)
* **Data da Demonstração:** 29 de Outubro de 2026
* **Tag de Entrega:** `v1.0.0-snct2026`
* **Licença:** Distribuído sob a [Licença MIT](https://opensource.org/licenses/MIT). Permitido o uso acadêmico, evolução e disseminação com atribuição dos autores do IFRO Campus Ariquemes.
