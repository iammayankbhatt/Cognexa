import { readFileSync } from "node:fs";
import path from "node:path";

import { describe, expect, it } from "vitest";

/** WCAG AA check on the theme tokens in globals.css (CLAUDE.md §6: all text meets AA). */
const css = readFileSync(path.resolve(__dirname, "../app/globals.css"), "utf8");

function tokens(theme: string): Record<string, string> {
  // Neon Noir shares its block with :root, so anchor on the data-theme selector's opening brace.
  const marker = `[data-theme="${theme}"] {`;
  const start = css.indexOf(marker);
  if (start === -1) throw new Error(`theme block not found: ${theme}`);
  const block = css.slice(start, css.indexOf("}", start));
  return Object.fromEntries(
    [...block.matchAll(/--([\w-]+):\s*(#[0-9a-f]{6});/gi)].map((m) => [m[1], m[2]]),
  );
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

const THEMES = ["neon-noir", "titanium-dark", "titanium-light"];
const KEYS = [
  "bg",
  "surface",
  "surface-2",
  "border",
  "text",
  "muted",
  "primary",
  "primary-fg",
  "accent",
  "success",
  "warning",
  "danger",
];

describe.each(THEMES)("%s contrast", (theme) => {
  const t = tokens(theme);

  it("defines every token", () => {
    for (const k of KEYS) expect(t[k], `--${k}`).toMatch(/^#[0-9a-f]{6}$/i);
  });

  it.each([
    ["text", "bg"],
    ["text", "surface"],
    ["text", "surface-2"],
    ["muted", "bg"],
    ["muted", "surface"],
    ["muted", "surface-2"],
    ["primary-fg", "primary"],
    ["success", "surface"],
    ["warning", "surface"],
    ["danger", "surface"],
  ])("%s on %s is at least 4.5:1", (fg, bg) => {
    expect(ratio(t[fg], t[bg])).toBeGreaterThanOrEqual(4.5);
  });
});
