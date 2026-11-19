import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { DEFAULT_THEME, THEME_STORAGE_KEY } from "@/lib/themes";

import { ThemeProvider } from "./theme-provider";
import { ThemeScript } from "./theme-script";
import { ThemeSwitcher } from "./theme-switcher";

function renderSwitcher() {
  return render(
    <ThemeProvider>
      <ThemeSwitcher />
    </ThemeProvider>,
  );
}

describe("theme switching", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.setAttribute("data-theme", DEFAULT_THEME);
  });

  it("starts on the default theme", () => {
    renderSwitcher();
    expect(screen.getByRole("radio", { name: /Neon Noir/ })).toBeChecked();
  });

  it("changes data-theme and persists to localStorage", async () => {
    renderSwitcher();
    await userEvent.click(screen.getByRole("radio", { name: /Titanium Light/ }));
    expect(document.documentElement.getAttribute("data-theme")).toBe("titanium-light");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("titanium-light");
    expect(screen.getByRole("radio", { name: /Titanium Light/ })).toBeChecked();
  });
});

describe("no-flash script", () => {
  function runScript() {
    const { container } = render(<ThemeScript />);
    const code = container.querySelector("script")!.innerHTML;
    new Function(code)();
  }

  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute("data-theme");
  });

  it("applies a stored theme before paint", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "titanium-dark");
    runScript();
    expect(document.documentElement.getAttribute("data-theme")).toBe("titanium-dark");
  });

  it("falls back to the default for unknown values", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "<script>alert(1)</script>");
    runScript();
    expect(document.documentElement.getAttribute("data-theme")).toBe(DEFAULT_THEME);
  });
});
