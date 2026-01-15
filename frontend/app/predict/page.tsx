"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const STOCKS = ["AAPL", "TSLA", "NVDA"];
const GRAPHQL_URL =
  typeof window !== "undefined"
    ? "/api/graphql"
    : process.env.NEXT_PUBLIC_GRAPHQL_URL || "http://localhost:8000/graphql";

type PriceSeries = {
  dates: string[];
  prices: number[];
};

type PredictedSeries = {
  dates: string[];
  prices: number[];
  high: number[];
  low: number[];
};

type PredictionResponse = {
  actual: PriceSeries;
  predicted: PredictedSeries;
};

export default function PredictPage() {
  const [symbol, setSymbol] = useState<string>("");
  const [data, setData] = useState<PredictionResponse | null>(null);

  useEffect(() => {
    if (!symbol) return;

    let socket: WebSocket | null = null;
    let isActive = true;

    const fetchOnce = () => {
      const query = `
        query StockPrediction($symbol: String!) {
          predictStock(symbol: $symbol) {
            actual {
              dates
              prices
            }
            predicted {
              dates
              prices
              high
              low
            }
          }
        }
      `;

      fetch(GRAPHQL_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query,
          variables: { symbol },
        }),
      })
        .then((res) => res.json())
        .then((resData) => {
          if (resData.errors) throw new Error(resData.errors[0].message);
          if (isActive) setData(resData.data.predictStock);
        })
        .catch((err) => console.error(err));
    };

    const connectSocket = () => {
      const protocol = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(
        `${protocol}://${window.location.host}/api/ws/predict/${symbol}`
      );
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data);
          if (payload.error) return;
          if (isActive) setData(payload);
        } catch (err) {
          console.error("Prediction socket parse error", err);
        }
      };
      socket.onerror = () => {
        fetchOnce();
      };
      socket.onclose = () => {
        if (isActive) {
          setTimeout(connectSocket, 3000);
        }
      };
    };

    connectSocket();
    fetchOnce();

    return () => {
      isActive = false;
      if (socket) socket.close();
    };
  }, [symbol]);

  // Merge last actual price with predicted for a continuous line
  const getCombinedPrediction = () => {
    if (!data) return null;

    const lastActualDate = data.actual.dates[data.actual.dates.length - 1];
    const lastActualPrice = data.actual.prices[data.actual.prices.length - 1];

    return {
      dates: [lastActualDate, ...data.predicted.dates],
      prices: [lastActualPrice, ...data.predicted.prices],
      high: [lastActualPrice, ...data.predicted.high],
      low: [lastActualPrice, ...data.predicted.low],
    };
  };

  const combinedPrediction = getCombinedPrediction();

  return (
    <div className="space-y-10">
      <div className="flex flex-col gap-4">
        <p className="text-xs uppercase tracking-[0.35em] text-muted">Predictions</p>
        <h1 className="text-4xl font-semibold">Stock Forecast Workspace</h1>
        <p className="text-muted">
          Select a symbol to visualize historical performance and the model’s
          forecast band for the next trading sessions.
        </p>
      </div>

      <div className="panel flex flex-col gap-6 p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-muted">Tracked Symbols</p>
            <h2 className="mt-2 text-xl font-semibold">Market Selection</h2>
          </div>
          <div className="panel-outline flex items-center gap-3 px-4 py-2">
            <span className="text-xs uppercase tracking-[0.2em] text-muted">Ticker</span>
            <select
              className="bg-slate-950/80 text-sm font-semibold text-white outline-none"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            >
              <option value="" disabled>Select stock</option>
              {STOCKS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="panel-outline flex flex-wrap items-center justify-between gap-4 px-4 py-3 text-sm text-muted">
          <span className="font-mono">Model: Global XGBoost</span>
          <span className="font-mono">Window: {data?.actual.dates.length ?? 0} days</span>
          <span className="font-mono">Forecast: 5 trading days</span>
        </div>

        {data && combinedPrediction ? (
          <div className="panel-outline overflow-hidden p-4">
            <Plot
              data={[
                {
                  x: data.actual.dates,
                  y: data.actual.prices,
                  type: "scatter",
                  mode: "lines",
                  name: "Actual",
                  line: { color: "#66c2ff", width: 2 },
                },
                {
                  x: combinedPrediction.dates,
                  y: combinedPrediction.prices,
                  type: "scatter",
                  mode: "lines",
                  name: "Predicted",
                  line: { dash: "dash", color: "#39d98a", width: 2 },
                },
                {
                  x: combinedPrediction.dates,
                  y: combinedPrediction.high,
                  type: "scatter",
                  mode: "lines",
                  name: "High",
                  line: { width: 0 },
                  showlegend: false,
                },
                {
                  x: combinedPrediction.dates,
                  y: combinedPrediction.low,
                  type: "scatter",
                  mode: "lines",
                  fill: "tonexty",
                  name: "Low",
                  opacity: 0.25,
                  line: { width: 0 },
                },
              ]}
              layout={{
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#e6edf3" },
                hoverlabel: {
                  font: { color: "#000000" },
                },
                hovermode: "x unified",
                xaxis: { title: "Date", showgrid: false },
                yaxis: { title: "Price ($)", gridcolor: "rgba(255,255,255,0.08)" },
                margin: { l: 50, r: 20, t: 20, b: 40 },
              }}
              style={{ width: "100%", height: "520px" }}
            />
          </div>
        ) : (
          <div className="panel-outline flex flex-col items-center gap-3 px-6 py-16 text-center text-muted">
            <p className="text-sm font-semibold text-accent">Awaiting symbol selection</p>
            <p className="text-sm">
              Choose a ticker above to render the AI forecast.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
