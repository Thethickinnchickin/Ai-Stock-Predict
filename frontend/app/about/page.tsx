// app/about/page.tsx
export default function AboutPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-4">About This App</h1>
      <p>
        This stock prediction app uses AI and live market data to provide alerts
        and predictions. Built with FastAPI, Redis, and Polygon.io for backend,
        and Next.js for the frontend.
      </p>
    </div>
  );
}
