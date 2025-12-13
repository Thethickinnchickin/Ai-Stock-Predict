"use client";

import { useEffect, useState } from "react";

export default function Dashboard() {
  const [symbol, setSymbol] = useState("AAPL");
  const [prediction, setPrediction] = useState<any>(null);
  const [currentPrice, setCurrentPrice] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);

  // Inputs for probability prediction
  const [targetPrice, setTargetPrice] = useState<number | null>(null);
  const [daysAhead, setDaysAhead] = useState<number>(5);
  const [simulations, setSimulations] = useState<number>(100);
  const [probability, setProbability] = useState<number | null>(null);

  // Fetch recent predictions
  async function fetchRecent() {
    try {
      const res = await fetch("http://localhost:8000/recent");
      if (!res.ok) throw new Error("Failed to fetch recent predictions");
      const data = await res.json();
      setRecent(data);
    } catch (err) {
      console.error("Error fetching recent:", err);
    }
  }

  // Fetch alerts
  async function fetchAlerts() {
    try {
      const res = await fetch("http://localhost:8000/alerts");
      if (!res.ok) throw new Error("Failed to fetch alerts");
      const data = await res.json();
      setAlerts(data);
    } catch (err) {
      console.error("Error fetching alerts:", err);
    }
  }

  // Fetch actual stock price
  async function fetchCurrentPrice(symbol: string) {
    try {
      const res = await fetch("http://localhost:8000/api/prices");
      if (!res.ok) throw new Error("Failed to fetch current prices");
      const data = await res.json();
      setCurrentPrice(data[symbol] ?? null);
    } catch (err) {
      console.error("Error fetching current price:", err);
      setCurrentPrice(null);
    }
  }

  // Predict a stock immediately
  async function handlePredict() {
    setLoading(true);
    setPrediction(null);
    setProbability(null);

    try {
      // 1️⃣ Run normal prediction
      const res = await fetch("http://localhost:8000/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol }),
      });
      if (!res.ok) throw new Error("Prediction failed");
      const data = await res.json();
      setPrediction(data);

      // 2️⃣ Run probability prediction if targetPrice is set
      if (targetPrice !== null) {
        const probRes = await fetch("http://localhost:8000/predict/probability", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol,
            target_price: targetPrice,
            steps: daysAhead,
            simulations,
          }),
        });
        if (!probRes.ok) throw new Error("Probability request failed");
        const probData = await probRes.json();
        setProbability(probData.probability);
      }

      // Fetch the current stock price and recent predictions
      await fetchCurrentPrice(symbol);
      fetchRecent();
    } catch (err) {
      console.error("Prediction error:", err);
    } finally {
      setLoading(false);
    }
  }

  // Auto-refresh recent predictions and alerts
  useEffect(() => {
    fetchRecent();
    fetchAlerts();

    const interval = setInterval(() => {
      fetchRecent();
      fetchAlerts();
      fetchCurrentPrice(symbol);
    }, 5000);

    return () => clearInterval(interval);
  }, [symbol]);

  return (
    <div className="p-8 space-y-10 max-w-5xl mx-auto">
      <h1 className="text-4xl font-extrabold text-gradient bg-clip-text bg-gradient-to-r from-blue-500 to-purple-600">
        📊 AI Stock Predictor Dashboard
      </h1>

      {/* Predictor */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6 rounded-xl shadow-lg hover:shadow-2xl transition-shadow duration-300">
        <h2 className="text-2xl font-semibold mb-4">Predict Stock</h2>
        <div className="flex flex-wrap gap-4 items-end">
          <div className="flex flex-col">
            <label className="mb-1 font-medium text-gray-700 dark:text-gray-300">Symbol</label>
            <input
              type="text"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="border p-3 rounded-lg w-40 focus:ring-2 focus:ring-blue-400 focus:outline-none"
              placeholder="AAPL"
            />
          </div>

          <div className="flex flex-col">
            <label className="mb-1 font-medium text-gray-700 dark:text-gray-300">Target Price</label>
            <input
              type="number"
              value={targetPrice ?? ""}
              onChange={(e) => setTargetPrice(e.target.value ? Number(e.target.value) : null)}
              className="border p-3 rounded-lg w-40 focus:ring-2 focus:ring-green-400 focus:outline-none"
              placeholder="e.g. 300"
            />
          </div>

          <div className="flex flex-col">
            <label className="mb-1 font-medium text-gray-700 dark:text-gray-300">Days Ahead</label>
            <input
              type="number"
              value={daysAhead}
              onChange={(e) => setDaysAhead(Number(e.target.value))}
              className="border p-3 rounded-lg w-32 focus:ring-2 focus:ring-yellow-400 focus:outline-none"
              placeholder="e.g. 5"
            />
          </div>

          <div className="flex flex-col">
            <label className="mb-1 font-medium text-gray-700 dark:text-gray-300">Simulations</label>
            <input
              type="number"
              value={simulations}
              onChange={(e) => setSimulations(Number(e.target.value))}
              className="border p-3 rounded-lg w-32 focus:ring-2 focus:ring-purple-400 focus:outline-none"
              placeholder="e.g. 100"
            />
          </div>

          <button
            onClick={handlePredict}
            disabled={loading}
            className="bg-gradient-to-r from-blue-500 to-purple-500 text-white px-6 py-3 rounded-lg shadow-lg hover:scale-105 transform transition-all duration-200 disabled:opacity-50"
          >
            {loading ? "Predicting..." : "Predict"}
          </button>
        </div>

        {prediction && (
          <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-inner">
            <h3 className="text-lg font-bold mb-2 text-blue-600 dark:text-blue-400">
              Prediction Result
            </h3>
            <p><strong>Symbol:</strong> {prediction.symbol}</p>
            <p><strong>Current Price:</strong> ${currentPrice ?? "N/A"}</p>
            <p><strong>Predicted Price:</strong> ${prediction.predicted_price}</p>
            <p><strong>Confidence:</strong> {Math.round(prediction.confidence * 100)}%</p>
            {probability !== null && (
              <p><strong>Probability to reach ${targetPrice} in {daysAhead} days:</strong> {Math.round(probability * 100)}%</p>
            )}
          </div>
        )}
      </div>

      {/* Recent Predictions */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300">
        <h2 className="text-2xl font-semibold mb-4">🕒 Recent Predictions</h2>
        {recent.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-300">No predictions yet.</p>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {recent.map((item, i) => (
              <li key={i} className="py-2 flex justify-between hover:bg-gray-100 dark:hover:bg-gray-700 rounded px-2">
                <span>{item.symbol}</span>
                <span className="font-semibold">${item.predicted_price}</span>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  ({Math.round(item.confidence * 100)}%)
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Alerts */}
      <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 p-6 rounded-xl shadow-lg hover:shadow-xl transition-shadow duration-300">
        <h2 className="text-2xl font-semibold mb-4 text-red-600 dark:text-red-400">🚨 Active Alerts</h2>
        {alerts.length === 0 ? (
          <p className="text-gray-500 dark:text-gray-300">No active alerts.</p>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {alerts.map((alert, i) => (
              <li key={i} className="py-2 px-2 text-red-700 dark:text-red-400 font-medium hover:bg-red-50 dark:hover:bg-red-800 rounded">
                {alert.symbol}: {alert.message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
