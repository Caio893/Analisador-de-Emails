# Roteiro de Apresentacao com Referencias de Codigo

Documento base: [`docs/presentation-script-code-references.md`](./presentation-script-code-references.md)

Este roteiro foi montado para apresentar o Email Radar / MailGuard AI para colegas de classe, com foco nos bastidores tecnicos. Cada bloco inclui os arquivos, funcoes e chamadas principais com links para as linhas correspondentes no codigo.

## Slide 1 - Abertura e Proposito (0:00-0:50)

Fala:

"Este projeto se chama Email Radar, tambem chamado MailGuard AI. A ideia central e ajudar o usuario a analisar emails do Gmail e identificar mensagens confiaveis, suspeitas ou perigosas antes de clicar em links, abrir anexos ou responder a golpes."

Pontos tecnicos:

- O app usa o escopo readonly do Gmail, definido em [`backend/api/services/gmail.py#L21`](../backend/api/services/gmail.py#L21).
- As pastas analisadas inicialmente sao inbox e spam, mapeadas em [`backend/api/services/gmail.py#L22`](../backend/api/services/gmail.py#L22).
- As classificacoes ficam no modelo `EmailAnalysis.Risk`, em [`backend/api/models.py#L106`](../backend/api/models.py#L106).

## Slide 2 - Arquitetura Geral (0:50-2:00)

Fala:

"A arquitetura foi separada em camadas. O frontend cuida da experiencia do usuario, o backend concentra regras de negocio e seguranca, o banco guarda mensagens e analises, o Gmail fornece os emails e a OpenAI entra como classificador avancado."

Fluxo:

```text
React/Vite
  -> apiClient
  -> Django REST API
  -> Gmail API / PostgreSQL / Valkey
  -> OpenAI Responses API
```

Referencias:

- Configuracao de variaveis `.env`: [`backend/config/settings.py#L10`](../backend/config/settings.py#L10) e [`backend/config/settings.py#L14`](../backend/config/settings.py#L14).
- Rotas principais da API: [`backend/api/urls.py#L19`](../backend/api/urls.py#L19) ate [`backend/api/urls.py#L30`](../backend/api/urls.py#L30).
- Cliente HTTP do frontend: [`frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L16`](../frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L16).
- Chamada real com `fetch`: [`frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L40`](../frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L40).
- Credenciais/cookies opcionais na API: [`frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L43`](../frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L43).

## Slide 3 - Jornada de Desenvolvimento (2:00-3:30)

Fala:

"O projeto evoluiu de uma interface de visualizacao para uma aplicacao full-stack. A principal mudanca foi tirar a responsabilidade sensivel do navegador e colocar no backend: OAuth, tokens, Gmail, banco, IA, fila e regras de seguranca."

Mudancas arquiteturais:

- De mock/frontend para API real: `fetchEmails()` chama `/emails/` em [`emailsApi.ts#L41`](../frontend/mailguard-ai-dashboard/src/features/emails/api/emailsApi.ts#L41) e faz `apiFetch` em [`emailsApi.ts#L57`](../frontend/mailguard-ai-dashboard/src/features/emails/api/emailsApi.ts#L57).
- De analise imediata para analise sob demanda: botao "Analisar com IA" dispara `analyzeFolder.mutate(activeFolder)` em [`AppSidebar.tsx#L147`](../frontend/mailguard-ai-dashboard/src/features/dashboard/components/AppSidebar.tsx#L147).
- De processamento direto para fila opcional: `EmailAnalyzeView` usa `enqueue_email_analysis()` em [`backend/api/views.py#L201`](../backend/api/views.py#L201).
- Worker separado processa a fila em [`backend/api/management/commands/process_email_analysis_queue.py#L1`](../backend/api/management/commands/process_email_analysis_queue.py#L1).

## Slide 4 - Stack Tecnologico e Justificativa (3:30-5:10)

Fala:

"A stack foi escolhida pensando em separacao de responsabilidades. React e TypeScript resolvem a interface. Django e DRF resolvem API, modelos e seguranca. PostgreSQL guarda dados persistentes. Valkey permite fila. OpenAI entra como motor de inferencia controlado pelo servidor."

Referencias por tecnologia:

- Django settings e seguranca por ambiente: [`backend/config/settings.py#L28`](../backend/config/settings.py#L28), [`backend/config/settings.py#L29`](../backend/config/settings.py#L29), [`backend/config/settings.py#L143`](../backend/config/settings.py#L143).
- Banco PostgreSQL/SQLite configurado em [`backend/config/settings.py#L148`](../backend/config/settings.py#L148) e [`backend/config/settings.py#L155`](../backend/config/settings.py#L155).
- CORS/CSRF em [`backend/config/settings.py#L167`](../backend/config/settings.py#L167) e [`backend/config/settings.py#L179`](../backend/config/settings.py#L179).
- Configuracoes OpenAI em [`backend/config/settings.py#L75`](../backend/config/settings.py#L75) ate [`backend/config/settings.py#L85`](../backend/config/settings.py#L85).
- Configuracoes Valkey/fila em [`backend/config/settings.py#L87`](../backend/config/settings.py#L87) ate [`backend/config/settings.py#L96`](../backend/config/settings.py#L96).
- React Query para emails: [`useEmails.ts#L19`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L19).
- Invalidacao de cache apos analise: [`useEmails.ts#L68`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L68) ate [`useEmails.ts#L71`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L71).

## Slide 5 - Fluxo de OAuth com Gmail (5:10-6:40)

Fala:

"O login com Google comeca no frontend, mas o fluxo OAuth e controlado pelo backend. Isso evita expor client secret e tokens no navegador."

Fluxo com linhas:

1. Frontend redireciona para `/auth/google/start/` em [`authStore.ts#L52`](../frontend/mailguard-ai-dashboard/src/features/auth/store/authStore.ts#L52).
2. A rota existe em [`backend/api/urls.py#L20`](../backend/api/urls.py#L20).
3. `GoogleAuthStartView` chama `build_google_auth_url()` em [`backend/api/views.py#L76`](../backend/api/views.py#L76).
4. `build_google_auth_url()` monta o fluxo OAuth em [`backend/api/services/gmail.py#L93`](../backend/api/services/gmail.py#L93).
5. O Google callback cai em [`backend/api/urls.py#L21`](../backend/api/urls.py#L21).
6. `GoogleAuthCallbackView` valida `state` em [`backend/api/views.py#L86`](../backend/api/views.py#L86) e troca o `code` por tokens em [`backend/api/views.py#L93`](../backend/api/views.py#L93).
7. `exchange_callback_for_account()` chama `flow.fetch_token()` em [`backend/api/services/gmail.py#L124`](../backend/api/services/gmail.py#L124).
8. O perfil Gmail e lido em [`backend/api/services/gmail.py#L127`](../backend/api/services/gmail.py#L127).
9. A conta e persistida em `GoogleAccount`, modelo definido em [`backend/api/models.py#L7`](../backend/api/models.py#L7).

## Slide 6 - Sincronizacao de Emails (6:40-8:20)

Fala:

"Depois de conectar a conta, a interface sincroniza emails. O backend consulta Gmail, extrai corpo, links, anexos, headers e salva tudo em `EmailRecord`."

Chamadas:

- Frontend chama `syncEmails()` em [`emailsApi.ts#L98`](../frontend/mailguard-ai-dashboard/src/features/emails/api/emailsApi.ts#L98).
- A chamada HTTP vai para `/emails/sync/` em [`emailsApi.ts#L116`](../frontend/mailguard-ai-dashboard/src/features/emails/api/emailsApi.ts#L116).
- A rota esta em [`backend/api/urls.py#L24`](../backend/api/urls.py#L24).
- `EmailSyncView` chama `sync_account_emails()` em [`backend/api/views.py#L158`](../backend/api/views.py#L158).
- `sync_account_emails()` comeca em [`backend/api/services/gmail.py#L673`](../backend/api/services/gmail.py#L673).
- Cada mensagem e parseada por `parse_gmail_message()` em [`backend/api/services/gmail.py#L424`](../backend/api/services/gmail.py#L424).
- O corpo e extraido em [`backend/api/services/gmail.py#L272`](../backend/api/services/gmail.py#L272).
- URLs sao extraidas em [`backend/api/services/gmail.py#L301`](../backend/api/services/gmail.py#L301).
- Dominios sao normalizados em [`backend/api/services/gmail.py#L306`](../backend/api/services/gmail.py#L306).
- Metadados de anexos sao coletados em [`backend/api/services/gmail.py#L233`](../backend/api/services/gmail.py#L233).
- `EmailRecord` e o modelo salvo no banco, definido em [`backend/api/models.py#L27`](../backend/api/models.py#L27).

## Slide 7 - Inferencia de IA (8:20-10:30)

Fala:

"A IA nao recebe o email bruto inteiro. O backend cria um contexto reduzido e controlado, envia para a OpenAI com um system prompt fixo e exige resposta em JSON Schema."

Funcoes e chamadas principais:

- Prompt do sistema: [`backend/api/services/openai_analysis.py#L18`](../backend/api/services/openai_analysis.py#L18).
- Schema estrito da resposta: [`backend/api/services/openai_analysis.py#L28`](../backend/api/services/openai_analysis.py#L28).
- Entrada da analise avancada: `analyze_email()` em [`backend/api/services/openai_analysis.py#L502`](../backend/api/services/openai_analysis.py#L502).
- Montagem do payload para IA: [`build_openai_analysis_payload()` em `openai_analysis.py#L140`](../backend/api/services/openai_analysis.py#L140).
- Limpeza de URLs do corpo textual: [`readable_text_for_ai()` em `openai_analysis.py#L78`](../backend/api/services/openai_analysis.py#L78).
- Hash do contexto analisado: [`analysis_content_hash()` em `openai_analysis.py#L170`](../backend/api/services/openai_analysis.py#L170).
- Reaproveitamento de analise por hash: [`reusable_analysis_for_hash()` em `openai_analysis.py#L366`](../backend/api/services/openai_analysis.py#L366).
- Chamada para OpenAI: [`client.responses.create()` em `openai_analysis.py#L325`](../backend/api/services/openai_analysis.py#L325).
- Uso de `json_schema`: [`openai_analysis.py#L330`](../backend/api/services/openai_analysis.py#L330).
- Leitura do texto de resposta: [`parse_response_text()` em `openai_analysis.py#L265`](../backend/api/services/openai_analysis.py#L265).
- Normalizacao defensiva: [`normalize_payload()` em `openai_analysis.py#L283`](../backend/api/services/openai_analysis.py#L283).
- Salvamento da analise: [`save_analysis_result()` em `openai_analysis.py#L438`](../backend/api/services/openai_analysis.py#L438).

## Slide 8 - Fallback Local e Controle de Falhas (10:30-11:40)

Fala:

"Mesmo usando IA, o sistema nao depende 100% dela. Se a chave nao existir, se a API falhar ou se o limite diario for atingido, a aplicacao ainda gera uma classificacao local."

Referencias:

- Heuristica local: [`heuristic_analysis()` em `openai_analysis.py#L176`](../backend/api/services/openai_analysis.py#L176).
- Analise local inicial: [`analyze_email_locally()` em `openai_analysis.py#L469`](../backend/api/services/openai_analysis.py#L469).
- Verificacao de limite diario: [`daily_analysis_limit_reached()` em `openai_analysis.py#L361`](../backend/api/services/openai_analysis.py#L361).
- Tratamento de falha amigavel: [`friendly_openai_failure()` em `openai_analysis.py#L347`](../backend/api/services/openai_analysis.py#L347).
- Fallback se a OpenAI falhar dentro de `analyze_email()`: [`openai_analysis.py#L529`](../backend/api/services/openai_analysis.py#L529).
- Durante sync, emails novos recebem analise local em [`backend/api/services/gmail.py#L704`](../backend/api/services/gmail.py#L704).

## Slide 9 - Fila com Valkey e Worker (11:40-12:50)

Fala:

"Para nao travar a API quando ha muitos emails, o sistema pode colocar analises em uma fila. A API enfileira, o worker processa, e o frontend consulta o status."

Referencias:

- Cliente Valkey: [`valkey_client()` em `analysis_queue.py#L12`](../backend/api/services/analysis_queue.py#L12).
- Enfileiramento com deduplicacao: [`enqueue_email_analysis()` em `analysis_queue.py#L29`](../backend/api/services/analysis_queue.py#L29).
- Pop bloqueante da fila: [`pop_email_analysis()` em `analysis_queue.py#L82`](../backend/api/services/analysis_queue.py#L82).
- Marcacao de execucao: [`mark_email_analysis_running()` em `analysis_queue.py#L104`](../backend/api/services/analysis_queue.py#L104).
- Worker de fila: [`process_email_analysis_queue.py#L11`](../backend/api/management/commands/process_email_analysis_queue.py#L11).
- Worker chama `analyze_email()` em [`process_email_analysis_queue.py#L39`](../backend/api/management/commands/process_email_analysis_queue.py#L39).
- Frontend refaz polling quando a analise esta pendente em [`useEmails.ts#L26`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L26) e [`useEmails.ts#L40`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L40).

## Slide 10 - Regras de Remetente Confiavel (12:50-13:50)

Fala:

"O usuario pode confiar em um remetente ou dominio, mas o sistema nao deixa essa regra ignorar sinais de alto risco, como spam ou extensoes perigosas."

Referencias:

- Botao no preview chama `trustSender.mutate()` em [`EmailPreviewPanel.tsx#L433`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L433) e [`EmailPreviewPanel.tsx#L434`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L434).
- API chama `/trusted-senders/` em [`emailsApi.ts#L171`](../frontend/mailguard-ai-dashboard/src/features/emails/api/emailsApi.ts#L171).
- Rota da API: [`backend/api/urls.py#L29`](../backend/api/urls.py#L29).
- View principal: [`TrustedSenderRuleView` em `views.py#L360`](../backend/api/views.py#L360).
- Criacao da regra: [`create_trusted_sender_rule()` em `trusted_senders.py#L55`](../backend/api/services/trusted_senders.py#L55).
- Normalizacao de dominio/email: [`normalize_rule_value()` em `trusted_senders.py#L4`](../backend/api/services/trusted_senders.py#L4).
- Bloqueio de bypass em alto risco: [`has_high_risk_trusted_sender_bypass()` em `trusted_senders.py#L25`](../backend/api/services/trusted_senders.py#L25).
- Aplicacao da regra antes da IA: [`trusted_sender_analysis()` em `openai_analysis.py#L249`](../backend/api/services/openai_analysis.py#L249).

## Slide 11 - Preview Seguro do Email (13:50-14:50)

Fala:

"O corpo do email pode conter HTML externo e links. Por isso, a exibicao e isolada em um iframe com sandbox e sem envio de referrer."

Referencias:

- Cabecalho HTML controlado do iframe: [`EMAIL_FRAME_HEAD` em `EmailPreviewPanel.tsx#L47`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L47).
- Escape de HTML em texto puro: [`escapeHtml()` em `EmailPreviewPanel.tsx#L74`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L74).
- Transformacao de texto em links: [`linkifyText()` em `EmailPreviewPanel.tsx#L83`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L83).
- Montagem do documento exibido: [`buildEmailDocument()` em `EmailPreviewPanel.tsx#L91`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L91).
- `iframe sandbox`: [`EmailPreviewPanel.tsx#L180`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L180).
- `referrerPolicy="no-referrer"`: [`EmailPreviewPanel.tsx#L181`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L181).
- `srcDoc` controlado: [`EmailPreviewPanel.tsx#L182`](../frontend/mailguard-ai-dashboard/src/features/preview/components/EmailPreviewPanel.tsx#L182).

## Slide 12 - Seguranca de Segredos e Tokens (14:50-16:10)

Fala:

"O projeto foi estruturado para nao publicar segredos. Os `.env` reais ficam fora do Git, os exemplos documentam as variaveis, e tokens OAuth podem ser criptografados no banco."

Referencias:

- `.env` carregado apenas localmente: [`settings.py#L10`](../backend/config/settings.py#L10) e [`settings.py#L11`](../backend/config/settings.py#L11).
- `SECRET_KEY` obrigatoria fora de debug: [`settings.py#L29`](../backend/config/settings.py#L29) ate [`settings.py#L34`](../backend/config/settings.py#L34).
- Chave de criptografia Google obrigatoria em producao: [`settings.py#L61`](../backend/config/settings.py#L61) ate [`settings.py#L64`](../backend/config/settings.py#L64).
- Campo criptografado: [`EncryptedTextField` em `fields.py#L6`](../backend/api/fields.py#L6).
- Criptografia Fernet: [`encrypt_text()` em `crypto.py#L33`](../backend/api/services/crypto.py#L33).
- Descriptografia Fernet: [`decrypt_text()` em `crypto.py#L45`](../backend/api/services/crypto.py#L45).
- Tokens OAuth no modelo `GoogleAccount`: [`backend/api/models.py#L7`](../backend/api/models.py#L7).
- Basic Auth da beta: [`BetaBasicAuthMiddleware` em `middleware.py#L8`](../backend/api/middleware.py#L8).
- Comparacao segura com `secrets.compare_digest`: [`middleware.py#L43`](../backend/api/middleware.py#L43).

## Slide 13 - Fluxo de Dados Completo para Demonstrar (16:10-17:20)

Fala:

"Se eu clicar em Analisar com IA, a chamada sai do botao, passa pelo hook, chega na API, seleciona emails elegiveis, chama IA ou fila, salva no banco e invalida o cache da tela."

Passo a passo com links:

1. Botao chama `analyzeFolder.mutate(activeFolder)`: [`AppSidebar.tsx#L147`](../frontend/mailguard-ai-dashboard/src/features/dashboard/components/AppSidebar.tsx#L147).
2. Hook `useAnalyzeFolder()` define a mutation: [`useEmails.ts#L62`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L62).
3. Mutation chama `analyzeFolder(folder)`: [`useEmails.ts#L66`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L66).
4. `analyzeFolder()` chama `/emails/analyze/`: [`emailsApi.ts#L141`](../frontend/mailguard-ai-dashboard/src/features/emails/api/emailsApi.ts#L141).
5. Rota chega em `EmailAnalyzeView`: [`backend/api/urls.py#L25`](../backend/api/urls.py#L25) e [`backend/api/views.py#L162`](../backend/api/views.py#L162).
6. Se fila estiver ativa, chama `enqueue_email_analysis()`: [`backend/api/views.py#L201`](../backend/api/views.py#L201).
7. Se fila estiver desativada, chama `analyze_email()`: [`backend/api/views.py#L223`](../backend/api/views.py#L223).
8. `analyze_email()` monta hash e reaproveita cache: [`openai_analysis.py#L504`](../backend/api/services/openai_analysis.py#L504) e [`openai_analysis.py#L505`](../backend/api/services/openai_analysis.py#L505).
9. OpenAI e chamada em [`openai_analysis.py#L325`](../backend/api/services/openai_analysis.py#L325).
10. Resultado e salvo em [`openai_analysis.py#L537`](../backend/api/services/openai_analysis.py#L537).
11. Frontend invalida caches de emails, detalhe, resumo e contadores em [`useEmails.ts#L68`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L68) ate [`useEmails.ts#L71`](../frontend/mailguard-ai-dashboard/src/features/emails/hooks/useEmails.ts#L71).

## Slide 14 - Encerramento (17:20-18:00)

Fala:

"O ponto mais importante do projeto e que ele nao e apenas um prompt para IA. Ele tem arquitetura de produto real: OAuth, backend, banco, extracao de metadados, inferencia estruturada, fallback local, fila, cache por hash, seguranca de tokens e uma interface que explica o risco para o usuario."

Resumo tecnico:

- Modelagem principal: [`GoogleAccount`](../backend/api/models.py#L7), [`EmailRecord`](../backend/api/models.py#L27), [`TrustedSenderRule`](../backend/api/models.py#L71), [`EmailAnalysis`](../backend/api/models.py#L106).
- Entrada Gmail: [`sync_account_emails()`](../backend/api/services/gmail.py#L673).
- Entrada IA: [`analyze_email()`](../backend/api/services/openai_analysis.py#L502).
- Entrada fila: [`enqueue_email_analysis()`](../backend/api/services/analysis_queue.py#L29).
- Entrada frontend: [`apiFetch()`](../frontend/mailguard-ai-dashboard/src/features/emails/api/apiClient.ts#L40).
