'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { agents as agentsApi, runs as runsApi } from '@/lib/api';
import RunList from '@/components/RunList';

export default function DashboardPage() {
  const { data: agentList = [] } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list,
  });

  const { data: recentRuns = [] } = useQuery({
    queryKey: ['runs', 'recent'],
    queryFn: () => runsApi.list(),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {agentList.length} agent{agentList.length !== 1 ? 's' : ''} available
          </p>
        </div>
        <Link
          href="/agents/new"
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
        >
          + New Agent
        </Link>
      </div>

      {/* Agent grid */}
      {agentList.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {agentList.map((agent) => (
            <Link
              key={agent.name}
              href={`/agents/${agent.name}`}
              className="bg-white rounded-xl border border-slate-200 p-5 hover:border-indigo-300 hover:shadow-sm transition-all group"
            >
              <div className="flex items-start justify-between mb-3">
                <span className="font-semibold text-slate-900 group-hover:text-indigo-700 transition-colors">
                  {agent.name}
                </span>
                {agent.stream_output && (
                  <span className="text-xs bg-indigo-50 text-indigo-600 px-2 py-0.5 rounded-full">
                    streaming
                  </span>
                )}
              </div>
              {agent.description && (
                <p className="text-sm text-slate-500 mb-3 line-clamp-2">{agent.description}</p>
              )}
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                  {agent.model}
                </span>
                {agent.tools.slice(0, 3).map((t) => (
                  <span key={t} className="text-xs bg-slate-50 text-slate-500 px-2 py-0.5 rounded border border-slate-200">
                    {t}
                  </span>
                ))}
                {agent.tools.length > 3 && (
                  <span className="text-xs text-slate-400">+{agent.tools.length - 3}</span>
                )}
              </div>
            </Link>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
          <p className="text-slate-500 mb-4">No agents yet.</p>
          <Link
            href="/agents/new"
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Create your first agent
          </Link>
        </div>
      )}

      {/* Recent runs */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold text-slate-900">Recent Runs</h2>
          <Link href="/runs" className="text-sm text-indigo-600 hover:underline">
            View all →
          </Link>
        </div>
        <RunList runs={recentRuns.slice(0, 5)} emptyMessage="No runs yet. Pick an agent and run it." />
      </div>
    </div>
  );
}
