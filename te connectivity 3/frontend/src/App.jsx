import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import dayjs from "dayjs";
import utc from "dayjs/plugin/utc";
import timezone from "dayjs/plugin/timezone";

import Sidebar from "./components/Sidebar";
import Header, { MACHINE_OPTIONS, TIME_WINDOW_OPTIONS } from "./components/Header";
import HealthMonitor from "./components/HealthMonitor";
import RootCause from "./components/RootCause";
import TelemetryGrid from "./components/TelemetryGrid";
import PredictionStats from "./components/PredictionStats";

dayjs.extend(utc);
dayjs.extend(timezone);

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8080";
const FUTURE_RISK_THRESHOLD = 0.6;

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

function App() {
  const [machineId, setMachineId] = useState("M-231");
  const [timeWindowMinutes, setTimeWindowMinutes] = useState(60);
  const [controlRoomData, setControlRoomData] = useState(null);
  const [limitOverrides, setLimitOverrides] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedSensor, setSelectedSensor] = useState(null);

  const selectedOption =
    TIME_WINDOW_OPTIONS.find((o) => o.value === timeWindowMinutes) || TIME_WINDOW_OPTIONS[0];

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
  const effectiveLimits = useMemo(
    () => mergeLimits(safeLimits, limitOverrides),
    [safeLimits, limitOverrides],
  );
  const timeline = controlRoomData?.timeline || [];
  const telemetryRows = Array.isArray(controlRoomData?.telemetry_grid)
    ? controlRoomData.telemetry_grid
    : [];

  const latestPastPoint = useMemo(() => {
    const past = timeline.filter((point) => !point.is_future);
    return past.length ? past[past.length - 1] : null;
  }, [timeline]);

  const isSensorFrozen = useMemo(() => {
    if (!latestPastPoint || !timeline.length) return false;
    const risk = toNumber(controlRoomData?.current_health?.risk_score) ?? 0;
    if (risk <= 0.8) return false;
    const trackedKeys = Object.keys(effectiveLimits);
    if (trackedKeys.length === 0) return false;
    const futurePoints = timeline.filter((p) => p.is_future);
    if (futurePoints.length === 0) return false;
    const firstFuturePoint = futurePoints[0];
    const pastSensors = latestPastPoint.sensors || {};
    const futureSensors = firstFuturePoint.sensors || {};
    return trackedKeys.every((k) => {
      const pastVal = toNumber(pastSensors[k]);
      const futureVal = toNumber(futureSensors[k]);
      return pastVal === futureVal;
    });
  }, [latestPastPoint, timeline, effectiveLimits, controlRoomData]);

  const rootCauses = useMemo(() => {
    const topLevel = controlRoomData?.root_causes;
    if (Array.isArray(topLevel)) {
      return topLevel
        .map((entry) => ({
          cause: typeof entry?.cause === "string" ? entry.cause : null,
          impact: toNumber(entry?.impact),
          risk_increasing: toNumber(entry?.risk_increasing),
          risk_decreasing: toNumber(entry?.risk_decreasing),
          top_parameters: Array.isArray(entry?.top_parameters) ? entry.top_parameters : [],
        }))
        .filter((entry) => Boolean(entry.cause))
        .slice(0, 3);
    }
    const fallback = controlRoomData?.current_health?.root_causes;
    if (Array.isArray(fallback)) {
      return fallback
        .filter((item) => typeof item === "string")
        .map((cause) => ({ cause, impact: null, top_parameters: [] }))
        .slice(0, 3);
    }
    return [];
  }, [controlRoomData]);

  const displayTimeline = useMemo(() => {
    if (!timeline.length) return [];
    return timeline.map((point) => ({
      ...point,
      risk_score: Number((toNumber(point.risk_score) ?? 0).toFixed(4)),
    }));
  }, [timeline]);

  const summaryStats = useMemo(() => {
    const base = controlRoomData?.summary_stats || {
      past_scrap_detected: 0,
      future_scrap_predicted: 0,
    };
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
    const critical = Object.keys(telemetryStatuses).find(
      (s) => telemetryStatuses[s] === "critical",
    );
    if (critical) return critical;
    const warning = Object.keys(telemetryStatuses).find(
      (s) => telemetryStatuses[s] === "warning",
    );
    return warning || null;
  }, [telemetryStatuses]);

  useEffect(() => {
    if (selectedSensor && telemetryStatuses[selectedSensor] === "good") {
      setSelectedSensor(firstAbnormalSensor);
    }
  }, [telemetryStatuses, selectedSensor, firstAbnormalSensor]);

  if (loading && !controlRoomData) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-surface-50 to-surface-100">
        <div className="flex flex-col items-center gap-4 animate-fade-in">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center shadow-glow animate-pulse_slow">
            <span className="text-white font-extrabold text-xl">TE</span>
          </div>
          <p className="text-sm font-medium text-slate-500">Loading Control Room...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <Sidebar />

      <main className="flex-1 min-h-screen p-4 md:p-6 lg:p-8">
        <div className="mx-auto max-w-[1400px] flex flex-col gap-5 stagger-children">
          <Header
            machineId={machineId}
            timeWindowMinutes={timeWindowMinutes}
            onMachineChange={setMachineId}
            onTimeWindowChange={setTimeWindowMinutes}
            healthStatus={currentHealth.status}
            isSensorFrozen={isSensorFrozen}
          />

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-3 text-sm text-red-600 font-medium animate-fade-in">
              {error}
            </div>
          )}

          <HealthMonitor timeline={displayTimeline} riskScore={currentHealth.risk_score} />

          <RootCause rootCauses={rootCauses} />

          <div className="h-[500px]">
            <TelemetryGrid
              telemetryRows={telemetryRows}
              selectedSensor={selectedSensor}
              onSelectSensor={setSelectedSensor}
            />
          </div>

          <PredictionStats summaryStats={summaryStats} timeline={displayTimeline} />
        </div>
      </main>
    </div>
  );
}

export default App;
