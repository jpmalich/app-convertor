import React from "react";

export default function SettingsRow({ est, update }) {
  return (
    <section className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
      <div className="card p-5">
        <div className="section-tag mb-3">Waste Factor</div>
        <div className="flex items-baseline gap-2">
          <input
            className="input num w-24"
            type="number"
            step="0.5"
            value={est.waste_pct || 0}
            onChange={(e) => update({ waste_pct: Number(e.target.value) || 0 })}
            data-testid="waste-pct"
          />
          <span className="text-[#52525B]">% extra material</span>
        </div>
      </div>
      <div className="card p-5">
        <div className="section-tag mb-3">Sales Tax</div>
        <label className="flex items-center gap-3 mb-3 text-sm">
          <input
            type="checkbox"
            checked={!!est.tax_enabled}
            onChange={(e) => update({ tax_enabled: e.target.checked })}
            data-testid="tax-toggle"
          />
          <span>Apply tax on material</span>
        </label>
        <div className="flex items-baseline gap-2">
          <input
            className="input num w-24"
            type="number"
            step="0.01"
            disabled={!est.tax_enabled}
            value={est.tax_rate || 0}
            onChange={(e) => update({ tax_rate: Number(e.target.value) || 0 })}
            data-testid="tax-rate"
          />
          <span className="text-[#52525B]">%</span>
        </div>
      </div>
      <div className="card p-5">
        <div className="section-tag mb-3">Margin</div>
        <div className="flex items-baseline gap-2 mb-3">
          <input
            className="input num w-24"
            type="number"
            step="1"
            value={est.margin_pct || 0}
            onChange={(e) => update({ margin_pct: Number(e.target.value) || 0 })}
            data-testid="margin-pct"
          />
          <span className="text-[#52525B]">% profit on base</span>
        </div>
        <input
          type="range"
          min="0"
          max="100"
          step="1"
          value={est.margin_pct || 0}
          onChange={(e) => update({ margin_pct: Number(e.target.value) || 0 })}
          className="w-full accent-[#F97316]"
          data-testid="margin-slider"
        />
      </div>
    </section>
  );
}
