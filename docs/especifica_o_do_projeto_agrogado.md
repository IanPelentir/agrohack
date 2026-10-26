# Especificação Integrada de Requisitos e Regras de Negócio
## AGROGADO: Sistema de Gestão Inteligente de Insumos Rurais e Manejo Pecuário
### AgroHack 2026/2 — Sistema de Apoio à Decisão Baseado em Regras Determinísticas

---

> **Instituição:** Instituto Federal de Educação, Ciência e Tecnologia de Rondônia (IFRO) — *Campus* Ariquemes  
> **Evento:** Semana Nacional de Ciência e Tecnologia (SNCT 2026) — 29 de Outubro de 2026  
> **Desafio Oficial:** *Gestão inteligente de insumos em uma propriedade rural com foco em pecuária de corte e leite*  
> **Stack Oficial:** Python 3.14 • Django 5.2 LTS • SQLite 3 • HTML5/CSS3 • Chart.js  
> **Versão do Documento:** 3.0 (Consolidação oficial com Lotes, Sanidade Animal, GTA e Regras Zootécnicas)

---

## 1. Visão Geral e Contexto do Projeto

### 1.1 Contexto e Justificativa
Propriedades rurais de pequeno e médio porte em Rondônia (especialmente na bacia leiteira e na pecuária de corte do Vale do Jamari) lidam diariamente com dezenas de insumos críticos distribuídos entre sanidade animal, suplementação nutricional, defensivos agrícolas, combustíveis e insumos para pastagens. 

O controle manual em cadernos ou planilhas desconexas costuma gerar sérios prejuízos financeiros e riscos legais/sanitários:
- **Perda de insumos perecíveis e vacinas:** Medicamentos veterinários e vacinas obrigatórias vencendo na prateleira antes da aplicação no rebanho.
- **Ruptura de estoque operacional:** Esgotamento repentino de sal mineral, ração concentrada ou combustível no meio de períodos críticos (como a transição seca/águas).
- **Inconformidade com a Defesa Sanitária:** Falta de controle sobre as campanhas oficiais de vacinação (IDARON) e sobre o histórico de carência para abate ou ordenha, gerando riscos de sanções e perda de mercado.
- **Desequilíbrio financeiro:** Ausência de visibilidade sobre o capital imobilizado em excesso versus itens com risco iminente de falta.

### 1.2 Objetivo da Solução
Desenvolver uma aplicação Web MVP intuitiva e determinística, centrada em um **Dashboard no formato *To-Do List*** com **sinalização semafórica acessível (🔴 ALTA / 🟡 MÉDIA / 🟢 BAIXA)**. O sistema cruza os **lotes de gado e rebanho** com o **inventário de insumos**, transformando registros em **diagnósticos explicáveis em linguagem simples**, orientando o produtor rural sobre as ações que precisam ser tomadas no dia para evitar prejuízos.

---

## 2. Partes Interessadas e Perfis de Usuário

| Perfil | Descrição e Papel no Sistema |
|---|---|
| **Produtor Rural / Capataz / Gestor da Propriedade** | Visualiza pendências prioritárias na tela inicial (*To-Do List*), confere alertas operacionais do rebanho/estoque e registra entradas/saídas rápidas sem burocracia. |
| **Médico(a) Veterinário(a) / Consultor(a) de Campo** | Valida protocolos sanitários obrigatórios, prazos de carência de medicamentos, escore de condição corporal (ECC) dos lotes e estimativas de consumo zootécnico. |
| **Banca Avaliadora do AGROHACK 2026/2** | Avalia conformidade com os 13 campos do regulamento, integração zootécnica, transparência dos cálculos, explicabilidade das justificativas e utilidade prática. |

---

## 3. Requisitos Funcionais (RF)

### 3.1 Ingestão, Importação e Atualização de Dados (RF01)
- **RF01.1 — Importação de Planilha CSV:** O sistema deve suportar upload e ingestão de arquivos CSV contendo os registros oficiais disponibilizados pela organização do evento, suportando delimitadores comuns (`,` e `;`) com prévia antes da confirmação.
- **RF01.2 — Suporte aos 13 Campos Oficiais do Regulamento:** O modelo de dados e a importação devem reconhecer e tratar rigorosamente os 13 campos oficiais do desafio:
  1. `produto`: Nome comercial / identificação do insumo.
  2. `categoria`: Categoria operacional (Sanidade Animal, Nutrição/Suplementação, Defensivos, Fertilizantes, Sementes, Combustíveis, Manutenção, EPIs).
  3. `unidade`: Unidade de medida associada (kg, L, sc, frasco, dose, un).
  4. `quantidade`: Volume numérico estocado ou movimentado.
  5. `estoque_minimo`: Nível de segurança estabelecido para reposição.
  6. `tipo_movimentacao`: Sentido da movimentação (`ENTRADA` ou `SAIDA`).
  7. `data_movimentacao`: Data efetiva da operação.
  8. `preco_aquisicao`: Custo unitário pago na aquisição do lote (R$).
  9. `lote`: Código do lote do fabricante para rastreabilidade de validade.
  10. `data_validade`: Data de expiração dos insumos perecíveis.
  11. `fornecedor`: Razão social ou nome fantasia da empresa fornecedora.
  12. `destino`: Setor, pasto, lote de animais ou talhão onde ocorreu a aplicação/uso.
  13. `responsavel`: Colaborador, operador ou Médico Veterinário encarregado do registro.
- **RF01.3 — Reanálise Automática em Tempo Real:** Toda inclusão manual ou importação de novas movimentações ou lotes de gado deve disparar o recálculo imediato de saldos, durações estimadas e alertas sem necessidade de intervenção técnica.

### 3.2 Painel Principal e Gestão de Alertas (Dashboard To-Do List) (RF02)
- **RF02.1 — Dashboard Estilo To-Do List:** A tela inicial deve funcionar como uma lista priorizada de ações práticas do dia, permitindo ao produtor identificar rapidamente as providências emergenciais.
- **RF02.2 — Priorização Semafórica Acessível:**
  - 🔴 **Prioridade ALTA (Vermelho):** Itens com saldo $\le$ estoque mínimo; lotes com validade vencida e saldo restante; vacinas/medicamentos com risco de vencimento antes do consumo projetado; campanhas de vacinação obrigatória (IDARON) com prazo final em $\le 7$ dias sem cobertura do rebanho.
  - 🟡 **Prioridade MÉDIA (Amarelo):** Itens com saldo entre 100% e 150% do estoque mínimo (zona de atenção para reposição); itens perecíveis com vencimento em até 30 dias; alertas sazonais de transição de período (ex: entrada na seca).
  - 🟢 **Prioridade BAIXA (Verde / Monitoramento):** Alertas informativos de capital expressivo imobilizado com alta cobertura de estoque ou rebanho com suplementação regular e segura.
- **RF02.3 — Justificativa Clara e Explicável:** Nenhum alerta pode ser exibido sem justificativa em linguagem natural amigável (ex.: *"Estoque crítico de Sal Mineral 90: Saldo atual (2 sacos) atinge o limite mínimo para o Lote 01 (150 cabeças) — estimado para esgotar em ~4 dias"*).

### 3.3 Motor de Análises Inteligentes do Estoque e Manejo Pecuário (RF03)
- **RF03.1 — Risco de Falta e Estoque Crítico:** Identificar produtos cujo saldo atual esteja igual ou abaixo do estoque mínimo, ou com saldo zerado/negativo.
- **RF03.2 — Análise de Validade e Perdas de Insumos:** Cruzar a data de validade dos lotes com o ritmo de consumo zootécnico recente. Se a quantidade remanescente for superior ao consumo projetado até a data de expiração, sinalizar perda financeira iminente com o volume estimado de descarte.
- **RF03.3 — Estimativa de Duração / Cobertura de Estoque por Lote:** Calcular os dias restantes de estoque projetados a partir do consumo diário do rebanho associado (ex: gramas/cabeça/dia de suplemento).
- **RF03.4 — Controle de Lotes de Animais e ECC:** Permitir o gerenciamento de lotes de corte e leite, registrando a quantidade de cabeças, pasto/localização e Escore de Condição Corporal (ECC de 1 a 5).
- **RF03.5 — Monitoramento de Campanhas Sanitárias (IDARON):** Acompanhar prazos legais de vacinação obrigatória (Aftosa, Brucelose, Raiva) e registrar a aplicação por lote com abatimento automático de doses no estoque.
- **RF03.6 — Controle de Trânsito Animal (GTA):** Registrar entradas e saídas de animais por meio de Guias de Trânsito Animal, mantendo o saldo físico do rebanho atualizado na propriedade.
- **RF03.7 — Análise Financeira e Excesso de Capital Parado:** Mapear produtos com alto valor agregado cujo saldo supere 3 vezes o estoque mínimo, orientando a retenção de novos pedidos para proteger o fluxo de caixa.

---

## 4. Regras de Negócio e Tratamento de Exceções (RN)

| ID | Regra de Negócio | Descrição e Comportamento do Sistema |
|:---:|---|---|
| **RN01** | **Incompatibilidade de Unidades de Medida** | Registros de um mesmo produto com unidades de medida distintas (ex.: litros vs. quilogramas, frascos vs. doses) **nunca são somados diretamente**. O sistema emite aviso de incompatibilidade e segrega os saldos por unidade. |
| **RN01.1** | **Bloqueio de Saldo Negativo** | O sistema não deve permitir o registro de saída com quantidade superior ao saldo atual disponível do insumo, emitindo mensagem impeditiva ao usuário. |
| **RN02** | **Tratamento de Dados Ausentes** | A ausência de preço unitário ou data de validade **não pode ser interpretada como R$ 0,00 ou data válida**. O sistema mantém valores nulos (`None`) e informa explicitamente a ausência do dado, sem distorcer médias financeiras. |
| **RN03** | **Comunicação Rigorosa de Incerteza** | Estimativas de duração baseadas em histórico recente insuficiente **não devem gerar previsões arbitrárias**. O sistema exibe textualmente: *"Não estimado: histórico insuficiente de movimentações ou rebanho não vinculado"*. |
| **RN04** | **Transparência e Governança de IA** | Em conformidade estrita com o regulamento do AgroHack, a equipe declara expressamente que a inteligência do sistema baseia-se em **regras determinísticas, matemáticas e 100% auditáveis**, sem algoritmos de caixa preta para decisões sanitárias ou zootécnicas. |

---

## 5. Requisitos Não Funcionais (RNF)

- **RNF01 — Usabilidade e Acessibilidade Rural:** Interface direta e limpa, com tipografia legível sob luz solar, cartões To-Do de alto contraste e indicadores que combinam cor, ícone e texto para assegurar acessibilidade.
- **RNF02 — Desempenho e Agilidade:** O recálculo de todos os diagnósticos e a renderização do Dashboard devem ser concluídos em **menos de 2 segundos** para bases de até 5.000 movimentações e múltiplos lotes de gado.
- **RNF03 — Segurança e Privacidade:** O código do repositório público não contém chaves de API secretas, senhas de banco ou dados confidenciais de terceiros. A `SECRET_KEY` do Django utiliza fallback seguro para ambiente de desenvolvimento local.
- **RNF04 — Portabilidade e Reprodutibilidade:** Solução Web baseada em Python 3.12+, Django 5.x e SQLite 3, executável localmente com apenas comandos padrão de terminal (`migrate`, `test`, `runserver`), sem necessidade de serviços externos pagos.

---

## 6. Critérios Matemáticos e Fórmulas de Apoio à Decisão

### 6.1 Saldo Atual do Insumo
$$\text{Saldo Atual} = \sum \text{Entradas} - \sum \text{Saídas}$$

### 6.2 Consumo Diário Global do Rebanho por Insumo
$$\text{Consumo Diário Global} = \sum_{i=1}^{N} \left( \text{Cabeças do Lote}_i \times \text{Consumo Diário por Cabeça}_i \right)$$

### 6.3 Duração Estimada do Estoque em Dias
$$\text{Autonomia (Dias)} = \left\lfloor \frac{\text{Saldo Atual do Insumo}}{\text{Consumo Diário Global}} \right\rfloor$$

### 6.4 Projeção de Perda de Insumo por Validade
$$\text{Dias Restantes} = \text{Data de Validade} - \text{Hoje}$$
$$\text{Consumo Projetado} = \text{Consumo Diário Global} \times \text{Dias Restantes}$$
$$\text{Sobra Estimada a Descartar} = \text{Saldo do Lote} - \text{Consumo Projetado}$$
*Se $\text{Dias Restantes} \le 30$ e $\text{Sobra Estimada} > 0 \implies$ **🔴 Prioridade ALTA com valor financeiro em risco**.*

---

## 7. Matriz de Rastreabilidade (Requisitos vs. Implementação Django)

| Requisito | Descrição Resumida | Componente no Código | Arquivo de Teste / Validação | Status MVP |
|:---:|---|---|---|:---:|
| **RF01.1 / RF01.2** | Carga CSV e 13 Campos Oficiais | `estoque/views.py` (`importar`) | Testes de carga e integridade | **Aprovado** |
| **RF01.3** | Reanálise Automática em Tempo Real | `estoque/views.py` (`movimentacao_nova`) | `test_reanalise_automatica` | **Aprovado** |
| **RF02.1 / RF02.2** | Dashboard To-Do List e Semáforo | `templates/estoque/painel.html` | `test_painel_renderiza_alertas` | **Aprovado** |
| **RF03.4** | Gestão de Lotes de Gado e ECC | `estoque/models.py` (`LoteAnimais`) | `test_criacao_lote_bovino` | **Aprovado** |
| **RF03.5** | Campanhas Sanitárias IDARON | `estoque/models.py` (`CampanhaVacina`) | `test_vacinacao_lote` | **Aprovado** |
| **RF03.6** | Controle de Trânsito Animal (GTA) | `estoque/models.py` (`GuiaTransitoAnimal`) | `test_gta_entrada_saida` | **Aprovado** |
| **RN01 / RN02** | Unidades Distintas e Valores Nulos | `estoque/models.py` e `seed.py` | `test_integridade_dados` | **Aprovado** |

---

## 8. Checklist de Avaliação da Banca do AGROHACK (100 Pontos)

| Critério Oficial | Peso | Evidência na Solução AGROGADO |
|---|:---:|---|
| **1. Problema, compreensão do público e aderência** | **20 pts** | Resolução de dores reais da pecuária de Rondônia (perdas de vacinas IDARON, ruptura de sal mineral e controle de lotes). |
| **2. Funcionamento e demonstração com os dados** | **20 pts** | Botão de simulação sazonal e demonstração imediata no painel com lotes e insumos pré-carregados. |
| **3. Análises, alertas, prioridades e apoio à decisão** | **20 pts** | Lista To-Do com semáforo de 3 níveis, justificativas explicáveis em linguagem natural e recálculo instantâneo. |
| **4. Validação, testes e utilidade prática** | **15 pts** | Suíte de testes automatizados com Django (`python manage.py test`) e validação zootécnica com Medicina Veterinária. |
| **5. Código, documentação, autoria e IA responsável** | **15 pts** | Arquitetura limpa em Django MTV, documentação completa e regras estritamente determinísticas. |
| **6. Clareza, acessibilidade, apresentação e respostas** | **10 pts** | Interface responsiva de alto contraste, otimizada para uso no campo e apresentação na SNCT 2026. |