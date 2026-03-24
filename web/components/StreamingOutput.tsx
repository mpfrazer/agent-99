'use client';

import { useEffect, useRef, useState } from 'react';
import type { SSEEvent } from '@/lib/types';
import { useActiveRuns } from '@/app/providers';

interface Props {
  runId: string;
  initialEvents?: SSEEvent[];
  onComplete?: (output: string) => void;
}

function ToolCallBlock({ event, result }: { event: SSEEvent; result?: SSEEvent }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="my-2 border border-indigo-100 rounded-lg overflow-hidden text-sm">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center gap-2 px-3 py-2 bg-indigo-50 hover:bg-indigo-100 transition-colors text-left"
      >
        <span className="text-indigo-600 font-medium font-mono">{event.name}</span>
        <span className="text-slate-400 text-xs">{open ? '▲' : '▼'}</span>
        {result && <span className="ml-auto text-xs text-emerald-600">✓ done</span>}
      </button>
      {open && (
        <div className="divide-y divide-slate-100">
          <div className="px-3 py-2 bg-white">
            <p className="text-xs text-slate-500 mb-1">Arguments</p>
            <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap">
              {JSON.stringify(event.arguments, null, 2)}
            </pre>
          </div>
          {result && (
            <div className="px-3 py-2 bg-white">
              <p className="text-xs text-slate-500 mb-1">Result</p>
              <pre className="text-xs font-mono text-slate-700 whitespace-pre-wrap">{result.result}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function StreamingOutput({ runId, initialEvents = [], onComplete }: Props) {
  const [events, setEvents] = useState<SSEEvent[]>(initialEvents);
  const [done, setDone] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const { updateRun, removeRun } = useActiveRuns();

  useEffect(() => {
    if (done) return;

    const es = new EventSource(`/api/runs/${runId}/stream`, { withCredentials: true });

    es.onmessage = (e) => {
      const evt: SSEEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, evt]);

      if (evt.type === 'done') {
        setDone(true);
        updateRun(runId, { status: 'completed' });
        setTimeout(() => removeRun(runId), 3000);
        onComplete?.(evt.content ?? '');
        es.close();
      } else if (evt.type === 'error') {
        setDone(true);
        updateRun(runId, { status: 'error' });
        setTimeout(() => removeRun(runId), 5000);
        es.close();
      } else if (evt.type === 'cancelled') {
        setDone(true);
        updateRun(runId, { status: 'cancelled' });
        setTimeout(() => removeRun(runId), 2000);
        es.close();
      }
    };

    es.onerror = () => {
      setDone(true);
      es.close();
    };

    return () => es.close();
  }, [runId, done, updateRun, removeRun, onComplete]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  // Build display: interleave text chunks with tool call blocks
  const rendered: React.ReactNode[] = [];
  let textBuffer = '';
  const toolResults = new Map<string, SSEEvent>(); // id → result event

  // Pre-pass: collect tool results
  for (const evt of events) {
    if (evt.type === 'tool_result' && evt.id) {
      toolResults.set(evt.id, evt);
    }
  }

  for (let i = 0; i < events.length; i++) {
    const evt = events[i];
    if (evt.type === 'chunk' && evt.content) {
      textBuffer += evt.content;
    } else if (evt.type === 'tool_call') {
      if (textBuffer) {
        rendered.push(
          <pre key={`text-${i}`} className="whitespace-pre-wrap font-mono text-sm text-slate-800 leading-relaxed">
            {textBuffer}
          </pre>
        );
        textBuffer = '';
      }
      rendered.push(
        <ToolCallBlock
          key={`tc-${i}`}
          event={evt}
          result={evt.id ? toolResults.get(evt.id) : undefined}
        />
      );
    }
  }

  if (textBuffer) {
    rendered.push(
      <pre key="text-final" className="whitespace-pre-wrap font-mono text-sm text-slate-800 leading-relaxed">
        {textBuffer}
      </pre>
    );
  }

  const hasError = events.some((e) => e.type === 'error');
  const isCancelled = events.some((e) => e.type === 'cancelled');

  return (
    <div className="rounded-xl border border-slate-200 bg-white">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
        <span className="text-xs font-medium text-slate-500">Output</span>
        {!done && (
          <span className="flex items-center gap-1.5 text-xs text-indigo-600">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
            Running…
          </span>
        )}
        {done && !hasError && !isCancelled && (
          <span className="text-xs text-emerald-600">✓ Completed</span>
        )}
        {hasError && <span className="text-xs text-red-500">✗ Error</span>}
        {isCancelled && <span className="text-xs text-slate-400">Cancelled</span>}
      </div>
      <div className="p-4 min-h-24 max-h-[60vh] overflow-y-auto">
        {rendered.length === 0 && !done && (
          <p className="text-sm text-slate-400 italic">Waiting for response…</p>
        )}
        {rendered}
        {hasError && (
          <p className="text-sm text-red-500 mt-2">
            {events.find((e) => e.type === 'error')?.message}
          </p>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
