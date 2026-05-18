import { Loader2 } from "lucide-react";
import { useAuth } from "../store/authStore";

interface ConnectGmailButtonProps {
  disabled?: boolean;
  describedBy?: string;
}

export function ConnectGmailButton({ disabled = false, describedBy }: ConnectGmailButtonProps) {
  const { connect, loading } = useAuth();

  const handle = async () => {
    if (disabled || loading) return;
    await connect();
  };

  return (
    <button
      onClick={handle}
      disabled={disabled || loading}
      aria-describedby={describedBy}
      style={{ fontFamily: "Roboto, Arial, sans-serif" }}
      className="inline-flex min-h-11 items-center justify-center gap-3 rounded border border-[#747775] bg-white px-3 py-2 text-sm font-medium text-[#1f1f1f] shadow-sm transition-colors hover:bg-[#f7f8f8] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:cursor-not-allowed disabled:opacity-60"
    >
      {loading ? (
        <>
          <Loader2 className="h-4 w-4 animate-spin text-[#1f1f1f]" />
          <span>Abrindo Google...</span>
        </>
      ) : (
        <>
          <GoogleIcon />
          <span>Continuar com Google</span>
        </>
      )}
    </button>
  );
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-[18px] w-[18px]" aria-hidden>
      <path
        d="M21.6 12.227c0-.71-.063-1.39-.182-2.045H12v3.868h5.39a4.61 4.61 0 0 1-2 3.027v2.515h3.232c1.892-1.745 2.978-4.314 2.978-7.365Z"
        fill="#4285F4"
      />
      <path
        d="M12 22c2.7 0 4.965-.895 6.622-2.408L15.39 17.077c-.896.6-2.04.96-3.39.96-2.604 0-4.81-1.76-5.6-4.123H3.064v2.59A9.997 9.997 0 0 0 12 22Z"
        fill="#34A853"
      />
      <path
        d="M6.4 13.914A6.013 6.013 0 0 1 6.087 12c0-.665.114-1.31.314-1.914V7.496H3.063A9.997 9.997 0 0 0 2 12c0 1.614.386 3.14 1.063 4.504L6.4 13.914Z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.964c1.468 0 2.786.505 3.823 1.496l2.868-2.868C16.96 2.99 14.695 2 12 2A9.997 9.997 0 0 0 3.063 7.496L6.4 10.086C7.19 7.722 9.396 5.964 12 5.964Z"
        fill="#EA4335"
      />
    </svg>
  );
}
