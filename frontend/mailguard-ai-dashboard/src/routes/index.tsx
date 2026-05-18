import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect } from "react";
import { LandingPage } from "@/features/landing/pages/LandingPage";
import { useAuth } from "@/features/auth/store/authStore";

export const Route = createFileRoute("/")({
  component: Index,
});

function Index() {
  const isConnected = useAuth((s) => s.isConnected);
  const navigate = useNavigate();
  useEffect(() => {
    if (isConnected) navigate({ to: "/app/inbox" });
  }, [isConnected, navigate]);
  return <LandingPage />;
}
