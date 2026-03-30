import React, { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronDown, ChevronUp } from "lucide-react";

const toNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

export default function RootCause({ rootCauses }) {
  const topCauses = useMemo(
    () => (Array.isArray(rootCauses) ? rootCauses.slice(0, 3) : []),
    [rootCauses],
  );
  const [expandedIndex, setExpandedIndex] = useState(null);

  return (
    <section className="glass-card p-5 animate-slide-up" style={{ animationDelay: "0.2s" }}>
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-700">
        <div className="w-8 h-8 rounded-lg bg-amber-50 flex items-center justify-center">
          <AlertTriangle size={16} className="text-amber-500" />
        </div>
        Root Cause Analysis
      </h2>

      {!topCauses.length ? (
        <div className="flex h-36 flex-col items-center justify-center gap-3 rounded-xl bg-emerald-50/50 border border-emerald-100">
          <div className="w-14 h-14 rounded-full bg-emerald-100 flex items-center justify-center">
            <CheckCircle2 size={28} className="text-emerald-500" />
          </div>
          <p className="text-base font-semibold text-emerald-700">All Systems Normal</p>
          <p className="text-xs text-emerald-500">No root causes detected at this time</p>
        </div>
      ) : (
        <div className="space-y-3">
          {topCauses.map((entry, index) => {
            const impact = toNumber(entry?.impact);
            const isExpanded = expandedIndex === index;
            const hasParams = entry?.top_parameters && entry.top_parameters.length > 0;
            return (
              <div
                key={`${entry?.cause || "cause"}-${index}`}
                className={`rounded-xl border px-5 py-4 transition-all duration-200 ${
                  hasParams ? "cursor-pointer" : ""
                } ${
                  isExpanded
                    ? "border-amber-300 bg-amber-50/80 shadow-md"
                    : "border-amber-100 bg-amber-50/40 hover:bg-amber-50/70 hover:shadow-sm"
                }`}
                onClick={() => hasParams && setExpandedIndex(isExpanded ? null : index)}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="w-6 h-6 rounded-full bg-amber-200 text-amber-800 flex items-center justify-center text-xs font-bold">
                      {index + 1}
                    </span>
                    <p className="text-sm font-semibold text-slate-700">
                      {entry?.cause || "Unknown Cause"}
                    </p>
                    {hasParams && (
                      isExpanded ? (
                        <ChevronUp size={14} className="text-amber-500" />
                      ) : (
                        <ChevronDown size={14} className="text-amber-400" />
                      )
                    )}
                  </div>
                  {impact !== null && (
                    <span className="rounded-lg bg-white border border-amber-200 px-3 py-1.5 text-xs font-bold text-amber-700 shadow-sm">
                      Impact {impact.toFixed(3)}
                    </span>
                  )}
                </div>
                {isExpanded && hasParams && (
                  <div className="mt-4 pt-3 border-t border-amber-200/60 pl-8 space-y-2">
                    <p className="text-[10px] font-bold text-amber-600/60 uppercase tracking-widest mb-2">
                      Specific Drivers
                    </p>
                    {entry.top_parameters.map((p, pIdx) => (
                      <div key={pIdx} className="flex justify-between items-center text-xs py-1">
                        <span className="text-slate-600 font-medium">
                          {String(p.parameter).replace(/_/g, " ").toLowerCase()}
                        </span>
                        <span
                          className={`font-mono font-semibold ${p.impact > 0 ? "text-red-500" : "text-emerald-600"}`}
                        >
                          {p.impact > 0 ? "+" : ""}
                          {p.impact.toFixed(4)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
