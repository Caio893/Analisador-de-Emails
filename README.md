# Email Radar / MailGuard AI

Aplicacao full-stack para analise de seguranca de emails do Gmail com IA. O sistema conecta uma conta Google com acesso somente leitura, sincroniza mensagens da inbox e do spam, extrai sinais tecnicos e classifica cada email por nivel de risco.

## Objetivo

O projeto ajuda usuarios a identificar mensagens confiaveis, suspeitas ou perigosas antes de clicar em links, abrir anexos ou responder a golpes. A classificacao combina heuristicas locais com analise avancada via OpenAI, mantendo a validacao final no backend.

## Funcionalidades

- Login com Google OAuth usando apenas o escopo `gmail.readonly`.
- Sincronizacao de emails da inbox e spam via Gmail API.
- Extracao de remetente, dominio, assunto, corpo, links, anexos, labels e headers relevantes.
- Classificacao em `trusted`, `slightly_trusted`, `suspicious` e `dangerous`.
- Score de risco, explicacao em portugues e sinais observados.
- Analise local de fallback quando a IA esta indisponivel.
- Analise avancada sob demanda com resposta estruturada por JSON Schema.
- Cache por hash de conteudo para evitar reanalises desnecessarias.
- Fila opcional com Valkey para processamento assincrono.
- Regras de remetente ou dominio confiavel, sem ignorar spam ou anexos perigosos.
- Preview seguro de email em iframe com sandbox.
- Deploy com Docker Compose, PostgreSQL, Valkey, Caddy e Nginx.

## Arquitetura

```text
Navegador
  -> Frontend React / Vite
  -> Django REST API
  -> PostgreSQL
  -> Gmail API
  -> OpenAI Responses API
  -> Valkey + worker opcional
```

O frontend nunca acessa Gmail ou OpenAI diretamente. Credenciais, tokens OAuth, chamadas externas e regras de negocio ficam no backend.

## Stack

- **React + TypeScript**: interface interativa, tipada e componentizada.
- **Vite / TanStack Router**: build moderno e roteamento client-side.
- **TanStack Query**: cache, paginacao, refetch e invalidacao de dados.
- **Zustand**: estado simples para conta conectada e selecao de email.
- **Django + Django REST Framework**: API, models, migrations, admin, sessoes e middleware.
- **PostgreSQL**: armazenamento de contas, emails, metadados e analises.
- **Valkey**: fila e deduplicacao de analises avancadas.
- **OpenAI SDK**: inferencia de risco com resposta estruturada.
- **Gmail API**: leitura de mensagens com permissao minima.
- **Docker Compose**: ambiente local e producao reproduzivel.
- **Caddy + Nginx**: proxy reverso publico e servidor estatico do frontend em producao.

## Pontos tecnicos de destaque

### Inferencia de IA

A logica principal fica em `backend/api/services/openai_analysis.py`.

O backend monta um payload reduzido com assunto, remetente, dominio, links, anexos, autenticacao e corpo limpo. A IA responde por um JSON Schema estrito com classificacao, score, categorias de ameaca, motivo e sinais. A resposta e normalizada pelo servidor antes de ser salva.

### Gerenciamento de contexto

Cada email recebe um `content_hash`, gerado a partir do payload usado na analise. Isso permite reaproveitar analises quando o conteudo nao mudou e evita chamadas repetidas para a IA. O campo `prompt_version` ajuda a controlar mudancas de comportamento quando o prompt evolui.

### Fallback local

Se a OpenAI estiver desativada, sem chave, com erro temporario ou limite atingido, o sistema aplica heuristicas locais. Elas observam termos suspeitos, label de spam do Gmail, anexos perigosos e outros metadados.

### Seguranca

- Arquivos `.env` reais sao ignorados pelo Git.
- `.env.example` e `.env.production.example` documentam variaveis sem segredos reais.
- Tokens OAuth ficam no banco do backend e podem ser criptografados com Fernet.
- O app usa escopo Gmail somente leitura.
- CORS, CSRF, cookies seguros, HSTS e headers de seguranca sao configuraveis por ambiente.
- O preview do corpo do email usa iframe com sandbox e `no-referrer`.

## Como rodar localmente

1. Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

2. Preencha as variaveis locais necessarias no `.env`, especialmente as credenciais Google OAuth e, se for usar IA real, `OPENAI_API_KEY`.

3. Suba os containers:

```bash
docker compose up --build
```

4. Acesse:

```text
Frontend: http://localhost:8080
Backend:  http://localhost:8000/api/healthz/
```

## Variaveis de ambiente

Use `.env.example` para desenvolvimento e `.env.production.example` para producao. Nunca publique arquivos `.env` reais.

Principais variaveis:

- `SECRET_KEY`
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_TOKEN_ENCRYPTION_KEY`
- `OPENAI_API_KEY`
- `POSTGRES_PASSWORD`
- `VITE_API_BASE_URL`

## Estrutura

```text
backend/
  api/
    services/
      gmail.py
      openai_analysis.py
      analysis_queue.py
      trusted_senders.py
  config/
frontend/
  mailguard-ai-dashboard/
docs/
caddy/
docker-compose.yml
docker-compose.prod.yml
```

## Observacoes

Este projeto foi desenvolvido como trabalho academico e portfolio tecnico. Para uso publico amplo, os proximos passos recomendados sao adicionar autenticacao propria por usuario, politicas formais de retencao de dados, backup automatizado e observabilidade de producao.
