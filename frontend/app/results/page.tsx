"use client";

import { useEffect, useState } from "react";

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

type DriftMetrics = {
  window: number;
  recentMae: number | null;
  priorMae: number | null;
  delta: number | null;
  status: string;
};

export default function ResultsPage() {
  const [results, setResults] = useState<BacktestResult[]>([]);
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
          body: JSON.stringify({
            query,
            variables: { limit: 30, window: 5 },
          }),
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

  const latest = results[results.length - 1];

  return (
    <section className="space-y-10">
      <div className="flex flex-col gap-4">
        <p className="text-xs uppercase tracking-[0.35em] text-muted">Results</p>
        <h1 className="text-4xl font-semibold">Backtest Performance</h1>
        <p className="text-muted">
          Nightly walk-forward backtests compare the model against a naive
          baseline. Use this to track accuracy trends over time.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="panel p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-muted">Latest Run</p>
              <h2 className="mt-2 text-xl font-semibold">Model vs Baseline</h2>
            </div>
            <span className="text-sm text-muted">
              {latest ? latest.timestamp : "No data yet"}
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
              No backtest results logged yet. The first entry will appear after
              tonight’s run.
            </div>
          )}
        </div>

        <div className="panel p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Trend Snapshot</p>
          <h2 className="mt-2 text-xl font-semibold">Recent Runs</h2>
          <div className="mt-6 space-y-3 text-sm text-muted">
            {results.length === 0 ? (
              <p>No history yet.</p>
            ) : (
              results
                .slice()
                .reverse()
                .map((entry) => (
                  <div
                    key={entry.timestamp}
                    className="panel-outline flex items-center justify-between px-4 py-3"
                  >
                    <span className="font-mono text-xs">{entry.timestamp}</span>
                    <span className="text-accent">
                      MAE {entry.maeModel.toFixed(4)}
                    </span>
                  </div>
                ))
            )}
          </div>
        </div>
      </div>

      <div className="panel p-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Model Drift</p>
            <h2 className="mt-2 text-xl font-semibold">Accuracy Trend</h2>
          </div>
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
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Recent MAE</p>
            <p className="mt-2 text-2xl font-semibold text-accent">
              {drift?.recentMae !== null && drift?.recentMae !== undefined
                ? drift.recentMae.toFixed(4)
                : "—"}
            </p>
          </div>
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Prior MAE</p>
            <p className="mt-2 text-2xl font-semibold text-accent">
              {drift?.priorMae !== null && drift?.priorMae !== undefined
                ? drift.priorMae.toFixed(4)
                : "—"}
            </p>
          </div>
          <div className="panel-outline px-4 py-4">
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Delta</p>
            <p className="mt-2 text-2xl font-semibold text-accent">
              {drift?.delta !== null && drift?.delta !== undefined
                ? drift.delta.toFixed(4)
                : "—"}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
