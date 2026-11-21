import { AppShell } from "@/components/app-shell";
import { HeroVortex } from "@/components/hero-vortex";
import { Badge } from "@/components/ui/badge";
import { results } from "@/lib/results";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <header className="relative isolate flex min-h-[380px] items-end overflow-hidden border-b sm:min-h-[460px]">
        <div className="absolute inset-0 -z-10">
          <HeroVortex />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/50 to-transparent" />
        </div>
        <div className="mx-auto w-full max-w-6xl px-4 pt-24 pb-10 sm:px-6">
          <Badge variant="secondary">Sustainable Energy · Usage and Efficiency · Emergency power for communities</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-balance sm:text-5xl">Campus Energy Forecaster</h1>
          <p className="mt-3 max-w-3xl text-lg text-muted-foreground text-pretty">
            A decision tool for schools, clinics and community buildings: it finds the electricity a building wastes, puts a cost and a
            carbon figure on it, and shows how long critical loads can keep running on backup power when the grid goes down. It
            runs on hourly meter data that most facilities already have.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <a href="#upload" className="rounded-lg bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow transition-opacity hover:opacity-90">
              Analyze your own meter data
            </a>
            <a href="#demo" className="rounded-lg border bg-background/60 px-5 py-2.5 text-sm font-medium backdrop-blur hover:bg-muted">
              See the demo building
            </a>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Demo data: {results.dataset.name}, a real office building, {results.dataset.period}. Public data, licence {results.dataset.license}.
            Your own file is analysed in your browser and never uploaded.
          </p>
        </div>
      </header>
      <AppShell />
    </main>
  );
}
