"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

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

type FeatureImportance = {
  name: string;
  importance: number;
};

type FeatureImportanceSnapshot = {
  timestamp: string;
  features: FeatureImportance[];
};

export default function ModelReportPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [drift, setDrift] = useState<DriftMetrics | null>(null);
  const [features, setFeatures] = useState<FeatureImportance[]>([]);
  const [featureTrend, setFeatureTrend] = useState<FeatureImportanceSnapshot[]>([]);

  useEffect(() => {
    let isActive = true;
    const loadResults = async () => {
      try {
        const query = `
          query BacktestResults($limit: Int!, $window: Int!, $topK: Int!, $trendLimit: Int!) {
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
            featureImportances(topK: $topK) {
              name
              importance
            }
            featureImportanceTrend(limit: $trendLimit) {
              timestamp
              features {
                name
                importance
              }
            }
          }
        `;

        const response = await fetch(GRAPHQL_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query,
            variables: { limit: 14, window: 5, topK: 8, trendLimit: 20 },
          }),
        });

        const payload = await response.json();
        if (!isActive || payload.errors) return;
        setResults(payload.data?.backtestResults ?? []);
        setDrift(payload.data?.driftMetrics ?? null);
        setFeatures(payload.data?.featureImportances ?? []);
        setFeatureTrend(payload.data?.featureImportanceTrend ?? []);
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

  const trendSeries = useMemo(() => {
    if (!featureTrend.length) return [];
    const latest = featureTrend[featureTrend.length - 1];
    const names = latest.features.slice(0, 3).map((item) => item.name);
    const timestamps = featureTrend.map((entry) => entry.timestamp);

    return names.map((name) => ({
      name,
      x: timestamps,
      y: featureTrend.map((entry) => {
        const match = entry.features.find((item) => item.name === name);
        return match ? match.importance : null;
      }),
    }));
  }, [featureTrend]);

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
            {features.length === 0 ? (
              <div className="panel-outline px-4 py-3">No importances available.</div>
            ) : (
              features.map((item) => (
                <div key={item.name} className="panel-outline px-4 py-3">
                  <div className="flex items-center justify-between">
                    <span className="text-white">{item.name}</span>
                    <span className="text-xs text-muted">{item.importance.toFixed(4)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Feature Drift</p>
            <h2 className="mt-2 text-xl font-semibold">Top Feature Importance Trend</h2>
          </div>
          <span className="text-sm text-muted">
            {featureTrend.length ? `${featureTrend.length} runs` : "No history"}
          </span>
        </div>

        {trendSeries.length ? (
          <div className="mt-6 panel-outline overflow-hidden p-4">
            <Plot
              data={trendSeries.map((series) => ({
                x: series.x,
                y: series.y,
                type: "scatter",
                mode: "lines+markers",
                name: series.name,
              }))}
              layout={{
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#e6edf3" },
                xaxis: { title: "Run", showgrid: false },
                yaxis: { title: "Importance", gridcolor: "rgba(255,255,255,0.08)" },
                margin: { l: 50, r: 20, t: 20, b: 40 },
                showlegend: true,
              }}
              style={{ width: "100%", height: "360px" }}
            />
          </div>
        ) : (
          <div className="mt-6 panel-outline px-6 py-10 text-center text-muted">
            No feature importance history logged yet.
          </div>
        )}
      </div>
    </section>
  );
}
