import React from "react";
import { Bell, Cpu } from "lucide-react";

const MACHINE_OPTIONS = [
  { value: "M-231", label: "M-231" },
  { value: "M-356", label: "M-356" },
  { value: "M-471", label: "M-471" },
  { value: "M-607", label: "M-607" },
  { value: "M-612", label: "M-612" },
];

const TIME_WINDOW_OPTIONS = [
  { value: 60, futureMinutes: 30, label: "1H Past / 30M Future" },
];

export { MACHINE_OPTIONS, TIME_WINDOW_OPTIONS };

export default function Header({
  machineId,
  timeWindowMinutes,
  onMachineChange,
  onTimeWindowChange,
  healthStatus,
  isSensorFrozen,
}) {
  const statusConfig =
    healthStatus === "CRITICAL" || healthStatus === "HIGH"
      ? { cls: "badge-critical", glow: "shadow-glow-red" }
      : healthStatus === "MEDIUM"
        ? { cls: "badge-warning", glow: "" }
        : { cls: "badge-normal", glow: "shadow-glow-green" };

  return (
    <header className="glass-card px-6 py-4 flex flex-wrap items-center justify-between gap-4 animate-fade-in" style={{ animationDelay: "0.1s" }}>
      <div>
        <h1 className="text-xl font-bold text-slate-800 tracking-tight flex items-center gap-2">
          <Cpu size={22} className="text-brand-500" />
          Predictive Maintenance Control Room
        </h1>
        <p className="text-xs text-slate-400 mt-0.5">
          Unified machine health, root cause, and telemetry view
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <select
          id="machine-select"
          value={machineId}
          onChange={(e) => onMachineChange(e.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 transition-all"
        >
          {MACHINE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <select
          id="time-range-select"
          value={timeWindowMinutes}
          onChange={(e) => onTimeWindowChange(Number(e.target.value))}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 shadow-sm outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100 transition-all"
        >
          {TIME_WINDOW_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>

        {/* Notification bell */}
        <button className="relative p-2.5 rounded-xl bg-white border border-slate-200 shadow-sm hover:shadow-md transition-all">
          <Bell size={18} className="text-slate-500" />
          {(healthStatus === "CRITICAL" || healthStatus === "HIGH") && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-pulse_slow border-2 border-white" />
          )}
        </button>

        {/* Status badge */}
        <span className={`rounded-xl px-4 py-2.5 text-xs font-bold tracking-wide ${statusConfig.cls} ${statusConfig.glow} transition-all`}>
          {healthStatus}
        </span>

        {isSensorFrozen && (
          <span className="rounded-xl px-3 py-2 text-xs font-bold bg-orange-50 text-orange-600 border border-orange-200">
            SENSOR FROZEN
          </span>
        )}
      </div>
    </header>
  );
}
