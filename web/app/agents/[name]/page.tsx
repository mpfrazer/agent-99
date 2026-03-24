'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';
import { agents as agentsApi, runs as runsApi } from '@/lib/api';
import StreamingOutput from '@/components/StreamingOutput';
import RunList from '@/components/RunList';
import { useActiveRuns } from '@/app/providers';
import type { StartRunResponse } from '@/lib/types';

interface Props {
  params: { name: string };
}

export default function AgentDetailPage({ params }: Props) {
  const { name } = params;
  const { addRun } = useActiveRuns();

  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', name],
    queryFn: () => agentsApi.get(name),
  });

  const { data: agentRuns = [], refetch: refetchRuns } = useQuery({
    queryKey: ['runs', 'agent', name],
    queryFn: () => runsApi.list(),
    select: (runs) => runs.filter((r) => r.agent_name === name),
  });

  // Run form state
  const [input, setInput] = useState('');
  const [streamOverride, setStreamOverride] = useState<boolean | null>(null);
  const [modelOverride, setModelOverride] = useState('');
  const [temperatureOverride, setTemperatureOverride] = useState('');
  const [maxIterOverride, setMaxIterOverride] = useState('');
  const [showOverrides, setShowOverrides] = useState(false);

  // Active run
  const [activeRun, setActiveRun] = useState<StartRunResponse | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState('');

  const handleRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agent || !input.trim()) return;
    setError('');
    setStarting(true);
    try {
      const res = await runsApi.start({
        agent_name: name,
        user_input: input.trim(),
        stream: streamOverride ?? undefined,
        model: modelOverride || undefined,
        temperature: temperatureOverride ? parseFloat(temperatureOverride) : undefined,
        max_iterations: maxIterOverride ? parseInt(maxIterOverride) : undefined,
      });
      setActiveRun(res);
      addRun({
        id: res.run_id,
        agent_name: res.agent_name,
        status: 'running',
        started_at: new Date().toISOString(),
        completed_at: null,
        model: modelOverride || agent.model,
        user_input: input.trim(),
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start run');
    } finally {
      setStarting(false);
    }
  };

  const handleComplete = () => {
    setActiveRun(null);
    setInput('');
    refetchRuns();
  };

  if (isLoading) return <p className="text-sm text-slate-400">Loading…</p>;
  if (!agent) return <p className="text-sm text-red-500">Agent not found.</p>;

  const streamDefault = streamOverride ?? agent.stream_output;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{agent.name}</h1>
          {agent.description && <p className="text-sm text-slate-500 mt-0.5">{agent.description}</p>}
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{agent.model}</span>
            {agent.tools.map((t) => (
              <span key={t} className="text-xs bg-slate-50 text-slate-500 border border-slate-200 px-2 py-0.5 rounded">{t}</span>
            ))}
          </div>
        </div>
        <Link
          href={`/agents/${name}/edit`}
          className="px-3 py-1.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors shrink-0"
        >
          Edit
        </Link>
      </div>

      {/* Run form */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <form onSubmit={handleRun} className="space-y-4">
          {error && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">{error}</div>
          )}
          <div>
            <label className="text-sm font-medium text-slate-700 block mb-1">Input</label>
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="input font-mono h-28 resize-y"
              placeholder="Ask something or give a task…"
              disabled={!!activeRun}
            />
          </div>

          {/* Override toggles */}
          <div className="space-y-3">
            <div className="flex items-center gap-4">
              {/* Stream toggle */}
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={streamDefault}
                  onChange={(e) => setStreamOverride(e.target.checked)}
                  className="w-4 h-4 rounded text-indigo-600"
                  disabled={!!activeRun}
                />
                <span className="text-sm text-slate-600">Stream output live</span>
              </label>
              <button
                type="button"
                onClick={() => setShowOverrides((o) => !o)}
                className="text-xs text-indigo-500 hover:underline"
              >
                {showOverrides ? 'Hide overrides ▲' : 'Show overrides ▼'}
              </button>
            </div>

            {showOverrides && (
              <div className="grid grid-cols-3 gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-500">Model override</label>
                  <input
                    type="text"
                    value={modelOverride}
                    onChange={(e) => setModelOverride(e.target.value)}
                    className="input text-xs font-mono"
                    placeholder={agent.model}
                    disabled={!!activeRun}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-500">Temperature</label>
                  <input
                    type="number"
                    step="0.05" min="0" max="2"
                    value={temperatureOverride}
                    onChange={(e) => setTemperatureOverride(e.target.value)}
                    className="input text-xs"
                    placeholder={String(agent.temperature)}
                    disabled={!!activeRun}
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-500">Max iterations</label>
                  <input
                    type="number"
                    min="1"
                    value={maxIterOverride}
                    onChange={(e) => setMaxIterOverride(e.target.value)}
                    className="input text-xs"
                    placeholder={String(agent.max_iterations)}
                    disabled={!!activeRun}
                  />
                </div>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={!input.trim() || starting || !!activeRun}
            className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
          >
            {starting ? 'Starting…' : 'Run Agent'}
          </button>
        </form>
      </div>

      {/* Active run output */}
      {activeRun && (
        <StreamingOutput
          runId={activeRun.run_id}
          onComplete={handleComplete}
        />
      )}

      {/* Run history for this agent */}
      {agentRuns.length > 0 && (
        <div>
          <h2 className="font-semibold text-slate-900 mb-3">Recent runs</h2>
          <RunList runs={agentRuns.slice(0, 10)} />
        </div>
      )}
    </div>
  );
}
