// app/about/page.tsx
export default function AboutPage() {
  return (
    <section className="grid gap-10 lg:grid-cols-[1fr_1fr]">
      <div className="space-y-5">
        <p className="text-xs uppercase tracking-[0.35em] text-muted">About</p>
        <h1 className="text-4xl font-semibold">Built for market clarity</h1>
        <p className="text-muted">
          AI Stock Predictor combines asynchronous data ingestion, Redis-backed
          caching, and ML inference into a single pipeline. The goal is to turn
          noisy price action into a clean, decision-ready signal.
        </p>
        <p className="text-muted">
          The backend uses FastAPI with Strawberry GraphQL, while the frontend
          focuses on high-contrast visualization for rapid scanning.
        </p>
      </div>

      <div className="panel p-6 space-y-6">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-muted">Core Pipeline</p>
          <h2 className="mt-2 text-xl font-semibold">Live data to forecasts</h2>
        </div>
        <div className="space-y-4 text-sm text-muted">
          <div className="panel-outline px-4 py-3">
            <p className="text-xs uppercase tracking-[0.25em] text-muted">Ingestion</p>
            <p className="mt-2">
              Streaming prices from Polygon.io with historical candles from Yahoo Finance.
            </p>
          </div>
          <div className="panel-outline px-4 py-3">
            <p className="text-xs uppercase tracking-[0.25em] text-muted">Model</p>
            <p className="mt-2">
              Global XGBoost model trained on cached daily prices and volumes.
            </p>
          </div>
          <div className="panel-outline px-4 py-3">
            <p className="text-xs uppercase tracking-[0.25em] text-muted">Delivery</p>
            <p className="mt-2">
              GraphQL endpoint returns actual + predicted series for charting.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
