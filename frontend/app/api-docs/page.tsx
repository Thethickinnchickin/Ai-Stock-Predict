"use client";

export default function ApiDocsPage() {
  return (
    <section className="space-y-10">
      <div className="flex flex-col gap-4">
        <p className="text-xs uppercase tracking-[0.35em] text-muted">API Docs</p>
        <h1 className="text-4xl font-semibold">GraphQL Interface</h1>
        <p className="text-muted">
          The backend exposes a single GraphQL endpoint for predictions, live
          prices, backtest results, and drift monitoring. Use these examples to
          explore the API quickly.
        </p>
      </div>

      <div className="panel p-6 space-y-6">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Endpoints</p>
          <div className="mt-3 grid gap-3 text-sm text-muted">
            <div className="panel-outline px-4 py-3">
              <span className="font-mono">POST /api/graphql</span>
              <span className="ml-3 text-xs text-muted">GraphQL endpoint</span>
            </div>
            <div className="panel-outline px-4 py-3">
              <span className="font-mono">GET /api/health</span>
              <span className="ml-3 text-xs text-muted">System health snapshot</span>
            </div>
          </div>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Predict Stock</p>
          <pre className="mt-3 panel-outline overflow-x-auto px-4 py-3 text-xs text-muted">
{`query PredictStock($symbol: String!) {
  predictStock(symbol: $symbol) {
    actual { dates prices }
    predicted { dates prices high low }
  }
}`}
          </pre>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Live Prices</p>
          <pre className="mt-3 panel-outline overflow-x-auto px-4 py-3 text-xs text-muted">
{`query LivePrices {
  livePrices(symbols: ["AAPL", "NVDA", "TSLA"]) {
    symbol
    price
    changePercent
    volume
  }
}`}
          </pre>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Backtest Results</p>
          <pre className="mt-3 panel-outline overflow-x-auto px-4 py-3 text-xs text-muted">
{`query Backtests {
  backtestResults(limit: 10) {
    timestamp
    maeModel
    maeBaseline
    directionalAccuracyModel
    directionalAccuracyBaseline
    validationSize
  }
}`}
          </pre>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Drift Metrics</p>
          <pre className="mt-3 panel-outline overflow-x-auto px-4 py-3 text-xs text-muted">
{`query Drift {
  driftMetrics(window: 5) {
    window
    recentMae
    priorMae
    delta
    status
  }
}`}
          </pre>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">cURL Example</p>
          <pre className="mt-3 panel-outline overflow-x-auto px-4 py-3 text-xs text-muted">
{`curl -k https://localhost/api/graphql \\
  -H "Content-Type: application/json" \\
  -d '{"query":"query { livePrices(symbols: [\\"AAPL\\"]) { symbol price } }"}'`}
          </pre>
        </div>
      </div>
    </section>
  );
}
