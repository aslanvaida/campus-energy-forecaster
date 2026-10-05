import { HeroVortex } from "@/components/hero-vortex";
import { ModelOverview } from "@/components/model-overview";
import { Workbench } from "@/components/workbench";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="relative isolate flex min-h-[340px] items-end overflow-hidden border-b sm:min-h-[420px]">
        <div className="absolute inset-0 -z-10">
          <HeroVortex />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
        </div>
        <div className="mx-auto w-full max-w-6xl px-4 pt-24 pb-10 sm:px-6">
          <p className="text-sm font-medium tracking-wide text-primary uppercase">NTU Datathon 2026 · Smart Campus Analytics</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance sm:text-5xl">Campus Energy Forecaster</h1>
          <p className="mt-3 max-w-2xl text-muted-foreground text-pretty">
            Upload a building-energy dataset, choose how much of it to train on, and see how accurately the model
            predicts energy usage on the rows it has never seen.
          </p>
        </div>
      </section>

      <div className="mx-auto flex w-full max-w-6xl flex-col gap-12 px-4 py-10 sm:px-6">
        <ModelOverview />
        <section aria-labelledby="try-heading" className="flex flex-col gap-5">
          <h2 id="try-heading" className="text-2xl font-semibold tracking-tight">Train and test it on your data</h2>
          <Workbench />
        </section>
      </div>
    </main>
  );
}
