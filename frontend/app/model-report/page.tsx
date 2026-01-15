"use client";

import { useEffect, useMemo, useState } from "react";

const GRAPHQL_URL =
  typeof window !== "undefined"
    ? "/api/graphql"
    : process.env.NEXT_PUBLIC_GRAPHQL_URL || "http://localhost:8000/graphql";

type BacktestResult = {
  timestamp: string;
  maeModel: number;
  maeBaseline: number;
  directionalAccuracyModel: number;
  directionalAccuracyBaseline: number;
  validationSize: number;
};

type HealthStatus = {
  model: { trained_at: string | null };
  backtest: { last_run: string | null };
};

type DriftMetrics = {
  window: number;
  recentMae: number | null;
  priorMae: number | null;
  delta: number | null;
  status: string;
};

export default function ModelReportPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [drift, setDrift] = useState<DriftMetrics | null>(null);

  useEffect(() => {
    let isActive = true;
    const loadResults = async () => {
      try {
        const query = `
          query BacktestResults($limit: Int!, $window: Int!) {
            backtestResults(limit: $limit) {
              timestamp
              maeModel
              maeBaseline
              directionalAccuracyModel
              directionalAccuracyBaseline
              validationSize
            }
            driftMetrics(window: $window) {
              window
              recentMae
              priorMae
              delta
              status
            }
          }
        `;

        const response = await fetch(GRAPHQL_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, variables: { limit: 14, window: 5 } }),
        });

        const payload = await response.json();
        if (!isActive || payload.errors) return;
        setResults(payload.data?.backtestResults ?? []);
        setDrift(payload.data?.driftMetrics ?? null);
      } catch (error) {
        console.error("Failed to load backtest results", error);
      }
    };

    loadResults();
    return () => {
      isActive = false;
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
    return () => {
      isActive = false;
    };
  }, []);

  const latest = results[results.length - 1];
  const avgMae = useMemo(() => {
    if (!results.length) return null;
    return (
      results.reduce((acc, entry) => acc + entry.maeModel, 0) / results.length
    );
  }, [results]);

  return (
    <section className="space-y-10">
      <div className="flex flex-col gap-4">
        <p className="text-xs uppercase tracking-[0.35em] text-muted">Model Report</p>
        <h1 className="text-4xl font-semibold">Performance & Signals</h1>
        <p className="text-muted">
          A concise narrative and quantitative snapshot of the current model.
          This section summarizes feature design choices, validation results, and
          the latest training status.
        </p>
      </div>

      <div className="panel p-6 space-y-6">
        <div className="flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Narrative</p>
          <p className="text-sm text-muted">
            The current model focuses on short-horizon forecasting using hourly
            OHLC-derived signals. It combines momentum (MACD), relative strength
            (RSI), volatility, and volume anomalies with market context (SPY,
            QQQ, VIX). The goal is to improve directional accuracy while keeping
            error low against a naive baseline.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Latest Train</p>
            <p className="mt-2 text-sm font-semibold break-all">
              {health?.model.trained_at ?? "No model timestamp"}
            </p>
          </div>
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Backtest Run</p>
            <p className="mt-2 text-sm font-semibold break-all">
              {health?.backtest.last_run ?? "No backtest yet"}
            </p>
          </div>
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Average MAE</p>
            <p className="mt-2 text-2xl font-semibold text-accent">
              {avgMae ? avgMae.toFixed(4) : "—"}
            </p>
          </div>
        </div>
        <div className="panel-outline px-4 py-4">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Drift Status</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <span
              className={`text-sm font-semibold ${
                drift?.status === "degrading"
                  ? "text-rose-300"
                  : drift?.status === "improving"
                  ? "text-accent"
                  : "text-muted"
              }`}
            >
              {drift?.status ?? "No data"}
            </span>
            <span className="text-xs text-muted">
              {drift?.delta !== null && drift?.delta !== undefined
                ? `Delta ${drift.delta.toFixed(4)}`
                : "Delta —"}
            </span>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="panel p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-muted">Latest Metrics</p>
              <h2 className="mt-2 text-xl font-semibold">Model vs Baseline</h2>
            </div>
            <span className="text-sm text-muted">
              {latest ? latest.timestamp : "No data"}
            </span>
          </div>
          {latest ? (
            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <div className="panel-outline px-4 py-4">
                <p className="text-xs uppercase tracking-[0.3em] text-muted">MAE</p>
                <p className="mt-2 text-2xl font-semibold text-accent">
                  {latest.maeModel.toFixed(4)}
                </p>
                <p className="text-xs text-muted">
                  Baseline: {latest.maeBaseline.toFixed(4)}
                </p>
              </div>
              <div className="panel-outline px-4 py-4">
                <p className="text-xs uppercase tracking-[0.3em] text-muted">Directional</p>
                <p className="mt-2 text-2xl font-semibold text-accent">
                  {(latest.directionalAccuracyModel * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-muted">
                  Baseline: {(latest.directionalAccuracyBaseline * 100).toFixed(1)}%
                </p>
              </div>
              <div className="panel-outline px-4 py-4">
                <p className="text-xs uppercase tracking-[0.3em] text-muted">Validation Size</p>
                <p className="mt-2 text-2xl font-semibold text-accent">
                  {latest.validationSize}
                </p>
              </div>
            </div>
          ) : (
            <div className="mt-6 panel-outline px-6 py-10 text-center text-muted">
              No backtest results logged yet.
            </div>
          )}
        </div>

        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Feature Set</p>
          <h2 className="mt-2 text-xl font-semibold">Key Inputs</h2>
          <div className="mt-6 grid gap-3 text-sm text-muted">
            {[
              "Hourly OHLC-derived signals",
              "RSI, MACD, and rolling volatility",
              "Volume z-score anomalies",
              "Market context (SPY, QQQ, VIX)",
              "Temporal features (hour, weekday)",
            ].map((item) => (
              <div key={item} className="panel-outline px-4 py-3">
                {item}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
