import { Dashboard } from "@/components/dashboard";
import { Badge } from "@/components/ui/badge";
import { results } from "@/lib/results";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <header className="border-b bg-gradient-to-b from-primary/10 to-transparent">
        <div className="mx-auto w-full max-w-6xl px-4 pt-14 pb-10 sm:px-6">
          <Badge variant="secondary">Sustainable energy · usage and efficiency · emergency power</Badge>
          <h1 className="mt-3 text-3xl font-semibold tracking-tight text-balance sm:text-5xl">Campus Energy Forecaster</h1>
          <p className="mt-3 max-w-3xl text-lg text-muted-foreground text-pretty">
            Finds energy a building wastes, and shows how long it can keep running on backup power when the grid goes down. Built on
            hourly meter data that any facilities team already has.
          </p>
          <p className="mt-3 text-sm text-muted-foreground">
            Demo data: {results.dataset.name}, a real office building, {results.dataset.period}. Public data, licence {results.dataset.license}.
          </p>
        </div>
      </header>
      <Dashboard />
    </main>
  );
}
