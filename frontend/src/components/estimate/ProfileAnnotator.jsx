// Iter 78z — Profile Annotator modal.
//
// Lets the contractor draw bounding boxes on uploaded photos / blueprint
// pages and tag each box with a canonical profile family (Shake / B&B /
// Lap / etc.). Annotations are saved per-estimate and applied as
// authoritative accents in the AI Measure / Blueprint worker — guaranteeing
// the catalog mapper emits the right per-profile line on the material list.
//
// Workflow:
//   1. Pick an image from the strip on the left (photos OR blueprint pages).
//   2. Optionally set the scale reference: click "+ Set scale", drag a line
//      between two points of known length, enter the real-world distance.
//      All boxes drawn on this image will auto-compute their ft².
//   3. Pick a profile from the palette.
//   4. Click-drag on the image to draw a box. The box appears with the
//      profile chip + auto-computed ft² (editable).
//   5. Repeat for each accent region.
//   6. Save → annotations persist on the estimate.
//
// The boxes use NORMALIZED coordinates (0-1) so they survive image resizing.
import React, { useEffect, useMemo, useRef, useState } from "react";
import { X, Plus, Trash2, Ruler, Save, MousePointer2 } from "lucide-react";
import { toast } from "sonner";
import api from "@/lib/api";

const PROFILES = [
  { value: "lap",          label: "Lap",          color: "#3B82F6", isSiding: true },
  { value: "dutch_lap",    label: "Dutch Lap",    color: "#2563EB", isSiding: true },
  { value: "shake",        label: "Shake",        color: "#F59E0B", isSiding: true },
  { value: "board_batten", label: "Board & Batten", color: "#EC4899", isSiding: true },
  { value: "vertical",     label: "Vertical",     color: "#DB2777", isSiding: true },
  { value: "nickel_gap",   label: "Nickel Gap",   color: "#A855F7", isSiding: true },
  { value: "stone",        label: "Stone",        color: "#71717A", isSiding: false },
  { value: "brick",        label: "Brick",        color: "#92400E", isSiding: false },
  { value: "stucco",       label: "Stucco",       color: "#9CA3AF", isSiding: false },
];

const ELEVATIONS = ["front", "right", "back", "left", "front-left", "front-right", "rear-left", "rear-right", "porch", "other"];

const newId = () => `box_${Math.random().toString(36).slice(2, 10)}`;

// Compute ft² for a box given the photo's scale reference (px_height for
// a known real-ft span). Falls back to a NaN / explicit "no scale" state
// when none is set — UI will surface "scale needed" + let the user
// manually type the ft².
function computeSqftFromBox(boxNorm, imgPx, scaleRef) {
  if (!scaleRef || !scaleRef.px_height || !scaleRef.real_ft || !imgPx?.h) return null;
  const ftPerPx = scaleRef.real_ft / scaleRef.px_height;
  const boxWpx = boxNorm.w_norm * imgPx.w;
  const boxHpx = boxNorm.h_norm * imgPx.h;
  const sqft = boxWpx * ftPerPx * boxHpx * ftPerPx;
  return Math.max(0, Math.round(sqft));
}

export default function ProfileAnnotator({
  estimateId, photos, initialAnnotations, defaultElevationByIdx, onClose, onSaved,
}) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const [annotations, setAnnotations] = useState(initialAnnotations || {});
  const [activeProfile, setActiveProfile] = useState("shake");
  const [drawing, setDrawing] = useState(null); // {x0, y0, x1, y1}
  // Scale ref draft mode: when truthy, a click+drag draws a calibration line.
  const [scaleDraft, setScaleDraft] = useState(null); // {x0,y0,x1,y1,active}
  const [scaleRefInput, setScaleRefInput] = useState({ open: false, pxHeight: 0, realFt: "6.67" });
  const [imgPx, setImgPx] = useState({ w: 0, h: 0 }); // displayed image pixel size
  const imgRef = useRef(null);
  const containerRef = useRef(null);

  const currentPhoto = photos?.[selectedIdx];
  const photoKey = String(selectedIdx);
  const boxes = (annotations[photoKey] || []).filter((b) => b && typeof b === "object");
  const scaleRefs = annotations._scale_refs || {};
  const scaleRef = scaleRefs[photoKey] || null;

  // Default elevation label for new boxes — pulled from AI's auto-tag
  // when available, otherwise "other".
  const defaultElevation = defaultElevationByIdx?.[selectedIdx] || "other";

  // Sync displayed image dimensions on load + window resize
  const updateImgPx = () => {
    if (imgRef.current) {
      const rect = imgRef.current.getBoundingClientRect();
      setImgPx({ w: rect.width, h: rect.height });
    }
  };
  useEffect(() => {
    updateImgPx();
    window.addEventListener("resize", updateImgPx);
    return () => window.removeEventListener("resize", updateImgPx);
  }, [selectedIdx]);

  const onMouseDown = (e) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = (e.clientY - rect.top) / rect.height;
    if (scaleDraft?.active) {
      setScaleDraft({ ...scaleDraft, x0: x, y0: y, x1: x, y1: y, dragging: true });
    } else {
      setDrawing({ x0: x, y0: y, x1: x, y1: y });
    }
  };
  const onMouseMove = (e) => {
    if (!imgRef.current) return;
    const rect = imgRef.current.getBoundingClientRect();
    const x = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    const y = Math.min(1, Math.max(0, (e.clientY - rect.top) / rect.height));
    if (scaleDraft?.dragging) {
      setScaleDraft({ ...scaleDraft, x1: x, y1: y });
    } else if (drawing) {
      setDrawing({ ...drawing, x1: x, y1: y });
    }
  };
  const onMouseUp = () => {
    if (scaleDraft?.dragging) {
      // finalize calibration line
      const dx = (scaleDraft.x1 - scaleDraft.x0) * imgPx.w;
      const dy = (scaleDraft.y1 - scaleDraft.y0) * imgPx.h;
      const pxHeight = Math.sqrt(dx * dx + dy * dy);
      if (pxHeight < 10) {
        toast.error("Calibration line too short — try again");
        setScaleDraft(null);
        return;
      }
      setScaleRefInput({ open: true, pxHeight, realFt: scaleRefInput.realFt });
      setScaleDraft(null);
      return;
    }
    if (!drawing) return;
    const xMin = Math.min(drawing.x0, drawing.x1);
    const yMin = Math.min(drawing.y0, drawing.y1);
    const w = Math.abs(drawing.x1 - drawing.x0);
    const h = Math.abs(drawing.y1 - drawing.y0);
    if (w < 0.01 || h < 0.01) {
      // ignore micro-drags / accidental clicks
      setDrawing(null);
      return;
    }
    const newBox = {
      id: newId(),
      x_norm: xMin, y_norm: yMin, w_norm: w, h_norm: h,
      elevation_label: defaultElevation,
      profile: activeProfile,
      sqft: 50, // sane default; recomputed below if scale ref exists
      callout: "",
    };
    const computed = computeSqftFromBox(newBox, imgPx, scaleRef);
    if (computed != null) newBox.sqft = computed;
    setAnnotations((prev) => ({
      ...prev,
      [photoKey]: [...(prev[photoKey] || []), newBox],
    }));
    setDrawing(null);
  };

  const updateBox = (boxId, patch) => {
    setAnnotations((prev) => ({
      ...prev,
      [photoKey]: (prev[photoKey] || []).map((b) =>
        b.id === boxId ? { ...b, ...patch } : b,
      ),
    }));
  };
  const deleteBox = (boxId) => {
    setAnnotations((prev) => ({
      ...prev,
      [photoKey]: (prev[photoKey] || []).filter((b) => b.id !== boxId),
    }));
  };

  const confirmScale = () => {
    const realFt = Number(scaleRefInput.realFt);
    if (!realFt || realFt <= 0) {
      toast.error("Enter a positive real-world distance");
      return;
    }
    const newRefs = { ...(annotations._scale_refs || {}) };
    newRefs[photoKey] = {
      px_height: scaleRefInput.pxHeight,
      real_ft: realFt,
    };
    // Re-compute sqft for every existing box on this photo using the new ref
    const newBoxes = (annotations[photoKey] || []).map((b) => {
      const computed = computeSqftFromBox(b, imgPx, newRefs[photoKey]);
      return computed != null ? { ...b, sqft: computed } : b;
    });
    setAnnotations((prev) => ({
      ...prev,
      [photoKey]: newBoxes,
      _scale_refs: newRefs,
    }));
    setScaleRefInput({ open: false, pxHeight: 0, realFt: "6.67" });
    toast.success("Scale reference saved — sqft updated");
  };

  const save = async () => {
    try {
      await api.put(`/estimates/${estimateId}/profile-annotations`, { annotations });
      toast.success("Annotations saved");
      if (onSaved) onSaved(annotations);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Failed to save");
    }
  };

  const totalBoxes = useMemo(() => {
    return Object.entries(annotations).reduce((acc, [k, v]) => (
      k.startsWith("_") ? acc : acc + (Array.isArray(v) ? v.length : 0)
    ), 0);
  }, [annotations]);

  return (
    <div
      className="fixed inset-0 z-[60] bg-black/60 flex items-center justify-center p-4"
      data-testid="profile-annotator"
      onClick={onClose}
    >
      <div
        className="bg-white max-w-6xl w-full h-[90vh] flex flex-col border border-[#E4E4E7]"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-[#E4E4E7]">
          <div>
            <div className="text-[10px] uppercase tracking-wider text-[#A1A1AA] font-bold">
              Profile Annotator
            </div>
            <div className="text-sm font-bold">
              Tag Shake / B&B / etc. so AI can&apos;t miss them
              <span className="text-[#71717A] font-normal text-xs ml-2">
                · {totalBoxes} box{totalBoxes === 1 ? "" : "es"}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={save}
              className="bg-[#F97316] text-white text-xs font-bold uppercase tracking-wider px-3 py-1.5 hover:bg-[#EA580C] flex items-center gap-1"
              data-testid="annotator-save"
            >
              <Save size={12} /> Save
            </button>
            <button
              type="button"
              onClick={onClose}
              className="text-[#71717A] hover:text-[#09090B]"
              data-testid="annotator-cancel"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="flex-1 flex min-h-0">
          {/* Image strip */}
          <div className="w-32 border-r border-[#E4E4E7] overflow-y-auto bg-[#FAFAFA] p-2 space-y-2">
            {(photos || []).map((p, i) => {
              const count = (annotations[String(i)] || []).length;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => setSelectedIdx(i)}
                  className={`block relative w-full border-2 ${i === selectedIdx ? "border-[#F97316]" : "border-[#E4E4E7]"}`}
                  data-testid={`annotator-strip-${i}`}
                >
                  <img src={p.url} alt={`photo ${i}`} className="w-full h-auto block" />
                  {count > 0 && (
                    <span className="absolute top-1 right-1 bg-[#F97316] text-white text-[9px] font-bold px-1.5 py-0.5">
                      {count}
                    </span>
                  )}
                  <span className="block text-[9px] text-center font-bold uppercase tracking-wider text-[#71717A] mt-0.5">
                    {p.label || `#${i + 1}`}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Canvas */}
          <div className="flex-1 overflow-auto p-4 bg-[#27272A]" ref={containerRef}>
            {currentPhoto ? (
              <div className="relative inline-block max-w-full">
                <img
                  ref={imgRef}
                  src={currentPhoto.url}
                  alt={`elevation ${selectedIdx}`}
                  className="block max-w-full select-none"
                  onLoad={updateImgPx}
                  onMouseDown={onMouseDown}
                  onMouseMove={onMouseMove}
                  onMouseUp={onMouseUp}
                  onMouseLeave={onMouseUp}
                  draggable={false}
                  style={{ userSelect: "none", cursor: scaleDraft?.active ? "crosshair" : "crosshair" }}
                />
                {/* Existing boxes */}
                {boxes.map((b) => {
                  const profileDef = PROFILES.find((p) => p.value === b.profile) || PROFILES[0];
                  return (
                    <div
                      key={b.id}
                      className="absolute border-2 pointer-events-none"
                      style={{
                        left: `${b.x_norm * 100}%`,
                        top: `${b.y_norm * 100}%`,
                        width: `${b.w_norm * 100}%`,
                        height: `${b.h_norm * 100}%`,
                        borderColor: profileDef.color,
                        background: `${profileDef.color}22`,
                      }}
                      data-testid={`annotator-box-${b.id}`}
                    >
                      <div
                        className="absolute -top-5 left-0 text-[10px] uppercase tracking-wider font-bold px-1 text-white"
                        style={{ background: profileDef.color }}
                      >
                        {profileDef.label} · {b.sqft}ft²
                      </div>
                    </div>
                  );
                })}
                {/* In-progress drawing rectangle */}
                {drawing && (
                  <div
                    className="absolute border-2 border-dashed pointer-events-none"
                    style={{
                      left: `${Math.min(drawing.x0, drawing.x1) * 100}%`,
                      top: `${Math.min(drawing.y0, drawing.y1) * 100}%`,
                      width: `${Math.abs(drawing.x1 - drawing.x0) * 100}%`,
                      height: `${Math.abs(drawing.y1 - drawing.y0) * 100}%`,
                      borderColor: (PROFILES.find((p) => p.value === activeProfile) || PROFILES[0]).color,
                      background: `${(PROFILES.find((p) => p.value === activeProfile) || PROFILES[0]).color}33`,
                    }}
                  />
                )}
                {/* Scale calibration line in progress */}
                {scaleDraft?.dragging && (
                  <svg
                    className="absolute inset-0 pointer-events-none"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                  >
                    <line
                      x1={scaleDraft.x0 * 100} y1={scaleDraft.y0 * 100}
                      x2={scaleDraft.x1 * 100} y2={scaleDraft.y1 * 100}
                      stroke="#10B981" strokeWidth="0.5" strokeDasharray="2 1"
                    />
                  </svg>
                )}
              </div>
            ) : (
              <div className="text-white text-sm">No photo selected</div>
            )}
          </div>

          {/* Right panel — palette + per-box editor */}
          <div className="w-72 border-l border-[#E4E4E7] flex flex-col">
            <div className="p-3 border-b border-[#E4E4E7]">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA] mb-2">
                Profile (drag on image to draw box)
              </div>
              <div className="grid grid-cols-3 gap-1">
                {PROFILES.map((p) => (
                  <button
                    key={p.value}
                    type="button"
                    onClick={() => setActiveProfile(p.value)}
                    className={`text-[10px] uppercase tracking-wider font-bold px-2 py-1.5 border ${activeProfile === p.value ? "ring-2 ring-[#F97316]" : "border-transparent"}`}
                    style={{ background: `${p.color}22`, color: p.color }}
                    data-testid={`annotator-profile-${p.value}`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="p-3 border-b border-[#E4E4E7]">
              <div className="flex items-center justify-between mb-1">
                <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA]">
                  Scale reference
                </div>
                {scaleRef ? (
                  <span className="text-[10px] text-[#16A34A] font-bold">
                    ✓ {scaleRef.real_ft.toFixed(2)}ft / {Math.round(scaleRef.px_height)}px
                  </span>
                ) : (
                  <span className="text-[10px] text-[#A1A1AA]">not set</span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setScaleDraft({ active: true })}
                className={`text-[10px] uppercase tracking-wider font-bold px-2 py-1.5 border w-full flex items-center justify-center gap-1 ${scaleDraft?.active ? "bg-[#10B981] text-white" : "border-[#E4E4E7] hover:bg-[#FAFAFA]"}`}
                data-testid="annotator-set-scale"
              >
                <Ruler size={12} />
                {scaleDraft?.active ? "Drag a known length on the image…" : "+ Set scale (drag a door/window)"}
              </button>
              {scaleRefInput.open && (
                <div className="mt-2 p-2 border border-[#10B981] bg-[#ECFDF5]">
                  <div className="text-[10px] uppercase tracking-wider font-bold text-[#065F46] mb-1">
                    What real-world length is that?
                  </div>
                  <div className="flex gap-1">
                    <input
                      type="number"
                      step="0.01"
                      min="0.1"
                      value={scaleRefInput.realFt}
                      onChange={(e) => setScaleRefInput({ ...scaleRefInput, realFt: e.target.value })}
                      className="flex-1 border border-[#E4E4E7] px-2 py-1 text-xs font-mono-num"
                      placeholder="ft"
                      autoFocus
                      data-testid="annotator-scale-ft"
                    />
                    <button
                      type="button"
                      onClick={confirmScale}
                      className="bg-[#10B981] text-white text-[10px] uppercase font-bold px-2"
                      data-testid="annotator-scale-confirm"
                    >
                      OK
                    </button>
                  </div>
                  <div className="text-[10px] text-[#065F46] mt-1">
                    Common refs: door = 6.67 ft · siding course = 4 in
                  </div>
                </div>
              )}
              {!scaleRef && (
                <p className="text-[10px] text-[#71717A] mt-1 italic">
                  Without scale, sqft defaults to 50 — type the real ft² in each box below to override.
                </p>
              )}
            </div>
            <div className="flex-1 overflow-y-auto p-3">
              <div className="text-[10px] uppercase tracking-wider font-bold text-[#A1A1AA] mb-2">
                Boxes on this image ({boxes.length})
              </div>
              {boxes.length === 0 && (
                <div className="text-[11px] text-[#A1A1AA] italic">
                  <MousePointer2 size={12} className="inline mr-1" />
                  Click and drag on the image to draw a box.
                </div>
              )}
              {boxes.map((b) => {
                const profileDef = PROFILES.find((p) => p.value === b.profile) || PROFILES[0];
                return (
                  <div key={b.id} className="border border-[#E4E4E7] p-2 mb-2" data-testid={`annotator-list-${b.id}`}>
                    <div className="flex items-center justify-between mb-1">
                      <select
                        value={b.profile}
                        onChange={(e) => updateBox(b.id, { profile: e.target.value })}
                        className="text-[10px] uppercase font-bold tracking-wider border-0 bg-transparent"
                        style={{ color: profileDef.color }}
                        data-testid={`annotator-list-profile-${b.id}`}
                      >
                        {PROFILES.map((p) => (
                          <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                      </select>
                      <button
                        type="button"
                        onClick={() => deleteBox(b.id)}
                        className="text-[#71717A] hover:text-[#EF4444]"
                        data-testid={`annotator-list-delete-${b.id}`}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                    <label className="block mb-1">
                      <span className="text-[9px] uppercase tracking-wider text-[#71717A] font-bold">Elevation</span>
                      <select
                        value={b.elevation_label}
                        onChange={(e) => updateBox(b.id, { elevation_label: e.target.value })}
                        className="block w-full text-[11px] border border-[#E4E4E7] px-1 py-0.5"
                      >
                        {ELEVATIONS.map((el) => (
                          <option key={el} value={el}>{el}</option>
                        ))}
                      </select>
                    </label>
                    <label className="block mb-1">
                      <span className="text-[9px] uppercase tracking-wider text-[#71717A] font-bold">ft²</span>
                      <input
                        type="number"
                        value={b.sqft}
                        onChange={(e) => updateBox(b.id, { sqft: Number(e.target.value) || 0 })}
                        className="block w-full text-[11px] border border-[#E4E4E7] px-1 py-0.5 font-mono-num"
                        data-testid={`annotator-list-sqft-${b.id}`}
                      />
                    </label>
                    <label className="block">
                      <span className="text-[9px] uppercase tracking-wider text-[#71717A] font-bold">Note</span>
                      <input
                        type="text"
                        value={b.callout}
                        onChange={(e) => updateBox(b.id, { callout: e.target.value })}
                        placeholder="e.g. porch face"
                        className="block w-full text-[11px] border border-[#E4E4E7] px-1 py-0.5"
                      />
                    </label>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer hint */}
        <div className="px-4 py-2 border-t border-[#E4E4E7] bg-[#FAFAFA] text-[10px] text-[#71717A]">
          Boxes guarantee per-profile material lines. Re-run AI Measure / Blueprint after saving to apply.
        </div>
      </div>
    </div>
  );
}
