import React from "react";
import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { fmt } from "@/lib/api";

export default function StickyBar({ est, totals }) {
  return (
    <div className="sell-bar" data-testid="sticky-bar">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center gap-3 sm:gap-6">
        <Link to="/" className="text-white/70 hover:text-white" aria-label="Back">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1 min-w-[180px]">
          <div className="text-[10px] uppercase tracking-[0.2em] text-white/50">Estimate</div>
          <div className="font-heading text-base sm:text-lg truncate">
            {est.customer_name || "Untitled"} · {est.estimate_number}
          </div>
        </div>
        <div className="flex items-center gap-5 sm:gap-8">
          <Stat label="Base" value={fmt(totals.base)} testid="bar-base" />
          <Stat label="Sell" value={fmt(totals.sell)} testid="bar-sell" emphasize />
          <div className="hidden sm:block">
            <Stat label="Profit" value={fmt(totals.profit)} testid="bar-profit" color="#10B981" />
          </div>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, testid, emphasize, color }) {
  return (
    <div className="text-right">
      <div
        className="text-[10px] uppercase tracking-[0.2em]"
        style={{ color: emphasize ? "#F97316" : "rgba(255,255,255,0.5)" }}
      >
        {label}
      </div>
      <div
        className={`font-mono-num ${emphasize ? "text-xl sm:text-2xl font-bold" : "text-sm sm:text-base"}`}
        style={{ color: emphasize ? "#F97316" : color || "#fff" }}
        data-testid={testid}
      >
        {value}
      </div>
    </div>
  );
}
