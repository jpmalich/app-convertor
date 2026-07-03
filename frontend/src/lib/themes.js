// Theme registry + persistence (docs/specs/theme-picker.md).
// The actual token values live in index.css [data-theme=…] blocks; this file
// only knows ids, swatch chips for the picker, and how to apply/persist.
//
// "auto" follows the OS prefers-color-scheme: dark → "dark", light → default.

export const THEME_STORAGE_KEY = "ui-theme-v1";

export const THEMES = [
  // labelKey resolves via i18n; chip = [brand, ink, app-bg] swatch dots.
  { id: "auto", labelKey: "theme.auto", chip: ["#F97316", "#18181B", "#F4F4F5"] },
  { id: "orange", labelKey: "theme.orange", chip: ["#F97316", "#09090B", "#F4F4F5"] },
  { id: "blueprint", labelKey: "theme.blueprint", chip: ["#2563EB", "#0C1220", "#F2F4F8"] },
  { id: "forest", labelKey: "theme.forest", chip: ["#15803D", "#0A0F0B", "#F1F5F1"] },
  { id: "steel", labelKey: "theme.steel", chip: ["#334155", "#0B0F14", "#F2F4F6"] },
  { id: "highvis", labelKey: "theme.highvis", chip: ["#FACC15", "#09090B", "#F4F4F5"] },
  { id: "dark", labelKey: "theme.dark", chip: ["#F97316", "#FAFAFA", "#18181B"] },
];

const mq = () => window.matchMedia("(prefers-color-scheme: dark)");

function resolve(id) {
  if (id === "auto") return mq().matches ? "dark" : "orange";
  return id;
}

export function getStoredTheme() {
  try {
    const v = localStorage.getItem(THEME_STORAGE_KEY);
    return THEMES.some((t) => t.id === v) ? v : "auto";
  } catch {
    return "auto";
  }
}

export function applyTheme(id) {
  const resolved = resolve(id);
  // "orange" is the :root default — no attribute keeps the CSS minimal.
  if (resolved === "orange") {
    document.documentElement.removeAttribute("data-theme");
  } else {
    document.documentElement.setAttribute("data-theme", resolved);
  }
}

export function setTheme(id) {
  try {
    localStorage.setItem(THEME_STORAGE_KEY, id);
  } catch {
    /* private mode — apply for this session only */
  }
  applyTheme(id);
}

/** Re-apply on OS scheme change while in "auto". Call once at app start. */
export function watchSystemTheme() {
  mq().addEventListener?.("change", () => {
    if (getStoredTheme() === "auto") applyTheme("auto");
  });
}
