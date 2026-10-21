# AgroHack 2026/2 — Gestão Inteligente de Insumos Rurais

> **Desafio Oficial:** *Gestão inteligente de insumos em uma propriedade rural*  
> **Instituição:** Instituto Federal de Educação, Ciência e Tecnologia de Rondônia (IFRO) — *Campus* Ariquemes  
> **Evento:** Semana Nacional de Ciência e Tecnologia (SNCT 2026) — 29 de Outubro de 2026  
> **Stack Tecnológica:** Python 3.14 • Django 5.2 LTS • SQLite 3 • HTML5/CSS3 • Chart.js  

---

## 1. Equipe

A equipe é multidisciplinar, integrando competências de tecnologia da informação e ciências agrárias para garantir aderência real às rotinas da produção rural no estado de Rondônia:

| Nome do Integrante | Curso / Período | Função no Projeto | Responsabilidade Principal |
|---|---|---|---|
| **Ian Pelentir Ramos** | ADS — 4º período | **Líder de Projeto & Arquiteto Back-end** | **Integrante Responsável**; arquitetura Django, modelagem de dados e conformidade regulamentar |
| **Bruna Pereira da Silva** | Medicina Veterinária — 2º período | **Consultora de Domínio Rural & Validação** | Definição das regras de negócio de medicamentos, defensivos, controle de lotes, carência e validação de campo |
| **Alan Menezes de Araújo** | ADS — 4º período | **Engenheiro de Dados & Motor Analítico** | Implementação das regras determinísticas de análise, cálculos estatísticos e suíte de testes |
| **Marco Antonio de Oliveira Medeiros** | ADS — 4º período | **Desenvolvedor Front-end & Usabilidade** | Construção da interface com foco no produtor rural (To-Do List, acessibilidade de semáforo e Chart.js) |

* **Integrante Responsável pelo Projeto:** Ian Pelentir Ramos (ADS — 4º período — IFRO Campus Ariquemes)  
* **Contato Técnico:** `ianpelentir7@gmail.com`

---

## 2. Problema e Público

### Contexto Rural
Na rotina de propriedades rurais de médio e pequeno porte em Rondônia (como na bacia leiteira e na produção agropecuária do Vale do Jamari), o controle de insumos frequentemente é realizado em cadernos manuais ou planilhas desconexas. O desafio do produtor não é a simples falta de um cadastro de itens, mas a **ausência de diagnósticos práticos e acionáveis** sobre o que precisa ser feito hoje para evitar prejuízos.

### Decisões Reais Apoiadas pela Solução
1. **Prevenção de Perdas de Medicamentos e Insumos Perecíveis:** Medicamentos veterinários (vacinas, antibióticos, antiparasitários), sementes fiscalizadas e defensivos agrícolas possuem prazos de validade críticos e alto custo unitário. A solução cruza o estoque disponível com o ritmo recente de uso, alertando antes que o insumo expire na prateleira sem uso.
2. **Previsão de Ruptura de Estoque em Atividades Críticas:** Antecipar a falta de insumos essenciais antes de períodos sazonais de preparo de solo, plantio ou gradagem, evitando a paralisação de tratores e equipes por falta de combustível, sementes ou adubos de cobertura.
3. **Equilíbrio Financeiro e Redução de Capital Parado:** Identificação de itens com excesso de estoque e alto valor financeiro imobilizado, permitindo melhor negociação de compras futuras e liberação de fluxo de caixa para a fazenda.

---

## 3. Solução

O sistema é uma aplicação Web de apoio à tomada de decisão construída em **Django + SQLite**, orientada à rotina diária do produtor rural:

* **Painel Principal Estilo "To-Do List" (RF02.1):** A tela inicial funciona como uma lista prioritária de tarefas do dia. Ao abrir o sistema, o produtor visualiza imediatamente as pendências que exigem ação, sem necessidade de navegar por menus complexos.
* **Semaforização Acessível em 3 Níveis (RF02.2 / RNF01):** Os alertas são ordenados por urgência (🔴 **ALTA**, 🟡 **MÉDIA**, 🟢 **BAIXA**). A sinalização não depende apenas de cores; ela combina rótulos textuais legíveis, ícones e contrastes adequados para uso em dispositivos móveis no campo ou sob luz solar.
* **Justificativas Claras e Amigáveis (RF02.3):** Cada alerta é acompanhado de explicação em linguagem acessível (ex.: *"Estoque crítico: mantendo o ritmo recente de saídas, o saldo será suficiente por apenas ~8 dias"*).
* **Acompanhamento Temporal Interativo (RF03.6):** Gráficos de sazonalidade e consumo gerados com Chart.js, permitindo correlacionar as retiradas com as épocas de plantio, calagem ou vacinação.
* **Ingestão com Validação Linha a Linha (RF01.1 / RF01.2):** Importação de planilhas CSV com suporte aos 13 campos do regulamento, exibição de prévia e transação atômica que impede dados inconsistentes no banco.

### Acesso à Aplicação
* **Execução Local:** `http://127.0.0.1:8000/` (após seguir o passo a passo de instalação).
* **Demonstração Online:** *(Opcional, conforme link disponibilizado no ambiente de apresentação do evento)*.

---

## 4. Como Testar

Instruções reprodutíveis para execução do ambiente de desenvolvimento no Linux/Windows/macOS:

### Pré-requisitos
* **Python:** versão 3.12 ou superior (testado e homologado no Python 3.14).
* **Git:** instalado na máquina.

### Passo a Passo de Execução

```bash
# 1. Clonar o repositório oficial
git clone https://github.com/IanPelentir/agrohack.git
cd agrohack

# 2. Criar e ativar o ambiente virtual (Linux / macOS)
python3 -m venv venv
source venv/bin/activate

# No Windows (PowerShell):
# python -m venv venv
# .\venv\Scripts\Activate.ps1

# 3. Instalar as dependências oficiais do projeto
pip install -r requirements.txt

# 4. Executar as migrações do banco de dados SQLite
python manage.py migrate

# 5. Executar os testes automatizados para verificar a integridade
python manage.py test

# 6. Iniciar o servidor de desenvolvimento Django
python manage.py runserver
```

Após iniciar o servidor, abra o navegador e acesse:  
👉 **[http://127.0.0.1:8000/](http://127.0.0.1:8000/)**

---

## 5. Dados e Critérios de Análise

### 5.1 Campos Suportados (RF01.2)
A base de dados suporta os **13 campos oficiais** descritos no regulamento do AgroHack:
1. `produto` (Nome comercial / especificação do insumo)
2. `categoria` (Defensivos, Fertilizantes, Medicamentos Veterinários, Sementes, Combustíveis, etc.)
3. `unidade` (kg, L, sc, frasco, dose, un)
4. `quantidade` (Volume numérico movimentado ou estocado)
5. `estoque_minimo` (Parâmetro de segurança operacional)
6. `tipo_movimentacao` (`ENTRADA` ou `SAIDA`)
7. `data_movimentacao` (Data da operação)
8. `preco_aquisicao` (Custo unitário pago pelo insumo)
9. `lote` (Código de rastreabilidade do fabricante)
10. `data_validade` (Data de expiração do lote perecível)
11. `fornecedor` (Origem comercial do insumo)
12. `destino` (Setor, pasto, talhão ou lote de animais de aplicação)
13. `responsavel` (Colaborador que realizou a retirada/aplicação)

### 5.2 Tratamento Rigoroso de Dados
* **Incompatibilidade de Unidades (RN01):** Registros com unidades de medida distintas (ex.: litros vs. quilogramas) para o mesmo produto **nunca são somados diretamente**. O sistema emite alerta de incompatibilidade e segrega os saldos por unidade.
* **Tratamento de Dados Ausentes (RN02):** A ausência de preço unitário ou data de validade é mantida como nula (`None`). O algoritmo **não converte ausência de preço em R$ 0,00**, evitando distorcer o valor total do estoque ou os custos médios.
* **Comunicação de Incerteza (RN03):** Se um insumo possui histórico insuficiente (menos de 5 retiradas registradas), o sistema exibe expressamente: *"Não estimado: histórico insuficiente de movimentações"*, recusando-se a inventar previsões infundadas.
* **Períodos sem Movimento:** Meses sem saídas no gráfico temporal representam *ausência de observação*, e **não prova de consumo zero futuro**.

### 5.3 Critérios Lógicos de Cálculo
* **Estoque Crítico (RF03.1):**
  $$\text{Saldo Atual} = \sum \text{Entradas} - \sum \text{Saídas}$$
  - $\text{Saldo} \le \text{Estoque Mínimo} \implies$ **🔴 Prioridade Alta**
  - $\text{Estoque Mínimo} < \text{Saldo} \le 1.5 \times \text{Estoque Mínimo} \implies$ **🟡 Prioridade Média**
  - $\text{Saldo} > 1.5 \times \text{Estoque Mínimo} \implies$ **🟢 Prioridade Baixa** (Regular)
* **Duração Estimada do Estoque (RF03.3):**
  $$\text{Consumo Médio Diário} = \frac{\text{Total de Saídas na Janela (30 dias)}}{30}$$
  $$\text{Duração Estimada (dias)} = \frac{\text{Saldo Atual}}{\text{Consumo Médio Diário}}$$
* **Risco de Validade e Perdas (RF03.2):**
  Se $(\text{Data de Validade} - \text{Hoje}) \le 30\text{ dias}$ e a quantidade restante do lote for superior à projeção de consumo até o vencimento, gera alerta de **🔴 Prioridade Alta** com indicação de perda iminente.
* **Detecção de Anomalias (RF03.4):**
  Registros de saída com desvio superior a 2 desvios-padrão ($|x - \mu| > 2\sigma$) em relação à média histórica (com base mínima de 5 registros).

---

## 6. Demonstração e Reanálise

### Reanálise Automática em Tempo Real (RF01.3)
Um dos requisitos centrais do desafio é demonstrar a capacidade do sistema de reprocessar todas as análises imediatamente após qualquer alteração:

1. Acesse o menu **"Nova Movimentação"** (`/movimentacoes/nova/`).
2. Selecione um insumo que atualmente esteja em situação regular (🟢 Prioridade Baixa).
3. Registre uma movimentação do tipo **"Saída"** com quantidade suficiente para rebaixar o saldo abaixo do estoque mínimo.
4. Clique em **"Salvar Movimentação e Reanalisar Estoque"**.
5. O sistema redirecionará imediatamente para a tela inicial (`/`), onde a nova pendência de **Estoque Crítico** (🔴 Alta Prioridade) aparecerá instantaneamente no topo da lista "To-Do", com a justificativa recalculada.

### Vídeo Demonstrativo
* **Link da Apresentação:** *(Espaço reservado para inclusão do link do YouTube / Loom com a demonstração prática da ferramenta utilizando os dados do desafio)*  
  `https://youtu.be/exemplo-agrohack-2026-demonstracao`

---

## 7. Validação e Testes

### 7.1 Testes Automatizados
O projeto conta com testes de unidade e integração utilizando o framework oficial do Django:
```bash
python manage.py test
```
* **Evidências Cobertas:**
  - Verificação de renderização e rotas HTTP 200 de todas as telas (`painel`, `produtos`, `detalhe`, `consumo`, `importar`, `movimentações`).
  - Testes das fórmulas determinísticas de saldo, cobertura e semaforização.
  - Teste de integridade de formulários e tratamento de erros de importação CSV.

### 7.2 Validação de Domínio (Medicina Veterinária)
A integrante Bruna Pereira da Silva (estudante de Medicina Veterinária — 2º período) conduziu a validação dos fluxos com foco nas práticas de campo:
* **Medicamentos e Vacinas:** Confirmação de que produtos biológicos não podem ter prazos de carência e validade ignorados. O controle por lote individual foi validado como essencial para evitar a aplicação de lotes vencidos no rebanho.
* **Linguagem Acessível:** Ajuste dos textos das justificativas para evitar termos técnicos excessivos de computação (como *"desvio padrão"*) e apresentar explicações diretas ao produtor (como *"saída atípica muito acima da média recente"*).

### 7.3 Limitações Conhecidas do MVP
* O sistema opera com acesso direto monousuário, sem tela de login/autenticação individual (decisão registrada para focar 100% da avaliação nos algoritmos analíticos e na praticidade de uso).
* A conversão automática entre unidades de volume (litros) e massa (quilos) não é realizada sem uma tabela de densidade específica do produto; o sistema opta com segurança por segregar e alertar o usuário (RN01).

---

## 8. Tecnologias e Uso de IA

### 8.1 Stack Tecnológico
* **Linguagem:** Python 3.14
* **Framework Web:** Django 5.2 LTS (arquitetura MTV — Model, Template, View)
* **Banco de Dados:** SQLite 3 (em conformidade com o regulamento do AgroHack)
* **Interface & Estilos:** HTML5 semântico, CSS3 puro (Vanilla CSS com Design System voltado à acessibilidade rural e alto contraste)
* **Visualização Gráfica:** Chart.js 4.4.x via CDN

### 8.2 Declaração de Uso Responsável de Inteligência Artificial (RN04)
Em cumprimento ao item 5 do regulamento oficial e ao requisito **RN04**, a equipe declara com total transparência:

1. **Apoio no Desenvolvimento:** Foram utilizadas ferramentas de Inteligência Artificial generativa (Google Antigravity e modelos de assistência ao código) exclusivamente como apoio na estruturação inicial de esqueletos de código, geração de marcações HTML e conferência de sintaxe.
2. **Autonomia e Validação Humana:** Nenhuma decisão agronômica, regra de negócio, critério estatístico de cálculo ou fórmula de semaforização foi gerada de forma autônoma ou "caixa preta" por IA.
3. **Determinismo:** O motor de análise de estoque funciona por **regras determinísticas, testáveis e 100% explicáveis**, garantindo que toda recomendação possa ser auditada e justificada perante a banca avaliadora.
4. **Revisão Integral:** Todo o código-fonte, templates e documentação foram revisados, testados, refatorados e aprovados pelos quatro integrantes da equipe.

---

## 9. Autoria e Licença

### Autoria
Este projeto foi integralmente concebido e desenvolvido pelos alunos do **IFRO — *Campus* Ariquemes** para participação no **AGROHACK 2026/2**.

### Segurança e Privacidade (RNF03)
* O repositório não contém senhas, chaves privadas de API ou credenciais de produção expostas.
* A chave `SECRET_KEY` do Django é lida a partir de variáveis de ambiente (`DJANGO_SECRET_KEY`), com valor padrão seguro restrito ao ambiente de desenvolvimento local.
* Arquivos temporários, bancos locais com dados de teste e pastas virtuais estão protegidos no `.gitignore`.

### Licença
Este software é distribuído sob a licença **MIT**, permitindo o uso acadêmico, aperfeiçoamento e reutilização com a devida atribuição de autoria.

---

## 10. Versão de Entrega

* **Evento de Avaliação:** AGROHACK 2026/2 — Semana Nacional de Ciência e Tecnologia (SNCT)  
* **Data da Demonstração:** 29 de Outubro de 2026  
* **Tag de Entrega:** `v1.0.0-snct2026`  
* **Identificador de Commit Final:** `HEAD` (auditado com `python manage.py check` e suíte de testes aprovada)  
* **Status do MVP:** Completo, testado e pronto para homologação com os dados oficiais do desafio.
