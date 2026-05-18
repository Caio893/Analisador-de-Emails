import { createFileRoute } from "@tanstack/react-router";
import { ProfilePage } from "@/features/profile/pages/ProfilePage";

export const Route = createFileRoute("/app/profile")({
  component: ProfilePage,
});
