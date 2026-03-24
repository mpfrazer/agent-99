import type { Metadata } from 'next';
import './globals.css';
import { Providers } from './providers';
import NavBar from '@/components/NavBar';
import ActiveRunsBar from '@/components/ActiveRunsBar';

export const metadata: Metadata = {
  title: 'agent-99',
  description: 'Lightweight local AI agent runner',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <Providers>
          <NavBar />
          <main className="flex-1 container mx-auto px-4 py-6 max-w-6xl">
            {children}
          </main>
          <ActiveRunsBar />
        </Providers>
      </body>
    </html>
  );
}
