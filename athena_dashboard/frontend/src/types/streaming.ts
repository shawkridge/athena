/**
 * Streaming types for real-time research updates
 */

export enum EventType {
  PROGRESS = "progress",
  FINDING = "finding",
  COMPLETE = "complete",
  ERROR = "error",
}

export interface StreamingUpdate {
  type: EventType;
  timestamp: string;
  data: Record<string, unknown>;
}

export interface Finding {
  id: string;
  title: string;
  content: string;
  source?: string;
  relevance_score: number;
  timestamp?: string;
}

export interface AgentProgress {
  agent_id: string;
  name: string;
  status: "running" | "waiting" | "complete";
  findings_count: number;
  total_findings: number;
  rate: number; // findings per second
  eta_seconds?: number;
  latency_ms?: number;
  started_at?: string;
  updated_at?: string;
}

export interface ResearchTaskData {
  findings: Finding[];
  agents: Record<string, AgentProgress>;
  total_findings: number;
  started_at: string;
}
