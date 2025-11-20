import { create } from 'zustand'

export interface Agent {
  id: string
  type: string
  status: 'idle' | 'busy' | 'failed'
  capabilities: string[]
  last_heartbeat?: string
  current_task_id?: string
  tasks_completed: number
}

export interface Task {
  id: number
  content: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  priority: number
  phase?: string
  assigned_agent_id?: string
  created_at?: string
  progress?: number
  result?: string
}

export interface OrchestrationMetrics {
  agents: {
    total: number
    idle: number
    busy: number
    failed: number
    stale: number
  }
  tasks: {
    pending: number
    in_progress: number
    completed: number
    total: number
  }
  progress: {
    percent: number
    completed: number
    total: number
  }
  health: {
    stale_agents: number
    failed_agents: number
    status: 'healthy' | 'degraded'
  }
}

interface OrchestrationState {
  agents: Agent[]
  tasks: Task[]
  metrics: OrchestrationMetrics | null
  isLoading: boolean
  error: string | null
  wsConnected: boolean
  selectedAgentId: string | null
  selectedTaskId: number | null

  // Actions
  setAgents: (agents: Agent[]) => void
  setTasks: (tasks: Task[]) => void
  setMetrics: (metrics: OrchestrationMetrics) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setWsConnected: (connected: boolean) => void
  setSelectedAgent: (agentId: string | null) => void
  setSelectedTask: (taskId: number | null) => void
  addTask: (task: Task) => void
  updateAgent: (agentId: string, updates: Partial<Agent>) => void
  updateTask: (taskId: number, updates: Partial<Task>) => void
}

export const useOrchestrationStore = create<OrchestrationState>((set) => ({
  agents: [],
  tasks: [],
  metrics: null,
  isLoading: false,
  error: null,
  wsConnected: false,
  selectedAgentId: null,
  selectedTaskId: null,

  setAgents: (agents) => set({ agents }),
  setTasks: (tasks) => set({ tasks }),
  setMetrics: (metrics) => set({ metrics }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
  setSelectedAgent: (selectedAgentId) => set({ selectedAgentId }),
  setSelectedTask: (selectedTaskId) => set({ selectedTaskId }),

  addTask: (task) =>
    set((state) => ({
      tasks: [task, ...state.tasks],
    })),

  updateAgent: (agentId, updates) =>
    set((state) => ({
      agents: state.agents.map((a) =>
        a.id === agentId ? { ...a, ...updates } : a
      ),
    })),

  updateTask: (taskId, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === taskId ? { ...t, ...updates } : t
      ),
    })),
}))
