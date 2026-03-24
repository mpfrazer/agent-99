'use client';

import { useQuery } from '@tanstack/react-query';
import { agents as agentsApi } from '@/lib/api';
import AgentForm from '@/components/AgentForm';

interface Props {
  params: { name: string };
}

export default function EditAgentPage({ params }: Props) {
  const { data: agent, isLoading } = useQuery({
    queryKey: ['agent', params.name],
    queryFn: () => agentsApi.get(params.name),
  });

  if (isLoading) return <p className="text-sm text-slate-400">Loading…</p>;
  if (!agent) return <p className="text-sm text-red-500">Agent not found.</p>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Edit — {params.name}</h1>
      <AgentForm initial={agent} mode="edit" />
    </div>
  );
}
