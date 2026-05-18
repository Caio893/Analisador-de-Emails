## Divisao Sugerida da Equipe

1. Interface do usuario: painel React, rotas, fluxo visual, conexao com Gmail, caixa de entrada e spam.
2. Camada Intermediaria: Caddy como proxy reverso publico e Nginx como servidor estatico da interface em producao.
3. Servidor da Aplicacao: API Django REST, modelos do banco, sincronizacao com Gmail, listagem de emails, regras de remetente confiavel e resumo.
4. Inteligencia Artificial: classificacao de risco com OpenAI, analise local, alternativa em caso de falha e validacao da resposta.
5. APIs, Seguranca e Prevencao: Gmail OAuth, API da OpenAI, variaveis de ambiente, criptografia, CORS/CSRF, autenticacao basica e prevencao contra injecao de prompt.

## Arquitetura Geral

Navegador
  |
  | Painel React / Vite
  v
Container da interface
  | desenvolvimento: Vite na porta 8080
  | producao: Nginx serve arquivos estaticos na porta 8080
  v
Caddy como proxy reverso publico em producao
  | /api/* -> backend:8000
  | outras rotas -> frontend:8080
  v
Servidor Django REST
  | leitura/escrita
  v
PostgreSQL
  |
  | suporte opcional a fila
  v
Redis / processador de analise
  |
  | APIs externas
  v
Google Gmail API + OpenAI Responses API

Arquivos principais para citar:

- Raiz do projeto: `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`, `.env.production.example`, `.gitignore`
- Interface do usuario: `frontend/mailguard-ai-dashboard/src/features/...`
- Servidor da interface em producao: `frontend/mailguard-ai-dashboard/nginx.conf.template`, `frontend/mailguard-ai-dashboard/Dockerfile.prod`
- Proxy reverso intermediario: `caddy/Caddyfile`
- Servidor da aplicacao: `backend/config/settings.py`, `backend/config/urls.py`, `backend/api/urls.py`, `backend/api/views.py`
- Modelos do banco: `backend/api/models.py`
- Servico Gmail: `backend/api/services/gmail.py`
- Analise com OpenAI: `backend/api/services/openai_analysis.py`
- Remetentes confiaveis: `backend/api/services/trusted_senders.py`
- Criptografia de tokens: `backend/api/fields.py`, `backend/api/services/crypto.py`
- Protecao da beta: `backend/api/middleware.py`

---

# Parte 1 - Interface do Usuario

## Explicacao

A interface do usuario e a parte visual do sistema, ou seja, aquilo que o usuario utiliza diretamente. Ela foi criada com React, TypeScript, Vite, TanStack Router, TanStack Query, Zustand, utilitarios de CSS, componentes Radix UI e icones Lucide.

O objetivo da interface e permitir que o usuario conecte uma conta Gmail, visualize mensagens da caixa de entrada e do spam, pesquise emails, selecione uma mensagem, leia o conteudo, veja a analise de risco feita pela IA ou pela analise local, confie em um remetente ou dominio, e remova um email da visualizacao do sistema.

A pasta principal da interface e `frontend/mailguard-ai-dashboard`. Dentro de `src/features`, o codigo foi separado por funcionalidades:

- `features/landing`: tela inicial, aviso de acesso somente leitura ao Gmail e botao de login com Google.
- `features/auth`: estado de conexao, tratamento do retorno do OAuth, armazenamento local, exclusao de dados locais e revogacao de acesso.
- `features/dashboard`: estrutura visual principal, menu lateral, barra superior, navegacao e botao "Analisar com IA".
- `features/emails`: chamadas para API, hooks, tipos, lista de emails, paginas de inbox e spam, badges de risco e estado de email selecionado.
- `features/summary`: cards de resumo, como emails triados hoje, spam detectado e emails suspeitos.
- `features/preview`: painel de leitura do email, renderizacao do corpo, acoes de confianca e explicacao da IA.
- `components/ui`: componentes visuais reutilizaveis.
- `shared`: utilitarios compartilhados, como formatacao de data e debounce.

## Fluxo da Interface

1. O usuario acessa a pagina inicial.
2. O usuario le o aviso sobre acesso somente leitura ao Gmail e aceita.
3. O usuario clica em "Continuar com Google".
4. A interface redireciona para `/api/auth/google/start/`.
5. O servidor faz o fluxo OAuth do Google e retorna para `/app/inbox?account=...&connected=1`.
6. `authStore.ts` le esses parametros, salva a conta conectada no armazenamento local e mostra a caixa de entrada.
7. O painel sincroniza os emails, mostra caixa de entrada/spam, permite pesquisa e selecao de mensagens.
8. O painel de preview mostra o conteudo do email, classificacao, pontuacao, explicacao e acoes.

## Por Que Separar Interface e Servidor?

A interface foi separada do servidor porque cada camada tem uma responsabilidade diferente. A interface cuida da experiencia do usuario, enquanto o servidor cuida de dados, seguranca, regras de negocio, acesso ao Gmail e chamadas para IA.

Essa separacao facilita manutencao, testes, implantacao separada e evita expor segredos no navegador, como credenciais do Google ou chave da OpenAI.

## Roteiro Curto de Fala

"A interface e a parte com a qual o usuario interage. Organizamos por funcionalidades, e nao apenas por tipo de arquivo, porque cada area da interface tem uma responsabilidade clara. A pagina inicial explica a permissao do Gmail, o estado de autenticacao trata o retorno do OAuth, o painel mostra pastas e busca, e a pre-visualizacao mostra o conteudo do email e a analise de risco. A interface nao fala diretamente com Gmail nem com OpenAI; ela chama apenas a nossa API do servidor."

## Possiveis Perguntas do Professor

Pergunta: Por que usar React e uma interface separada?

Resposta: Porque a interface tem muitos estados interativos: email selecionado, busca, carregamento infinito, estado do OAuth e atualizacao da analise. React ajuda a controlar isso. Separar do Django tambem evita misturar interface com logica sensivel de seguranca.

Pergunta: Por que usar TanStack Query?

Resposta: Porque ele gerencia dados vindos do servidor, cache, paginacao, nova busca automatica e invalidacao. Por exemplo, depois de clicar em "Analisar com IA", o hook `useAnalyzeFolder` invalida emails, email selecionado, resumo e contagem das pastas para atualizar a interface.

Pergunta: Por que existe `apiClient.ts`?

Resposta: Para centralizar chamadas ao servidor. Ele monta a URL da API usando `VITE_API_BASE_URL`, adiciona a conta conectada no cabecalho em desenvolvimento, envia credenciais quando configurado e padroniza tratamento de erro.

Pergunta: Por que o email e exibido em um iframe?

Resposta: Para isolar o HTML do email da aplicacao principal. O iframe usa `sandbox`, `referrerPolicy="no-referrer"` e conteudo controlado por `srcDoc`.

## Motivacao Tecnica

A arquitetura por funcionalidades foi escolhida porque o painel tem varios fluxos: conexao OAuth, sincronizacao, analise, gerenciamento de remetentes confiaveis e leitura de emails. Separar `api`, `hooks`, `components`, `pages` e `store` dentro de cada funcionalidade facilita manutencao e divisao de trabalho.

Exemplo simples:

```text
Usuario clica em "Analisar com IA"
  -> AppSidebar.tsx chama useAnalyzeFolder()
  -> useEmails.ts chama analyzeFolder()
  -> emailsApi.ts envia POST /api/emails/analyze/
  -> servidor analisa os emails elegiveis
  -> React Query invalida os caches
  -> interface mostra riscos e resumos atualizados
```

---

# Parte 2 - Nginx / Camada Intermediaria

## Explicacao

Neste projeto, a camada intermediaria tem duas partes reais:

1. O Caddy e o proxy reverso publico em producao.
2. O Nginx serve os arquivos estaticos da interface dentro do container de producao.

Existe uma pasta `nginx` no repositorio, mas a configuracao real do Nginx esta em `frontend/mailguard-ai-dashboard/nginx.conf.template`. Ja o proxy publico esta em `caddy/Caddyfile`.

Em producao, `docker-compose.prod.yml` inicia o Caddy nas portas 80 e 443. O Caddy recebe o trafego do navegador e roteia:

- `/api/*` para `backend:8000`.
- os demais caminhos para `frontend:8080`.

O container da interface em producao usa Nginx. O `Dockerfile.prod` primeiro compila o React com Node e depois copia o resultado para uma imagem `nginx:1.27-alpine`. O Nginx escuta na porta 8080 e serve os arquivos da aplicacao.

A configuracao do Nginx tambem oferece:

- `/healthz` para verificacao de status.
- `/privacy` e `/terms` como paginas publicas.
- cache longo para arquivos `/_build/`.
- `try_files ... /index.html` para que rotas do React funcionem ao atualizar a pagina.
- suporte opcional a autenticacao basica.

## Por Que Essa Camada E Util?

Essa camada intermediaria e util porque o navegador acessa um unico site em producao, mas internamente o sistema continua dividido entre interface e servidor. Isso facilita implantacao, organizacao de portas e seguranca, pois apenas o proxy fica exposto publicamente.

## Roteiro Curto de Fala

"Em producao, a entrada publica e o Caddy, enquanto o Nginx serve a interface compilada. O Caddy decide se a requisicao e da API ou da interface. Se o caminho comeca com `/api/`, ele envia para o Django. Caso contrario, envia para o container da interface. O Nginx entao serve os arquivos React compilados e permite que as rotas da interface funcionem."

## Possiveis Perguntas do Professor

Pergunta: Por que usar um proxy reverso?

Resposta: Porque ele permite expor publicamente apenas as portas 80 e 443, mantendo servidor, interface, Postgres e Redis em portas internas ou locais. Ele tambem centraliza roteamento e HTTPS.

Pergunta: Por que a interface usa Nginx em producao em vez do Vite?

Resposta: Porque o Vite e um servidor de desenvolvimento. Em producao, a interface vira arquivos estaticos, e o Nginx e mais adequado para servir esses arquivos.

Pergunta: Por que o Nginx usa `try_files $uri $uri/ /index.html`?

Resposta: Porque a interface e uma aplicacao de pagina unica. Se o usuario atualizar `/app/inbox`, o Nginx precisa retornar `index.html` para o React Router resolver a rota.

Pergunta: Qual e o papel do gerenciamento de portas?

Resposta: Em desenvolvimento, servidor e interface ficam expostos em 8000 e 8080. Em producao, o Caddy expoe 80/443, enquanto servidor e interface ficam vinculados a `127.0.0.1` por padrao. Isso reduz a superficie publica de ataque.

## Motivacao Tecnica

A camada intermediaria organiza a implantacao. Interface e servidor podem ser compilados, reiniciados e mantidos separadamente, enquanto o Caddy apresenta tudo como um unico site.

Exemplo simples:

```text
GET https://email-radar.com/app/inbox
  -> Caddy envia para frontend:8080
  -> Nginx retorna index.html
  -> React renderiza InboxPage

GET https://email-radar.com/api/emails/?folder=inbox
  -> Caddy envia para backend:8000
  -> Django retorna JSON
```

---

# Parte 3 - Servidor da Aplicacao

## Explicacao

O servidor foi construido com Django e Django REST Framework. Ele e responsavel pela logica principal da aplicacao porque armazena dados, comunica com o Gmail, protege segredos, controla OAuth, valida requisicoes, aplica regras de negocio e chama a OpenAI.

A interface nao deve fazer essas tarefas porque codigo no navegador pode ser inspecionado pelo usuario e nao e seguro para guardar credenciais.

## Estrutura do Servidor

- `backend/config`: configuracao principal do Django.
  - `settings.py`: variaveis de ambiente, banco de dados, CORS, CSRF, seguranca, OAuth, OpenAI e Redis.
  - `urls.py`: rotas `/admin/` e `/api/`.
  - `asgi.py` e `wsgi.py`: pontos de entrada do servidor.
- `backend/api`: aplicacao principal.
  - `models.py`: modelos do banco de dados.
  - `views.py`: endpoints da API.
  - `urls.py`: mapeamento de rotas da API.
  - `serializers.py`: conversao dos modelos para JSON usado na interface.
  - `services/gmail.py`: OAuth do Gmail e leitura de mensagens.
  - `services/openai_analysis.py`: analise por IA e analise local.
  - `services/trusted_senders.py`: regras de remetente/dominio confiavel.
  - `services/crypto.py` e `fields.py`: criptografia de tokens do Google.
  - `middleware.py`: autenticacao basica da beta fechada.
  - `management/commands/process_email_analysis_queue.py`: comando do processador de analise.
  - `admin.py`: registro dos modelos no Django Admin.

## Modelos Principais

- `GoogleAccount`: guarda a conta Gmail conectada e os tokens OAuth criptografados.
- `EmailRecord`: guarda emails sincronizados, pasta, remetente, assunto, corpo, metadados, anexos, status oculto e datas.
- `EmailAnalysis`: guarda classificacao de risco, pontuacao, explicacao, sinais, modelo usado e data da analise.
- `TrustedSenderRule`: guarda regras de email ou dominio confiavel por conta.

## Endpoints Principais

- `GET /api/healthz/`: verificacao de status.
- `GET /api/auth/google/start/`: inicia OAuth do Google.
- `GET /api/auth/google/callback/`: finaliza OAuth e salva a conta.
- `DELETE /api/account/`: apaga dados locais da conta.
- `POST /api/account/revoke/`: tenta revogar acesso OAuth no Google.
- `POST /api/emails/sync/`: sincroniza inbox/spam do Gmail.
- `POST /api/emails/analyze/`: executa analise avancada de uma pasta.
- `GET /api/emails/`: lista paginada de emails com pasta e busca.
- `GET /api/emails/<id>/`: detalhe do email e corpo para exibicao.
- `POST /api/emails/<id>/remove/`: oculta o email do painel.
- `POST /api/trusted-senders/`: cria regra de remetente/dominio confiavel.
- `GET /api/summary/`: resumo do painel.

## Regras de Negocio

O servidor trata mensagens como objetos `EmailRecord`. Ele trata usuarios nesta versao como contas `GoogleAccount` conectadas e sessoes do Django, nao como um sistema completo de usuarios proprio.

O projeto nao implementa agendamentos de atendimento. A parte mais parecida com uma execucao assincroma e a fila/processador de analise usando Redis e `process_email_analysis_queue.py`.

O projeto tambem nao implementa comandos administrativos por WhatsApp. As operacoes administrativas existem via Django Admin e endpoints da API.

## Roteiro Curto de Fala

"O servidor e onde ficam as regras reais da aplicacao. A interface pede dados, mas o Django decide qual conta Gmail esta ativa, sincroniza mensagens, salva no banco, aplica analise local e por IA, valida pastas, oculta emails removidos e calcula os resumos do painel. Separamos servicos como Gmail, OpenAI, remetentes confiaveis e criptografia para que cada responsabilidade seja mais facil de testar e explicar."

## Possiveis Perguntas do Professor

Pergunta: Por que usar Django no servidor?

Resposta: Porque Django oferece modelos, migracoes, painel administrativo, middleware, configuracoes, sessoes e recursos de seguranca. Isso e util porque o servidor lida com tokens OAuth e dados de email.

Pergunta: Por que `EmailRecord` guarda metadados?

Resposta: Porque metadados como dominio do remetente, reply-to, return-path, links, nomes de anexos, SPF, cabecalhos de autenticacao e labels ajudam a identificar risco e explicar por que uma mensagem e suspeita.

Pergunta: Por que `EmailRemoveView` oculta o email em vez de apagar?

Resposta: Porque ela define `hidden_at`, escondendo o email do painel sem destruir imediatamente o registro sincronizado. Isso evita exclusao destrutiva acidental.

Pergunta: Por que criar `TrustedSenderRule`?

Resposta: Para permitir que o usuario marque um email ou dominio como confiavel, reduzindo chamadas desnecessarias para IA. Mesmo assim, essa regra nao ignora casos de alto risco, como spam do Gmail ou anexos perigosos.

Pergunta: Como interface e servidor se comunicam?

Resposta: Por rotas REST em JSON abaixo de `/api/`. A interface usa `apiClient.ts` e o servidor responde com JSON serializado pelo Django REST Framework.

## Motivacao Tecnica

O servidor controla a logica principal porque e o unico ambiente confiavel. Ele guarda segredos no `.env`, criptografa tokens, valida pastas permitidas, controla paginacao e decide quando chamar APIs externas.

Exemplo simples:

```text
POST /api/emails/sync/ com folder inbox
  -> EmailSyncView valida conta e pasta
  -> sync_account_emails() chama Gmail
  -> parse_gmail_message() extrai cabecalhos, corpo, links e anexos
  -> EmailRecord e criado ou atualizado
  -> analyze_email_locally() cria classificacao local inicial
  -> interface busca novamente e exibe os resultados
```

---

# Parte 4 - Inteligencia Artificial

## Explicacao

A IA e usada para classificar emails por risco de seguranca. O arquivo principal e `backend/api/services/openai_analysis.py`.

O sistema pode classificar mensagens como:

- `trusted`: confiavel.
- `slightly_trusted`: levemente confiavel.
- `suspicious`: suspeito.
- `dangerous`: perigoso.

A integracao com a OpenAI monta um pacote de dados minimo com:

- pasta do email;
- assunto;
- nome e email do remetente;
- dominio do remetente;
- texto legivel do corpo.

O projeto evita enviar o objeto bruto completo do Gmail para a OpenAI. A funcao `build_openai_analysis_payload()` cria uma versao reduzida. A funcao `readable_text_for_ai()` remove URLs brutas do corpo antes da analise, para que o modelo foque no texto legivel e nao receba links longos de rastreamento desnecessariamente.

O modelo recebe o `OPENAI_SYSTEM_PROMPT`, que orienta a atuar como analista de seguranca de email, classificar risco, considerar spam, phishing, malware, virus e spoofing, e responder em portugues brasileiro.

A resposta da API e controlada por um esquema JSON estrito chamado `email_security_analysis`, exigindo classificacao, pontuacao, categorias de ameaca, explicacao e sinais.

## Por Que A IA Nao Decide Tudo Sozinha?

Mesmo usando IA, o servidor valida e normaliza a resposta:

- `normalize_payload()` valida a classificacao.
- `clamp_score()` limita a pontuacao entre 0 e 100.
- `create_response_with_retry()` tenta novamente em erros temporarios.
- `analyze_email()` usa analise local alternativa se a OpenAI falhar.
- `trusted_sender_analysis()` pode pular a OpenAI quando o remetente/dominio e confiavel.

A analise local e importante porque a IA nao deve ser a unica protecao. Se a chave da OpenAI nao existir, se a analise estiver desativada, se a API falhar ou se houver limite temporario, o sistema ainda gera uma classificacao preliminar usando termos suspeitos, etiqueta de spam do Gmail, metadados de anexo e extensoes perigosas.

O sistema atual nao interpreta transcricoes de audio, pedidos de agendamento, bairros, nomes de clientes ou comandos administrativos por WhatsApp. Ele interpreta dados de seguranca de email: remetente, dominio, assunto, corpo, pasta do Gmail, links, cabecalhos e anexos.

## Roteiro Curto de Fala

"A IA e usada como classificador avancado de seguranca de email. Nos nao enviamos tudo de forma cega para o modelo. O servidor monta um pacote de dados pequeno, remove URLs brutas do corpo legivel, pede uma resposta JSON estrita para a OpenAI e depois valida o resultado. Se a OpenAI falhar, a aplicacao continua funcionando com heuristicas locais. Isso e importante porque a IA apoia o sistema, mas o servidor continua responsavel pela validacao e seguranca."

## Possiveis Perguntas do Professor

Pergunta: Por que usar OpenAI em vez de apenas regras?

Resposta: Regras identificam padroes obvios, mas a IA consegue analisar contexto e explicar o risco em linguagem natural. Mesmo assim, regras continuam necessarias para alternativa em caso de falha, validacao e seguranca deterministica.

Pergunta: Por que remover URLs brutas antes de enviar o corpo para a IA?

Resposta: Links longos de rastreamento podem gerar ruido e expor dados desnecessarios. O projeto ja extrai metadados de links durante a leitura do Gmail, e o pacote de dados da IA mantem o corpo mais limpo.

Pergunta: Por que usar esquema JSON?

Resposta: Porque o esquema torna a resposta previsivel. O servidor espera campos como classificacao, pontuacao, explicacao e sinais. Isso evita respostas livres dificeis de salvar e exibir.

Pergunta: O que acontece se a OpenAI estiver indisponivel?

Resposta: `analyze_email()` captura o erro e usa analise local. Assim o usuario ainda recebe uma classificacao em vez de erro 500.

Pergunta: Por que nao confiar totalmente na IA?

Resposta: Porque IA pode errar, variar resposta ou ser influenciada pelo texto do email. Por isso o servidor valida classificacao, limita pontuacao, aplica regras de confianca com cuidado e nao permite que regra confiavel ignore spam ou anexos perigosos.

## Motivacao Tecnica

A arquitetura de IA e hibrida: regras locais garantem disponibilidade e seguranca basica, OpenAI melhora explicacao e classificacao, e o servidor valida o resultado final. Isso e mais seguro do que depender apenas do modelo.

Exemplo simples:

```text
Assunto: "Urgent account verification"
Corpo: "Click to verify your password"
Pasta: spam
Anexo: nenhum

Analise local:
  termos encontrados: urgent, verify, password, click
  label de spam do Gmail presente
  classificacao: dangerous

Analise com IA:
  retorna JSON com pontuacao, motivo em portugues e sinais de ameaca
```

---

# Parte 5 - APIs, Seguranca e Prevencao

## Explicacao

As APIs externas usadas no projeto atual sao:

- Google OAuth e Gmail API.
- OpenAI Responses API.

Nao existe integracao com WhatsApp no codigo atual. Se perguntarem, a resposta correta e: "Esta versao foca em seguranca de emails do Gmail. Integracao com WhatsApp e normalizacao de telefone nao foram implementadas."

## Integracao com Google

- O app usa escopo somente leitura do Gmail: `https://www.googleapis.com/auth/gmail.readonly`.
- O OAuth inicia em `build_google_auth_url()`.
- O callback e processado em `exchange_callback_for_account()`.
- As mensagens do Gmail sao buscadas com `build_gmail_service()` e interpretadas em `parse_gmail_message()`.
- Os tokens ficam apenas no banco do servidor, nao na interface.
- Access token e refresh token usam `EncryptedTextField`, com criptografia Fernet quando `GOOGLE_TOKEN_ENCRYPTION_KEY` esta configurada.

## Integracao com OpenAI

- A chave vem de `OPENAI_API_KEY`.
- O modelo vem de `OPENAI_MODEL` e `OPENAI_BULK_MODEL`.
- As chamadas ocorrem em `analyze_with_openai()`.
- A resposta usa esquema JSON estrito.
- Novas tentativas e alternativa local reduzem impacto de falhas.

## Variaveis de Ambiente

- `.env.example` documenta o ambiente local.
- `.env.production.example` documenta o ambiente de producao.
- `.gitignore` ignora `.env` e `.env.*`, mas permite arquivos de exemplo.
- Segredos como `SECRET_KEY`, segredo do Google, chave de criptografia de token, chave da OpenAI, senha beta e senha do banco nunca devem ser hardcoded nem commitados.

## Medidas de Seguranca Implementadas

- `DEBUG=false` no exemplo de producao.
- `SECRET_KEY`, `ALLOWED_HOSTS`, `POSTGRES_PASSWORD` e `GOOGLE_TOKEN_ENCRYPTION_KEY` sao exigidos quando necessario.
- CORS e CSRF sao controlados por variaveis de ambiente.
- Cookies seguros estao previstos para producao.
- `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`, HSTS e `X_FRAME_OPTIONS = "DENY"` estao configurados.
- Autenticacao basica da beta fechada existe em `BetaBasicAuthMiddleware`.
- Docker de producao deixa servidor/interface em localhost por padrao e expoe apenas Caddy em 80/443.
- PostgreSQL e Redis nao ficam publicos no compose de producao.
- O `state` do OAuth do Google e verificado no callback.
- Tokens OAuth nao sao enviados a interface.
- O corpo do email e exibido em iframe com sandbox e no-referrer.
- A resposta da IA e limitada por esquema e normalizada.
- Chamadas OpenAI tem novas tentativas e alternativa local.
- Regras de remetente confiavel nao ignoram spam do Gmail nem anexos perigosos.
- `ALLOW_ACCOUNT_HEADER_AUTH=false` em producao evita selecionar contas por header.

## Prevencao Contra Injecao de Prompt

O projeto nao possui um detector dedicado de injecao de prompt, mas reduz o risco de forma pratica:

- O modelo recebe um system prompt fixo.
- O email e enviado como dados JSON, nao como instrucao de sistema ou de desenvolvedor.
- A resposta esperada e limitada por esquema JSON.
- O servidor valida classificacao e pontuacao depois da resposta.
- O servidor mantem autoridade final sobre regras de confianca e alternativa local.
- URLs brutas sao removidas do corpo legivel antes da analise.

## Protecao de Comandos Administrativos

Nao existem comandos administrativos via WhatsApp neste projeto. As operacoes administrativas sao protegidas por:

- Painel administrativo do Django em `/admin/`.
- Autenticacao basica da beta fechada.
- Configuracoes de producao por variaveis de ambiente.
- Segredos acessiveis apenas no servidor.
- Logica de API que exige conta Gmail conectada ou sessao.

## Normalizacao de Telefone

Nao ha tratamento de telefone no codigo atual. O equivalente implementado e a normalizacao de emails e dominios em `trusted_senders.py`, onde remetentes e dominios sao convertidos para minusculo, aparados e normalizados antes de salvar ou comparar.

## Roteiro Curto de Fala

"As principais APIs externas sao Gmail e OpenAI. O Gmail e usado apenas com permissao de leitura, e os tokens OAuth ficam no servidor criptografados no banco. A OpenAI e usada para classificacao de risco, mas o servidor valida a resposta e possui alternativa local. Os segredos sao controlados por variaveis de ambiente e ignorados pelo Git. O codigo atual nao inclui WhatsApp nem logica de telefone, entao nao devemos afirmar que essas funcionalidades existem."

## Possiveis Perguntas do Professor

Pergunta: Por que segredos nao devem ser hardcoded?

Resposta: Porque pacotes gerados da interface e repositorios Git podem ser inspecionados. Segredos devem ficar em variaveis de ambiente para que cada ambiente use seus proprios valores sem expor no codigo-fonte.

Pergunta: Qual e a diferenca entre `.env` e `.env.example`?

Resposta: `.env` contem segredos reais locais e e ignorado pelo Git. `.env.example` contem valores de exemplo e documenta quais variaveis sao necessarias.

Pergunta: Como os tokens do Google sao protegidos?

Resposta: Eles ficam no modelo `GoogleAccount` usando `EncryptedTextField`. Em producao, a criptografia Fernet exige `GOOGLE_TOKEN_ENCRYPTION_KEY`.

Pergunta: Injecao de prompt esta totalmente resolvida?

Resposta: Nenhum sistema deve prometer isso totalmente. O projeto reduz risco com prompt fixo, pacote de dados JSON, esquema de resposta, normalizacao, limpeza de URLs e autoridade final no servidor.

Pergunta: Por que apenas administradores autorizados podem executar comandos?

Resposta: Neste projeto nao existem comandos via WhatsApp. O acesso administrativo e controlado pelo painel administrativo do Django, autenticacao basica da beta, configuracoes de ambiente e segredos mantidos no servidor.

Pergunta: Onde esta a normalizacao de telefone?

Resposta: Ela nao existe porque o projeto nao processa telefones. A normalizacao implementada e de emails e dominios confiaveis.

## Motivacao Tecnica

A seguranca foi desenhada com a ideia de que o servidor e confiavel e a interface nao e. A interface pode solicitar acoes, mas o servidor armazena tokens, controla OAuth, valida dados e chama APIs externas.

Exemplo simples:

```text
Callback OAuth retorna do Google
  -> servidor verifica state
  -> servidor troca code por tokens
  -> servidor salva tokens em GoogleAccount
  -> EncryptedTextField criptografa antes de gravar no banco
  -> interface recebe apenas account email + connected=1
```

---

# Encerramento da Apresentacao

"Em resumo, este projeto usa uma arquitetura separada porque cada camada tem uma responsabilidade clara. A interface apresenta o painel de seguranca de emails. A camada intermediaria roteia o trafego de producao e serve arquivos estaticos com eficiencia. O servidor controla as regras de negocio, banco de dados, integracao com Gmail e chamadas para OpenAI. A IA ajuda a classificar e explicar emails arriscados, mas o servidor valida e protege o sistema. Decisoes como acesso somente leitura ao Gmail, tokens OAuth criptografados, variaveis de ambiente, autenticacao basica, configuracao de CORS/CSRF e alternativa local tornam o projeto mais seguro e mais facil de publicar."
