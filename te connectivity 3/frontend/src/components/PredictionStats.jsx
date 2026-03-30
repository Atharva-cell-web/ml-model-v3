import React, { useMemo } from "react";
import { TrendingUp, TrendingDown, Minus, BarChart3, Zap } from "lucide-react";

const toNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

export default function PredictionStats({ summaryStats, timeline }) {
  const stats = useMemo(() => {
    const pastPoints = timeline?.filter((p) => !p.is_future) || [];
    const futurePoints = timeline?.filter((p) => p.is_future) || [];

    const avgPastRisk = pastPoints.length
      ? (pastPoints.reduce((acc, p) => acc + p.risk_score, 0) / pastPoints.length) * 100
      : 0;
    const avgFutureRisk = futurePoints.length
      ? (futurePoints.reduce((acc, p) => acc + p.risk_score, 0) / futurePoints.length) * 100
      : 0;

    const pastScrapCount = summaryStats?.past_scrap_detected || 0;
    const futureScrapCount = summaryStats?.future_scrap_predicted || 0;

    const riskTrend = avgFutureRisk - avgPastRisk;

    return {
      pastScrapCount,
      futureScrapCount,
      avgPastRisk,
      riskTrend,
      trendText:
        riskTrend > 0
          ? `+${riskTrend.toFixed(1)}%`
          : riskTrend < 0
            ? `${riskTrend.toFixed(1)}%`
            : "0.0%",
      trendLabel: riskTrend > 0 ? "Upward" : riskTrend < 0 ? "Downward" : "Stable",
      trendColor: riskTrend > 0 ? "text-red-500" : riskTrend < 0 ? "text-emerald-600" : "text-slate-500",
      trendBg: riskTrend > 0 ? "bg-red-50 border-red-100" : riskTrend < 0 ? "bg-emerald-50 border-emerald-100" : "bg-slate-50 border-slate-200",
      TrendIcon: riskTrend > 0 ? TrendingUp : riskTrend < 0 ? TrendingDown : Minus,
    };
  }, [summaryStats, timeline]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-slide-up" style={{ animationDelay: "0.3s" }}>
      {/* Past Scrap Analysis Card */}
      <section className="glass-card p-5">
        <div className="flex justify-between items-center mb-5">
          <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-brand-50 flex items-center justify-center">
              <BarChart3 size={14} className="text-brand-500" />
            </div>
            Past Scrap Analysis
          </h3>
          <span className="px-2.5 py-1 text-[10px] uppercase font-bold tracking-wider text-brand-600 bg-brand-50 border border-brand-100 rounded-lg">
            Actual
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl bg-slate-50/80 border border-slate-200/80">
            <p className="text-[11px] text-slate-400 mb-1.5 font-semibold uppercase tracking-wide">Total Scrap</p>
            <p className="text-3xl font-extrabold text-slate-800">
              {stats.pastScrapCount}
              <span className="text-sm font-medium text-slate-400 ml-1.5">units</span>
            </p>
            <p className="text-[10px] text-slate-400 mt-1.5">Last 60 min</p>
          </div>
          <div className="p-4 rounded-xl bg-brand-50/60 border border-brand-100">
            <p className="text-[11px] text-brand-500 mb-1.5 font-semibold uppercase tracking-wide">Avg Risk</p>
            <p className="text-3xl font-extrabold text-brand-600">
              {stats.avgPastRisk.toFixed(1)}%
            </p>
            <p className="text-[10px] text-brand-400 mt-1.5">Historical baseline</p>
          </div>
        </div>
      </section>

      {/* Future Scrap Forecast Card */}
      <section className="glass-card p-5">
        <div className="flex justify-between items-center mb-5">
          <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-amber-50 flex items-center justify-center">
              <Zap size={14} className="text-amber-500" />
            </div>
            Future Scrap Forecast
          </h3>
          <span className="px-2.5 py-1 text-[10px] uppercase font-bold tracking-wider text-amber-600 bg-amber-50 border border-amber-100 rounded-lg">
            Predicted
          </span>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl bg-amber-50/60 border border-amber-100">
            <p className="text-[11px] text-amber-600 mb-1.5 font-semibold uppercase tracking-wide">Predicted Scrap</p>
            <p className="text-3xl font-extrabold text-amber-600">
              {stats.futureScrapCount}
              <span className="text-sm font-medium text-amber-400 ml-1.5">units</span>
            </p>
            <p className="text-[10px] text-amber-400 mt-1.5">Next 30 min</p>
          </div>
          <div className={`p-4 rounded-xl border ${stats.trendBg}`}>
            <p className="text-[11px] text-slate-400 mb-1.5 font-semibold uppercase tracking-wide">Trend</p>
            <div className="flex items-center gap-2">
              <stats.TrendIcon size={20} className={stats.trendColor} />
              <p className={`text-2xl font-extrabold ${stats.trendColor}`}>
                {stats.trendText}
              </p>
            </div>
            <p className="text-[10px] text-slate-400 mt-1.5">{stats.trendLabel} · Future vs Past</p>
          </div>
        </div>
      </section>
    </div>
  );
}
