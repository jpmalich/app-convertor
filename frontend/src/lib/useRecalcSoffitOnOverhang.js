import { useEffect, useRef } from "react";
import { toast } from "sonner";

// Iter 78ai — Auto-recalculate soffit material qty when the contractor
// changes the Eave Overhang field. Soffit pieces are computed at import
// time using whatever overhang value the estimate had at that moment;
// without this hook, editing overhang from 12" → 24" later in the
// quoting flow leaves the original soffit qty stale.
//
// Behaviour:
//   • Fires only when `est.overhang_in` actually changes (skips initial mount).
//   • Recomputes qty for the 3 soffit rows (Charter Oak + LP Vented + LP Closed)
//     using `eaves_lf` + `rakes_lf` cached on `est.hover_measurements`.
//   • If `hover_measurements` is missing or has no LF data, the hook
//     no-ops (nothing to recompute from).
//   • Always overwrites existing qty — Howard's call (Iter 78ai) so the
//     reactive behavior is predictable. Contractor can still type a
//     custom qty after the recalc and it will stick until the next
//     overhang change.
//   • Single toast summarising what was recalculated so the contractor
//     understands why qty changed.

const CHARTER_OAK_SOFFIT = "Charter Oak Soffit Standard color";
const LP_VENTED = "38 Series Soffit 16 x 16 Vented";
const LP_CLOSED = "38 Series Soffit 16 x 16 Closed";

// PDF coverage rates — must mirror `backend/lp_smartside_formulas.py`
// and the legacy Vinyl/Ascend formulas in `backend/routes/hover.py`.
const LP_SOFFIT_SQFT_PER_PC = 21.3;     // 16" Soffit panel (Howard's default)
const LP_WASTE = 1.10;                   // 10% waste + ceil
const CHARTER_OAK_SQFT_PER_PC = 10.0;    // 10" exposure × 12' panel

function lpSoffitPcs(overhangIn, lf) {
  if (!lf || lf <= 0) return 0;
  return Math.max(0, Math.ceil((overhangIn / 12.0) * lf / LP_SOFFIT_SQFT_PER_PC * LP_WASTE));
}

function charterOakSoffitPcs(overhangIn, eavesLf, rakesLf) {
  const totalLf = (eavesLf || 0) + (rakesLf || 0);
  if (totalLf <= 0) return 0;
  return Math.max(0, Math.ceil((overhangIn / 12.0) * totalLf / CHARTER_OAK_SQFT_PER_PC));
}

export default function useRecalcSoffitOnOverhang(est, update) {
  const prevRef = useRef(undefined);

  useEffect(() => {
    if (!est) return;
    const current = Number(est.overhang_in ?? 12);
    const prev = prevRef.current;
    prevRef.current = current;

    // Skip initial mount — only react to actual changes.
    if (prev === undefined) return;
    if (prev === current) return;

    const m = est.hover_measurements;
    if (!m) {
      toast.info(
        `Overhang ${prev}" → ${current}" — soffit qty stays as-is (no HOVER/AI measurement on this estimate to recalculate from)`
      );
      return;
    }
    const eavesLf = Number(m.eaves_lf) || 0;
    const rakesLf = Number(m.rakes_lf) || 0;
    if (eavesLf <= 0 && rakesLf <= 0) {
      toast.info(
        `Overhang ${prev}" → ${current}" — no eaves/rakes LF in measurements, nothing to recalc`
      );
      return;
    }

    const targets = {
      [CHARTER_OAK_SOFFIT]: charterOakSoffitPcs(current, eavesLf, rakesLf),
      [LP_VENTED]: lpSoffitPcs(current, eavesLf),
      [LP_CLOSED]: lpSoffitPcs(current, rakesLf),
    };

    let changed = 0;
    const newLines = (est.lines || []).map((l) => {
      if (!(l.name in targets)) return l;
      const newQty = targets[l.name];
      if (l.qty === newQty) return l;
      changed += 1;
      return { ...l, qty: newQty };
    });

    if (changed === 0) {
      // Edge case: overhang changed but no soffit rows in the estimate
      // (e.g. contractor cleared them, or never imported). Quiet toast.
      toast.info(
        `Overhang updated to ${current}". No soffit rows in this estimate to recalc — they'll pick up the new value on the next HOVER/AI import.`
      );
      return;
    }

    update({ lines: newLines });
    toast.success(
      `Overhang ${prev}" → ${current}" — recalculated ${changed} soffit row${changed === 1 ? "" : "s"}`
    );
    // ESLint disable next line — we intentionally only react to overhang
    // changes; including the full `est` would re-run on every keystroke.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [est?.overhang_in]);
}
