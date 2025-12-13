// app/layout.tsx
import './globals.css'; // your global CSS / Tailwind import
import Link from 'next/link';

export const metadata = {
  title: 'AI Stock Predictor',
  description: 'Live stock predictions with AI',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <header className="bg-white shadow-md p-4">
          <nav className="flex justify-between items-center max-w-6xl mx-auto">
            <h1 className="text-xl font-bold">AI Stock Predictor</h1>
            <ul className="flex space-x-4">
              <li>
                <Link href="/" className="hover:underline">Home</Link>
              </li>
              <li>
                <Link href="/dashboard" className="hover:underline">Dashboard</Link>
              </li>
              <li>
                <Link href="/about" className="hover:underline">About</Link>
              </li>
            </ul>
          </nav>
        </header>

        <main className="max-w-6xl mx-auto p-8">
          {children}
        </main>

        <footer className="bg-white shadow-inner p-4 mt-8 text-center text-sm text-gray-500">
          &copy; 2025 AI Stock Predictor
        </footer>
      </body>
    </html>
  );
}
