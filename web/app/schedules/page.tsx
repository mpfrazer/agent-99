'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { agents as agentsApi, schedules as schedulesApi } from '@/lib/api';
import type { Schedule, SchedulePayload } from '@/lib/types';
import ScheduleForm from '@/components/ScheduleForm';

function formatNextRun(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const diffMs = d.getTime() - now.getTime();
  if (diffMs < 0) return 'overdue';
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'in <1 min';
  if (diffMin < 60) return `in ${diffMin}m`;
  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `in ${diffHr}h ${diffMin % 60}m`;
  return d.toLocaleString();
}

function describeSchedule(s: Schedule): string {
  if (s.mode === 'interval') {
    return `Every ${s.interval_value} ${s.interval_unit}`;
  }
  const n = s.every_n_days === 1 ? 'day' : `${s.every_n_days} days`;
  return `Daily at ${s.daily_time}, every ${n}`;
}

export default function SchedulesPage() {
  const qc = useQueryClient();
  const { data: scheduleList = [], isLoading: loadingSchedules } = useQuery({
    queryKey: ['schedules'],
    queryFn: schedulesApi.list,
    refetchInterval: 30_000,
  });
  const { data: agentList = [], isLoading: loadingAgents } = useQuery({
    queryKey: ['agents'],
    queryFn: agentsApi.list,
  });

  const [showForm, setShowForm] = useState(false);
  const [editTarget, setEditTarget] = useState<Schedule | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: schedulesApi.create,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedules'] }); setShowForm(false); },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: SchedulePayload }) =>
      schedulesApi.update(id, payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedules'] }); setEditTarget(null); },
  });

  const toggleMutation = useMutation({
    mutationFn: schedulesApi.toggle,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['schedules'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: schedulesApi.delete,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['schedules'] }); setConfirmDelete(null); },
  });

  const isLoading = loadingSchedules || loadingAgents;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">Schedules</h1>
        {!showForm && !editTarget && (
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            + New Schedule
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <div className="bg-white rounded-xl border border-slate-200 p-6">
          <h2 className="text-lg font-semibold text-slate-800 mb-4">New Schedule</h2>
          <ScheduleForm
            agents={agentList}
            onSubmit={payload => createMutation.mutate(payload)}
            onCancel={() => setShowForm(false)}
            isSubmitting={createMutation.isPending}
          />
          {createMutation.isError && (
            <p className="text-sm text-red-600 mt-2">{String(createMutation.error)}</p>
          )}
        </div>
      )}

      {isLoading && <p className="text-sm text-slate-400">Loading…</p>}

      {!isLoading && scheduleList.length === 0 && !showForm && (
        <div className="bg-white rounded-xl border border-dashed border-slate-300 p-12 text-center">
          <p className="text-slate-500 mb-4">No schedules defined yet.</p>
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
          >
            Create your first schedule
          </button>
        </div>
      )}

      <div className="divide-y divide-slate-100 rounded-xl border border-slate-200 bg-white overflow-hidden">
        {scheduleList.map(schedule => (
          <div key={schedule.id}>
            {editTarget?.id === schedule.id ? (
              <div className="px-4 py-4">
                <h2 className="text-sm font-semibold text-slate-700 mb-3">Edit Schedule</h2>
                <ScheduleForm
                  agents={agentList}
                  initial={schedule}
                  onSubmit={payload => updateMutation.mutate({ id: schedule.id, payload })}
                  onCancel={() => setEditTarget(null)}
                  isSubmitting={updateMutation.isPending}
                />
                {updateMutation.isError && (
                  <p className="text-sm text-red-600 mt-2">{String(updateMutation.error)}</p>
                )}
              </div>
            ) : (
              <div className="flex items-start gap-4 px-4 py-4">
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-semibold text-slate-900">{schedule.agent_name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      schedule.active
                        ? 'bg-green-100 text-green-700'
                        : 'bg-slate-100 text-slate-500'
                    }`}>
                      {schedule.active ? 'Active' : 'Paused'}
                    </span>
                    <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                      {describeSchedule(schedule)}
                    </span>
                  </div>
                  <p className="text-sm text-slate-500 truncate">{schedule.prompt}</p>
                  <p className="text-xs text-slate-400">
                    Next run: <span className="text-slate-600 font-medium">{formatNextRun(schedule.next_run)}</span>
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => toggleMutation.mutate(schedule.id)}
                    disabled={toggleMutation.isPending}
                    className={`px-3 py-1.5 rounded-lg text-sm border transition-colors disabled:opacity-50 ${
                      schedule.active
                        ? 'border-amber-200 text-amber-600 hover:bg-amber-50'
                        : 'border-green-200 text-green-600 hover:bg-green-50'
                    }`}
                  >
                    {schedule.active ? 'Pause' : 'Resume'}
                  </button>
                  <button
                    onClick={() => setEditTarget(schedule)}
                    className="px-3 py-1.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    Edit
                  </button>
                  {confirmDelete === schedule.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => deleteMutation.mutate(schedule.id)}
                        className="px-3 py-1.5 rounded-lg bg-red-600 text-white text-sm hover:bg-red-700 transition-colors"
                      >
                        Confirm
                      </button>
                      <button
                        onClick={() => setConfirmDelete(null)}
                        className="px-3 py-1.5 rounded-lg border border-slate-300 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setConfirmDelete(schedule.id)}
                      className="px-3 py-1.5 rounded-lg border border-red-200 text-sm text-red-500 hover:bg-red-50 transition-colors"
                    >
                      Delete
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
