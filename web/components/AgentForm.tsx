'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { agents as agentsApi } from '@/lib/api';
import type { AgentConfig } from '@/lib/types';

const DEFAULTS: AgentConfig = {
  name: '',
  description: '',
  model: 'ollama/mistral',
  system_prompt: '',
  tools: [],
  memory: { type: 'none' },
  max_iterations: 20,
  temperature: 0.7,
  api_base: null,
  stream_output: true,
};

const BUILT_IN_TOOLS = ['read_file', 'write_file', 'list_dir'];

interface Props {
  initial?: AgentConfig;
  mode: 'create' | 'edit';
}

export default function AgentForm({ initial, mode }: Props) {
  const router = useRouter();
  const [form, setForm] = useState<AgentConfig>(initial ?? DEFAULTS);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const set = <K extends keyof AgentConfig>(key: K, value: AgentConfig[K]) => {
    setForm((f) => ({ ...f, [key]: value }));
  };

  const toggleTool = (tool: string) => {
    set('tools', form.tools.includes(tool)
      ? form.tools.filter((t) => t !== tool)
      : [...form.tools, tool]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSaving(true);
    try {
      if (mode === 'create') {
        await agentsApi.create(form);
      } else {
        await agentsApi.update(initial!.name, form);
      }
      router.push(`/agents/${mode === 'create' ? form.name : initial!.name}`);
      router.refresh();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Identity */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="font-semibold text-slate-900">Identity</h2>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Name" required>
            <input
              type="text"
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              disabled={mode === 'edit'}
              className="input"
              placeholder="my-agent"
              pattern="[a-z0-9-]+"
              title="Lowercase letters, numbers, and hyphens only"
            />
          </Field>
          <Field label="Description">
            <input
              type="text"
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              className="input"
              placeholder="What this agent does"
            />
          </Field>
        </div>
      </section>

      {/* Model */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="font-semibold text-slate-900">Model</h2>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Model" required>
            <input
              type="text"
              value={form.model}
              onChange={(e) => set('model', e.target.value)}
              className="input font-mono"
              placeholder="ollama/mistral"
            />
          </Field>
          <Field label="API Base (optional)">
            <input
              type="text"
              value={form.api_base ?? ''}
              onChange={(e) => set('api_base', e.target.value || null)}
              className="input font-mono"
              placeholder="http://192.168.2.107:11434"
            />
          </Field>
          <Field label="Temperature">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min="0" max="2" step="0.05"
                value={form.temperature}
                onChange={(e) => set('temperature', parseFloat(e.target.value))}
                className="flex-1"
              />
              <span className="text-sm font-mono w-10 text-right">{form.temperature.toFixed(2)}</span>
            </div>
          </Field>
          <Field label="Max Iterations">
            <input
              type="number"
              min="1" max="100"
              value={form.max_iterations}
              onChange={(e) => set('max_iterations', parseInt(e.target.value))}
              className="input"
            />
          </Field>
        </div>
      </section>

      {/* System Prompt */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="font-semibold text-slate-900">System Prompt</h2>
        <textarea
          value={form.system_prompt}
          onChange={(e) => set('system_prompt', e.target.value)}
          className="input font-mono h-32 resize-y"
          placeholder="You are a helpful assistant…"
        />
      </section>

      {/* Tools */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="font-semibold text-slate-900">Tools</h2>
        <div className="flex flex-wrap gap-2">
          {BUILT_IN_TOOLS.map((tool) => (
            <button
              key={tool}
              type="button"
              onClick={() => toggleTool(tool)}
              className={`px-3 py-1.5 rounded-full text-sm font-mono font-medium border transition-colors ${
                form.tools.includes(tool)
                  ? 'bg-indigo-600 text-white border-indigo-600'
                  : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'
              }`}
            >
              {tool}
            </button>
          ))}
        </div>
      </section>

      {/* Memory & Streaming */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 space-y-4">
        <h2 className="font-semibold text-slate-900">Memory & Output</h2>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Memory Backend">
            <select
              value={form.memory.type}
              onChange={(e) => set('memory', { type: e.target.value as 'none' | 'sqlite' | 'chromadb' })}
              className="input"
            >
              <option value="none">None (stateless)</option>
              <option value="sqlite">SQLite (persistent)</option>
            </select>
          </Field>
          <Field label="Stream Output by Default">
            <label className="flex items-center gap-2 cursor-pointer mt-2">
              <input
                type="checkbox"
                checked={form.stream_output}
                onChange={(e) => set('stream_output', e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600"
              />
              <span className="text-sm text-slate-600">Stream tokens live</span>
            </label>
          </Field>
        </div>
      </section>

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saving}
          className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving…' : mode === 'create' ? 'Create Agent' : 'Save Changes'}
        </button>
        <button
          type="button"
          onClick={() => router.back()}
          className="px-5 py-2 rounded-lg border border-slate-300 text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}

function Field({ label, required, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium text-slate-700">
        {label}{required && <span className="text-red-500 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}
