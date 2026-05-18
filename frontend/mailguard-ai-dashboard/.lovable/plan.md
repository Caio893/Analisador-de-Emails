# MailGuard AI — Frontend (Vite + React + TS, arquitetura feature-based)

Aplicação web moderna, dark mode, inspirada em Thunderbird + Linear + Notion. Apenas frontend, com estado fake e dados mockados, pronta para futura integração com backend Django + Gmail API.

> Observação técnica: o template base usa TanStack Start (que já roda sobre Vite). Vamos manter o runtime Vite + React 19 + TS do template, mas substituir o roteador por **React Router v6** e remover o uso de loaders/SSR de rota, conforme solicitado. Resultado prático: mesmo stack pedido (Vite + React + TS + Tailwind), sem amarras com TanStack.

## Stack

- Vite + React 19 + TypeScript
- TailwindCSS v4 (tokens em `src/styles.css`)
- React Router v6 (`react-router-dom`)
- Zustand para estado global desacoplado
- TanStack Query para camada de dados (cache, paginação, retries) — independente do router
- shadcn/ui + lucide-react
- framer-motion para transições

## Arquitetura feature-based

```
src/
  app/
    App.tsx              # Providers (QueryClient, Router, Theme)
    router.tsx           # Definição de rotas
    routes.ts            # Constantes de paths
  features/
    auth/
      store/authStore.ts          # Zustand: isConnected, loading, connect, disconnect
      components/ConnectGmailButton.tsx
      hooks/useAuth.ts
    landing/
      pages/LandingPage.tsx
      components/Hero.tsx
    dashboard/
      layout/DashboardLayout.tsx  # Sidebar + Topbar + <Outlet/>
      components/AppSidebar.tsx
      components/Topbar.tsx
      components/AiActiveBadge.tsx
    emails/
      api/emailsApi.ts            # fetchEmails({folder,page,pageSize,search}), fetchEmail(id)
      api/emailsMock.ts           # dataset mockado realista
      hooks/useEmails.ts          # useInfiniteQuery / useQuery
      hooks/useEmail.ts
      store/emailSelectionStore.ts# Zustand: selectedEmailId (DESACOPLADO do preview)
      components/EmailList.tsx
      components/EmailListItem.tsx
      components/EmailPagination.tsx
      components/RiskBadge.tsx
      components/RiskScore.tsx
      pages/InboxPage.tsx
      pages/SpamPage.tsx
      types.ts                    # Email, RiskLevel, Folder, Paginated<T>
    preview/
      components/EmailPreviewPanel.tsx   # lê selectedEmailId do store; sem prop drilling
      components/EmptyPreview.tsx
    summary/
      api/summaryApi.ts
      hooks/useSummary.ts
      components/SummaryCards.tsx
    settings/pages/SettingsPage.tsx
    profile/pages/ProfilePage.tsx
  shared/
    ui/                  # shadcn (já existente)
    components/SearchInput.tsx
    lib/http.ts          # wrapper fetch (base URL via env, pronto pro Django)
    lib/queryClient.ts
    lib/format.ts        # datas, truncate
    hooks/useDebounce.ts
  styles.css
  main.tsx
```

Cada feature é autocontida (api, hooks, store, components, pages). Imports cruzados via barrel `index.ts` da feature, nunca acessando arquivos internos de outra feature diretamente.

## Roteamento (React Router v6)

```
/                       LandingPage  (redireciona pra /app se conectado)
/app                    DashboardLayout
  /app/inbox            InboxPage
  /app/spam             SpamPage
  /app/settings         SettingsPage
  /app/profile          ProfilePage
* NotFound
```

`ProtectedRoute` wrapper consulta `useAuth()` e redireciona pra `/`.

## Estado desacoplado do preview

- `emailSelectionStore` (Zustand) guarda apenas `selectedEmailId`.
- `EmailListItem` chama `setSelected(id)`.
- `EmailPreviewPanel` lê `selectedEmailId` + `useEmail(id)` independentemente — pode ser montado em qualquer lugar (drawer mobile, painel direito desktop, modal) sem refator.
- Lista e preview não compartilham props; comunicam via store + query cache.

## Paginação

- API mock e contrato real seguem `{ items, page, pageSize, total, hasMore }`.
- `useEmails` usa `useInfiniteQuery` com `getNextPageParam`.
- `EmailList` com scroll infinito (IntersectionObserver) **ou** botão "Carregar mais" — escolho scroll infinito + fallback de botão.
- Filtro de busca (`search`) e filtro de pasta entram na `queryKey` para cache correto.

## Camada de API pronta pro Django

- `shared/lib/http.ts`: `const API_BASE = import.meta.env.VITE_API_URL ?? ""`. Em modo mock (`VITE_USE_MOCKS=true`, default), `emailsApi` retorna do dataset com `setTimeout` simulando latência. Trocar pra real = mudar 1 flag e implementar fetch.
- DTOs em `features/emails/types.ts` espelham o schema esperado do Django REST Framework (snake_case → camelCase via mapper opcional).

## Fluxo de auth (mock)

1. Landing → botão "Conectar Gmail" (estilo Google OAuth, com logo G).
2. `connect()` → `loading=true` por ~1500ms (spinner + "Autenticando com Google…") → `isConnected=true`, persistido em `localStorage`.
3. Navega pra `/app/inbox`.
4. Profile tem botão "Desconectar" → `disconnect()` limpa store + storage → volta pra `/`.

## Dashboard — UI

```text
┌────────────────────────────────────────────────────────────────┐
│ Topbar:  🔍 Search (debounced) · ● IA ativa · Avatar          │
├──────────┬───────────────────────────────┬─────────────────────┤
│ Sidebar  │ SummaryCards (4 KPIs)         │ EmailPreviewPanel   │
│ Logo     │ ───────────────────────────── │ (assunto, from,     │
│ Inbox 12 │ EmailList (paginada)          │  body, RiskScore,   │
│ Spam   3 │  • item selecionado destaca   │  motivo da IA)      │
│ Settings │  • scroll infinito            │                     │
│ Profile  │                               │ EmptyPreview se     │
│          │                               │ nada selecionado    │
└──────────┴───────────────────────────────┴─────────────────────┘
```

- Resumo Inteligente: 4 cards — Emails analisados hoje, Spam detectado, Suspeitos, Taxa de risco %.
- Sidebar: contadores derivados de `useSummary()`.
- `<1024px`: preview vira `Sheet` (drawer) lateral, mesmo store.

## Design system (`src/styles.css`)

Tokens dark azulados + neon sutil em **oklch**:
- `--background` ~ `oklch(0.18 0.02 260)`
- `--card` ~ `oklch(0.22 0.025 260)`
- `--primary` ~ `oklch(0.72 0.17 250)` (azul neon)
- `--accent-glow` ~ ciano sutil para indicadores
- Risco: `--risk-safe` (verde), `--risk-suspicious` (âmbar), `--risk-phishing` (vermelho)
- Tipografia: Inter
- Sombras suaves, gradientes muito discretos, bordas arredondadas

## Polish

- Skeletons na primeira carga (lista, summary, preview).
- framer-motion: fade/slide do preview, stagger nos cards de resumo.
- Hover elegante nos itens; selecionado com borda lateral neon.
- Indicador "IA ativa": dot pulsante verde-neon no topbar.
- Busca debounced (250ms) integrada à `queryKey`.
- `localStorage` persiste `isConnected` e `selectedEmailId` (opcional).

## Dataset mockado

15–20 emails realistas em PT-BR (newsletters, bancos, phishing, promo spam, trabalho), distribuídos entre `inbox` e `spam`, cada um com `risk`, `riskScore` (0–100) e `aiReason` curto explicando a classificação.

## Fora de escopo

OAuth real, Gmail API, backend Django, IA real, persistência server-side.

Pronto pra implementar assim que aprovado.