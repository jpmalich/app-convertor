// Catalog items that contractors commonly need but the HOVER report can't
// auto-quantify (or doesn't cover at all). These render with a yellow row
// background in SectionAccordion so the contractor visually scans them
// before sending a quote and can't forget them.
//
// To add/remove from this list, just edit the set below — no other code change
// needed. Match must be EXACT (catalog item name).
export const COMMONLY_NEEDED_ITEMS = new Set([
  ".019 Coil (1 per 5 Sq Siding)",
  "Caulking (per color)",
  "J-blocks, Dryer vents",
  "Shutters (louvered, raised panel) standard sizes",
  "Tear-Off",
  "clean up/ haul away job debris",
  "Dumpster",
  'Fascia/rake or frieze up to 8" coverage',
  'Downspout 6"',
  "elbow",
  "Capping general",
  "Flashing",
]);

export function isCommonlyNeeded(itemName) {
  return COMMONLY_NEEDED_ITEMS.has(itemName);
}

/** Returns the count of commonly-needed items in a section's line list that
 *  are still unfilled (qty <= 0). Used on collapsed section headers to show a
 *  small "N items to review" hint so the contractor knows to open it. */
export function unfilledCommonCount(lines) {
  return (lines || []).filter(
    (l) => COMMONLY_NEEDED_ITEMS.has(l.name) && (l.qty || 0) <= 0
  ).length;
}
