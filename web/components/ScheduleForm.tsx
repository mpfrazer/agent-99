'use client';

import { useState, useEffect } from 'react';
import type { AgentSummary, Schedule, SchedulePayload, ScheduleMode, IntervalUnit } from '@/lib/types';

interface Props {
  agents: AgentSummary[];
  initial?: Schedule;
  onSubmit: (payload: SchedulePayload) => void;
  onCancel: () => void;
  isSubmitting?: boolean;
}

export default function ScheduleForm({ agents, initial, onSubmit, onCancel, isSubmitting }: Props) {
  const [agentName, setAgentName] = useState(initial?.agent_name ?? agents[0]?.name ?? '');
  const [prompt, setPrompt] = useState(initial?.prompt ?? '');
  const [mode, setMode] = useState<ScheduleMode>(initial?.mode ?? 'interval');

  // interval mode
  const [intervalValue, setIntervalValue] = useState(String(initial?.interval_value ?? '30'));
  const [intervalUnit, setIntervalUnit] = useState<IntervalUnit>(initial?.interval_unit ?? 'minutes');

  // daily mode
  const [dailyTime, setDailyTime] = useState(initial?.daily_time ?? '09:00');
  const [everyNDays, setEveryNDays] = useState(String(initial?.every_n_days ?? '1'));

  const [error, setError] = useState<string | null>(null);

  // Show prompt reuse notice when editing
  const isEdit = !!initial;

  useEffect(() => {
    if (initial) {
      setAgentName(initial.agent_name);
      setPrompt(initial.prompt);
      setMode(initial.mode);
      setIntervalValue(String(initial.interval_value ?? '30'));
      setIntervalUnit(initial.interval_unit ?? 'minutes');
      setDailyTime(initial.daily_time ?? '09:00');
      setEveryNDays(String(initial.every_n_days ?? '1'));
    }
  }, [initial]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    const payload: SchedulePayload = {
      agent_name: agentName,
      prompt,
      mode,
    };

    if (mode === 'interval') {
      const val = parseInt(intervalValue, 10);
      if (!val || val < 1) { setError('Interval value must be a positive integer.'); return; }
      payload.interval_value = val;
      payload.interval_unit = intervalUnit;
    } else {
      const n = parseInt(everyNDays, 10);
      if (!n || n < 1) { setError('Every N days must be a positive integer.'); return; }
      payload.daily_time = dailyTime;
      payload.every_n_days = n;
    }

    onSubmit(payload);
  }

  const inputCls = 'w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500';
  const labelCls = 'block text-sm font-medium text-slate-700 mb-1';

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {/* Agent */}
      <div>
        <label className={labelCls}>Agent</label>
        <select
          value={agentName}
          onChange={e => setAgentName(e.target.value)}
          className={inputCls}
          required
        >
          {agents.map(a => (
            <option key={a.name} value={a.name}>{a.name}</option>
          ))}
        </select>
      </div>

      {/* Prompt */}
      <div>
        <label className={labelCls}>Prompt</label>
        {isEdit && (
          <p className="text-xs text-amber-600 mb-1">
            Note: this same prompt will be used for every scheduled execution.
          </p>
        )}
        {!isEdit && (
          <p className="text-xs text-slate-500 mb-1">
            This same prompt will be sent to the agent on every scheduled execution.
          </p>
        )}
        <textarea
          value={prompt}
          onChange={e => setPrompt(e.target.value)}
          rows={3}
          className={inputCls}
          placeholder="What should the agent do each time it runs?"
          required
        />
      </div>

      {/* Mode toggle */}
      <div>
        <label className={labelCls}>Schedule mode</label>
        <div className="flex gap-2">
          {(['interval', 'daily'] as ScheduleMode[]).map(m => (
            <button
              key={m}
              type="button"
              onClick={() => setMode(m)}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                mode === m
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
            >
              {m === 'interval' ? 'Interval' : 'Daily'}
            </button>
          ))}
        </div>
      </div>

      {/* Interval fields */}
      {mode === 'interval' && (
        <div className="flex gap-3">
          <div className="flex-1">
            <label className={labelCls}>Every</label>
            <input
              type="number"
              min={1}
              value={intervalValue}
              onChange={e => setIntervalValue(e.target.value)}
              className={inputCls}
              required
            />
          </div>
          <div className="flex-1">
            <label className={labelCls}>Unit</label>
            <select
              value={intervalUnit}
              onChange={e => setIntervalUnit(e.target.value as IntervalUnit)}
              className={inputCls}
            >
              <option value="minutes">Minutes</option>
              <option value="hours">Hours</option>
              <option value="days">Days</option>
            </select>
          </div>
        </div>
      )}

      {/* Daily fields */}
      {mode === 'daily' && (
        <div className="flex gap-3">
          <div className="flex-1">
            <label className={labelCls}>Time (HH:MM)</label>
            <input
              type="time"
              value={dailyTime}
              onChange={e => setDailyTime(e.target.value)}
              className={inputCls}
              required
            />
          </div>
          <div className="flex-1">
            <label className={labelCls}>Every N days</label>
            <input
              type="number"
              min={1}
              value={everyNDays}
              onChange={e => setEveryNDays(e.target.value)}
              className={inputCls}
              required
            />
          </div>
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex gap-2 pt-1">
        <button
          type="submit"
          disabled={isSubmitting}
          className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {isSubmitting ? 'Saving…' : isEdit ? 'Update Schedule' : 'Create Schedule'}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
