"use client";

import * as React from "react";
import * as THREE from "three";

export type ThemeMode = "auto" | "light" | "dark";

const FALLBACK = { primary: "#e5e5e5", muted: "#737373" };

/** Resolve any CSS color (including oklch) to a THREE.Color by painting it on a 1x1 canvas. */
function toThreeColor(value: string, fallback: string): THREE.Color {
  const ctx = document.createElement("canvas").getContext("2d", { willReadFrequently: true });
  if (!ctx) return new THREE.Color(fallback);
  ctx.fillStyle = fallback;
  ctx.fillStyle = value || fallback;
  ctx.fillRect(0, 0, 1, 1);
  const [r, g, b] = ctx.getImageData(0, 0, 1, 1).data;
  return new THREE.Color().setRGB(r / 255, g / 255, b / 255, THREE.SRGBColorSpace);
}

/** Read --primary and --muted-foreground for the requested theme from a probe element. */
function readColors(theme: ThemeMode) {
  const probe = document.createElement("div");
  probe.style.display = "none";
  if (theme === "dark") probe.className = "dark";
  document.body.appendChild(probe);
  const style = getComputedStyle(probe);
  const colors = {
    primaryColor: toThreeColor(style.getPropertyValue("--primary").trim(), FALLBACK.primary),
    mutedColor: toThreeColor(style.getPropertyValue("--muted-foreground").trim(), FALLBACK.muted),
  };
  probe.remove();
  return colors;
}

/**
 * The shadcn theme colors as THREE.Colors. Re-reads them when the `dark` class on <html>
 * or the system color scheme changes.
 */
export function useShadcnTheme(theme: ThemeMode = "auto") {
  const [colors, setColors] = React.useState(() => ({
    primaryColor: new THREE.Color(FALLBACK.primary),
    mutedColor: new THREE.Color(FALLBACK.muted),
  }));

  React.useEffect(() => {
    const update = () => setColors(readColors(theme));
    update();
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class", "style"] });
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    media.addEventListener("change", update);
    return () => {
      observer.disconnect();
      media.removeEventListener("change", update);
    };
  }, [theme]);

  return colors;
}
