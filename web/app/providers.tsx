'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import type { RunSummary } from '@/lib/types';
import { runs as runsApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// React Query
// ---------------------------------------------------------------------------

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5000, retry: 1 } },
});

// ---------------------------------------------------------------------------
// Active Runs Context
// ---------------------------------------------------------------------------

interface ActiveRunsCtx {
  activeRuns: Map<string, RunSummary>;
  addRun: (run: RunSummary) => void;
  updateRun: (id: string, update: Partial<RunSummary>) => void;
  removeRun: (id: string) => void;
  cancelRun: (id: string) => Promise<void>;
}

const ActiveRunsContext = createContext<ActiveRunsCtx>({
  activeRuns: new Map(),
  addRun: () => {},
  updateRun: () => {},
  removeRun: () => {},
  cancelRun: async () => {},
});

export function useActiveRuns() {
  return useContext(ActiveRunsContext);
}

// ---------------------------------------------------------------------------
// Provider tree
// ---------------------------------------------------------------------------

export function Providers({ children }: { children: ReactNode }) {
  const [activeRuns, setActiveRuns] = useState<Map<string, RunSummary>>(new Map());

  const addRun = useCallback((run: RunSummary) => {
    setActiveRuns((m) => new Map(m).set(run.id, run));
  }, []);

  const updateRun = useCallback((id: string, update: Partial<RunSummary>) => {
    setActiveRuns((m) => {
      const next = new Map(m);
      const existing = next.get(id);
      if (existing) next.set(id, { ...existing, ...update });
      return next;
    });
  }, []);

  const removeRun = useCallback((id: string) => {
    setActiveRuns((m) => {
      const next = new Map(m);
      next.delete(id);
      return next;
    });
  }, []);

  const cancelRun = useCallback(async (id: string) => {
    await runsApi.cancel(id);
    updateRun(id, { status: 'cancelled' });
    setTimeout(() => removeRun(id), 2000);
  }, [updateRun, removeRun]);

  return (
    <QueryClientProvider client={queryClient}>
      <ActiveRunsContext.Provider value={{ activeRuns, addRun, updateRun, removeRun, cancelRun }}>
        {children}
      </ActiveRunsContext.Provider>
    </QueryClientProvider>
  );
}
