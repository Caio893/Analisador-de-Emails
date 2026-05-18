import { createFileRoute, Outlet } from "@tanstack/react-router";
import { useAuth } from "@/features/auth/store/authStore";
import { useEffect } from "react";
import { useNavigate } from "@tanstack/react-router";

export const Route = createFileRoute("/app")({
  component: AppLayout,
});

function AppLayout() {
  const isConnected = useAuth((s) => s.isConnected);
  const completeOAuthFromUrl = useAuth((s) => s.completeOAuthFromUrl);
  const navigate = useNavigate();

  useEffect(() => {
    if (completeOAuthFromUrl()) return;
    if (!isConnected) navigate({ to: "/" });
  }, [completeOAuthFromUrl, isConnected, navigate]);

  if (!isConnected) return null;
  return <Outlet />;
}
