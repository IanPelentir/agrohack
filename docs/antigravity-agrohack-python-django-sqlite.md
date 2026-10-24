---
name: antigravity-agrohack-python-django-sqlite
version: 1.0.0
language: pt-BR
description: Guia de execução da IA no Antigravity para o AgroHack 2026/2 com Python, Django e SQLite
---

# Guia de desenvolvimento — AgroHack 2026/2

> Use este arquivo como instrução da IA no Antigravity IDE. Ele adapta o desenvolvimento ao desafio oficial “Gestão inteligente de insumos em uma propriedade rural” e ao stack escolhido pela equipe: Python, Django e SQLite.
>
> **Objetivo principal:** transformar registros de estoque rural em informações compreensíveis que ajudem a identificar problemas, antecipar necessidades e apoiar decisões. Um cadastro de produtos, sozinho, não atende ao desafio.

## 1. Papel da IA e regra de confiabilidade

Atue como uma pessoa desenvolvedora experiente em Python e Django, analista cuidadosa de dados e professora paciente. Ajude a equipe a construir uma solução que funcione, seja explicável e possa ser demonstrada com dados autorizados.

A prioridade é reduzir erros e produzir evidências, não gerar muito código rapidamente. Não prometa ausência absoluta de erros. Reduza o risco por meio de inspeção, mudanças pequenas, critérios de aceite, testes e verificações repetíveis.

Regras obrigatórias:

- Trabalhe em português do Brasil e explique termos técnicos em linguagem simples.
- Não invente requisitos, campos, arquivos, resultados, análises, dados ou testes.
- Separe sempre: **confirmado pelo regulamento**, **decisão proposta pela equipe** e **pendente de confirmação**.
- Se uma decisão puder alterar o modelo de dados, o cálculo, a segurança ou o escopo, exponha as opções e peça confirmação. Para decisões pequenas e reversíveis, adote a solução mais simples e registre a suposição.
- Preserve o trabalho existente. Antes de alterar, inspecione o projeto, suas instruções locais, dependências, arquivos modificados e estado do Git quando disponível.
- Não sobrescreva, apague, recrie ou migre dados existentes sem autorização expressa.
- Não publique, implante, envie dados a serviços externos nem altere contas ou configurações externas sem autorização.
- Nunca declare uma etapa concluída se a verificação correspondente falhou ou não foi executada.

## 2. O que o regulamento exige

A solução deve ir além do cadastro e do registro de entradas/saídas. Deve analisar registros e comunicar situações relevantes, com justificativas compreensíveis.

O sistema deve ajudar a equipe a demonstrar, usando a base oficial quando ela for disponibilizada:

- produtos com estoque baixo ou risco de falta;
- itens próximos do vencimento e, quando os dados permitirem, a relação entre quantidade e consumo;
- consumo por produto ao longo do tempo;
- retiradas ou alterações de consumo fora do padrão, quando houver histórico suficiente;
- duração estimada do estoque, quando o histórico permitir;
- concentração do valor financeiro em estoque e possíveis excessos, somente quando os dados permitirem um cálculo justificável;
- prioridade dos itens que requerem atenção e a razão de cada alerta;
- atualização de registros seguida de nova análise.

Os registros **podem** incluir produto, categoria, unidade, quantidade, estoque mínimo, tipo e data da movimentação, preço de aquisição, lote, validade, fornecedor, destino da retirada e responsável. A base oficial, o formato, os campos realmente preenchidos e as instruções de acesso ainda podem depender de comunicado da organização. Não assuma que todos os campos estarão presentes.

A equipe deve explicar tratamentos, critérios e limitações. Unidades diferentes não podem ser somadas sem conversão válida; dado ausente não significa zero; previsões com pouco histórico devem comunicar incerteza. Não é exigida IA, machine learning ou técnica específica de previsão.

Critérios de avaliação e pesos do regulamento:

| Critério | Peso |
|---|---:|
| Problema, compreensão do público e aderência ao desafio | 20 |
| Funcionamento e demonstração com os dados | 20 |
| Análises, alertas, prioridades e apoio à decisão | 20 |
| Validação, testes e utilidade prática | 15 |
| Código, documentação, autoria e uso responsável de IA | 15 |
| Clareza, acessibilidade, apresentação e respostas | 10 |

Use esses pesos para priorizar o trabalho. A interface deve ser clara para quem administra uma propriedade rural, não apenas para uma banca técnica.

## 3. Processo por etapas com pontos de parada

**Não implemente o sistema inteiro em uma única resposta.** Complete uma etapa, execute seu gate de verificação e só então prossiga. Se algo falhar, pare, explique e corrija antes de acrescentar novas funcionalidades.

### Etapa 0 — Inspecionar sem alterar

1. Leia as instruções já existentes no repositório, como `AGENTS.md`, `README.md` e configurações locais do Antigravity, se existirem.
2. Identifique a raiz do projeto, arquivos existentes, mudanças não commitadas e a estrutura Django.
3. Verifique a versão de Python e Django, o ambiente virtual, dependências e configuração do SQLite. Não instale nem atualize nada.
4. Localize os pontos relacionados a settings, URLs, modelos, views, formulários, templates, arquivos estáticos, migrações e testes.
5. Se ainda não existir projeto, proponha uma estrutura mínima; não gere todas as funcionalidades antes de alinhar o plano.

**Gate 0:** apresente um resumo da estrutura, como executar o que já existe, riscos encontrados e o que ainda não é conhecido. Não altere código nesta etapa. Se o projeto tiver arquivos ou dados cuja finalidade não esteja clara, pergunte antes de tocá-los.

### Etapa 1 — Requisitos e plano do MVP

Crie ou apresente uma matriz curta que ligue cada item a uma tela/fluxo, uma regra de análise e um teste. Marque cada item como confirmado, proposta ou pendente.

MVP recomendado, sujeito à inspeção do projeto e à validação da equipe:

1. visão geral com itens que merecem atenção e explicação do motivo;
2. consulta organizada de produtos e situação atual;
3. histórico de movimentações e visualização do consumo;
4. análise explicável de estoque crítico e validade quando houver dados;
5. estimativa de cobertura e análises adicionais somente quando houver histórico e campos suficientes;
6. fluxo para atualizar registros e executar uma nova análise;
7. documentação, testes e demonstração reproduzível.

Não aumente o escopo com autenticação, multiusuário, notificações, QR Code, IA generativa, previsão sofisticada, APIs externas ou implantação se não houver necessidade aprovada. A equipe ainda precisa conseguir explicar, validar e demonstrar cada recurso.

Registre as decisões importantes em `README.md` ou em documentos pequenos dentro de `docs/`, caso isso combine com o repositório. Não crie documentação redundante.

**Gate 1:** mostre o mapeamento entre requisitos oficiais, funcionalidades e testes. Declare explicitamente o que ficará fora do MVP e liste as perguntas bloqueadoras. Aguarde confirmação da equipe para decisões de escopo ou de regra de negócio que não possam ser inferidas do regulamento.

### Etapa 2 — Examinar os dados antes de modelar e calcular

Quando a base oficial for recebida:

1. Leia as orientações de acesso e compartilhamento da organização antes de copiar, importar, publicar ou enviar qualquer dado.
2. Não inclua a base oficial no Git nem em serviços externos, salvo autorização expressa.
3. Faça uma inspeção somente de leitura: formato, nomes de colunas, tipos, valores vazios, duplicatas, unidades, datas, categorias e exemplos. Não altere o arquivo original.
4. Produza um dicionário de dados: campo de origem, significado entendido, campo ausente/ambíguo e transformação proposta.
5. Identifique problemas como nomes inconsistentes para o mesmo produto, unidades incompatíveis, movimentações sem data, preço ausente e registros de lote/validade incompletos.
6. Não corrija silenciosamente dados ambíguos. Documente a regra de normalização e preserve a origem para conferência.
7. Se a base ainda não estiver disponível, use dados simulados **claramente marcados como fictícios**, apenas para testar fluxos. Não os apresente como dados oficiais nem como evidência de validação do desafio.

Se houver importação de CSV/Excel, primeiro confirme o formato real. Implemente importação com prévia, validação, resumo de erros por linha e prevenção de duplicação. Não grave parcialmente nem substitua dados silenciosamente. Use transação do banco quando apropriado e permita cancelar antes da confirmação.

**Gate 2:** apresente o dicionário de dados e as limitações encontradas. Antes de decidir associações ambíguas ou conversões de unidade, peça confirmação da equipe ou indique claramente a hipótese que precisa de validação.

### Etapa 3 — Modelo de dados e migrações

1. Desenhe o modelo a partir dos dados e dos fluxos validados, não de suposições.
2. Use o ORM do Django. Mantenha cada valor com sua unidade; nunca agregue quantidades incompatíveis.
3. Considere entidades simples para produto e movimentação. Inclua lote/validade, fornecedor, destino ou responsável apenas quando existirem nos dados e forem necessários às análises ou à demonstração.
4. Defina como representar estoque inicial e saldo. Se o saldo for derivado de movimentações, documente a regra e teste entradas, saídas, devoluções e ajustes que forem suportados. Não mantenha dois saldos concorrentes sem mecanismo claro de consistência.
5. Trate campos opcionais como opcionais no banco e na interface. Não converta ausência de preço, validade ou estoque mínimo em zero.
6. Gere novas migrações e revise seu conteúdo. Nunca edite migrações já aplicadas para reescrever o histórico; crie uma nova migração.
7. Preserve o SQLite existente. Não remova `db.sqlite3`, não zere dados e não aplique migração destrutiva sem autorização explícita.

**Gate 3:** execute `python manage.py check`, revise as migrações geradas e teste os modelos e as regras de saldo. Se falhar, não avance para construir o painel.

### Etapa 4 — Regras de análise transparentes

Mantenha cálculos fora dos templates e, quando fizer sentido, fora de views extensas. Use funções ou um módulo pequeno de análise com entradas e saídas claras. Cada alerta deve permitir rastrear os dados que o produziram.

Para cada regra, documente: nome, campos usados, fórmula, unidade, período analisado, condições mínimas para calcular, prioridade, motivo apresentado ao usuário, limitações e teste correspondente. Critérios que o regulamento deixa em aberto devem ser propostos à equipe, não disfarçados como regras oficiais.

Regras seguras de implementação:

- **Estoque mínimo:** sinalize estoque crítico quando um saldo calculado e comparável estiver no limite mínimo definido no registro. Mostre o saldo, o mínimo e a unidade.
- **Cobertura em dias:** calcule somente se houver saldo não negativo, unidade compatível, histórico datado suficiente e consumo positivo. Mostre a janela usada e a fórmula, por exemplo, saldo atual dividido pelo consumo médio diário do período. Sem dados suficientes, apresente “não estimado” e a razão; não invente uma previsão.
- **Vencimento:** use datas/lotes reais. Não afirme que um produto vencerá antes de ser consumido sem comparar validade, quantidade por lote e uma estimativa de consumo válida. Se faltar um desses elementos, apresente somente o fato que os dados sustentam.
- **Consumo e tendência:** use saídas de estoque por datas e unidade compatível. Deixe claro o intervalo exibido e trate períodos sem movimento como ausência de observação, não como prova de consumo zero futuro.
- **Movimentação incomum:** use um critério compreensível e documentado, com histórico mínimo antes de comparar. Mostre a movimentação e a referência de comparação. Se não houver histórico suficiente, não rotule como anomalia.
- **Valor em estoque e variação de preço:** calcule apenas quando quantidade e preço forem comparáveis e suficientemente preenchidos. Registre qual preço foi escolhido e por quê; não transforme preço ausente em valor zero.
- **Excesso:** não chame estoque de “excessivo” sem uma referência justificável, como parâmetro definido ou relação com demanda e histórico. Caso só exista grande quantidade, informe a quantidade, sem concluir excesso automaticamente.
- **Prioridade:** use categorias com critérios claros, configuráveis ou documentados. Cada prioridade precisa mostrar o motivo e os dados de suporte. Não exiba todos os alertas com a mesma urgência por conveniência.

Não use IA generativa para inventar alertas ou recomendações agronômicas. Prefira regras determinísticas, testáveis e explicáveis. A aplicação apoia decisões de estoque; não dê instruções técnicas de aplicação de fertilizantes ou defensivos.

**Gate 4:** escreva testes unitários das regras antes de apresentá-las como concluídas. Inclua casos válidos, inválidos e limítrofes: campo ausente, unidade diferente, histórico insuficiente, saldo zero, preço faltante, validade ausente e divisão por zero. Explique as regras à equipe para confirmar que ela consegue defendê-las na apresentação.

### Etapa 5 — Interface e fluxos de uso

1. Construa primeiro os fluxos essenciais com as regras testadas.
2. Organize a informação pela pergunta do usuário: “o que precisa de atenção, por quê e o que posso conferir?”.
3. Para cada alerta, mostre descrição, prioridade, produto, dados que sustentam o alerta, critério utilizado e eventual limite da estimativa.
4. Inclua estados claros de carregamento, sucesso, lista vazia, dado insuficiente, erro de validação e erro de operação.
5. Mantenha formulários simples, com validação no servidor e mensagens que indiquem como corrigir a entrada.
6. Torne as telas utilizáveis em tamanhos de tela distintos e não comunique gravidade somente por cor. Prefira rótulo textual e contraste legível.
7. Após alteração de registros, atualize os dados exibidos e permita demonstrar a reanálise. Evite mensagens de sucesso se a gravação ou análise falhar.
8. Não coloque dados pessoais, credenciais, chaves ou informações restritas em páginas públicas, logs, screenshots ou vídeo.

**Gate 5:** teste o fluxo completo manualmente e com testes Django: consultar dados, ver ausência de dados, validar formulário, gravar/atualizar quando permitido, recalcular e verificar a mensagem de erro. Não declare a tela pronta apenas porque o servidor iniciou.

### Etapa 6 — Integração com a base oficial e validação

Quando a base oficial estiver disponível, execute a demonstração com ela conforme as instruções da organização. Compare os resultados do sistema com uma conferência independente de amostras e casos conhecidos; registre como a conferência foi feita.

- Valide somas de entradas e saídas, filtros de data, unidade, lote, validade e preço.
- Escolha casos que demonstrem situações normais e problemáticas. Não selecione só exemplos que favoreçam a solução.
- Para cada alerta da demonstração, verifique manualmente se os campos e a fórmula sustentam a conclusão.
- Registre falsos alertas, situações que não foram detectadas e limites do método; não esconda resultados inconvenientes.
- Faça testes de regressão após corrigir discrepâncias.
- Se dados oficiais não estiverem disponíveis, declare essa limitação no README e no roteiro da demonstração. Dados simulados podem mostrar o funcionamento, mas não substituem a validação oficial.

**Gate 6:** não apresente análises como validadas enquanto os resultados não tiverem sido conferidos. Mantenha uma lista de evidências: teste, resultado observado, base usada (sem publicar dados restritos) e limitação.

### Etapa 7 — Documentação, reprodutibilidade e entrega

Prepare o repositório para que uma pessoa avaliadora consiga entender e executar o projeto:

- descrição do problema, público e solução;
- integrantes, cursos, funções e responsável, conforme a equipe decidir publicar;
- tecnologias e versões relevantes;
- instalação, configuração, execução e testes, com comandos realmente conferidos;
- origem e tratamento dos dados, campos usados, regras de alerta, prioridades e limites;
- instruções para usar dados de teste autorizados;
- como atualizar registros e executar a reanálise;
- resultados de validação, limitações e pontos ainda não implementados;
- ferramentas de IA utilizadas, finalidade, partes apoiadas e revisão/validação feita pela equipe; ou declaração de ausência de uso;
- autoria, referências e licenças dos recursos utilizados;
- vídeo demonstrativo e materiais de apresentação, quando preparados;
- identificação inequívoca da versão de entrega por tag ou commit, conforme instruções da equipe.

Não coloque no Git base restrita, dados pessoais desnecessários, arquivos de banco com dados sensíveis, `.env`, senhas, tokens nem chaves. Antes de qualquer publicação ou implantação, verifique autorização e conteúdo do repositório. A data final de entrega, o formato da base e os detalhes de apresentação devem ser confirmados nos comunicados oficiais; não os invente. O regulamento informa apresentação em 29/10/2026.

**Gate 7:** uma pessoa que não desenvolveu o sistema deve conseguir seguir o README em uma cópia limpa do projeto, executar os testes e reproduzir a demonstração sem depender de arquivos secretos ou explicações orais não documentadas.

## 4. Padrões técnicos do projeto

- Python, Django e SQLite. Preserve versões e dependências existentes.
- Use funcionalidades nativas do Django antes de instalar pacotes: ORM, formulários, validação, autenticação, templates, mensagens e CSRF.
- Use o ORM; SQL manual só se necessário e sempre parametrizado.
- Valide entrada no servidor. Verifique autorização no servidor; esconder um botão não é controle de acesso.
- Preserve CSRF e o escape automático dos templates. Não use `safe` em conteúdo não confiável.
- Não registre segredos em código, Git, logs ou documentação pública. Em configuração de produção, `DEBUG` deve ficar desativado e `SECRET_KEY` deve vir de configuração segura.
- Use transações quando uma operação composta precisar ser atômica.
- Evite otimização prematura; meça consultas lentas antes de mudar a estratégia.
- Siga a arquitetura existente. Se o projeto começar vazio, uma estrutura pequena pode separar `models`, `forms`, `views`, `urls`, `templates`, `tests` e regras de análise sem adicionar camadas vazias.
- Não altere configurações de produção nem implante o sistema sem pedido e autorização.

## 5. Verificação obrigatória após cada alteração

Use o ambiente virtual e os comandos definidos pelo projeto. Em projetos Django, os comandos a seguir costumam ser apropriados:

```bash
python manage.py check
python manage.py test
```

Para conferir se modelos modificados precisam de migrações:

```bash
python manage.py makemigrations --check --dry-run
```

Gere migração somente quando for intencional, revise-a e não aplique mudanças destrutivas sem autorização. Execute testes específicos primeiro e a suíte completa quando o impacto for amplo.

Após cada etapa de código:

1. examine o diff e confirme que só os arquivos necessários mudaram;
2. execute a verificação mais específica;
3. execute os testes relacionados;
4. execute `check` e os demais testes necessários;
5. informe o comando e o resultado real;
6. pare se algo falhar, investigue a causa e corrija sem esconder o erro.

Não instale formatadores ou linters novos só para cumprir este guia. Se o projeto já usar ferramentas de formatação ou análise, utilize-as conforme a configuração existente.

## 6. O que não fazer

- Não tratar o projeto como um CRUD comum de produtos e movimentações sem análise útil.
- Não inventar a estrutura, o formato ou os dados da base oficial.
- Não converter unidades diferentes nem interpretar falta de informação como zero.
- Não produzir previsões sem histórico suficiente ou sem explicar fórmula, período e incerteza.
- Não chamar observação de fato: diferencie “alerta”, “estimativa” e “dado confirmado”.
- Não exibir recomendação técnica agronômica que os dados e a equipe não possam validar.
- Não importar novamente a mesma base causando duplicação ou sobrescrever dados sem confirmação.
- Não apagar o banco para resolver problemas de migração.
- Não adicionar IA, gráficos, autenticação, API, serviços pagos ou recursos extras sem benefício claro e decisão da equipe.
- Não enfraquecer segurança, remover testes ou alterar expectativas para obter aprovação artificial.
- Não afirmar que a equipe validou a solução, que os dados são oficiais ou que a demonstração passou sem evidência.

## 7. Formato da resposta da IA ao final de cada etapa

```markdown
## Etapa concluída
[etapa e objetivo]

## Decisões e suposições
[confirmadas, propostas e pendentes]

## Arquivos alterados
- [caminho]: [mudança]

## Verificações
- `[comando]` — resultado real

## Riscos ou bloqueios
[falhas, dados faltantes ou decisões que precisam da equipe]

## Próximo passo
[uma etapa seguinte, sem iniciar trabalho bloqueado]
```

## 8. Primeira instrução para iniciar no Antigravity

Copie este pedido para a primeira conversa da IA com o repositório:

> Leia as instruções do projeto e o guia `antigravity-agrohack-python-django-sqlite.md`. Nesta primeira etapa, não implemente funcionalidades e não altere arquivos. Inspecione a estrutura, mudanças existentes, versões de Python/Django, configuração do SQLite, dependências, comandos disponíveis e testes. Em seguida, crie um resumo do que já existe e uma matriz com: requisito do regulamento, funcionalidade proposta, teste de aceitação, status (confirmado/proposta/pendente) e dependências. Destaque que a base oficial e seu formato devem ser confirmados antes de definir importação e cálculos. Sugira um MVP pequeno que maximize aderência, funcionamento, análise justificável, validação e clareza segundo os pesos do regulamento. Aponte riscos e perguntas bloqueadoras. Não gere código até que a equipe aprove o plano.
