"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";

const Plot = dynamic(() => import("react-plotly.js"), { ssr: false });

const STOCKS = ["AAPL", "TSLA", "NVDA"];

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

    fetch("http://localhost:8000/graphql", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        variables: { symbol },
      }),
    })
      .then(res => res.json())
      .then(resData => {
        if (resData.errors) throw new Error(resData.errors[0].message);
        setData(resData.data.predictStock);
      })
      .catch(err => console.error(err));
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
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-3xl mb-6 text-yellow-400">
        Stock Prediction Dashboard
      </h1>

      <select
        className="bg-gray-700 px-4 py-2 rounded mb-6"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
      >
        <option value="" disabled>Select stock</option>
        {STOCKS.map(s => (
          <option key={s} value={s}>{s}</option>
        ))}
      </select>

      {data && combinedPrediction && (
        <Plot
          data={[
            {
              x: data.actual.dates,
              y: data.actual.prices,
              type: "scatter",
              mode: "lines",
              name: "Actual",
            },
            {
              x: combinedPrediction.dates,
              y: combinedPrediction.prices,
              type: "scatter",
              mode: "lines",
              name: "Predicted",
              line: { dash: "dash", color: "yellow" },
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
              opacity: 0.3,
            },
          ]}
          layout={{
            paper_bgcolor: "#111827",
            plot_bgcolor: "#111827",
            font: { color: "white" },
            hovermode: "x unified",
            xaxis: { title: "Date" },
            yaxis: { title: "Price ($)" },
          }}
          style={{ width: "100%", height: "500px" }}
        />
      )}
    </div>
  );
}
