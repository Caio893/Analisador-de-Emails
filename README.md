# Email Radar / MailGuard AI

---

<p align="left">
  <img alt="Python" src="https://img.shields.io/badge/PYTHON-3776AB?style=flat-square&logo=python&logoColor=white" />
  <img alt="Django" src="https://img.shields.io/badge/DJANGO-092E20?style=flat-square&logo=django&logoColor=white" />
  <img alt="Django REST Framework" src="https://img.shields.io/badge/DRF-B71C1C?style=flat-square&logo=django&logoColor=white" />
  <img alt="React" src="https://img.shields.io/badge/REACT-20232A?style=flat-square&logo=react&logoColor=61DAFB" />
  <img alt="TypeScript" src="https://img.shields.io/badge/TYPESCRIPT-3178C6?style=flat-square&logo=typescript&logoColor=white" />
  <img alt="Vite" src="https://img.shields.io/badge/VITE-646CFF?style=flat-square&logo=vite&logoColor=white" />
  <img alt="IA" src="https://img.shields.io/badge/IA%20INFERENCE-FF4F8B?style=flat-square&logo=openai&logoColor=white" />
</p>

<p align="left">
  <img alt="Gmail API" src="https://img.shields.io/badge/GMAIL%20API-EA4335?style=flat-square&logo=gmail&logoColor=white" />
  <img alt="OpenAI" src="https://img.shields.io/badge/OPENAI-111111?style=flat-square&logo=openai&logoColor=white" />
  <img alt="PostgreSQL" src="https://img.shields.io/badge/POSTGRESQL-4169E1?style=flat-square&logo=postgresql&logoColor=white" />
  <img alt="Valkey" src="https://img.shields.io/badge/VALKEY-CB0000?style=flat-square&logo=redis&logoColor=white" />
  <img alt="Docker" src="https://img.shields.io/badge/DOCKER-2496ED?style=flat-square&logo=docker&logoColor=white" />
  <img alt="Caddy" src="https://img.shields.io/badge/CADDY-1F88C0?style=flat-square&logo=caddy&logoColor=white" />
  <img alt="Nginx" src="https://img.shields.io/badge/NGINX-009639?style=flat-square&logo=nginx&logoColor=white" />
  <img alt="Security" src="https://img.shields.io/badge/SECURITY-FIRST-FFD43B?style=flat-square&logo=shield&logoColor=black" />
  <img alt="Production ready" src="https://img.shields.io/badge/PRODUCTION%20READY-22C55E?style=flat-square&logo=checkmarx&logoColor=white" />
</p>

Aplicacao web full-stack para analise de seguranca de emails do Gmail com painel React, API Django, sincronizacao via Gmail API, heuristicas locais e inferencia com IA.

O projeto foi preparado como entrega publicavel: o frontend roda em `frontend/mailguard-ai-dashboard/`, o backend em `backend/`, a configuracao de producao usa `docker-compose.prod.yml`, e os arquivos reais de ambiente ficam fora do Git por seguranca.

## Objetivo

O Email Radar ajuda usuarios a identificar mensagens confiaveis, suspeitas ou perigosas antes de clicar em links, abrir anexos ou responder a golpes. A classificacao combina sinais tecnicos do Gmail com analise avancada via OpenAI, mantendo a validacao final no backend.

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

| Camada | Tecnologias | Motivo |
| --- | --- | --- |
| Frontend | React, TypeScript, Vite | UI interativa, tipada e rapida para desenvolvimento. |
| Rotas e estado | TanStack Router, TanStack Query, Zustand | Cache, refetch, paginacao, selecao de email e estado de conta. |
| Backend | Django, Django REST Framework | API, models, migrations, admin, sessoes e middleware. |
| Dados | PostgreSQL | Persistencia de contas, emails, metadados e analises. |
| Fila | Valkey | Processamento assincrono e deduplicacao de analises. |
| IA | OpenAI Responses API | Inferencia estruturada com classificacao, score e explicacao. |
| Email | Gmail API + OAuth2 | Leitura de mensagens com permissao minima. |
| Deploy | Docker Compose, Caddy, Nginx | Ambiente reproduzivel, proxy reverso e frontend estatico em producao. |

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
