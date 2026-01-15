"use client";

import { useEffect, useState } from "react";

type StatusPayload = {
  uptime_seconds: number;
  server_time: string;
  backtest_last_run: string | null;
  symbols: { symbol: string; last_update: string | null; age_seconds: number | null }[];
};

const formatDuration = (seconds: number) => {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${minutes}m`;
};

export default function StatusPage() {
  const [status, setStatus] = useState<StatusPayload | null>(null);

  useEffect(() => {
    let isActive = true;
    const loadStatus = async () => {
      try {
        const response = await fetch("/api/status");
        if (!response.ok) return;
        const payload = await response.json();
        if (isActive) setStatus(payload);
      } catch (error) {
        console.error("Failed to load status", error);
      }
    };

    loadStatus();
    const interval = setInterval(loadStatus, 60000);
    return () => {
      isActive = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <section className="space-y-10">
      <div className="flex flex-col gap-4">
        <p className="text-xs uppercase tracking-[0.35em] text-muted">Status</p>
        <h1 className="text-4xl font-semibold">System Status</h1>
        <p className="text-muted">
          High-level uptime and data freshness signals for the full stack.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Uptime</p>
          <p className="mt-3 text-3xl font-semibold text-accent">
            {status ? formatDuration(status.uptime_seconds) : "—"}
          </p>
          <p className="mt-2 text-sm text-muted">
            Server time: {status?.server_time ?? "—"}
          </p>
        </div>
        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Backtest</p>
          <p className="mt-3 text-xl font-semibold break-all">
            {status?.backtest_last_run ?? "No backtest logged"}
          </p>
          <p className="mt-2 text-sm text-muted">
            Logs sourced from nightly runs.
          </p>
        </div>
      </div>

      <div className="panel p-6">
        <p className="text-xs uppercase tracking-[0.3em] text-muted">Data Freshness</p>
        <h2 className="mt-2 text-xl font-semibold">Live Feed</h2>
        <div className="mt-6 space-y-3 text-sm text-muted">
          {(status?.symbols ?? []).map((entry) => (
            <div
              key={entry.symbol}
              className="panel-outline flex items-center justify-between px-4 py-3"
            >
              <span className="text-white">{entry.symbol}</span>
              <span>
                {entry.last_update
                  ? `Updated ${entry.age_seconds}s ago`
                  : "No data yet"}
              </span>
            </div>
          ))}
          {!status?.symbols?.length && <p>No symbol data available.</p>}
        </div>
      </div>
    </section>
  );
}
