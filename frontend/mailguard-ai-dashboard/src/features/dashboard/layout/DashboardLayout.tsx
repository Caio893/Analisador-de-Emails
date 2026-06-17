import { useEffect, useState, type ReactNode } from "react";
import { AppSidebar } from "../components/AppSidebar";
import { Topbar } from "../components/Topbar";
import { SummaryCards } from "@/features/summary/components/SummaryCards";
import { EmailList } from "@/features/emails/components/EmailList";
import { useEmailSelection } from "@/features/emails/store/emailSelectionStore";
import { EmailPreviewPanel } from "@/features/preview/components/EmailPreviewPanel";
import { useDebounce } from "@/shared/hooks/useDebounce";
import { cn } from "@/lib/utils";
import type { Folder } from "@/features/emails/types";

interface Props {
  folder: Folder;
  title: string;
  customMain?: ReactNode;
}

export function DashboardLayout({ folder, title, customMain }: Props) {
  const [search, setSearch] = useState("");
  const debounced = useDebounce(search, 250);
  const selectedEmailId = useEmailSelection((s) => s.selectedId);
  const selectEmail = useEmailSelection((s) => s.select);

  useEffect(() => {
    selectEmail(null);
  }, [folder, selectEmail]);

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-background">
      <AppSidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar search={search} onSearch={setSearch} />
        <div className="flex min-h-0 flex-1">
          {customMain ? (
            <main className="min-w-0 flex-1 overflow-y-auto">{customMain}</main>
          ) : (
            <main className="min-w-0 flex-1 overflow-hidden">
              <div className="flex h-full min-h-0 overflow-hidden">
                <section
                  className={cn(
                    "flex min-h-0 w-full flex-col overflow-hidden bg-background lg:w-[340px] lg:shrink-0 lg:border-r lg:border-border/70 xl:w-[360px] 2xl:w-[400px]",
                    selectedEmailId && "hidden lg:flex",
                  )}
                >
                  <div className="border-b border-border/60 bg-card/45 px-3 py-3 sm:px-5 sm:py-4">
                    <div className="mb-3 flex items-center justify-between">
                      <h1 className="text-base font-semibold text-foreground">{title}</h1>
                    </div>
                    <SummaryCards compact />
                  </div>
                  <div className="min-h-0 flex-1 overflow-y-auto">
                    <EmailList folder={folder} search={debounced} />
                  </div>
                </section>

                <section
                  className={cn(
                    "min-h-0 flex-1 overflow-hidden bg-background",
                    !selectedEmailId && "hidden lg:block",
                  )}
                >
                  <EmailPreviewPanel />
                </section>
              </div>
            </main>
          )}
        </div>
      </div>
    </div>
  );
}
