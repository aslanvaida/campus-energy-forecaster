"use client";

import * as React from "react";
import { Canvas } from "@react-three/fiber";

import { cn } from "@/lib/utils";
import type { ThemeMode } from "@/components/ui/vortex-utils/use-shadcn-theme";

const ENVIRONMENTS = {
  night: "radial-gradient(ellipse at 50% 45%, oklch(0.22 0.03 265) 0%, oklch(0.13 0.01 265) 70%)",
  dusk: "radial-gradient(ellipse at 50% 45%, oklch(0.3 0.06 30) 0%, oklch(0.15 0.03 290) 75%)",
  none: "transparent",
} as const;

export type SceneContainerProps = {
  children: React.ReactNode;
  className?: string;
  theme?: ThemeMode;
  /** Backdrop painted behind the transparent WebGL canvas. */
  environment?: keyof typeof ENVIRONMENTS;
  camera?: [number, number, number];
  fov?: number;
};

/** A full-size react-three-fiber canvas with a themed CSS backdrop. */
export function SceneContainer({
  children,
  className,
  theme = "auto",
  environment = "night",
  camera = [0, 0, 8],
  fov = 50,
}: SceneContainerProps) {
  return (
    <div
      className={cn("relative h-full w-full overflow-hidden", theme === "dark" && "dark", className)}
      style={{ background: ENVIRONMENTS[environment] }}
    >
      <Canvas
        camera={{ position: camera, fov }}
        dpr={[1, 2]}
        gl={{ alpha: true, antialias: true }}
        style={{ position: "absolute", inset: 0 }}
        aria-hidden
      >
        {children}
      </Canvas>
    </div>
  );
}
