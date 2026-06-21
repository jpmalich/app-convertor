// Iter 57aa — Item help descriptions.
//
// Keyed by EXACT catalog item name → { en, es } strings. When a name
// is present here, SectionAccordion renders a small `?` button next
// to the row name. Clicking it pops a Radix Popover with the matching
// description in the user's active language. No entry → no button.
//
// To add a new description, drop a new key/value pair below. Multi-line
// JS strings are fine — the popover wraps text. Howard writes these
// in English first; ES translation can be added at any time.
//
// Conventions:
// - Use exact catalog item name as the key (case + punctuation matter).
// - When multiple catalog rows share the same physical item (e.g.
//   Standard color vs Architectural color), repeat the description
//   under each key so the popover works regardless of which row is
//   clicked.

const ITEM_DESCRIPTIONS = {
  // ----- Finish trim (3 catalog rows share the same description) -----
  "Finish Trim Standard color": {
    en: "Finish trim is used to lock down the cut edge of a siding panel where there's no built-in lock to grab onto. Used under window sills and eaves, or under any horizontal trim or band where a panel terminates against it.",
    es: "El finish trim (riel de cierre) se usa para fijar el borde cortado de un panel de revestimiento cuando no hay un seguro integrado para sujetarlo. Se instala bajo los alféizares de las ventanas, los aleros, o debajo de cualquier moldura horizontal donde un panel termina contra ella.",
  },
  "Finish Trim Architectural color": {
    en: "Finish trim is used to lock down the cut edge of a siding panel where there's no built-in lock to grab onto. Used under window sills and eaves, or under any horizontal trim or band where a panel terminates against it.",
    es: "El finish trim (riel de cierre) se usa para fijar el borde cortado de un panel de revestimiento cuando no hay un seguro integrado para sujetarlo. Se instala bajo los alféizares de las ventanas, los aleros, o debajo de cualquier moldura horizontal donde un panel termina contra ella.",
  },
  "ASCEND Finish Trim": {
    en: "Finish trim is used to lock down the cut edge of a siding panel where there's no built-in lock to grab onto. Used under window sills and eaves, or under any horizontal trim or band where a panel terminates against it.",
    es: "El finish trim (riel de cierre) se usa para fijar el borde cortado de un panel de revestimiento cuando no hay un seguro integrado para sujetarlo. Se instala bajo los alféizares de las ventanas, los aleros, o debajo de cualquier moldura horizontal donde un panel termina contra ella.",
  },
};

export function getItemDescription(name, lang = "en") {
  if (!name) return null;
  const entry = ITEM_DESCRIPTIONS[name];
  if (!entry) return null;
  return entry[lang] || entry.en || null;
}

export function hasItemDescription(name) {
  return !!ITEM_DESCRIPTIONS[name];
}

export default ITEM_DESCRIPTIONS;
