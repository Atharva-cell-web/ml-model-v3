import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Activity, AlertTriangle, CheckCircle2, Flame } from "lucide-react";

const API_BASE = "http://127.0.0.1:8000";
const FUTURE_RISK_THRESHOLD = 0.6;

const MACHINE_OPTIONS = [
  { value: "M-231", label: "M-231" },
  { value: "M-356", label: "M-356" },
  { value: "M-471", label: "M-471" },
  { value: "M-607", label: "M-607" },
  { value: "M-612", label: "M-612" },
];

const TIME_WINDOW_OPTIONS = [
  { value: 120, futureMinutes: 35, label: "2H Past / 35M Future" },
  { value: 60, futureMinutes: 20, label: "1H Past / 20M Future" },
];

const toNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

const mergeLimits = (safeLimits, overrides) => {
  const merged = { ...(safeLimits || {}) };
  Object.entries(overrides || {}).forEach(([sensor, override]) => {
    merged[sensor] = {
      ...(merged[sensor] || {}),
      ...override,
    };
  });
  return merged;
};

const formatClock = (timestamp) => {
  if (!timestamp || typeof timestamp !== "string") {
    return "";
  }
  return timestamp.slice(11, 16);
};

const fetchWithRetry = async (url, options = {}, retries = 3, delay = 1000) => {
  try {
    const response = await axios.get(url, options);
    return response.data;
  } catch (err) {
    if (retries > 0) {
      await new Promise((resolve) => setTimeout(resolve, delay));
      return fetchWithRetry(url, options, retries - 1, delay);
    }
    throw err;
  }
};

function GlobalHeader({
  machineId,
  timeWindowMinutes,
  onMachineChange,
  onTimeWindowChange,
  healthStatus,
  isSensorFrozen,
}) {
  const statusClass =
    healthStatus === "CRITICAL" || healthStatus === "HIGH"
      ? "border-red-500 bg-red-500/15 text-red-300"
      : healthStatus === "MEDIUM"
        ? "border-amber-500 bg-amber-500/15 text-amber-300"
        : "border-emerald-500 bg-emerald-500/15 text-emerald-300";

  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-slate-700 bg-slate-900/70 px-5 py-4">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Predictive Maintenance Control Room</h1>
        <p className="text-xs text-slate-400">Unified machine health, root cause, and telemetry view</p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <select
          value={machineId}
          onChange={(event) => onMachineChange(event.target.value)}
          className="rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none"
        >
          {MACHINE_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={timeWindowMinutes}
          onChange={(event) => onTimeWindowChange(Number(event.target.value))}
          className="rounded-md border border-slate-600 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none"
        >
          {TIME_WINDOW_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <span className={`rounded-md border px-3 py-2 text-xs font-semibold ${statusClass}`}>
          STATUS: {healthStatus}
        </span>
        {isSensorFrozen && (
          <span className="rounded-md border border-orange-500 bg-orange-500/15 px-3 py-2 text-xs font-semibold text-orange-300">
            SENSOR FROZEN
          </span>
        )}
      </div>
    </header>
  );
}

function SystemHealthMonitor({ timeline, riskScore }) {
  const chartData = useMemo(
    () =>
      (timeline || []).map((point) => {
        const risk = toNumber(point.risk_score) ?? 0;
        const alertDot = point.is_scrap_actual === 1 || (point.is_future && risk > FUTURE_RISK_THRESHOLD);
        return {
          time: point.timestamp,
          pastRisk: point.is_future ? null : risk,
          futureRisk: point.is_future ? risk : null,
          alertDot,
        };
      }),
    [timeline],
  );

  if (!chartData.length) {
    return <div className="flex h-64 items-center justify-center text-sm text-slate-400">No timeline data available.</div>;
  }

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-200">
          <Activity size={16} className="text-cyan-300" />
          Section A: System Health Monitor
        </h2>
        <div className="text-xs text-slate-400">Current risk score: {(riskScore * 100).toFixed(1)}%</div>
      </div>
      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" tickFormatter={formatClock} tick={{ fill: "#94a3b8", fontSize: 11 }} interval="preserveStartEnd" label={{ value: 'Time', position: 'insideBottomRight', offset: -5, fill: '#94a3b8', fontSize: 12 }} />
            <YAxis domain={[0, 1]} tick={{ fill: "#94a3b8", fontSize: 11 }} label={{ value: 'Risk Probability', angle: -90, position: 'insideLeft', fill: '#94a3b8', fontSize: 12 }} />
            <Tooltip
              contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", color: "#e2e8f0" }}
              formatter={(value) => (toNumber(value) ?? 0).toFixed(3)}
              labelFormatter={(value) => value}
            />
            <Legend verticalAlign="top" height={36} iconType="line" />
            <Line type="monotone" dataKey="pastRisk" name="Past (Actual)" stroke="#00E5FF" strokeWidth={2} dot={false} />
            <Line
              type="monotone"
              dataKey="futureRisk"
              name="Future (Predicted)"
              stroke="#FFA500"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ r: 4 }}
            />
            <ReferenceLine y={FUTURE_RISK_THRESHOLD} stroke="#ef4444" strokeDasharray="5 5" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}

function RootCauseAnalyzer({ rootCauses }) {
  const topCauses = useMemo(() => (Array.isArray(rootCauses) ? rootCauses.slice(0, 3) : []), [rootCauses]);

  return (
    <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-200">
        <AlertTriangle size={16} className="text-amber-300" />
        Section B: Root Cause Analysis
      </h2>

      {!topCauses.length ? (
        <div className="flex h-40 flex-col items-center justify-center gap-3">
          <CheckCircle2 size={48} className="text-emerald-400" />
          <p className="text-lg font-semibold text-emerald-300">All Systems Normal</p>
        </div>
      ) : (
        <div className="space-y-3">
          {topCauses.map((entry, index) => {
            const impact = toNumber(entry?.impact);
            return (
              <div
                key={`${entry?.cause || "cause"}-${index}`}
                className="rounded-lg border border-amber-900/50 bg-amber-900/10 px-4 py-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-amber-200">
                    {index + 1}. {entry?.cause || "Unknown Cause"}
                  </p>
                  {impact !== null && (
                    <span className="rounded border border-amber-700/60 bg-slate-950/40 px-2 py-1 text-xs font-semibold text-amber-300">
                      Impact {impact.toFixed(3)}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function TelemetryPanel({ telemetryRows, selectedSensor, onSelectSensor }) {
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
    <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4 flex flex-col h-full">
      <h2 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-slate-200 shrink-0">
        <Activity size={16} className="text-emerald-400" />
        Section C: Real-Time Telemetry Grid
      </h2>

      <div className="flex-1 overflow-auto rounded-lg border border-slate-700/50 bg-slate-900 shadow-inner">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="sticky top-0 bg-slate-800 text-xs uppercase text-slate-400 z-10 shadow-md">
            <tr>
              <th className="px-4 py-3 font-medium">Parameter</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Current</th>
              <th className="px-4 py-3 font-medium">Delta Trend</th>
              <th className="px-4 py-3 font-medium">Safe Range</th>
              <th className="px-4 py-3 font-medium">Trend</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-700/50">
            {tableData.map((row, idx) => {
              const status = String(row?.status || "NORMAL").toUpperCase();
              const isRoot = Boolean(row?.is_root_cause);
              const isClickable = status !== "NORMAL" || isRoot;
              const isSelected = selectedSensor === row?.sensor;
              const delta = toNumber(row?.trend_delta) ?? 0;
              const trendDirection = row?.trend_direction;
              const trendIcon = trendDirection === "up" ? "\u25B2" : trendDirection === "down" ? "\u25BC" : "\u2014";
              const trendColor = trendDirection === "up"
                ? "text-emerald-300"
                : trendDirection === "down"
                  ? "text-rose-300"
                  : "text-slate-300";

              const statusColor = status === "EXCEEDED"
                ? "text-red-400"
                : status === "WARNING"
                  ? "text-amber-300"
                  : "text-emerald-400";

              const sparklineData = (Array.isArray(row?.sparkline) ? row.sparkline : [])
                .map((value, pointIndex) => ({ pointIndex, value: toNumber(value) }))
                .filter((point) => point.value !== null);

              const rowClassName = [
                "transition-colors",
                isRoot ? "bg-amber-900/15" : "",
                isSelected ? "bg-cyan-900/25 border-l-2 border-l-cyan-400" : "",
                isClickable ? "cursor-pointer hover:bg-slate-800/60" : "cursor-default",
              ].filter(Boolean).join(" ");

              return (
                <tr
                  key={`${row?.sensor || "sensor"}-${idx}`}
                  className={rowClassName}
                  onClick={() => { if (isClickable) onSelectSensor(row.sensor); }}
                >
                  <td className="px-4 py-3 font-medium text-slate-300">
                    <div className="flex items-center gap-2">
                      {isRoot && <Flame size={14} className="text-amber-400" />}
                      <span className="capitalize">{String(row?.sensor || "").replace(/_/g, " ").toLowerCase()}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-semibold ${statusColor}`}>{status}</span>
                  </td>
                  <td className="px-4 py-3 font-mono text-slate-200">
                    {toNumber(row?.value) !== null ? Number(row.value).toFixed(2) : "--"}
                  </td>
                  <td className={`px-4 py-3 font-mono ${trendColor}`}>
                    {trendIcon} {delta > 0 ? "+" : ""}{delta.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {toNumber(row?.safe_min) !== null ? Number(row.safe_min).toFixed(2) : "0"}
                    <span className="text-slate-600 px-1">~</span>
                    {toNumber(row?.safe_max) !== null ? Number(row.safe_max).toFixed(2) : "inf"}
                  </td>
                  <td className="px-4 py-3">
                    {sparklineData.length ? (
                      <LineChart width={110} height={30} data={sparklineData}>
                        <Line
                          type="monotone"
                          dataKey="value"
                          stroke={isRoot ? "#f59e0b" : "#60a5fa"}
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    ) : (
                      <span className="text-xs text-slate-500">--</span>
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

function PredictionSummary({ summaryStats, timeline }) {
  const stats = useMemo(() => {
    const pastPoints = timeline?.filter(p => !p.is_future) || [];
    const futurePoints = timeline?.filter(p => p.is_future) || [];

    const avgPastRisk = pastPoints.length ? (pastPoints.reduce((acc, p) => acc + p.risk_score, 0) / pastPoints.length) * 100 : 0;
    const avgFutureRisk = futurePoints.length ? (futurePoints.reduce((acc, p) => acc + p.risk_score, 0) / futurePoints.length) * 100 : 0;

    const pastScrapCount = summaryStats?.past_scrap_detected || 0;
    const futureScrapCount = summaryStats?.future_scrap_predicted || 0;

    const riskTrend = avgFutureRisk - avgPastRisk;

    return {
      pastScrapCount,
      futureScrapCount,
      avgPastRisk,
      riskTrend,
      trendText: riskTrend > 0 ? `Upward +${riskTrend.toFixed(1)}%` : riskTrend < 0 ? `Downward ${riskTrend.toFixed(1)}%` : "Stable 0.0%",
      trendColor: riskTrend > 0 ? "text-red-400" : riskTrend < 0 ? "text-emerald-400" : "text-slate-400",
      trendBorder: riskTrend > 0 ? "border-red-900/50 bg-red-900/10" : "border-slate-700/50 bg-slate-800/50"
    };
  }, [summaryStats, timeline]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Past Scrap Analysis Card */}
      <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-200">Past Scrap Analysis</h3>
          <span className="px-2 py-1 text-[10px] uppercase font-bold tracking-wider text-emerald-400 bg-emerald-400/10 rounded">Actual</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-lg border border-slate-700/50 bg-slate-800/50">
            <p className="text-xs text-slate-400 mb-1 font-medium">Total Past Scrap</p>
            <p className="text-2xl font-bold text-slate-100">{stats.pastScrapCount} <span className="text-sm font-normal text-slate-500">units</span></p>
            <p className="text-xs text-slate-500 mt-1">Last 4 hours</p>
          </div>
          <div className="p-4 rounded-lg border border-cyan-900/50 bg-cyan-900/10">
            <p className="text-xs text-cyan-400/70 mb-1 font-medium">Average Past Risk</p>
            <p className="text-2xl font-bold text-cyan-400">{stats.avgPastRisk.toFixed(1)}%</p>
            <p className="text-xs text-cyan-500/50 mt-1">Historical baseline</p>
          </div>
        </div>
      </section>

      {/* Future Scrap Forecast Card */}
      <section className="rounded-xl border border-slate-700 bg-slate-900/70 p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-sm font-semibold text-slate-200">Future Scrap Forecast</h3>
          <span className="px-2 py-1 text-[10px] uppercase font-bold tracking-wider text-amber-400 bg-amber-400/10 rounded">Predicted</span>
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="p-4 rounded-lg border border-amber-900/50 bg-amber-900/10">
            <p className="text-xs text-amber-400/70 mb-1 font-medium">Predicted Scrap</p>
            <p className="text-2xl font-bold text-amber-400">{stats.futureScrapCount} <span className="text-sm font-normal text-amber-700/50">units</span></p>
            <p className="text-xs text-amber-500/50 mt-1">Next 60 min</p>
          </div>
          <div className={`p-4 rounded-lg border ${stats.trendBorder}`}>
            <p className="text-xs text-slate-400 mb-1 font-medium">Trend Comparison</p>
            <p className={`text-2xl font-bold ${stats.trendColor}`}>{stats.trendText}</p>
            <p className="text-xs text-slate-500 mt-1">Future vs Past</p>
          </div>
        </div>
      </section>
    </div>
  );
}

function App() {
  const [machineId, setMachineId] = useState("M-231");
  const [timeWindowMinutes, setTimeWindowMinutes] = useState(120);
  const [controlRoomData, setControlRoomData] = useState(null);
  const [limitOverrides, setLimitOverrides] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSensor, setSelectedSensor] = useState(null);

  const selectedOption = TIME_WINDOW_OPTIONS.find(o => o.value === timeWindowMinutes) || TIME_WINDOW_OPTIONS[0];

  const fetchControlRoom = useCallback(async () => {
    try {
      setLoading(true);
      const apiUrl = `${API_BASE}/api/control-room/${machineId}`;
      const data = await fetchWithRetry(apiUrl, {
        params: { time_window: timeWindowMinutes, future_window: selectedOption.futureMinutes },
      });
      setControlRoomData(data);
      setError(null);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }, [machineId, timeWindowMinutes, selectedOption.futureMinutes]);

  useEffect(() => {
    fetchControlRoom();
    const intervalId = setInterval(fetchControlRoom, 15000);
    return () => clearInterval(intervalId);
  }, [fetchControlRoom]);

  useEffect(() => {
    setLimitOverrides({});
    setSelectedSensor(null);
  }, [machineId, timeWindowMinutes]);

  const safeLimits = controlRoomData?.safe_limits || {};
  const effectiveLimits = useMemo(() => mergeLimits(safeLimits, limitOverrides), [safeLimits, limitOverrides]);
  const timeline = controlRoomData?.timeline || [];
  const telemetryRows = Array.isArray(controlRoomData?.telemetry_grid) ? controlRoomData.telemetry_grid : [];

  const latestPastPoint = useMemo(() => {
    const past = timeline.filter((point) => !point.is_future);
    return past.length ? past[past.length - 1] : null;
  }, [timeline]);

  const isSensorFrozen = useMemo(() => {
    if (!latestPastPoint || !timeline.length) return false;
    
    // 1. Current risk must be > 0.8
    const risk = toNumber(controlRoomData?.current_health?.risk_score) ?? 0;
    if (risk <= 0.8) return false;

    // 2. Future predictions must match current actuals perfectly
    const trackedKeys = Object.keys(effectiveLimits);
    if (trackedKeys.length === 0) return false;

    const futurePoints = timeline.filter(p => p.is_future);
    if (futurePoints.length === 0) return false;

    const firstFuturePoint = futurePoints[0];
    const pastSensors = latestPastPoint.sensors || {};
    const futureSensors = firstFuturePoint.sensors || {};

    return trackedKeys.every(k => {
      const pastVal = toNumber(pastSensors[k]);
      const futureVal = toNumber(futureSensors[k]);
      return pastVal === futureVal;
    });
  }, [latestPastPoint, timeline, effectiveLimits, controlRoomData]);

  const latestSensors = latestPastPoint?.sensors || {};

  const rootCauses = useMemo(() => {
    const topLevel = controlRoomData?.root_causes;
    if (Array.isArray(topLevel)) {
      return topLevel
        .map((entry) => ({
          cause: typeof entry?.cause === "string" ? entry.cause : null,
          impact: toNumber(entry?.impact),
        }))
        .filter((entry) => Boolean(entry.cause))
        .slice(0, 3);
    }

    const fallback = controlRoomData?.current_health?.root_causes;
    if (Array.isArray(fallback)) {
      return fallback
        .filter((item) => typeof item === "string")
        .map((cause) => ({ cause, impact: null }))
        .slice(0, 3);
    }

    return [];
  }, [controlRoomData]);

  const displayTimeline = useMemo(() => {
    if (!timeline.length) {
      return [];
    }
    // Use risk_score exactly as returned by the backend â€” no UI mutations.
    return timeline.map((point) => ({
      ...point,
      risk_score: Number((toNumber(point.risk_score) ?? 0).toFixed(4)),
    }));
  }, [timeline]);

  const summaryStats = useMemo(() => {
    const base = controlRoomData?.summary_stats || { past_scrap_detected: 0, future_scrap_predicted: 0 };
    const timelineFutureCount = displayTimeline.filter(
      (point) => point.is_future && (toNumber(point.risk_score) ?? 0) > FUTURE_RISK_THRESHOLD,
    ).length;
    return {
      past_scrap_detected: base.past_scrap_detected ?? 0,
      future_scrap_predicted: Math.max(base.future_scrap_predicted ?? 0, timelineFutureCount),
    };
  }, [controlRoomData, displayTimeline]);

  const currentHealth = useMemo(() => {
    const apiHealth = controlRoomData?.current_health || {};
    return {
      status: apiHealth.status || "NORMAL",
      risk_score: toNumber(apiHealth.risk_score) ?? 0,
    };
  }, [controlRoomData]);

  // --- Telemetry status map for auto-switching logic ---
  const telemetryStatuses = useMemo(() => {
    const statuses = {};
    telemetryRows.forEach((row) => {
      const sensor = row?.sensor;
      if (!sensor) return;
      const status = String(row?.status || "NORMAL").toUpperCase();
      if (status === "EXCEEDED") {
        statuses[sensor] = "critical";
      } else if (status === "WARNING") {
        statuses[sensor] = "warning";
      } else {
        statuses[sensor] = "good";
      }
    });
    return statuses;
  }, [telemetryRows]);

  const firstAbnormalSensor = useMemo(() => {
    const critical = Object.keys(telemetryStatuses).find(s => telemetryStatuses[s] === "critical");
    if (critical) return critical;
    const warning = Object.keys(telemetryStatuses).find(s => telemetryStatuses[s] === "warning");
    return warning || null;
  }, [telemetryStatuses]);

  useEffect(() => {
    if (selectedSensor && telemetryStatuses[selectedSensor] === "good") {
      setSelectedSensor(firstAbnormalSensor);
    }
  }, [telemetryStatuses, selectedSensor, firstAbnormalSensor]);

  if (loading && !controlRoomData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        Loading Control Room data...
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-950 p-4 text-slate-100 md:p-6">
      <div className="mx-auto flex max-w-[1500px] flex-col gap-4">
        <GlobalHeader
          machineId={machineId}
          timeWindowMinutes={timeWindowMinutes}
          onMachineChange={setMachineId}
          onTimeWindowChange={setTimeWindowMinutes}
          healthStatus={currentHealth.status}
          isSensorFrozen={isSensorFrozen}
        />

        {error && <div className="rounded-md border border-red-700 bg-red-950/50 px-4 py-2 text-sm text-red-200">{error}</div>}

        <div className="grid grid-cols-12 gap-4">

          <div className="col-span-12">
            <SystemHealthMonitor timeline={displayTimeline} riskScore={currentHealth.risk_score} />
          </div>

          <div className="col-span-12 flex flex-col">
            <RootCauseAnalyzer rootCauses={rootCauses} />
          </div>
          <div className="col-span-12 flex flex-col h-[500px]">
            <TelemetryPanel
              telemetryRows={telemetryRows}
              selectedSensor={selectedSensor}
              onSelectSensor={setSelectedSensor}
            />
          </div>

          <div className="col-span-12 mt-2">
            <PredictionSummary summaryStats={summaryStats} timeline={displayTimeline} />
          </div>

        </div>
      </div>
    </main>
  );
}

export default App;



