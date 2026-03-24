'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { runs as runsApi } from '@/lib/api';
import StreamingOutput from '@/components/StreamingOutput';
import { useActiveRuns } from '@/app/providers';

interface Props {
  params: { id: string };
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    running: 'bg-indigo-100 text-indigo-700',
    completed: 'bg-emerald-100 text-emerald-700',
    cancelled: 'bg-slate-100 text-slate-600',
    error: 'bg-red-100 text-red-700',
  };
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${styles[status] ?? 'bg-slate-100 text-slate-600'}`}>
      {status}
    </span>
  );
}

export default function RunDetailPage({ params }: Props) {
  const { id } = params;
  const { activeRuns, cancelRun } = useActiveRuns();
  const activeRun = activeRuns.get(id);

  const { data: run, isLoading } = useQuery({
    queryKey: ['run', id],
    queryFn: () => runsApi.get(id),
    refetchInterval: activeRun ? undefined : false,
  });

  if (isLoading) return <p className="text-sm text-slate-400">Loading…</p>;
  if (!run && !activeRun) return <p className="text-sm text-red-500">Run not found.</p>;

  const isRunning = activeRun?.status === 'running' || run?.status === 'running';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <Link href="/runs" className="text-sm text-slate-400 hover:text-slate-600">← Runs</Link>
            <StatusBadge status={activeRun?.status ?? run?.status ?? 'unknown'} />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">
            {run?.agent_name ?? activeRun?.agent_name}
          </h1>
          <p className="text-xs text-slate-400 font-mono">{id}</p>
        </div>
        {isRunning && (
          <button
            onClick={() => cancelRun(id)}
            className="px-4 py-2 rounded-lg border border-red-200 text-sm text-red-600 hover:bg-red-50 transition-colors"
          >
            Cancel
          </button>
        )}
      </div>

      {/* Meta */}
      {run && (
        <div className="bg-white rounded-xl border border-slate-200 p-4 grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Agent</p>
            <Link href={`/agents/${run.agent_name}`} className="text-indigo-600 hover:underline font-medium">
              {run.agent_name}
            </Link>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Model</p>
            <p className="font-mono text-slate-700">{run.model}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Started</p>
            <p className="text-slate-700">{run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</p>
          </div>
          <div>
            <p className="text-xs text-slate-400 mb-0.5">Completed</p>
            <p className="text-slate-700">{run.completed_at ? new Date(run.completed_at).toLocaleString() : '—'}</p>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <p className="text-xs font-medium text-slate-400 mb-2">Input</p>
        <pre className="text-sm font-mono text-slate-800 whitespace-pre-wrap">
          {run?.user_input ?? activeRun?.user_input}
        </pre>
      </div>

      {/* Output — stream if active, static if completed */}
      {isRunning ? (
        <StreamingOutput
          runId={id}
          initialEvents={run?.events ?? []}
        />
      ) : (
        run && (
          <div className="rounded-xl border border-slate-200 bg-white">
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
              <span className="text-xs font-medium text-slate-500">Output</span>
              <StatusBadge status={run.status} />
            </div>
            <div className="p-4">
              {run.error && (
                <p className="text-sm text-red-500 mb-2">{run.error}</p>
              )}
              {run.tool_calls?.length > 0 && (
                <div className="mb-4 space-y-2">
                  {run.tool_calls.map((tc, i) => (
                    <details key={i} className="border border-indigo-100 rounded-lg overflow-hidden text-sm">
                      <summary className="px-3 py-2 bg-indigo-50 cursor-pointer font-mono font-medium text-indigo-700">
                        {tc.name}
                      </summary>
                      <div className="p-3 space-y-2">
                        <pre className="text-xs text-slate-600 whitespace-pre-wrap">
                          {JSON.stringify(tc.arguments, null, 2)}
                        </pre>
                        {tc.result && (
                          <pre className="text-xs text-slate-700 whitespace-pre-wrap border-t pt-2">
                            {tc.result}
                          </pre>
                        )}
                      </div>
                    </details>
                  ))}
                </div>
              )}
              <pre className="whitespace-pre-wrap font-mono text-sm text-slate-800 leading-relaxed">
                {run.final_output}
              </pre>
            </div>
          </div>
        )
      )}
    </div>
  );
}
