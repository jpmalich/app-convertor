import React, { useState } from "react";
import { Palette, Check } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useLang } from "@/lib/i18n";
import { THEMES, getStoredTheme, setTheme } from "@/lib/themes";

/**
 * Theme picker (docs/specs/theme-picker.md §6).
 * Default: palette icon button opening a Radix popover (Escape/focus handled
 * by Radix). `inline` renders the option list directly (Team page card).
 * Selection applies instantly and persists to localStorage.
 */
function ThemeOptions({ onPicked }) {
  const { t } = useLang();
  const [current, setCurrent] = useState(getStoredTheme);

  const pick = (id) => {
    setTheme(id);
    setCurrent(id);
    onPicked?.();
  };

  return (
    <div role="radiogroup" aria-label={t("theme.toggle.aria")} data-testid="theme-options">
      {THEMES.map((th) => {
        const active = th.id === current;
        return (
          <button
            key={th.id}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => pick(th.id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 text-left text-sm transition-colors ${
              active
                ? "bg-[var(--bg-app)] border border-[var(--border-strong)]"
                : "border border-transparent hover:bg-[var(--bg-app)]"
            }`}
            data-testid={`theme-${th.id}`}
          >
            <span className="flex gap-1 flex-shrink-0" aria-hidden="true">
              {th.chip.map((c, i) => (
                <span
                  key={i}
                  className="w-3.5 h-3.5 border border-[var(--ink)]/20"
                  style={{ background: c }}
                />
              ))}
            </span>
            <span className={`flex-1 ${active ? "font-bold text-[var(--ink)]" : "font-medium text-[var(--ink-2)]"}`}>
              {t(th.labelKey)}
            </span>
            {active && <Check className="w-4 h-4 text-[var(--brand-text)]" aria-hidden="true" />}
          </button>
        );
      })}
      <div className="sr-only" role="status" aria-live="polite">
        {t("theme.status", { name: t(THEMES.find((th) => th.id === current)?.labelKey || "theme.auto") })}
      </div>
    </div>
  );
}

export default function ThemePicker({ inline = false }) {
  const { t } = useLang();
  const [open, setOpen] = useState(false);

  if (inline) return <ThemeOptions />;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          className="btn-ghost"
          aria-label={t("theme.toggle.aria")}
          data-testid="theme-picker-btn"
        >
          <Palette className="w-4 h-4" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="w-60 p-1.5 bg-[var(--surface)] border border-[var(--border)] rounded-none shadow-lg"
      >
        <div className="px-3 pt-2 pb-1 text-[10px] font-bold uppercase tracking-[0.18em] text-[var(--ink-2)]">
          {t("theme.toggle.aria")}
        </div>
        <ThemeOptions onPicked={() => setOpen(false)} />
      </PopoverContent>
    </Popover>
  );
}
