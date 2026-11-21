"use client";

import * as React from "react";

import { Dashboard } from "@/components/dashboard";
import { UploadAnalysis } from "@/components/upload-analysis";

type View = "demo" | "upload";
const HASH: Record<View, string> = { demo: "#demo", upload: "#upload" };

/** Two views behind a sticky tab bar: the demo-building results, and the analysis of the visitor's own CSV. */
export function AppShell() {
  const [view, setView] = React.useState<View>("demo");

  React.useEffect(() => {
    const sync = () => {
      const next: View = window.location.hash === HASH.upload ? "upload" : "demo";
      setView(next);
      if (window.location.hash) document.getElementById("views")?.scrollIntoView({ behavior: "smooth", block: "start" });
    };
    sync();
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  const select = (v: View) => {
    window.history.replaceState(null, "", HASH[v]);
    setView(v);
  };

  const tab = (v: View, label: string, sub: string, badge?: string) => (
    <button
      type="button"
      role="tab"
      aria-selected={view === v}
      onClick={() => select(v)}
      className={`flex min-h-12 flex-1 flex-col items-start rounded-lg border px-3 py-2 sm:px-4 text-left transition-colors sm:flex-none sm:min-w-64 ${
        view === v ? "border-primary bg-primary text-primary-foreground" : "hover:bg-muted"
      }`}
    >
      <span className="flex items-center gap-2 text-sm font-semibold">
        {label}
        {badge && <span className={`shrink-0 whitespace-nowrap rounded-full px-2 py-0.5 text-[10px] uppercase ${view === v ? "bg-primary-foreground/20" : "bg-primary text-primary-foreground"}`}>{badge}</span>}
      </span>
      <span className={`hidden text-xs sm:block ${view === v ? "text-primary-foreground/80" : "text-muted-foreground"}`}>{sub}</span>
    </button>
  );

  return (
    <>
      <div id="views" className="sticky top-0 z-20 scroll-mt-0 border-b bg-background/90 backdrop-blur">
        <div role="tablist" aria-label="Views" className="mx-auto flex w-full max-w-6xl gap-2 px-4 py-2 sm:px-6">
          {tab("demo", "Demo building", "Alerts, forecasts, peaks, emergency power")}
          {tab("upload", "Analyze your own data", "Upload a meter CSV, see results instantly", "Try it")}
        </div>
      </div>
      {view === "demo" ? (
        <Dashboard />
      ) : (
        <div role="tabpanel" className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
          <UploadAnalysis />
        </div>
      )}
    </>
  );
}
