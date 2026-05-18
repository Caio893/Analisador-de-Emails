# Email Radar / MailGuard AI

![Django](https://img.shields.io/badge/Django-REST-0C4B33?style=for-the-badge&logo=django)
![React](https://img.shields.io/badge/React-TypeScript-149ECA?style=for-the-badge&logo=react)
![OpenAI](https://img.shields.io/badge/OpenAI-AI%20Analysis-111827?style=for-the-badge&logo=openai)
![Gmail](https://img.shields.io/badge/Gmail-Readonly%20OAuth-EA4335?style=for-the-badge&logo=gmail)
![Docker](https://img.shields.io/badge/Docker-Production%20Ready-2496ED?style=for-the-badge&logo=docker)

Plataforma full-stack de seguranca para Gmail que sincroniza mensagens com acesso somente leitura, classifica riscos de phishing/spam/golpes com IA e exibe uma explicacao clara para o usuario antes que ele clique em algo perigoso.

Este repositorio foi preparado como projeto publico de portfolio: ele demonstra arquitetura real, integracao com APIs externas, cuidado com privacidade, conteinerizacao, fallback local de IA e uma interface moderna orientada a produto.

## O Que Chama Atencao

- **Produto completo, nao apenas CRUD:** o sistema resolve um problema real de seguranca, com fluxo OAuth, sincronizacao Gmail, analise de risco, painel visual e acoes do usuario.
- **Seguranca como requisito de arquitetura:** segredos ficam no backend, tokens OAuth sao criptografados em repouso e o frontend nunca recebe chaves do Google ou da OpenAI.
- **IA com fallback confiavel:** quando a API de IA falha, nao ha tela quebrada; o backend usa heuristicas locais para manter uma classificacao preliminar.
- **Experiencia de avaliacao simples:** o frontend suporta modo mock para demonstracao visual sem conectar uma conta real.
- **Deploy pensado para producao:** stack com Django, React/Vite, PostgreSQL, Redis, Nginx e Caddy com HTTPS automatizado.

## Principais Funcionalidades

- Login com Google OAuth usando apenas o escopo `gmail.readonly`.
- Sincronizacao de mensagens da caixa de entrada e spam.
- Classificacao de risco em quatro niveis: confiavel, levemente confiavel, suspeito e perigoso.
- Pontuacao de risco de 0 a 100 com justificativa em portugues.
- Analise de phishing, spam, golpes, spoofing, malware, anexos perigosos, links e inconsistencias de dominio.
- Lista paginada de emails com busca por remetente, assunto, resumo e corpo.
- Painel de leitura com explicacao da IA e sinais detectados.
- Regras de remetente ou dominio confiavel para reduzir falsos positivos.
- Revogacao de token OAuth e exclusao dos dados locais da conta.
- Fila opcional com Redis para processamento assíncrono de analises.
- Configuracao de beta fechada com Basic Auth, CORS/CSRF e cookies seguros.

## Arquitetura

```mermaid
flowchart LR
    U["Usuario"] --> F["Frontend React + Vite"]
    F --> A["API Django REST"]
    A --> DB["PostgreSQL"]
    A --> R["Redis / fila opcional"]
    A --> G["Gmail API readonly"]
    A --> O["OpenAI Responses API"]
    C["Caddy HTTPS"] --> F
    C --> A
    N["Nginx producao"] --> F
```

## Stack Tecnica

- **Backend:** Django, Django REST Framework, PostgreSQL, Redis, Cryptography/Fernet.
- **Frontend:** React, TypeScript, Vite, TanStack Router, TanStack Query, Zustand, Radix UI, Lucide, Tailwind CSS.
- **IA:** OpenAI Responses API com JSON Schema estrito e fallback heuristico local.
- **Integracoes:** Google OAuth 2.0 e Gmail API com acesso somente leitura.
- **Infra:** Docker Compose, Caddy como proxy reverso, Nginx para servir o frontend em producao.

## Estrutura Do Projeto

```text
backend/                         API Django, modelos, servicos e seguranca
frontend/mailguard-ai-dashboard/ Frontend React/TypeScript
caddy/                           Proxy reverso publico para producao
docs/                            Guias de OAuth, deploy e revisao de seguranca
docker-compose.yml               Ambiente local
docker-compose.prod.yml          Stack de producao
.env.example                     Variaveis locais sem segredos reais
.env.production.example          Template de producao sem segredos reais
```

## Como Rodar Em Modo Demonstracao

Para avaliar rapidamente a interface sem Gmail real, use o modo mock do frontend.

```bash
cd frontend/mailguard-ai-dashboard
npm install
VITE_USE_MOCKS=true npm run dev
```

O painel ficara disponivel no endereco mostrado pelo Vite. Nesse modo, a UI usa emails ficticios e permite observar fluxos de lista, busca, resumo, preview e classificacao de risco.

## Como Rodar Com Backend Real

1. Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

2. Configure as variaveis necessarias:

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/api/auth/google/callback/
OPENAI_API_KEY=...
```

3. Suba a stack local:

```bash
docker compose up --build
```

4. Acesse:

```text
Frontend: http://localhost:8080
Backend healthcheck: http://localhost:8000/api/healthz/
```

Sem `OPENAI_API_KEY`, o backend continua funcionando com classificacao heuristica local.

## Decisoes De Seguranca

- O frontend chama apenas a API do backend; ele nao possui segredos de Gmail ou OpenAI.
- Tokens de acesso e refresh do Google sao persistidos no backend e criptografados com `GOOGLE_TOKEN_ENCRYPTION_KEY` quando configurado.
- O payload enviado para IA e reduzido: remetente, dominio, assunto e texto legivel limitado.
- URLs brutas sao removidas do corpo antes da analise por IA para reduzir ruído e exposicao desnecessaria.
- Em producao, `DEBUG=false` exige `SECRET_KEY`, `ALLOWED_HOSTS`, `POSTGRES_PASSWORD` e chave de criptografia.
- A copia publica remove arquivos locais de ambiente, historico Git e artefatos gerados.

Leia tambem: [PUBLICATION_SECURITY_REVIEW.md](PUBLICATION_SECURITY_REVIEW.md).

## Pontos Para Avaliadores

- [backend/api/services/gmail.py](backend/api/services/gmail.py): fluxo OAuth, leitura Gmail, parse de mensagens, links, anexos e cabecalhos.
- [backend/api/services/openai_analysis.py](backend/api/services/openai_analysis.py): prompt de seguranca, JSON Schema, retry, fallback local e normalizacao da resposta.
- [backend/api/fields.py](backend/api/fields.py): campo customizado para criptografia transparente de tokens.
- [backend/api/views.py](backend/api/views.py): endpoints de sincronizacao, analise, resumo, revogacao OAuth e regras de confianca.
- [frontend/mailguard-ai-dashboard/src/features](frontend/mailguard-ai-dashboard/src/features): organizacao por funcionalidades no frontend.
- [docs/google-oauth-verification-launch.md](docs/google-oauth-verification-launch.md): preparacao para verificacao OAuth do Google.

## Roadmap

- Autenticacao propria por usuario alem da beta fechada.
- Politicas de ownership para multiplas contas e equipes.
- Observabilidade com metricas de analise, latencia e falhas externas.
- Testes end-to-end do fluxo Gmail/OAuth em ambiente de staging.
- Painel administrativo para regras globais de confianca e bloqueio.

---

Projeto criado para demonstrar capacidade full-stack aplicada a seguranca, IA, privacidade, arquitetura de produto e preparo para producao.
