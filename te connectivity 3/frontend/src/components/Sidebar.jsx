import React from "react";
import {
  LayoutDashboard,
  Activity,
  AlertTriangle,
  BarChart3,
  Settings,
  HelpCircle,
} from "lucide-react";

const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "telemetry", label: "Telemetry", icon: Activity },
  { id: "alerts", label: "Alerts", icon: AlertTriangle },
  { id: "analytics", label: "Analytics", icon: BarChart3 },
];

const BOTTOM_ITEMS = [
  { id: "settings", label: "Settings", icon: Settings },
  { id: "help", label: "Help", icon: HelpCircle },
];

export default function Sidebar() {
  return (
    <aside className="hidden lg:flex flex-col w-[240px] shrink-0 h-screen sticky top-0 bg-white/50 backdrop-blur-xl border-r border-slate-200/80 animate-slide-in-left">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-6 border-b border-slate-100">
        <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-glow">
          <span className="text-white font-extrabold text-sm tracking-tight">TE</span>
        </div>
        <div>
          <p className="text-sm font-bold text-slate-800 leading-tight">TE Connectivity</p>
          <p className="text-[10px] text-slate-400 font-medium">Predictive AI</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = item.id === "dashboard";
          return (
            <button
              key={item.id}
              className={`sidebar-link w-full ${isActive ? "active" : ""}`}
            >
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </nav>

      {/* Bottom */}
      <div className="px-3 py-4 border-t border-slate-100 space-y-1">
        {BOTTOM_ITEMS.map((item) => {
          const Icon = item.icon;
          return (
            <button key={item.id} className="sidebar-link w-full">
              <Icon size={18} />
              {item.label}
            </button>
          );
        })}
      </div>
    </aside>
  );
}
