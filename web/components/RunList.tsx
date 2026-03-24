'use client';

import Link from 'next/link';
import type { RunSummary } from '@/lib/types';

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: 'bg-indigo-100 text-indigo-700',
    completed: 'bg-emerald-100 text-emerald-700',
    cancelled: 'bg-slate-100 text-slate-600',
    error: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  );
}

function relativeTime(iso: string): string {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

interface Props {
  runs: RunSummary[];
  emptyMessage?: string;
}

export default function RunList({ runs, emptyMessage = 'No runs yet.' }: Props) {
  if (runs.length === 0) {
    return <p className="text-sm text-slate-400 py-8 text-center">{emptyMessage}</p>;
  }

  return (
    <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white overflow-hidden">
      {runs.map((run) => (
        <Link
          key={run.id}
          href={`/runs/${run.id}`}
          className="flex items-center gap-4 px-4 py-3 hover:bg-slate-50 transition-colors"
        >
          <StatusBadge status={run.status} />
          <span className="font-medium text-sm text-slate-800 w-32 shrink-0 truncate">
            {run.agent_name}
          </span>
          <span className="text-sm text-slate-500 font-mono truncate flex-1 min-w-0">
            {run.user_input}
          </span>
          <span className="text-xs text-slate-400 shrink-0">{run.model}</span>
          <span className="text-xs text-slate-400 shrink-0 w-20 text-right">
            {relativeTime(run.started_at)}
          </span>
        </Link>
      ))}
    </div>
  );
}
