import { createFileRoute } from "@tanstack/react-router";
import { SpamPage } from "@/features/emails/pages/SpamPage";

export const Route = createFileRoute("/app/spam")({
  component: SpamPage,
  head: () => ({ meta: [{ title: "Spam — MailGuard AI" }] }),
});
