export type ThemeId = "neon-noir" | "titanium-dark" | "titanium-light";

export interface ThemeMeta {
  id: ThemeId;
  label: string;
  description: string;
  isDark: boolean;
}

export const DEFAULT_THEME: ThemeId = "neon-noir";
export const THEME_STORAGE_KEY = "cognexa-theme";

export const THEMES: readonly ThemeMeta[] = [
  { id: "neon-noir", label: "Neon Noir", description: "Default dark theme", isDark: true },
  { id: "titanium-dark", label: "Titanium Dark", description: "Graphite and red", isDark: true },
  {
    id: "titanium-light",
    label: "Titanium Light",
    description: "High-contrast, for projectors",
    isDark: false,
  },
] as const;

export function isThemeId(value: unknown): value is ThemeId {
  return THEMES.some((t) => t.id === value);
}
