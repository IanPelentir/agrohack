# 1. Visão Geral do SistemaO sistema consiste em uma solução de gestão inteligente de insumos rurais voltada para o apoio à tomada de decisão de produtores rurais. A aplicação deve analisar registros de estoque e movimentações históricos e atuais para identificar riscos, gerar alertas priorizados e antecipar necessidades do campo.   

## 2. Requisitos Funcionais (RF)

- 📥 RF01 - Importação e Atualização de DadosRF01.1: O sistema deve permitir a carga e ingestão dos registros oficiais disponibilizados pela organização do evento.

- RF01.2: O sistema deve suportar os seguintes campos por registro:   Produto, Categoria, Unidade de Medida, Quantidade em Estoque, Estoque Mínimo, Tipo de Movimentação (Entrada/Saída), Data da Movimentação, Preço de Aquisição, Lote, Data de Validade, Fornecedor, Destino da Retirada e Responsável.   RF01.3 (Reanálise): O sistema deve permitir a atualização dos registros e reprocessar automaticamente todas as análises e alertas com base nos novos dados inseridos.   

- 🚨 RF02 - Painel Principal e Gestão de Alertas (Dashboard "To-Do List")RF02.1: O sistema deve exibir na tela inicial após o login uma visão consolidada das pendências e alertas de atenção imediata (estilo To-Do List).   

- RF02.2 (Priorização/Semaforização): O sistema deve classificar e priorizar visualmente os alertas por nível de urgência (ex.: Alta/Vermelho, Média/Amarelo, Baixa/Verde), evitando tratar todos os eventos como de mesma importância.   

- RF02.3 (Justificativa Clara): Todos os alertas gerados devem acompanhar uma justificativa amigável e explicativa em linguagem simples (ex.: "Estoque crítico: mantendo o consumo médio recente, o saldo atual será suficiente por aproximadamente 8 dias").

- 📊-RF03 - Motor de Análises Inteligentes do EstoqueRF03.1 (Risco de Falta / Stock Crítico): Identificar produtos cujo saldo esteja abaixo do estoque mínimo ou cuja projeção de consumo indique esgotamento em breve.   

- RF03.2 (Análise de Validade / Perdas): Cruzar a data de validade dos insumos (medicamentos, defensivos, sementes) com o histórico de consumo para identificar itens com risco de vencer antes de serem totalmente utilizados.   

- RF03.3 (Estimativa de Duração): Calcular a estimativa de tempo restante do estoque com base no histórico recente de movimentações e saídas.   

- RF03.4 (Detecção de Anomalias): Identificar movimentações fora do padrão, como saídas atipicamente altas, mudanças abruptas de ritmo ou registros duplicados/inconsistentes.   

- RF03.5 (Análise Financeira e Excesso): Identificar produtos com capital financeiro parado em excesso ou de alto valor agregado com baixa movimentação.   

- RF03.6 (Acompanhamento Temporal): Permitir a visualização do comportamento e evolução do consumo dos produtos ao longo do tempo (sazonalidade de plantio/gradagem).   

## 3. Requisitos Não Funcionais (RNF)

- RNF01 (Usabilidade): A interface deve ser simples, acessível e direta ao ponto, focando na rotina e nas necessidades do produtor rural sem exigir navegação em menus complexos.   

- RNF02 (Desempenho e Agilidade): As análises e o recálculo dos alertas devem ser executados em tempo hábil após qualquer nova atualização de registro.   

- RNF03 (Segurança e Privacidade): O código e o repositório público não devem conter credenciais expostas, chaves de API secretas ou dados confidenciais de terceiros.   

- RNF04 (Portabilidade e Acesso): A solução pode ser Web, Mobile ou Desktop, sendo disponibilizada preferencialmente via link online ou pacote com instruções reproduzíveis.   

## 4. Tratamento de Exceções e Regras de Negócio (RN)

- RN01 (Unidades Distintas): Registros com unidades de medida diferentes para o mesmo produto não podem ser somados diretamente sem o devido tratamento ou conversão.   

- RN02 (Valores Ausentes): Ausência de preço ou data de validade em um registro não deve ser interpretada pelo algoritmo como valor zero ou data válida padrão.   

- RN03 (Incerteza de Dados): Estimativas baseadas em histórico escasso ou insuficiente devem informar expressamente o grau de incerteza ao usuário.   

- RN04 (Transparência de IA): Caso sejam utilizadas ferramentas de Inteligência Artificial, sua presença, finalidade e partes desenvolvidas devem ser expressamente declaradas na documentação do projeto.   

## 5. Requisitos de Entrega e Avaliação (Checklist de Conformidade)Para garantir pontuação máxima nos critérios da banca avaliadora (100 pontos):   Repositório GitHub Acessível: Conter código-fonte funcional, instruções reproduzíveis de teste e commit/tag identificando a versão de entrega.   Documentação README.md Completa: Conforme estrutura do Anexo II (Equipe, Problema, Solução, Como Testar, Análise de Dados, Tecnologias/IA, Licença).   Vídeo Demonstrativo: Gravação com demonstração funcional da solução utilizando os dados do desafio.   Demonstração Presencial/Online: Apresentação agendada para 29/10/2026 na SNCT.   