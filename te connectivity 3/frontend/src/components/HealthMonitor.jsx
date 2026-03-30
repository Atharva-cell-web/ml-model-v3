import React, { useMemo } from "react";
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
  Area,
  AreaChart,
} from "recharts";
import { Activity } from "lucide-react";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

dayjs.extend(utc);
dayjs.extend(timezone);

const toNumber = (value) => {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
};

export default function HealthMonitor({ timeline, riskScore }) {
  const chartData = useMemo(
    () =>
      (timeline || [])
        .map((point) => {
          const risk = toNumber(point.risk_score) ?? 0;
          const isFuture = point.type === "future" || point.is_future;
          const isBridge = point.type === "bridge";

          let time = null;
          if (typeof point.timestamp === "number" && Number.isFinite(point.timestamp)) {
            time = point.timestamp;
          } else if (typeof point.timestamp === "string") {
            const rawTs = point.timestamp.replace(" ", "T");
            time = Date.parse(rawTs);
          }
          if (!Number.isFinite(time)) return null;

          if (isBridge) {
            return {
              time,
              pastRisk: risk,
              futureRisk: toNumber(point.bridge_future_risk) ?? risk,
              isFuture: false,
              isBridge: true,
            };
          }

          return {
            time,
            pastRisk: isFuture ? null : risk,
            futureRisk: isFuture ? risk : null,
            isFuture,
            isBridge: false,
          };
        })
        .filter(Boolean)
        .sort((a, b) => a.time - b.time),
    [timeline],
  );

  const predictionStartTime = useMemo(() => {
    const bridge = chartData.find((p) => p.isBridge);
    if (bridge) return bridge.time;
    const firstFuture = chartData.find((p) => p.isFuture);
    return firstFuture ? firstFuture.time : null;
  }, [chartData]);

  if (!chartData.length) {
    return (
      <div className="glass-card flex h-64 items-center justify-center text-sm text-slate-400">
        No timeline data available.
      </div>
    );
  }

  const tooltipLabelFormatter = (value) => {
    if (value === null || value === undefined) return "";
    return dayjs(value).tz("Asia/Kolkata").format("MMM DD YYYY HH:mm:ss");
  };

  const riskPercent = (riskScore * 100).toFixed(1);
  const riskColor =
    riskScore > 0.7 ? "text-red-600" : riskScore > 0.4 ? "text-amber-600" : "text-emerald-600";

  return (
    <section className="glass-card p-5 animate-slide-up" style={{ animationDelay: "0.15s" }}>
      <div className="mb-4 flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-bold uppercase tracking-wider text-slate-700">
          <div className="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center">
            <Activity size={16} className="text-brand-500" />
          </div>
          System Health Monitor
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-xs text-slate-400 font-medium">Current Risk</span>
          <span className={`text-2xl font-extrabold ${riskColor}`}>{riskPercent}%</span>
        </div>
      </div>
      <div className="h-72 -mx-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="pastGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#3b82f6" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="futureGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f97316" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#f97316" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis
              dataKey="time"
              type="number"
              scale="time"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(t) => dayjs(t).tz("Asia/Kolkata").format("HH:mm")}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={{ stroke: "#cbd5e1" }}
              tickLine={{ stroke: "#cbd5e1" }}
              label={{ value: "Time", position: "insideBottomRight", offset: -5, fill: "#64748b", fontSize: 12 }}
            />
            <YAxis
              domain={[0, 1]}
              tick={{ fill: "#64748b", fontSize: 11 }}
              axisLine={{ stroke: "#cbd5e1" }}
              tickLine={{ stroke: "#cbd5e1" }}
              label={{ value: "Risk Probability", angle: -90, position: "insideLeft", fill: "#64748b", fontSize: 12 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(255,255,255,0.95)",
                backdropFilter: "blur(12px)",
                border: "1px solid #e2e8f0",
                borderRadius: "12px",
                color: "#1e293b",
                boxShadow: "0 8px 30px rgba(0,0,0,0.08)",
              }}
              formatter={(value, name) => [(toNumber(value) ?? 0).toFixed(4), name]}
              labelFormatter={tooltipLabelFormatter}
            />
            <Legend
              verticalAlign="top"
              height={36}
              iconType="circle"
              wrapperStyle={{ fontSize: "12px", fontWeight: 500, color: "#475569" }}
            />
            <Area
              type="monotone"
              dataKey="pastRisk"
              name="Past (Actual)"
              stroke="#3b82f6"
              strokeWidth={2.5}
              fill="url(#pastGradient)"
              dot={false}
              connectNulls={false}
            />
            <Area
              type="monotone"
              dataKey="futureRisk"
              name="Future (Predicted)"
              stroke="#f97316"
              strokeWidth={2.5}
              strokeDasharray="6 4"
              fill="url(#futureGradient)"
              dot={{ r: 4, fill: "#f97316", stroke: "#fff", strokeWidth: 2 }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />
            {predictionStartTime && (
              <ReferenceLine
                x={predictionStartTime}
                stroke="#94a3b8"
                strokeDasharray="4 4"
                label={{ value: "Prediction Starts", fill: "#94a3b8", fontSize: 10, position: "top" }}
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
