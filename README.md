# AGROGADO — Gestão de Insumos e Recursos Rurais

> **Desafio:** *Gestão inteligente de insumos em uma propriedade rural*
> **Instituição:** Instituto Federal de Educação, Ciência e Tecnologia de Rondônia (IFRO) — *Campus* Ariquemes
> **Aplicação hospedada:** [https://agrohack.onrender.com/](https://agrohack.onrender.com/)
> **Apresentação prevista:** 29 de outubro de 2026, durante a SNCT
> **Ambiente validado:** Python 3.13.16 • Django 5.2.18 • SQLite • templates Django • HTML/CSS/JavaScript • Chart.js
> **Testes:** 33 testes automatizados aprovados em `python manage.py test estoque` (última verificação registrada neste README)

---

## 1. Identificação da Equipe

A equipe reúne estudantes de Análise e Desenvolvimento de Sistemas e Medicina Veterinária. O regulamento exige equipe de 2 a 4 estudantes e ao menos um integrante de ADS:

| Integrante | Curso / Matrícula | Função no Projeto | Responsabilidades Principais |
|---|---|---|---|
| **Ian Pelentir Ramos** | ADS — 4º período | **Integrante responsável** | Arquitetura Django, modelagem relacional e integração dos módulos |
| **Bruna Pereira da Silva** | Medicina Veterinária — 2º período | Consultoria de domínio rural | Apoio à validação de informações pecuárias e sanitárias |
| **Alan Menezes de Araújo** | ADS — 4º período | Motor analítico e testes | Regras determinísticas, alertas, cobertura de estoque e testes |
| **Marco Antonio de Oliveira Medeiros** | ADS — 4º período | Interface e usabilidade | Painel, formulários e experiência de uso |

* **Integrante responsável:** Ian Pelentir Ramos.
* **Local:** IFRO — Campus Ariquemes, Rondônia.

---

## 2. Problema e público

O desafio do AGROHACK pede uma solução que transforme registros de produtos e movimentações em informações úteis para reconhecer risco de falta, vencimento, excesso, consumo fora do padrão e valor financeiro parado. O público principal é o responsável pelo estoque de uma propriedade rural; o sistema deve explicar os motivos dos alertas e comunicar incerteza quando os dados forem insuficientes.

O AGROGADO organiza entradas, saídas, estoque, histórico e alertas em um painel. Também inclui recursos demonstrativos para rebanho, ativos da fazenda e transferências de produção interna, sem substituir a validação do responsável pela propriedade.

---

## 3. Arquitetura e Funcionalidades do Sistema

```
                    ┌─────────────────────────────┐
                    │       PAINEL AGROGADO       │
                    │ Alertas • Tarefas • Estoque │
                    └──────────────┬──────────────┘
                 ┌─────────────────────┼──────────────────────┐
                 ▼                     ▼                      ▼
               ┌───────────────┐    ┌────────────────┐     ┌──────────────────┐
               │ Produtos e    │    │ Recursos rurais│     │ Rebanho e análise│
               │ movimentações │    │ Ativos/manutenção│   │ consumo/validade│
               └───────────────┘    └────────────────┘     └──────────────────┘
                 └────────────── transferências internas ─────┘
```

### 3.1 Módulos Principais

1. **Alertas e tarefas persistentes:**
   * **Alta prioridade:** saldo zerado/negativo, saldo no mínimo, lote vencido com saldo ou manutenção de ativo marcada como necessária.
   * **Média prioridade:** saldo até 1,5 vez o mínimo, validade próxima sem histórico suficiente e outras condições definidas pelo motor.
   * Cada alerta apresenta justificativa. Uma tarefa pode ser criada a partir do alerta, concluída ou reaberta. Concluir uma tarefa não esconde o alerta: ele continua enquanto a condição de origem persistir.

2. **Gestão de Lotes de Animais & Rebanho:**
   * Cadastro completo com Nome do Lote, Categoria Zootécnica, Cabeças, Pasto/Localização, Escore de Condição Corporal (ECC de 1 a 5), Peso Médio Estimado e Consumo Diário/Cabeça.
   * Vinculação direta ao insumo suplementar (sal mineral, ração, suplemento proteico).
   * **Cálculo de Autonomia:** estimativa usando o consumo cadastrado do lote e o saldo do produto vinculado; a tela sinaliza quando não há dados suficientes.
   * **Interface Dupla:** Alternância dinâmica entre visualização em **Cards Visuais** e **Tabela Completa**, com barra de busca instantânea.
   * Operações completas de criação, edição e exclusão de lotes com modais integrados.

3. **Simulador Sazonal de Seca (Vale do Jamari / RO):**
   * Botão alternador no cabeçalho e suporte a parâmetro de URL (`/?seca=1`).
   * Cenário de simulação que aplica fator 2 ao consumo diário configurado dos lotes. É uma hipótese demonstrativa, não uma previsão meteorológica nem uma recomendação zootécnica universal.

4. **Painel de Indicadores Regionais:**
   * Exibe uma cotação de referência configurada para demonstração; não é cotação de mercado em tempo real.
   * Total de cabeças de gado ativas no sistema.
   * Valor financeiro total imobilizado em estoque (R$).

5. **Estoque, rastreabilidade e importação:**
   * Cadastro de itens com categoria, tipo específico livre, unidade, embalagem, peso/volume e dados patrimoniais quando aplicáveis.
   * Bloqueio rigoroso de estoque negativo (impede saídas maiores que o saldo em depósito).
   * Rastreabilidade por número de lote do fabricante e data de validade.
   * Importação CSV com prévia antes da confirmação e transação atômica (`transaction.atomic`).
   * **Reanálise em Tempo Real (RF01.3):** Ao salvar qualquer movimentação, o motor analítico recalcula imediatamente todos os alertas sem necessidade de intervenção manual.

6. **Ativos e produção interna:**
   * Veículos e máquinas têm status de manutenção, consumo médio, odômetro/horímetro e histórico de serviços.
   * Combustíveis, óleos e peças podem ser associados ao ativo utilizado.
   * Transferências internas registram recurso de origem, recurso de destino, origem externa/própria e as quantidades em unidades independentes.

---

## 4. Guia Rápido de Instalação e Execução

O projeto foi validado em Linux com Python 3.13.16 e Django 5.2.18. Outras versões e sistemas operacionais podem funcionar, mas não foram verificados nesta execução.

### Pré-requisitos
* **Python:** 3.13 (versão validada neste projeto).
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

# 5. Opcional: carregar dados simulados em um banco descartável
# ATENÇÃO: este comando apaga e recria os registros do app estoque.
python manage.py popular_dados

# 6. Executar os testes automatizados
python manage.py test estoque

# 7. Iniciar o servidor de desenvolvimento
python manage.py runserver
```

Rotas principais após iniciar o servidor:
* **Painel e alertas:** `http://127.0.0.1:8000/`
* **Simulação sazonal:** `http://127.0.0.1:8000/?seca=1`
* **Catálogo de itens:** `http://127.0.0.1:8000/produtos/`
* **Nova movimentação:** `http://127.0.0.1:8000/movimentacoes/nova/`
* **Recursos, manutenção e produção interna:** `http://127.0.0.1:8000/recursos/`
* **Análise de consumo:** `http://127.0.0.1:8000/consumo/`
* **Importação CSV:** `http://127.0.0.1:8000/importar/`

### Dados de demonstração

Os dados gerados por `python manage.py popular_dados` são fictícios e servem apenas para testes e demonstrações. A função apaga e recria os registros de produtos, movimentações, lotes, rebanho, ativos, manutenções e transferências; use-a somente em banco descartável ou após fazer uma cópia. O conjunto oficial do desafio deverá ser importado quando for disponibilizado pela organização, e não deve ser substituído pela massa simulada.

---

## 5. Critérios Analíticos e Regras de Negócio

### 5.1 Fórmulas Matemáticas do Motor Analítico

| Critério | Fórmula / Regra Lógica | Ação Disparada |
|---|---|---|
| **Saldo** | $\sum \text{Entradas} - \sum \text{Saídas}$, sempre na unidade cadastrada do item | Saldo zerado ou até o mínimo: prioridade alta; até 1,5× o mínimo: média |
| **Cobertura histórica** | Saldo dividido pelo consumo médio diário dos últimos 30 dias | Só estima com ao menos 2 saídas na janela; caso contrário informa histórico insuficiente |
| **Autonomia do rebanho** | Cabeças × consumo diário configurado por cabeça, comparado ao estoque vinculado | Complementa a cobertura histórica para produtos associados aos lotes |
| **Cenário de seca** | Consumo configurado × fator de simulação 2,0 | Cenário hipotético, sem previsão climática ou recomendação automática de dieta |
| **Validade** | Lotes vencidos com saldo ou vencimento em até 30 dias combinado com consumo estimado | Prioriza perda provável; com histórico insuficiente, sinaliza a limitação |
| **Saída atípica** | Comparação estatística das retiradas, com base mínima implementada no motor | Alerta explicável; não determina sozinho a causa da retirada |
| **Manutenção de ativo** | Status marcado como revisão, manutenção ou inativo | Gera alerta ligado ao veículo/maquinário |

### 5.2 Tratamento Rigoroso de Dados (RN01, RN02, RN03)
* **Unidades e saldo:** cada produto mantém uma unidade canônica; não se somam litros e sacos. Saídas acima do saldo total ou do saldo do lote informado são bloqueadas.
* **RN02 — Preservação de Dados Ausentes:** Preços e datas de validade não informados são mantidos como nulos (`None`). O algoritmo **não converte ausência de custo em R$ 0,00**, evitando mascarar o valor patrimonial da fazenda.
* **Histórico insuficiente:** cobertura histórica requer ao menos 2 saídas nos últimos 30 dias; a análise de anomalia usa sua própria base mínima. Ausência de dados não é tratada como consumo zero.
* **Transparência:** os alertas implementados são regras determinísticas com justificativa. A aplicação não usa IA em tempo de execução.

---

## 6. Validação Zootécnica e Veterinária

O módulo de rebanho registra categoria, número de cabeças, pasto, ECC, peso estimado e consumo configurado por cabeça. O sistema calcula indicadores a partir desses valores, mas não diagnostica animais nem prescreve dieta, tratamento veterinário ou protocolo sanitário. As referências demonstrativas devem ser revisadas por profissionais e substituídas por dados validados da propriedade.

---

## 7. Validação e testes

A suíte Django cobre painel, catálogo, importação, movimentações, alertas, ativos, manutenção, tarefas persistentes e transferências de produção interna. Na última verificação, foram aprovados **33 testes**:

```bash
$ python manage.py test estoque
Found 33 test(s).
Creating test database for alias 'default'...
System check identified no issues (0 silenced).
.................................
----------------------------------------------------------------------
Ran 33 tests

OK
Destroying test database for alias 'default'...
```

Os testes também verificam que concluir uma tarefa não oculta um alerta enquanto a condição de origem persistir e que a reposição efetiva remove o alerta após a reanálise.

---

## 8. Estrutura do repositório

```text
agrohack/
├── manage.py
├── requirements.txt
├── agrohack_project/                 # Configurações Django
├── estoque/                          # Modelos, formulários, regras e views
│   ├── analises.py                    # Alertas e estimativas determinísticas
│   ├── management/commands/           # Comando popular_dados
│   ├── migrations/                    # Histórico de alterações do banco
│   ├── models.py                      # Produtos, ativos, rebanho e transferências
│   ├── seed.py                        # Dados simulados para demonstração
│   ├── tests.py                       # Testes automatizados
│   └── views.py
├── templates/
│   ├── base.html
│   └── estoque/                       # Painel, recursos, formulários e análises
├── static/css/style.css
├── static/js/
└── docs/                              # Regulamento e especificações
```

---

## 9. Uso de IA, autoria e transparência

Ferramentas de IA generativa, incluindo Google Antigravity e GitHub Copilot, foram usadas como apoio durante a implementação, revisão de código, elaboração de testes e atualização da documentação. O uso deve ser declarado no repositório de entrega conforme as ferramentas e contribuições efetivamente utilizadas pela equipe.

O sistema não usa IA em tempo de execução para calcular saldos ou emitir alertas. As regras do motor analítico são determinísticas e exibem justificativas. Os integrantes devem revisar o código, os resultados, as referências e as limitações antes da apresentação.

---

## 10. Preparação para entrega

O regulamento pede repositório acessível, instruções reproduzíveis, demonstração funcional, vídeo, explicação dos dados e critérios, evidências de teste e identificação da versão avaliada. Antes da entrega, conferir:

- importar e demonstrar a base oficial do desafio quando a organização a disponibilizar; os registros do comando `popular_dados` são simulados;
- gravar um vídeo demonstrativo e preparar a apresentação para a SNCT de 29/10/2026;
- registrar um commit ou tag específico da versão entregue;
- escolher e incluir um arquivo de licença antes de declarar condições de redistribuição.

**Estado deste repositório:** não há arquivo `LICENSE` nem tag de entrega no momento desta revisão. A licença e a versão final devem ser definidas pela equipe, não presumidas neste README.

## 11. Referências do desafio

- [Regulamento AGROHACK 2026/2](docs/regulamento-agrohack.pdf)
- [Especificação de requisitos do projeto](docs/especificacao_de_requisitos.md)
- [Especificação técnica do ambiente](docs/antigravity-agrohack-python-django-sqlite.md)
