import { DEFAULT_THEME, THEME_STORAGE_KEY, THEMES } from "@/lib/themes";

/**
 * Inline script that runs before first paint and sets data-theme from localStorage,
 * so there is no flash of the wrong theme. The content is a static, build-time string.
 */
const script = `(function(){try{var t=localStorage.getItem(${JSON.stringify(THEME_STORAGE_KEY)});var ok=${JSON.stringify(
  THEMES.map((x) => x.id),
)};document.documentElement.setAttribute("data-theme",ok.indexOf(t)>-1?t:${JSON.stringify(
  DEFAULT_THEME,
)});}catch(e){document.documentElement.setAttribute("data-theme",${JSON.stringify(DEFAULT_THEME)});}})();`;

export function ThemeScript() {
  return <script dangerouslySetInnerHTML={{ __html: script }} />;
}
