export interface AgentSummary {
  name: string;
  description: string;
  model: string;
  stream_output: boolean;
  tools: string[];
}

export interface AgentConfig {
  name: string;
  description: string;
  model: string;
  system_prompt: string;
  tools: string[];
  memory: { type: 'none' | 'sqlite' | 'chromadb' | 'markdown'; path?: string };
  max_iterations: number;
  temperature: number;
  api_base: string | null;
  stream_output: boolean;
}

export interface RunSummary {
  id: string;
  agent_name: string;
  status: 'running' | 'completed' | 'cancelled' | 'error';
  started_at: string;
  completed_at: string | null;
  model: string;
  user_input: string;
  trigger?: 'manual' | 'scheduled';
}

export type ScheduleMode = 'interval' | 'daily';
export type IntervalUnit = 'minutes' | 'hours' | 'days';

export interface Schedule {
  id: string;
  agent_name: string;
  prompt: string;
  mode: ScheduleMode;
  interval_value: number | null;
  interval_unit: IntervalUnit | null;
  daily_time: string | null;
  every_n_days: number | null;
  active: number; // 1 = active, 0 = paused
  created_at: string;
  anchor: string;
  next_run: string;
}

export interface SchedulePayload {
  agent_name: string;
  prompt: string;
  mode: ScheduleMode;
  interval_value?: number;
  interval_unit?: IntervalUnit;
  daily_time?: string;
  every_n_days?: number;
}

export interface RunDetail extends RunSummary {
  final_output: string;
  tool_calls: ToolCallRecord[];
  events: SSEEvent[];
  error: string | null;
  user_input: string;
}

export interface ToolCallRecord {
  name: string;
  arguments: Record<string, unknown>;
  result: string | null;
}

export interface SSEEvent {
  type: 'chunk' | 'tool_call' | 'tool_result' | 'done' | 'error' | 'cancelled';
  content?: string;
  id?: string;
  name?: string;
  arguments?: Record<string, unknown>;
  result?: string;
  message?: string;
}

export interface StartRunRequest {
  agent_name: string;
  user_input: string;
  stream?: boolean;
  model?: string;
  temperature?: number;
  max_iterations?: number;
}

export interface StartRunResponse {
  run_id: string;
  agent_name: string;
  status: string;
  stream: boolean;
}
