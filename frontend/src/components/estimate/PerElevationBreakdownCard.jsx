// Iter 78z (P1.3) — Per-Elevation Breakdown card with "+ Add Accent" override.
//
// Renders the AI's per-elevation profile callouts (Lap, Shake, B&B, etc.)
// as compact chips per elevation, plus an "Add Accent" button that lets
// the contractor manually inject profiles Claude missed (e.g. small porch
// B&B panels that vision tends to overlook on the Campbell house).
//
// Adding an accent updates `measurements._per_elevation_breakdown` AND
// `_per_profile_sqft`, then re-runs the backend catalog mapper via
// POST /api/measure/map so the line items reflect the override.
import React, { useMemo, useState } from "react";
import { Plus, X, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const PROFILE_LABELS = {
  lap:          "Lap",
  dutch_lap:    "Dutch Lap",
  shake:        "Shake",
  board_batten: "B&B",
  vertical:     "Vertical",
  nickel_gap:   "Nickel Gap",
  stone:        "Stone",
  brick:        "Brick",
  stucco:       "Stucco",
  unknown:      "Unknown",
};

const PROFILE_COLORS = {
  lap:          { bg: "#EFF6FF", border: "#3B82F6", text: "#1E3A8A" },
  dutch_lap:    { bg: "#EFF6FF", border: "#3B82F6", text: "#1E3A8A" },
  shake:        { bg: "#FEF3C7", border: "#F59E0B", text: "#78350F" },
  board_batten: { bg: "#FCE7F3", border: "#EC4899", text: "#831843" },
  vertical:     { bg: "#FCE7F3", border: "#EC4899", text: "#831843" },
  nickel_gap:   { bg: "#F3E8FF", border: "#A855F7", text: "#581C87" },
  stone:        { bg: "#F4F4F5", border: "#A1A1AA", text: "#3F3F46" },
  brick:        { bg: "#F4F4F5", border: "#A1A1AA", text: "#3F3F46" },
  stucco:       { bg: "#F4F4F5", border: "#A1A1AA", text: "#3F3F46" },
  unknown:      { bg: "#FEF2F2", border: "#EF4444", text: "#7F1D1D" },
};

const SIDING_FAMILIES = new Set([
  "lap", "dutch_lap", "shake", "board_batten", "vertical", "nickel_gap",
]);

const ACCENT_OPTIONS = [
  { value: "lap",          label: "Lap" },
  { value: "dutch_lap",    label: "Dutch Lap" },
  { value: "shake",        label: "Shake" },
  { value: "board_batten", label: "Board & Batten" },
  { value: "vertical",     label: "Vertical" },
  { value: "nickel_gap",   label: "Nickel Gap" },
];

function ProfileChip({ family, sqft, suffix }) {
  const c = PROFILE_COLORS[family] || PROFILE_COLORS.unknown;
  const label = PROFILE_LABELS[family] || family;
  const sqftStr = Math.round(sqft).toLocaleString();
  return (
    <div
      className="inline-flex items-baseline gap-1.5 border px-2 py-0.5 text-[11px]"
      style={{ background: c.bg, borderColor: c.border, color: c.text }}
      data-testid={`profile-chip-${family}`}
    >
      <span className="font-bold uppercase tracking-wider text-[10px]">{label}</span>
      <span className="font-mono-num font-bold">{sqftStr}</span>
      <span className="text-[9px] opacity-75">ft²{suffix ? ` · ${suffix}` : ""}</span>
    </div>
  );
}

function AddAccentModal({ elevationLabel, onClose, onSubmit }) {
  const [profile, setProfile] = useState("board_batten");
  const [sqft, setSqft] = useState("");
  const [location, setLocation] = useState("");
  const [busy, setBusy] = useState(false);
  const sqftNum = Number(sqft) || 0;
  const canSubmit = sqftNum > 0 && !busy;

  const submit = async () => {
    if (!canSubmit) return;
    setBusy(true);
    try {
      await onSubmit({ profile, sqft: sqftNum, location: location.trim() });
      onClose();
    } catch (e) {
      toast.error(e.message || "Failed to add accent");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4"
      data-testid="add-accent-modal"
      onClick={onClose}
    >
      <div
        className="bg-white max-w-md w-full border border-[#E4E4E7]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E4E4E7]">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] font-bold">
              {elevationLabel} elevation
            </div>
            <div className="text-sm font-bold">Add accent profile</div>
          </div>
          <button
            type="button"
            className="text-[#71717A] hover:text-[#09090B]"
            onClick={onClose}
            data-testid="add-accent-cancel"
          >
            <X size={16} />
          </button>
        </div>
        <div className="p-4 space-y-3">
          <p className="text-[11px] text-[#52525B] leading-snug">
            Use this to inject a profile the AI missed (e.g. a porch column
            wrap or a small B&B panel under a gable). The accent ft² is
            ADDED to that profile&apos;s total — it won&apos;t shrink the
            main wall area.
          </p>
          <label className="block">
            <span className="text-[10px] uppercase tracking-wider text-[#71717A] font-bold">
              Profile
            </span>
            <select
              className="block w-full mt-1 border border-[#E4E4E7] px-2 py-1.5 text-sm"
              value={profile}
              onChange={(e) => setProfile(e.target.value)}
              data-testid="add-accent-profile"
            >
              {ACCENT_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-wider text-[#71717A] font-bold">
              Approx ft²
            </span>
            <input
              type="number"
              min={1}
              step={1}
              className="block w-full mt-1 border border-[#E4E4E7] px-2 py-1.5 text-sm font-mono-num"
              value={sqft}
              onChange={(e) => setSqft(e.target.value)}
              placeholder="e.g. 48"
              data-testid="add-accent-sqft"
              autoFocus
            />
          </label>
          <label className="block">
            <span className="text-[10px] uppercase tracking-wider text-[#71717A] font-bold">
              Location (optional)
            </span>
            <input
              type="text"
              className="block w-full mt-1 border border-[#E4E4E7] px-2 py-1.5 text-sm"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. porch face"
              data-testid="add-accent-location"
            />
          </label>
        </div>
        <div className="flex justify-end gap-2 px-4 py-3 border-t border-[#E4E4E7] bg-[#FAFAFA]">
          <button
            type="button"
            className="border border-[#E4E4E7] px-3 py-1.5 text-sm hover:bg-white"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!canSubmit}
            className="bg-[#F97316] text-white px-3 py-1.5 text-sm font-bold disabled:opacity-50 hover:bg-[#EA580C]"
            onClick={submit}
            data-testid="add-accent-submit"
          >
            {busy ? "Adding…" : "Add accent"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PerElevationBreakdownCard({ measurements, onUpdate }) {
  const [accentElev, setAccentElev] = useState(null);

  const perElevation = measurements?._per_elevation_breakdown || [];
  const perProfile = useMemo(
    () => measurements?._per_profile_sqft || {},
    [measurements],
  );
  const sidingSqft = Number(measurements?.siding_sqft) || 0;

  // Sum of all SIDING families in per_profile (excludes stone/brick/stucco).
  const sumSidingProfiles = useMemo(() => {
    return Object.entries(perProfile).reduce((acc, [fam, sq]) => {
      if (!SIDING_FAMILIES.has(fam)) return acc;
      return acc + (Number(sq) || 0);
    }, 0);
  }, [perProfile]);

  // Skip rendering when AI didn't produce a per-elevation breakdown
  // (legacy / HOVER PDF runs).
  if (!perElevation.length) return null;

  // Sum-check banner — fires when the breakdown doesn't match siding_sqft
  // by more than 10% (rough guardrail for stale data / Claude misses).
  const driftPct = sidingSqft > 0
    ? Math.abs(sumSidingProfiles - sidingSqft) / sidingSqft * 100
    : 0;
  const showDrift = sidingSqft > 0 && driftPct > 10;

  const handleAddAccent = async ({ profile, sqft, location }) => {
    // Mutate the breakdown locally then call the backend to re-run the
    // catalog mapper. The map endpoint returns updated lines.
    const newPerElev = perElevation.map((e, i) => {
      if (i !== accentElev) return e;
      const accents = [...(e.accents || []), {
        location: location || "manual",
        profile,
        callout: "manual override",
        sqft,
      }];
      return { ...e, accents };
    });
    const newPerProfile = { ...perProfile };
    newPerProfile[profile] = (Number(newPerProfile[profile]) || 0) + sqft;

    const newMeasurements = {
      ...measurements,
      _per_elevation_breakdown: newPerElev,
      _per_profile_sqft: newPerProfile,
    };

    // Ask the backend to remap to lines (using the same /measure/map
    // endpoint AI Measure restore uses).
    const res = await api.post("/measure/map", { measurements: newMeasurements });
    const data = res?.data || {};
    if (!data?.lines) throw new Error("Backend did not return updated lines");
    onUpdate({ measurements: data.measurements || newMeasurements, lines: data.lines });
    toast.success(`Added ${PROFILE_LABELS[profile]} ${sqft} ft² to ${perElevation[accentElev].label}`);
  };

  return (
    <section
      className="p-5 border-b border-[#E4E4E7] bg-white"
      data-testid="per-elevation-breakdown"
    >
      <div className="flex items-center justify-between mb-2">
        <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA]">
          Per-Elevation Breakdown
        </div>
        <div className="text-[10px] text-[#71717A]">
          {perElevation.length} elevation{perElevation.length === 1 ? "" : "s"} ·
          {" "}
          <span className="font-mono-num font-bold text-[#09090B]">
            {Math.round(sumSidingProfiles).toLocaleString()}
          </span>{" "}
          ft² siding split
        </div>
      </div>
      <p className="text-[11px] text-[#52525B] leading-snug mb-3">
        AI reads the wall callouts on each elevation and splits siding into
        separate quote lines per profile. Use{" "}
        <span className="font-bold">+ Add Accent</span> to inject anything
        the AI missed (porch B&B, column shake, dormer scallop, etc.).
      </p>
      {showDrift && (
        <div
          className="flex items-start gap-2 border border-[#F59E0B] bg-[#FEF3C7] px-3 py-2 mb-3"
          data-testid="per-elevation-drift-warning"
        >
          <AlertTriangle size={14} className="text-[#92400E] flex-shrink-0 mt-0.5" />
          <div className="text-[11px] text-[#78350F] leading-snug">
            <span className="font-bold">Breakdown total drifts from siding total.</span>{" "}
            Profile sum is{" "}
            <span className="font-mono-num font-bold">
              {Math.round(sumSidingProfiles).toLocaleString()}
            </span>{" "}
            ft² but the measurement reports{" "}
            <span className="font-mono-num font-bold">
              {Math.round(sidingSqft).toLocaleString()}
            </span>{" "}
            ft² — a {driftPct.toFixed(0)}% gap. Add accents or re-run AI on this elevation.
          </div>
        </div>
      )}
      <div className="space-y-2">
        {perElevation.map((e, i) => {
          const bodyOk = e.wall_body_sqft > 0 && SIDING_FAMILIES.has(e.wall_body_profile);
          return (
            <div
              key={`${e.label}-${i}`}
              className="border border-[#E4E4E7] px-3 py-2"
              data-testid={`elevation-row-${e.label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <div className="text-xs font-bold uppercase tracking-wider text-[#09090B]">
                  {e.label || `Elevation ${i + 1}`}
                </div>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider font-bold text-[#F97316] hover:text-[#EA580C]"
                  onClick={() => setAccentElev(i)}
                  data-testid={`add-accent-btn-${i}`}
                >
                  <Plus size={12} /> Add Accent
                </button>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {bodyOk && (
                  <ProfileChip family={e.wall_body_profile} sqft={e.wall_body_sqft} suffix="body" />
                )}
                {e.gable_sqft > 0 && SIDING_FAMILIES.has(e.gable_profile) && (
                  <ProfileChip family={e.gable_profile} sqft={e.gable_sqft} suffix="gable" />
                )}
                {e.dormer_sqft > 0 && SIDING_FAMILIES.has(e.dormer_profile) && (
                  <ProfileChip family={e.dormer_profile} sqft={e.dormer_sqft} suffix="dormer" />
                )}
                {(e.accents || []).map((a, ai) => (
                  <ProfileChip
                    key={`${a.location}-${ai}`}
                    family={a.profile}
                    sqft={a.sqft}
                    suffix={a.location || "accent"}
                  />
                ))}
                {e.stone_sqft > 0 && (
                  <ProfileChip family="stone" sqft={e.stone_sqft} suffix="not siding" />
                )}
                {!bodyOk && !e.gable_sqft && !e.dormer_sqft && !(e.accents || []).length && (
                  <span className="text-[11px] text-[#A1A1AA] italic">
                    No siding profiles detected on this elevation
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      {accentElev !== null && (
        <AddAccentModal
          elevationLabel={perElevation[accentElev]?.label || "Selected"}
          onClose={() => setAccentElev(null)}
          onSubmit={handleAddAccent}
        />
      )}
    </section>
  );
}
