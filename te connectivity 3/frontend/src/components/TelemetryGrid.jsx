import React, { useMemo } from "react";
import { LineChart, Line } from "recharts";
import { Activity, Flame } from "lucide-react";

const toNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

export default function TelemetryGrid({ telemetryRows, selectedSensor, onSelectSensor }) {
  const tableData = useMemo(() => {
    const rows = Array.isArray(telemetryRows) ? telemetryRows : [];
    const statusWeight = { EXCEEDED: 3, WARNING: 2, NORMAL: 1 };
    return [...rows].sort((a, b) => {
      const aRoot = a?.is_root_cause ? 1 : 0;
      const bRoot = b?.is_root_cause ? 1 : 0;
      if (bRoot !== aRoot) return bRoot - aRoot;
      return (statusWeight[b?.status] || 0) - (statusWeight[a?.status] || 0);
    });
  }, [telemetryRows]);

  return (
    <section className="glass-card p-5 flex flex-col h-full animate-slide-up" style={{ animationDelay: "0.25s" }}>
      <h2 className="mb-4 flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-700 shrink-0">
        <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center">
          <Activity size={16} className="text-emerald-500" />
        </div>
        Real-Time Telemetry Grid
      </h2>

      <div className="flex-1 overflow-auto rounded-xl border border-slate-200/80 bg-white/50">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="sticky top-0 bg-slate-50/95 backdrop-blur-sm text-[11px] uppercase text-slate-500 z-10 border-b border-slate-200">
            <tr>
              <th className="px-5 py-3.5 font-semibold">Parameter</th>
              <th className="px-5 py-3.5 font-semibold">Status</th>
              <th className="px-5 py-3.5 font-semibold">Current</th>
              <th className="px-5 py-3.5 font-semibold">Delta Trend</th>
              <th className="px-5 py-3.5 font-semibold">Safe Range</th>
              <th className="px-5 py-3.5 font-semibold">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {tableData.map((row, idx) => {
              const status = String(row?.status || "NORMAL").toUpperCase();
              const isRoot = Boolean(row?.is_root_cause);
              const isClickable = status !== "NORMAL" || isRoot;
              const isSelected = selectedSensor === row?.sensor;
              const delta = toNumber(row?.trend_delta) ?? 0;
              const trendDirection = row?.trend_direction;
              const trendIcon =
                trendDirection === "up" ? "▲" : trendDirection === "down" ? "▼" : "—";
              const trendColor =
                trendDirection === "up"
                  ? "text-emerald-600"
                  : trendDirection === "down"
                    ? "text-red-500"
                    : "text-slate-400";

              const statusBadgeClass =
                status === "EXCEEDED"
                  ? "bg-red-50 text-red-600 border-red-200"
                  : status === "WARNING"
                    ? "bg-amber-50 text-amber-600 border-amber-200"
                    : "bg-emerald-50 text-emerald-600 border-emerald-200";

              const sparklineData = (Array.isArray(row?.sparkline) ? row.sparkline : [])
                .map((value, pointIndex) => ({ pointIndex, value: toNumber(value) }))
                .filter((point) => point.value !== null);

              const rowClassName = [
                "transition-all duration-200",
                isRoot ? "bg-amber-50/50" : "hover:bg-slate-50/80",
                isSelected ? "bg-brand-50/60 border-l-[3px] border-l-brand-500" : "",
                isClickable ? "cursor-pointer" : "cursor-default",
              ]
                .filter(Boolean)
                .join(" ");

              return (
                <tr
                  key={`${row?.sensor || "sensor"}-${idx}`}
                  className={rowClassName}
                  onClick={() => {
                    if (isClickable) onSelectSensor(row.sensor);
                  }}
                >
                  <td className="px-5 py-3.5 font-medium text-slate-700">
                    <div className="flex items-center gap-2">
                      {isRoot && (
                        <span className="w-5 h-5 rounded bg-amber-100 flex items-center justify-center">
                          <Flame size={12} className="text-amber-500" />
                        </span>
                      )}
                      <span className="capitalize">
                        {String(row?.sensor || "").replace(/_/g, " ").toLowerCase()}
                      </span>
                    </div>
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-block rounded-lg border px-2.5 py-1 text-[10px] font-bold tracking-wide ${statusBadgeClass}`}
                    >
                      {status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-slate-800 font-medium">
                    {toNumber(row?.value) !== null ? Number(row.value).toFixed(2) : "--"}
                  </td>
                  <td className={`px-5 py-3.5 font-mono font-medium ${trendColor}`}>
                    {trendIcon} {delta > 0 ? "+" : ""}
                    {delta.toFixed(2)}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-slate-400 font-medium">
                    {toNumber(row?.safe_min) !== null ? Number(row.safe_min).toFixed(2) : "0"}
                    <span className="text-slate-300 px-1.5">~</span>
                    {toNumber(row?.safe_max) !== null ? Number(row.safe_max).toFixed(2) : "inf"}
                  </td>
                  <td className="px-5 py-3.5">
                    {sparklineData.length ? (
                      <LineChart width={110} height={30} data={sparklineData}>
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={isRoot ? "#f59e0b" : "#3b82f6"}
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    ) : (
                      <span className="text-xs text-slate-300">--</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
