# Especificação Integrada de Requisitos e Regras de Negócio
## AgroHack 2026/2 — Sistema de Gestão Inteligente de Insumos Rurais e Apoio à Decisão

---

> **Instituição:** Instituto Federal de Educação, Ciência e Tecnologia de Rondônia (IFRO) — *Campus* Ariquemes  
> **Evento:** Semana Nacional de Ciência e Tecnologia (SNCT 2026) — 29 de Outubro de 2026  
> **Desafio Oficial:** *Gestão inteligente de insumos em uma propriedade rural*  
> **Stack Oficial:** Python 3.14 • Django 5.2 LTS • SQLite 3 • HTML5/CSS3 • Chart.js  
> **Versão do Documento:** 2.0 (Consolidação oficial de requisitos, regras de negócio e rastreabilidade)

---

## 1. Visão Geral e Contexto do Projeto

### 1.1 Contexto e Justificativa
Propriedades rurais de médio e pequeno porte em Rondônia (como na bacia leiteira e na produção agropecuária do Vale do Jamari) lidam diariamente com dezenas de insumos críticos distribuídos entre sanidade animal, suplementação nutricional, defensivos agrícolas, combustíveis e insumos para pastagens. 

O controle manual em cadernos ou planilhas desconexas costuma gerar sérios prejuízos financeiros e riscos sanitários:
- **Perda de insumos perecíveis:** Medicamentos veterinários (antibióticos, antiparasitários) e vacinas vencendo na prateleira antes da aplicação no rebanho.
- **Ruptura de estoque operacional:** Esgotamento repentino de sal mineral, ração concentrada ou combustível no meio de períodos críticos (como a transição seca/águas ou épocas de gradagem/plantio).
- **Desequilíbrio financeiro:** Ausência de visibilidade sobre o capital imobilizado em excesso versus itens com risco iminente de falta.

### 1.2 Objetivo da Solução
Desenvolver uma aplicação Web MVP intuitiva e determinística, centrada em um **Dashboard no formato *To-Do List*** com **sinalização semafórica acessível (🔴 ALTA / 🟡 MÉDIA / 🟢 BAIXA)**. O sistema transforma registros históricos e atuais de movimentações em **diagnósticos explicáveis em linguagem simples**, orientando o produtor rural sobre as ações que precisam ser tomadas no dia para evitar prejuízos.

---

## 2. Partes Interessadas e Perfis de Usuário

| Perfil | Descrição e Papel no Sistema |
|---|---|
| **Produtor Rural / Capataz / Gestor da Propriedade** | Visualiza pendências prioritárias na tela inicial (*To-Do List*), confere alertas operacionais e registra entradas/saídas rápidas de insumos sem burocracia. |
| **Médico(a) Veterinário(a) / Consultor(a) de Campo** | Valida protocolos de validade de medicamentos, regras de lote, carência e estimativas de consumo vinculadas ao destino (pasto, lote de animais, talhão). |
| **Banca Avaliadora do AGROHACK 2026/2** | Avalia conformidade com os 13 campos do regulamento, transparência dos cálculos, explicabilidade das justificativas, integridade dos testes e facilidade de demonstração. |

---

## 3. Requisitos Funcionais (RF)

### 3.1 Ingestão, Importação e Atualização de Dados (RF01)
- **RF01.1 — Importação de Planilha CSV:** O sistema deve suportar upload e ingestão de arquivos CSV contendo os registros oficiais disponibilizados pela organização do evento, suportando delimitadores comuns (`,` e `;`) com prévia antes da confirmação.
- **RF01.2 — Suporte aos 13 Campos Oficiais do Regulamento:** O modelo de dados e a importação devem reconhecer e tratar rigorosamente os 13 campos oficiais do desafio:
  1. `produto`: Nome comercial / identificação do insumo.
  2. `categoria`: Categoria operacional (Defensivos, Fertilizantes, Sementes, Medicamentos Veterinários, Combustíveis, Suplementos/Rações, Manutenção, EPIs).
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
  13. `responsavel`: Colaborador ou operador encarregado do registro.
- **RF01.3 — Reanálise Automática em Tempo Real:** Toda inclusão manual ou importação de novas movimentações deve disparar o recálculo imediato de saldos, durações estimadas e alertas sem necessidade de intervenção técnica ou reinicialização.

### 3.2 Painel Principal e Gestão de Alertas (Dashboard To-Do List) (RF02)
- **RF02.1 — Dashboard Estilo To-Do List:** A tela inicial deve funcionar como uma lista priorizada de ações práticas do dia, permitindo ao produtor identificar rapidamente as providências emergenciais.
- **RF02.2 — Priorização Semafórica Acessível:**
  - 🔴 **Prioridade ALTA (Vermelho):** Itens com saldo $\le$ estoque mínimo; lotes com validade vencida e saldo restante; lotes com risco de vencimento antes do consumo projetado.
  - 🟡 **Prioridade MÉDIA (Amarelo):** Itens com saldo entre 100% e 150% do estoque mínimo (zona de atenção para reposição); saídas atípicas/anomalias estatísticas; lotes com vencimento em até 30 dias com histórico insuficiente de projeção.
  - 🟢 **Prioridade BAIXA (Verde / Monitoramento):** Alertas informativos de capital expressivo imobilizado com alta cobertura de estoque (excesso de compras).
- **RF02.3 — Justificativa Clara e Explicável:** Nenhum alerta pode ser exibido sem justificativa em linguagem natural amigável (ex.: *"Estoque crítico: Saldo atual (18.0 L) atingiu o limite mínimo (50.0 L) — estimado para ~11 dia(s)"*).

### 3.3 Motor de Análises Inteligentes do Estoque (RF03)
- **RF03.1 — Risco de Falta e Estoque Crítico:** Identificar produtos cujo saldo atual esteja igual ou abaixo do estoque mínimo, ou com saldo zerado/negativo.
- **RF03.2 — Análise de Validade e Perdas de Insumos:** Cruzar a data de validade dos lotes com o ritmo de consumo recente. Se a quantidade remanescente for superior ao consumo projetado até a data de expiração, sinalizar perda financeira iminente com o volume estimado de descarte.
- **RF03.3 — Estimativa de Duração / Cobertura de Estoque:** Calcular os dias restantes de estoque projetados a partir do consumo médio diário na janela móvel de saídas.
- **RF03.4 — Detecção de Anomalias de Saída:** Identificar movimentações com volumes atipicamente elevados em relação ao padrão histórico recente (desvio superior a $2\sigma$ da média, quando houver base histórica confiável).
- **RF03.5 — Análise Financeira e Excesso de Capital Parado:** Mapear produtos com alto valor financeiro agregado (acima de R$ 5.000,00) cujo saldo supere 3 vezes o estoque mínimo, orientando a retenção de novos pedidos para proteger o fluxo de caixa.
- **RF03.6 — Acompanhamento Temporal Interativo:** Exibir a evolução gráfica do consumo mensal por produto (via Chart.js), possibilitando identificar sazonalidades agrícolas e pecuárias.

---

## 4. Regras de Negócio e Tratamento de Exceções (RN)

| ID | Regra de Negócio | Descrição e Comportamento do Sistema |
|:---:|---|---|
| **RN01** | **Incompatibilidade de Unidades de Medida** | Registros de um mesmo produto com unidades de medida distintas (ex.: litros vs. quilogramas, frascos vs. doses) **nunca são somados diretamente**. O sistema emite aviso de incompatibilidade e segrega os saldos por unidade. |
| **RN01.1** | **Bloqueio de Saldo Negativo** | O sistema não deve permitir o registro de saída com quantidade superior ao saldo atual disponível do insumo, emitindo mensagem impeditiva ao usuário. |
| **RN02** | **Tratamento de Dados Ausentes** | A ausência de preço unitário ou data de validade **não pode ser interpretada como R$ 0,00 ou data válida**. O sistema mantém valores nulos (`None`) e informa explicitamente a ausência do dado, sem distorcer médias financeiras. |
| **RN03** | **Comunicação Rigorosa de Incerteza** | Estimativas de duração baseadas em histórico recente insuficiente (menos de 2 saídas na janela ou menos de 5 registros para anomalias) **não devem gerar previsões arbitrárias**. O sistema exibe textualmente: *"Não estimado: histórico insuficiente de movimentações"*. |
| **RN04** | **Transparência e Governança de IA** | Em conformidade estrita com o regulamento do AgroHack, a equipe declara expressamente que a inteligência do sistema baseia-se em **regras determinísticas, matemáticas e 100% auditáveis**, sem algoritmos de caixa preta para decisões agronômicas ou sanitárias. |

---

## 5. Requisitos Não Funcionais (RNF)

- **RNF01 — Usabilidade e Acessibilidade Rural:** Interface direta e limpa, com tipografia legível sob luz solar, cartões To-Do de alto contraste e indicadores que combinam cor, ícone e texto para assegurar acessibilidade.
- **RNF02 — Desempenho e Agilidade:** O recálculo de todos os diagnósticos e a renderização do Dashboard devem ser concluídos em **menos de 2 segundos** para bases de até 5.000 movimentações.
- **RNF03 — Segurança e Privacidade:** O código do repositório público não contém chaves de API secretas, senhas de banco ou dados confidenciais de terceiros. A `SECRET_KEY` do Django utiliza fallback seguro para ambiente de desenvolvimento local.
- **RNF04 — Portabilidade e Reprodutibilidade:** Solução Web baseada em Python 3.12+, Django 5.x e SQLite 3, executável localmente com apenas comandos padrão de terminal (`migrate`, `test`, `runserver`), sem necessidade de serviços externos pagos ou containers proprietários.

---

## 6. Critérios Matemáticos e Fórmulas de Apoio à Decisão

### 6.1 Saldo Atual do Insumo
$$\text{Saldo Atual} = \sum \text{Entradas} - \sum \text{Saídas}$$

### 6.2 Priorização de Estoque Crítico
- $\text{Saldo} \le \text{Estoque Mínimo} \implies$ **🔴 Prioridade ALTA**
- $\text{Estoque Mínimo} < \text{Saldo} \le 1.5 \times \text{Estoque Mínimo} \implies$ **🟡 Prioridade MÉDIA**
- $\text{Saldo} > 1.5 \times \text{Estoque Mínimo} \implies$ **🟢 Prioridade BAIXA (Monitoramento Normal)**

### 6.3 Duração Estimada do Estoque (Janela Móvel de 30 dias)
$$\text{Consumo Diário} = \frac{\sum \text{Saídas no Período}}{\text{Dias Observados}}$$
$$\text{Duração Estimada (Dias)} = \left\lceil \frac{\text{Saldo Atual}}{\text{Consumo Diário}} \right\rceil$$

### 6.4 Projeção de Perda por Validade
$$\text{Dias Restantes} = \text{Data de Validade} - \text{Hoje}$$
$$\text{Consumo Projetado} = \text{Consumo Diário} \times \text{Dias Restantes}$$
$$\text{Sobra Estimada a Descartar} = \text{Saldo do Lote} - \text{Consumo Projetado}$$
*Se $\text{Dias Restantes} \le 30$ e $\text{Sobra Estimada} > 0 \implies$ **🔴 Prioridade ALTA com valor financeiro de risco**.*

### 6.5 Detecção de Saídas Atípicas (Anomalias)
$$\text{Limite Superior} = \mu + 2\sigma$$
*Onde $\mu$ é a média das saídas e $\sigma$ é o desvio-padrão amostral (aplicado para histórico com $N \ge 5$).*

---

## 7. Matriz de Rastreabilidade (Requisitos vs. Implementação Django)

| Requisito | Descrição Resumida | Componente no Código | Arquivo de Teste / Validação | Status MVP |
|:---:|---|---|---|:---:|
| **RF01.1 / RF01.2** | Carga CSV e 13 Campos Oficiais | `estoque/views.py` (`importar`) | Testes de carga e integridade | Homologado |
| **RF01.3** | Reanálise Automática em Tempo Real | `estoque/views.py` (`movimentacao_nova`) | `test_reanalise_automatica_apos_nova_movimentacao` | **Aprovado** |
| **RF02.1 / RF02.2** | Dashboard To-Do List e Semáforo | `templates/estoque/painel.html` | `test_painel_renderiza_com_alertas_priorizados` | **Aprovado** |
| **RF02.3** | Justificativa Explicável dos Alertas | `estoque/analises.py` | Asserções de texto explicativo em testes | **Aprovado** |
| **RF03.1** | Estoque Crítico e Falta | `estoque/analises.py` (`calcular_estoque_critico`) | `test_estoque_critico_tebuconazol` | **Aprovado** |
| **RF03.2** | Validade e Risco de Perdas | `estoque/analises.py` (`analisar_validade`) | `test_alerta_validade_proxima_vacina` e `test_lote_vencido_oxitetraciclina` | **Aprovado** |
| **RF03.3** | Duração Estimada de Cobertura | `estoque/analises.py` (`estimar_duracao`) | Testes determinísticos de cálculo | **Aprovado** |
| **RF03.4** | Detecção de Saídas Atípicas | `estoque/analises.py` (`detectar_anomalias`) | `test_anomalia_diesel` | **Aprovado** |
| **RF03.5** | Capital Imobilizado / Excesso | `estoque/analises.py` (`analisar_financeiro`) | `test_excesso_capital_semente` | **Aprovado** |
| **RF03.6** | Acompanhamento Temporal | `estoque/views.py` (`consumo`) | Renderização de série temporal Chart.js | **Aprovado** |
| **RN01 / RN02** | Unidades Distintas e Valores Nulos | `estoque/models.py` e `seed.py` | `test_dados_ficticios_foram_carregados` | **Aprovado** |
| **RN03** | Incerteza para Histórico Insuficiente | `estoque/analises.py` (`estimar_duracao`) | `test_historico_insuficiente_epi` | **Aprovado** |

---

## 8. Checklist de Avaliação da Banca do AGROHACK (100 Pontos)

| Critério Oficial | Peso | Evidência na Solução AgroHack |
|---|:---:|---|
| **1. Problema, compreensão do público e aderência** | **20 pts** | Resolução de dores reais da agropecuária de Rondônia (perdas de vacinas, ruptura de sal mineral e fertilizantes, excesso de capital). |
| **2. Funcionamento e demonstração com os dados** | **20 pts** | Botão de demonstração imediata no painel (~80 registros simulados cobrindo todos os cenários) e importador CSV para a base oficial. |
| **3. Análises, alertas, prioridades e apoio à decisão** | **20 pts** | Lista To-Do com semáforo de 3 níveis, justificativas claras em linguagem natural e recálculo instantâneo a cada movimentação. |
| **4. Validação, testes e utilidade prática** | **15 pts** | Suíte de testes unitários automatizados com Django (`python manage.py test`) e validação de regras de campo com Medicina Veterinária. |
| **5. Código, documentação, autoria e IA responsável** | **15 pts** | Código limpo em Django MTV, documentação completa de requisitos e declaração de uso ético de IA sem decisões agronômicas automáticas. |
| **6. Clareza, acessibilidade, apresentação e respostas** | **10 pts** | Interface de alto contraste utilizável no campo sob luz solar, sem dependência de cores isoladas para transmitir urgência. |
