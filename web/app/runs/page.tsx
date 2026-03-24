'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { runs as runsApi } from '@/lib/api';
import RunList from '@/components/RunList';

const STATUSES = ['all', 'running', 'completed', 'error', 'cancelled'];

export default function RunsPage() {
  const [filter, setFilter] = useState('all');

  const { data: runList = [], isLoading } = useQuery({
    queryKey: ['runs', filter],
    queryFn: () => runsApi.list(filter === 'all' ? undefined : filter),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Run History</h1>

      <div className="flex gap-2">
        {STATUSES.map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${
              filter === s
                ? 'bg-indigo-600 text-white'
                : 'bg-white border border-slate-300 text-slate-600 hover:bg-slate-50'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-400">Loading…</p>
      ) : (
        <RunList runs={runList} emptyMessage={`No ${filter === 'all' ? '' : filter + ' '}runs found.`} />
      )}
    </div>
  );
}
