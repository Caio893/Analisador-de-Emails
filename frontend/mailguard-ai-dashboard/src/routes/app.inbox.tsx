import { createFileRoute } from "@tanstack/react-router";
import { InboxPage } from "@/features/emails/pages/InboxPage";

export const Route = createFileRoute("/app/inbox")({
  component: InboxPage,
  head: () => ({ meta: [{ title: "Caixa de Entrada — MailGuard AI" }] }),
});
