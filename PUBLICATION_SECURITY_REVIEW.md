# Publication Security Review

Este documento registra a revisao feita antes de preparar esta copia para um repositorio publico. O objetivo e evitar vazamento de senhas, tokens, chaves de API, credenciais OAuth e arquivos locais que nao devem ser publicados.

## Resultado

A pasta publica foi criada em:

```text
C:\Users\caio_\IdeaProjects\mailguard-ai-public
```

Ela foi gerada a partir do projeto original, mas sem:

- `.git/`
- `.env`
- `.env.production.test`
- arquivos `.env.*` locais, exceto `.env.example` e `.env.production.example`
- `node_modules/`
- caches, builds, logs, banco local SQLite e arquivos de IDE

## Achados No Projeto Original

| Local | Risco | Motivo | Acao na copia publica |
| --- | --- | --- | --- |
| `.env` | Alto | Continha `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `OPENAI_API_KEY` preenchidos. | Arquivo nao copiado. |
| `.env.production.test` | Medio/Alto | Continha senha preenchida de Basic Auth para beta/teste. Mesmo que seja teste, pode facilitar abuso se reutilizada. | Arquivo nao copiado. |
| `.env.example` | Baixo | Contem placeholders e variaveis esperadas, sem chaves reais. | Mantido. |
| `.env.production.example` | Baixo | Contem placeholders de producao e instrucoes de configuracao, sem chaves reais. | Mantido. |
| `docker-compose*.yml` | Baixo | Usa interpolacao de variaveis de ambiente; nao contem segredo literal. | Mantido. |
| `backend/config/settings.py` | Baixo | Le segredos via ambiente e valida configuracoes de producao. | Mantido. |
| `backend/api/services/gmail.py` | Baixo | Referencia `GOOGLE_CLIENT_SECRET`, access token e refresh token por variavel/objeto, sem valor literal. | Mantido. |
| `backend/api/services/openai_analysis.py` | Baixo | Usa `OPENAI_API_KEY` via settings, sem valor literal. | Mantido. |
| `docs/` | Baixo | Cita variaveis sensiveis como documentacao e usa placeholders. | Mantido. |

## Por Que Esses Itens Sao Sensíveis

- **OpenAI API key:** permite consumo pago da API em nome do dono da chave.
- **Google OAuth client secret:** faz parte da credencial do app OAuth e deve ficar apenas no backend/secret store.
- **Django `SECRET_KEY`:** protege assinaturas criptograficas do Django; expor essa chave pode comprometer sessoes e tokens assinados.
- **Basic Auth password:** mesmo em beta, uma senha compartilhada publicada pode permitir acesso nao autorizado.
- **Refresh/access tokens do Google:** permitem acesso a dados Gmail dentro dos escopos concedidos; devem ser criptografados em repouso e nunca versionados.

## Decisoes Aplicadas Na Copia Publica

- Publicar apenas templates `.env.example` e `.env.production.example`.
- Manter `.gitignore` bloqueando `.env`, `.env.*`, bancos locais, caches e artefatos de build.
- Nao copiar historico Git do projeto original, evitando que segredos antigos aparecam no historico publico.
- Manter as documentacoes de deploy e OAuth com placeholders para demonstrar maturidade operacional sem expor credenciais.
- Adicionar este relatorio para mostrar aos avaliadores que a publicacao foi tratada como uma etapa de seguranca, nao apenas como upload de codigo.

## Checklist Antes De Subir Para O GitHub

- Criar o repositorio Git a partir da pasta `mailguard-ai-public`, nao do projeto original.
- Conferir que `git status --ignored` nao mostra `.env` ou arquivos sensiveis prontos para commit.
- Rodar um scanner de segredos antes do primeiro push, por exemplo `gitleaks detect --source .` ou `trufflehog filesystem .`.
- Ativar secret scanning no GitHub, se a conta/organizacao permitir.
- Caso alguma chave real tenha sido exposta fora da maquina local, rotacionar imediatamente:
  - OpenAI API key
  - Google OAuth client secret
  - Django `SECRET_KEY`
  - senhas de banco ou Basic Auth
- Nunca publicar banco de dados, dumps, prints contendo emails reais ou logs de producao.

## Comandos De Verificacao Sugeridos

```bash
git init
git status --ignored
gitleaks detect --source .
```

Tambem e util pesquisar termos sensiveis manualmente:

```bash
rg -n --hidden -i "secret|password|token|api_key|client_secret|refresh_token|access_token|bearer|openai|google_client"
```

Observacao: esse comando encontra referencias normais a variaveis e codigo. O ponto de atencao e valor real preenchido, nao o nome da variavel.
