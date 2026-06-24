// Takeoff Reconciliation Card
//
// Iter 78 (LETRICK follow-up): drop-in panel rendered inside the HOVER
// import and Blueprint Read preview modals. Shows three columns per row
// so Howard can spot drift between what the AI/HOVER returned and what
// the catalog will actually quote:
//
//   • Raw measurement   — the source number (eaves_lf, siding_sqft, etc.)
//   • Formula yields    — the line-qty the catalog mapper produced
//   • Order at X% waste — formula qty × (1 + waste/100), only for items
//                         where waste applies (siding + soffit panels)
//
// Reads `measurements` + `lines` from the takeoff result and the
// estimate's `waste_pct`. Pure presentation — no side effects.
import React from "react";
import { isCutProneItem } from "@/lib/wasteLogic";

// Items to surface, in display order. Two parallel row sets keyed by
// estimate.kind: vinyl/ascend uses the standard catalog item names;
// LP SmartSide uses the LP-specific catalog (38 Series Lap, 540 OSC,
// 440/540 Series Trim, 38 Series Soffit). Gutters / downspouts / end
// caps are shared across all siding tabs.
//
// Each entry maps:
//   label  — what the contractor sees
//   raw    — function(measurements) → "108 LF" / "1,800 ft²" / "—"
//   item   — exact catalog item name to look up in `lines`
//   tab    — which tab the line lives on
const VINYL_RECON_ROWS = [
  {
    label: "Siding",
    raw: (m) => fmtSq(m.siding_sqft),
    item: "Install Vinyl Siding",
    tab: "vinyl",
  },
  {
    label: "Outside corners",
    raw: (m) => fmtLf(m.outside_corner_lf),
    item: "Outside corners Standard color",
    tab: "vinyl",
  },
  {
    label: "Inside corners",
    raw: (m) => fmtLf(m.inside_corner_lf),
    item: "Inside Corners (Siding) Standard color",
    tab: "vinyl",
  },
  {
    label: "J-Channel",
    raw: () => "—",
    item: '3/4" J-Channel Standard color (2 per Sq of siding)',
    tab: "vinyl",
  },
  {
    label: "Finish Trim",
    raw: () => "—",
    item: "Finish Trim Standard color",
    tab: "vinyl",
  },
  {
    label: "Soffit (Charter Oak)",
    raw: (m) => fmtSqft(m.soffit_sqft),
    item: "Charter Oak Soffit Standard color",
    tab: "vinyl",
  },
  {
    label: "Soffit J-Channel",
    raw: () => "—",
    item: '3/4" Soffit J-Channel (Charter Oak) Standard color',
    tab: "vinyl",
  },
  {
    label: "Gutter",
    raw: (m) => fmtLf(m.eaves_lf),
    item: 'Gutter 6"',
    tab: "vinyl",
  },
  {
    label: "Downspouts",
    raw: () => "—",
    item: 'Downspout 6"',
    tab: "vinyl",
  },
  {
    label: "End caps",
    raw: () => "—",
    item: "End Cap",
    tab: "vinyl",
  },
];

// LP SmartSide rows — uses the LP factory-finish catalog.
const LP_RECON_ROWS = [
  {
    label: "LP Lap Siding (38 Series)",
    raw: (m) => fmtSq(m.siding_sqft),
    item: '38 Series Lap 3/8" x 8" x 16\'',
    tab: "lp_smart",
  },
  {
    label: "Outside Corner (540 OSC)",
    raw: (m) => fmtLf(m.outside_corner_lf),
    item: "540 Series OSC 5/4\" x 4\" x 16'",
    tab: "lp_smart",
  },
  {
    label: "Trim (440 Series)",
    raw: () => "—",
    item: '440 Series Trim 4/4" x 4" x 16\'',
    tab: "lp_smart",
  },
  {
    label: "Trim (540 Series)",
    raw: () => "—",
    item: '540 Series Trim 5/4" x 4" x 16\'',
    tab: "lp_smart",
  },
  {
    label: "Soffit Vented (38 Series)",
    raw: (m) => fmtSqft(m.soffit_sqft),
    item: "38 Series Soffit 16 x 16 Vented",
    tab: "lp_smart",
  },
  {
    label: "Soffit Closed (38 Series)",
    raw: () => "—",
    item: "38 Series Soffit 16 x 16 Closed",
    tab: "lp_smart",
  },
  {
    label: "Coil (.019)",
    raw: () => "—",
    item: ".019 Coil",
    tab: "lp_smart",
  },
  {
    label: "Gutter",
    raw: (m) => fmtLf(m.eaves_lf),
    item: 'Gutter 6"',
    tab: "lp_smart",
  },
  {
    label: "Downspouts",
    raw: () => "—",
    item: 'Downspout 6"',
    tab: "lp_smart",
  },
  {
    label: "End caps",
    raw: () => "—",
    item: "End Cap",
    tab: "lp_smart",
  },
];

const num = (v) => (v == null ? null : Number(v));
const fmt = (v, decimals = 0) =>
  v == null || isNaN(Number(v))
    ? "—"
    : Number(v).toLocaleString(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: decimals,
      });
const fmtLf = (v) => (v == null ? "—" : `${fmt(v, 0)} LF`);
const fmtSqft = (v) => (v == null ? "—" : `${fmt(v, 0)} ft²`);
const fmtSq = (v) => {
  const n = num(v);
  if (n == null || isNaN(n)) return "—";
  return `${(n / 100).toFixed(1)} SQ`;
};

const roundUpHalf = (n) => {
  const x = Number(n);
  if (!isFinite(x) || x <= 0) return 0;
  return Math.ceil(x * 2) / 2;
};

export default function TakeoffReconCard({ measurements, lines, wastePct = 0, kind = "siding" }) {
  if (!measurements || !lines || !lines.length) return null;
  const pct = Math.max(0, Number(wastePct) || 0);
  const rowSet = kind === "lp_smart" ? LP_RECON_ROWS : VINYL_RECON_ROWS;

  // Build a quick lookup: item name (lowercase) → first matching line.
  // Prefer same-tab matches; fall back to any tab so kind=ascend or
  // kind=lp estimates still surface a row.
  const byName = (name, tab) => {
    const lc = (name || "").toLowerCase();
    return (
      lines.find(
        (l) =>
          (l.name || "").toLowerCase() === lc && (l.tab || "vinyl") === tab
      ) ||
      lines.find((l) => (l.name || "").toLowerCase() === lc) ||
      null
    );
  };

  const rows = rowSet.map((r) => {
    const ln = byName(r.item, r.tab);
    if (!ln) return null;
    const qty = Number(ln.qty) || 0;
    const rawQty = Number(ln.raw_qty);
    const unit = ln.unit || "";
    // Iter 78 — waste is baked into qty on apply (via bakeWasteIntoLines).
    // Two scenarios:
    //   1) PRE-apply (preview modal): line has raw qty in `qty` and no
    //      `raw_qty` field. Simulate the waste for display so Howard sees
    //      what the estimate WILL look like after Apply.
    //   2) POST-apply (line already on the estimate): qty has waste baked
    //      in; raw_qty carries the original measurement.
    const hasRaw = isFinite(rawQty) && rawQty > 0;
    let formulaQty;
    let orderQty;
    if (hasRaw) {
      formulaQty = rawQty;
      orderQty = qty;
    } else if (isCutProneItem(ln)) {
      formulaQty = qty;
      orderQty = roundUpHalf(qty * (1 + pct / 100));
    } else {
      formulaQty = qty;
      orderQty = qty;
    }
    return {
      label: r.label,
      raw: r.raw(measurements),
      formula: formulaQty > 0 ? `${fmt(formulaQty, 1)} ${unit}` : "—",
      order: orderQty > 0 ? `${fmt(orderQty, 1)} ${unit}` : "—",
      drift: orderQty > formulaQty,
    };
  }).filter(Boolean);

  if (!rows.length) return null;

  return (
    <section
      className="p-5 border-b border-[#E4E4E7] bg-white"
      data-testid="takeoff-recon-card"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA]">
          Takeoff Reconciliation
        </div>
        <div className="text-[10px] uppercase tracking-wider text-[#71717A]">
          Waste · <span className="font-bold text-[#09090B]">{pct}%</span>{" "}
          <span className="text-[#A1A1AA]">(Siding + Soffit panels only)</span>
        </div>
      </div>
      <p className="text-[11px] text-[#52525B] leading-snug mb-3">
        AI reads the raw measurements; the catalog mapper converts them to
        line quantities; the Order column applies the waste factor so you
        can spot drift against what you&apos;d actually need to order.
      </p>
      <div className="border border-[#E4E4E7] overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#FAFAFA] text-[10px] uppercase tracking-wider text-[#71717A]">
            <tr>
              <th className="text-left px-3 py-2">Item</th>
              <th className="text-right px-3 py-2 w-32">AI raw</th>
              <th className="text-right px-3 py-2 w-32">Formula yields</th>
              <th className="text-right px-3 py-2 w-36">
                Order @ {pct}% waste
              </th>
            </tr>
          </thead>
          <tbody className="font-mono-num">
            {rows.map((r, i) => (
              <tr
                key={r.label}
                className={i % 2 ? "bg-white" : "bg-[#FAFAFA]"}
                data-testid={`recon-row-${r.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
              >
                <td className="px-3 py-1.5 text-[#09090B] font-bold font-sans">
                  {r.label}
                </td>
                <td className="px-3 py-1.5 text-right text-[#52525B]">{r.raw}</td>
                <td className="px-3 py-1.5 text-right text-[#09090B]">
                  {r.formula}
                </td>
                <td
                  className={`px-3 py-1.5 text-right ${
                    r.drift ? "text-[#F97316] font-bold" : "text-[#09090B]"
                  }`}
                >
                  {r.order}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
