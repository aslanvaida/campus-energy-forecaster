"use client";

import * as React from "react";
import dynamic from "next/dynamic";

// three.js needs the browser, so skip prerendering the canvas.
const Vortex = dynamic(() => import("@/components/ui/vortex"), { ssr: false });

export function HeroVortex() {
  const [reduceMotion, setReduceMotion] = React.useState(false);

  React.useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduceMotion(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return <Vortex className="absolute inset-0" speed={reduceMotion ? 0 : 0.8} count={2600} />;
}
