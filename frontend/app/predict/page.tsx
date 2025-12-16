"use client";

import { useState } from "react";

const STOCKS = ["AAPL", "TSLA", "NVDA"];

const PredictPage = () => {
  const [symbol, setSymbol] = useState<string | null>(null);

  const imgUrl = symbol
    ? `http://localhost:8000/predict/plot/${symbol}`
    : null;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-gradient-to-b from-gray-900 to-gray-800 text-white p-6">
      <h1 className="text-4xl font-extrabold mb-6 tracking-tight text-yellow-400">
        Stock Prediction Dashboard
      </h1>

      {/* Dropdown */}
      <div className="mb-8">
        <select
          value={symbol || ""}
          onChange={(e) => setSymbol(e.target.value)}
          className="bg-gray-700 text-white px-4 py-2 rounded-lg shadow-lg focus:outline-none focus:ring-2 focus:ring-yellow-400 transition"
        >
          <option value="" disabled>
            Select a stock
          </option>
          {STOCKS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {/* Chart */}
      {symbol && imgUrl ? (
        <div className="w-full max-w-4xl bg-gray-900 rounded-2xl shadow-2xl p-4">
          <h2 className="text-xl font-semibold mb-2 text-center text-yellow-300">
            {symbol} — Prediction vs Actual
          </h2>
          <img
            src={imgUrl}
            alt={`${symbol} prediction chart`}
            className="w-full h-auto rounded-xl border border-gray-700 shadow-md"
          />
        </div>
      ) : (
        <p className="text-gray-300 text-lg mt-4">Please select a stock to see the chart.</p>
      )}
    </div>
  );
};

export default PredictPage;
