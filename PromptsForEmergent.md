# Prompts for Emergent

Copy-pasteable prompts for the Emergent AI tool (https://app.emergent.sh) that replicate
changes made in this repository into the Emergent-hosted version of the app.

**How to use:** open the Emergent project chat and paste the prompt block of any entry not
yet applied there, oldest first. Each prompt is self-contained — it describes the change by
rule and intent so the Emergent agent can implement it without seeing this repo's diffs.

**Maintenance rule:** every time a feature or change is completed in this repo, a new entry
is appended here (newest at the bottom) — date, summary, and the ready-to-paste prompt.
**Excluded by design:** anything related to decoupling this repo from the Emergent platform
(the direct-Anthropic LLM client, Docker self-hosting, removal of Emergent branding/telemetry,
dependency swaps). Those changes are intentionally NOT for replication into Emergent.

---

## 1 — WCAG AA accessibility pass + emoji-to-SVG icon cleanup (2026-07-02)

**What changed here:** ~410 context-sensitive contrast fixes across 63 frontend files, emoji
UI icons replaced with lucide SVGs, reduced-motion support, and the rules codified in
`design_guidelines.json`.

**Prompt for Emergent:**

```
Apply a WCAG AA accessibility pass to the entire React frontend. Keep the existing
Swiss/industrial brand (safety orange #F97316 on white/concrete grays) — change only the
tokens below, judging each occurrence by the effective background behind it (walk up the
JSX tree; modal headers and the sticky sell-bar are often black #09090B while bodies are
white).

RULE 1 — muted gray text #A1A1AA (2.56:1 on white — fails WCAG):
- As TEXT or ICON color on a light background (white, #FAFAFA, #F4F4F5 — the app default):
  replace #A1A1AA with #71717A (4.83:1).
- On a dark background (bg-[#09090B], bg-black, dark overlays/headers): KEEP #A1A1AA
  (7.76:1 on black — changing it there would be a regression).
- As a BORDER color or canvas/SVG drawing color (measurement lines drawn over photos):
  leave unchanged.

RULE 2 — brand orange as text, text-[#F97316] (2.80:1 on white — fails):
- On a light background: replace with text-[#C2410C] (5.18:1).
- On a dark background (sticky sell-bar active tab/sell price, black modal headers,
  dark logo boxes): KEEP text-[#F97316] (7.10:1 on black).
- bg-[#F97316] fills, border-[#F97316] accents, focus rings, canvas colors: leave unchanged.
- Inline-style JS constants that feed style={{color}} on light rows count as text colors —
  darken those too.

RULE 3 — orange buttons with white labels (2.80:1 — fails):
- Any element whose className contains BOTH bg-[#F97316] AND text-white: change text-white
  to text-[#09090B]. Black-on-safety-orange is 7.10:1 and fits the industrial brand.
  This includes .btn-primary in index.css, orange modal/submodal headers, count badges,
  and orange CTA links in the generated email HTML (lib/emailQuote.js) and print documents
  (lib/printTakeoff.js, lib/materialList.js — their standalone HTML is white-backed, so
  Rule 1 and 2 apply there as well).

RULE 4 — global CSS (src/index.css):
- :root --muted becomes #71717A; add --brand-text: #C2410C.
- .input:focus border-color uses #C2410C (focus indicators need 3:1 against white; #F97316
  is only 2.80:1).
- Add a prefers-reduced-motion block that zeroes animation/transition durations:
  @media (prefers-reduced-motion: reduce) { *, *::before, *::after {
    animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important; scroll-behavior: auto !important; } }

RULE 5 — replace emoji glyphs used as UI icons with lucide-react SVG icons (the library is
already installed). Known instances and their replacements:
- "🔍 Deep Verify" (HoverImportButton, both occurrences) → <ScanSearch> inline icon + text
- "⚡ Fast Track" (GuidedCaptureWizard toggle) → <Zap>
- "💡 Gable ft² …" hint and both "🔍 …" labels in AIMeasureButton → <Lightbulb> / <ScanSearch>
- "✏️ Precision · Pencil" chip (PhotoAnnotateModal) → <Pencil>
- Guided step titles in PhotoAnnotateModal: 🎯→<Crosshair>, 📏→<Ruler>, 🪟→<AppWindow>,
  🧱→<BrickWall>, 🏠→<Home>
- "✨ Auto-detect" (ProfileAnnotator) → <Sparkles>
- 💡 feedback-banner glyph (Dashboard) → <Lightbulb>
Give each icon aria-hidden="true" and a small inline size (w-3/w-4). Do NOT touch the
ASCII/pictograph positioning diagrams in GuidedCaptureWizard ("🏠 ← YOU (25-30 ft)" etc.) —
those are instructional content, not UI icons.

RULE 6 — small component fixes:
- EmailPipeline: the shared Stage badge applies one literal text-white over four fill
  colors; add a per-stage textColor prop (default text-white) and pass text-[#09090B] for
  the light gray "Sent" and orange "Clicked" stages.
- SectionAccordion "commonly needed" rows: keep the yellow tint + Lightbulb icon pairing
  (non-color cue), bump the icon to text-yellow-700, and use #C2410C for the
  orange-outline badges' text.
- InstallBanner: the Smartphone icon inside the orange tile gets text-[#09090B].

Finally, record these rules in design_guidelines.json: set colors.text.muted to #71717A,
add colors.brand.primary_text_on_light #C2410C, set borders.focus to #C2410C, change the
primary_button spec to black label text, set icons_strategy to lucide-react with a
"never use emoji as UI icons" note, and add an "accessibility" section stating: text on
light >= 4.5:1; orange text on light uses #C2410C; orange buttons use black labels;
#A1A1AA only on dark; focus indicators >= 3:1; reduced motion honored; never rely on
color alone.

Verify when done: no text-[#A1A1AA] remains on light surfaces, no className combines
bg-[#F97316] with text-white, no emoji UI icons remain, and the app builds.
```

---
