'use client';

import Link from 'next/link';
import { useActiveRuns } from '@/app/providers';
import { usePathname } from 'next/navigation';

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: 'bg-indigo-500 animate-pulse',
    completed: 'bg-emerald-500',
    cancelled: 'bg-slate-400',
    error: 'bg-red-500',
  };
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] ?? 'bg-slate-400'}`} />;
}

export default function ActiveRunsBar() {
  const { activeRuns, cancelRun } = useActiveRuns();
  const pathname = usePathname();

  if (pathname === '/login') return null;
  if (activeRuns.size === 0) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 z-50 bg-white border-t border-slate-200 shadow-lg">
      <div className="container mx-auto px-4 max-w-6xl">
        <div className="flex items-center gap-4 h-12 overflow-x-auto">
          <span className="text-xs font-medium text-slate-500 shrink-0">Active runs:</span>
          {Array.from(activeRuns.values()).map((run) => (
            <div
              key={run.id}
              className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-full px-3 py-1 shrink-0"
            >
              <StatusDot status={run.status} />
              <Link
                href={`/runs/${run.id}`}
                className="text-xs font-medium text-slate-700 hover:text-indigo-600 transition-colors"
              >
                {run.agent_name}
              </Link>
              {run.status === 'running' && (
                <button
                  onClick={() => cancelRun(run.id)}
                  className="text-xs text-slate-400 hover:text-red-500 transition-colors ml-1"
                  title="Cancel"
                >
                  ✕
                </button>
              )}
              {run.status !== 'running' && (
                <span className="text-xs text-slate-400 capitalize">{run.status}</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
