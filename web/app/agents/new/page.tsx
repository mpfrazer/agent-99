import AgentForm from '@/components/AgentForm';

export default function NewAgentPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">New Agent</h1>
      <AgentForm mode="create" />
    </div>
  );
}
