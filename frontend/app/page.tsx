"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

const GRAPHQL_URL =
  typeof window !== "undefined"
    ? "/api/graphql"
    : process.env.NEXT_PUBLIC_GRAPHQL_URL || "http://localhost:8000/graphql";

const STOCKS = ["NVDA", "AAPL", "TSLA"];

type LivePrice = {
  symbol: string;
  price: number | null;
  changePercent: number | null;
};

type HealthStatus = {
  server_time: string;
  redis: { ok: boolean };
  symbols: { symbol: string; last_update: string | null; age_seconds: number | null }[];
  model: { trained_at: string | null };
  backtest: { last_run: string | null };
};

export default function Home() {
  const [livePrices, setLivePrices] = useState<Record<string, LivePrice>>({});
  const [health, setHealth] = useState<HealthStatus | null>(null);

  useEffect(() => {
    let isActive = true;
    let socket: WebSocket | null = null;

    const loadPrices = async () => {
      try {
        const query = `
          query LivePrices($symbols: [String!]) {
            livePrices(symbols: $symbols) {
              symbol
              price
              changePercent
            }
          }
        `;

        const response = await fetch(GRAPHQL_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            variables: { symbols: STOCKS },
          }),
        });

        const result = await response.json();
        if (!isActive || result.errors) return;

        const mapped = (result.data?.livePrices ?? []).reduce(
          (acc: Record<string, LivePrice>, item: LivePrice) => {
            acc[item.symbol] = item;
            return acc;
          },
          {}
        );
        setLivePrices(mapped);
      } catch (error) {
        console.error("Failed to load live prices", error);
      }
    };

    const connectSocket = () => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${protocol}://${window.location.host}/api/ws/live`);
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.type !== "live_prices") return;
          const mapped = (payload.data ?? []).reduce(
            (acc: Record<string, LivePrice>, item: { symbol: string; price: number | null; change_percent: number | null }) => {
              acc[item.symbol] = {
                symbol: item.symbol,
                price: item.price,
                changePercent: item.change_percent,
              };
              return acc;
            },
            {}
          );
          if (isActive) setLivePrices(mapped);
        } catch (err) {
          console.error("Live socket parse error", err);
        }
      };
      socket.onerror = () => {
        loadPrices();
      };
      socket.onclose = () => {
        if (isActive) {
          setTimeout(connectSocket, 3000);
        }
      };
    };

    connectSocket();
    loadPrices();
    const interval = setInterval(loadPrices, 30000);
    return () => {
      isActive = false;
      if (socket) {
        socket.close();
      }
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    let isActive = true;
    const loadHealth = async () => {
      try {
        const response = await fetch("/api/health");
        if (!response.ok) return;
        const payload = await response.json();
        if (isActive) setHealth(payload);
      } catch (error) {
        console.error("Failed to load health", error);
      }
    };

    loadHealth();
    const interval = setInterval(loadHealth, 60000);
    return () => {
      isActive = false;
      clearInterval(interval);
    };
  }, []);

  const rows = useMemo(() => {
    return STOCKS.map((symbol) => {
      const live = livePrices[symbol];
      return {
        symbol,
        price: live?.price ?? null,
        change: live?.changePercent ?? null,
      };
    });
  }, [livePrices]);

  const hasLiveData = rows.some((row) => row.price !== null);

  const formatPrice = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    return `$${value.toLocaleString(undefined, {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatChange = (value: number | null | undefined) => {
    if (value === null || value === undefined) return "—";
    const sign = value >= 0 ? "+" : "";
    return `${sign}${value.toFixed(2)}%`;
  };

  return (
    <section className="grid items-center gap-12 lg:grid-cols-[1.15fr_0.85fr]">
      <div className="flex flex-col gap-8">
        <span className="panel-outline w-fit px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] text-accent">
          Live Market Intelligence
        </span>
        <div className="space-y-5">
          <h2 className="text-4xl font-semibold leading-tight md:text-5xl">
            Forecast momentum, volatility, and market direction in one sleek
            dashboard.
          </h2>
          <p className="text-lg text-muted">
            AI Stock Predictor blends streaming price ingestion, Redis-backed
            caching, and ML inference to surface forward-looking signals for
            tracked symbols.
          </p>
        </div>
        <div className="flex flex-wrap gap-4">
          <Link
            href="/predict"
            className="glow-ring rounded-2xl bg-emerald-400/90 px-6 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-slate-900 transition hover:bg-emerald-300"
          >
            View Predictions
          </Link>
          <Link
            href="/about"
            className="rounded-2xl border border-emerald-400/40 px-6 py-3 text-sm font-semibold uppercase tracking-[0.2em] text-emerald-200 transition hover:border-emerald-300/80 hover:text-white"
          >
            Architecture
          </Link>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {[
            { label: "Tracked Symbols", value: "5+" },
            { label: "Prediction Horizon", value: "5D" },
            { label: "Live Refresh", value: "120s" },
          ].map((stat) => (
            <div key={stat.label} className="panel-outline px-4 py-3">
              <p className="text-xs uppercase tracking-[0.3em] text-muted">
                {stat.label}
              </p>
              <p className="mt-2 text-2xl font-semibold text-accent">
                {stat.value}
              </p>
            </div>
          ))}
        </div>
        <div className="panel-outline px-4 py-3 text-sm text-muted">
          Live prices stream into Redis → hourly model retraining → GraphQL/WebSocket
          predictions → Results + Status dashboards.
        </div>
      </div>

      <div className="panel glow-ring p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-muted">
              Market Pulse
            </p>
            <h3 className="mt-2 text-2xl font-semibold">Signal Dashboard</h3>
          </div>
          <span
            className={`text-sm font-semibold ${
              hasLiveData ? "text-accent-2" : "text-rose-300"
            }`}
          >
            {hasLiveData ? "Realtime" : "Awaiting feed"}
          </span>
        </div>

        <div className="mt-6 space-y-4">
          {rows.map((row) => (
            <div
              key={row.symbol}
              className="flex items-center justify-between rounded-2xl bg-slate-950/40 px-4 py-3"
            >
              <div>
                <p className="text-sm font-semibold">{row.symbol}</p>
                <p className="text-xs text-muted">Model confidence: High</p>
              </div>
              <div className="text-right">
                <p className="text-sm font-semibold">{formatPrice(row.price)}</p>
                <p
                  className={`text-xs font-semibold ${
                    row.change === null
                      ? "text-muted"
                      : row.change < 0
                      ? "text-rose-300"
                      : "text-accent"
                  }`}
                >
                  {formatChange(row.change)}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-4">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">
            Signal Summary
          </p>
          <p className="mt-2 text-sm text-muted">
            Momentum remains positive across large-cap tech, while volatility
            bands tighten into the next trading window.
          </p>
        </div>
      </div>

      <div className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-muted">System Health</p>
            <h3 className="mt-2 text-2xl font-semibold">Operational Status</h3>
          </div>
          <span
            className={`text-sm font-semibold ${
              health?.redis.ok ? "text-accent" : "text-rose-300"
            }`}
          >
            {health?.redis.ok ? "All systems nominal" : "Check services"}
          </span>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Model</p>
            <p className="mt-2 text-sm font-semibold break-all">
              {health?.model.trained_at ?? "No model timestamp"}
            </p>
          </div>
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Backtest</p>
            <p className="mt-2 text-sm font-semibold break-all">
              {health?.backtest.last_run ?? "No backtest yet"}
            </p>
          </div>
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Redis</p>
            <p className="mt-2 text-sm font-semibold">
              {health?.redis.ok ? "Connected" : "Unavailable"}
            </p>
          </div>
        </div>

        <div className="mt-6 space-y-3 text-sm text-muted">
          {(health?.symbols ?? []).map((entry) => (
            <div
              key={entry.symbol}
              className="panel-outline flex items-center justify-between px-4 py-3"
            >
              <span className="font-semibold text-white">{entry.symbol}</span>
              <span className="text-xs text-muted">
                {entry.last_update ? `Last update ${entry.age_seconds}s ago` : "No live data yet"}
              </span>
            </div>
          ))}
          {!health?.symbols?.length && (
            <p>No symbol telemetry available yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}
