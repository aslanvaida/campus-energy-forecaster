import { DatasetSplitter } from "@/components/dataset-splitter";
import { HeroVortex } from "@/components/hero-vortex";

export default function Home() {
  return (
    <main className="flex flex-1 flex-col">
      <section className="relative isolate flex min-h-[340px] items-end overflow-hidden border-b sm:min-h-[420px]">
        <div className="absolute inset-0 -z-10">
          <HeroVortex />
          <div className="absolute inset-0 bg-gradient-to-t from-background via-background/40 to-transparent" />
        </div>
        <div className="mx-auto w-full max-w-5xl px-4 pt-24 pb-10 sm:px-6">
          <p className="text-sm font-medium tracking-wide text-primary uppercase">Campus Energy Forecaster</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-balance sm:text-5xl">Train / test splitter</h1>
          <p className="mt-3 max-w-2xl text-muted-foreground text-pretty">
            Upload a dataset, choose how much goes to training and how much to testing, and download two
            non-overlapping CSVs ready for the model.
          </p>
        </div>
      </section>

      <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        <DatasetSplitter />
      </div>
    </main>
  );
}
