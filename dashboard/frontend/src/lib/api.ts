/**
 * Athena Dashboard API Client
 *
 * Type-safe API client for all Athena backend endpoints.
 * Uses axios for HTTP requests with automatic error handling.
 */

import axios, { AxiosError } from 'axios'

// Base API URL - points directly to FastAPI backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Response interceptor for error handling
client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.response?.data || error.message)
    throw error
  }
)

// ============================================================================
// Type Definitions
// ============================================================================

export interface SystemStatus {
  status: string
  subsystems: {
    memory: {
      episodic: any
      semantic: any
      procedural: any
      prospective: any
      graph: any
      meta: any
      consolidation: any
      planning: any
    }
  }
  timestamp: string
}

export interface EpisodicEvent {
  id: number
  timestamp: string
  event_type: string
  content: string
  importance_score: number
  session_id: string
  lifecycle_status?: string
  consolidation_score?: number
}

export interface EpisodicEventsResponse {
  events: EpisodicEvent[]
  total: number
  limit: number
}

export interface RecentEventsResponse {
  events: EpisodicEvent[]
  total: number
}

export interface SemanticSearchResult {
  id: number
  content: string
  memory_type?: string
  usefulness_score?: number
}

export interface SemanticSearchResponse {
  results: SemanticSearchResult[]
  total: number
  query: string
}

export interface Procedure {
  id: number
  name: string
  category: string
  success_rate: number
  usage_count: number
  last_used?: string
}

export interface ProceduresResponse {
  procedures: Procedure[]
  total: number
}

export interface Task {
  id: number
  content: string
  status: string
  priority: number
  phase: string
  created_at: string
  due_at?: string
}

export interface TasksResponse {
  tasks: Task[]
  total: number
}

export interface Entity {
  id: number
  name: string
  entity_type: string
  source: string
}

export interface EntitiesResponse {
  entities: Entity[]
  total: number
}

export interface RelatedEntity {
  id: number
  name: string
  entity_type: string
  relation_type?: string
}

export interface RelatedEntitiesResponse {
  entity_id: number
  related: RelatedEntity[]
  total: number
}

export interface ConsolidationRun {
  id?: number
  started_at?: string
  status?: string
  patterns_extracted?: number
}

export interface ConsolidationHistoryResponse {
  runs: ConsolidationRun[]
  total: number
}

export interface Plan {
  id?: number
  name?: string
  status?: string
}

export interface PlansResponse {
  plans: Plan[]
  total: number
}

// ============================================================================
// API Functions
// ============================================================================

export const api = {
  // System & Health
  healthCheck: async () => {
    const { data } = await client.get('/health')
    return data
  },

  getSystemStatus: async (): Promise<SystemStatus> => {
    const { data } = await client.get<SystemStatus>('/api/system/status')
    return data
  },

  // Episodic Memory (Project-scoped)
  getEpisodicStatistics: async (sessionId?: string, projectId: number = 1) => {
    const { data } = await client.get('/api/episodic/statistics', {
      params: { session_id: sessionId, project_id: projectId },
    })
    return data
  },

  getEpisodicEvents: async (
    limit: number = 100,
    sessionId?: string,
    projectId: number = 1
  ): Promise<EpisodicEventsResponse> => {
    const { data } = await client.get<EpisodicEventsResponse>('/api/episodic/events', {
      params: { limit, session_id: sessionId, project_id: projectId },
    })
    return data
  },

  getEpisodicRecent: async (limit: number = 10): Promise<RecentEventsResponse> => {
    const { data } = await client.get<RecentEventsResponse>('/api/episodic/recent', {
      params: { limit },
    })
    return data
  },

  // Semantic Memory
  searchSemanticMemories: async (
    query: string,
    limit: number = 10
  ): Promise<SemanticSearchResponse> => {
    const { data } = await client.get<SemanticSearchResponse>('/api/semantic/search', {
      params: { query, limit },
    })
    return data
  },

  // Procedural Memory
  getProceduralStatistics: async () => {
    const { data } = await client.get('/api/procedural/statistics')
    return data
  },

  getProcedures: async (
    limit: number = 100,
    category?: string
  ): Promise<ProceduresResponse> => {
    const { data } = await client.get<ProceduresResponse>('/api/procedural/procedures', {
      params: { limit, category },
    })
    return data
  },

  // Prospective Memory
  getProspectiveStatistics: async () => {
    const { data } = await client.get('/api/prospective/statistics')
    return data
  },

  getTasks: async (
    status?: string,
    limit: number = 100
  ): Promise<TasksResponse> => {
    const { data } = await client.get<TasksResponse>('/api/prospective/tasks', {
      params: { status, limit },
    })
    return data
  },

  // Knowledge Graph (Project-scoped)
  getGraphStatistics: async (projectId?: number) => {
    const { data } = await client.get('/api/graph/statistics', {
      params: projectId ? { project_id: projectId } : {},
    })
    return data
  },

  getEntities: async (
    entityType?: string,
    limit: number = 100,
    projectId?: number
  ): Promise<EntitiesResponse> => {
    const { data } = await client.get<EntitiesResponse>('/api/graph/entities', {
      params: { entity_type: entityType, limit, project_id: projectId },
    })
    return data
  },

  getEntityRelations: async (
    entityId: number,
    limit: number = 50
  ): Promise<RelatedEntitiesResponse> => {
    const { data } = await client.get<RelatedEntitiesResponse>(
      `/api/graph/entities/${entityId}/related`,
      { params: { limit } }
    )
    return data
  },

  // Meta-Memory
  getMetaStatistics: async () => {
    const { data } = await client.get('/api/meta/statistics')
    return data
  },

  // Consolidation
  getConsolidationStatistics: async () => {
    const { data } = await client.get('/api/consolidation/statistics')
    return data
  },

  getConsolidationHistory: async (
    limit: number = 20
  ): Promise<ConsolidationHistoryResponse> => {
    const { data } = await client.get<ConsolidationHistoryResponse>(
      '/api/consolidation/history',
      { params: { limit } }
    )
    return data
  },

  // Planning
  getPlanningStatistics: async () => {
    const { data } = await client.get('/api/planning/statistics')
    return data
  },

  getPlans: async (limit: number = 50): Promise<PlansResponse> => {
    const { data } = await client.get<PlansResponse>('/api/planning/plans', {
      params: { limit },
    })
    return data
  },

  // Research
  getResearchTasks: async (status?: string, limit: number = 50) => {
    const { data } = await client.get('/api/research/tasks', {
      params: { status, limit },
    })
    return data
  },

  getResearchStatistics: async () => {
    const { data } = await client.get('/api/research/statistics')
    return data
  },

  // Code Intelligence
  getCodeArtifacts: async (limit: number = 50) => {
    const { data } = await client.get('/api/code/artifacts', {
      params: { limit },
    })
    return data
  },

  getCodeStatistics: async () => {
    const { data } = await client.get('/api/code/statistics')
    return data
  },

  // Skills & Agents
  getSkills: async (domain?: string, limit: number = 50) => {
    const { data } = await client.get('/api/skills/library', {
      params: { domain, limit },
    })
    return data
  },

  getSkillsStatistics: async () => {
    const { data } = await client.get('/api/skills/statistics')
    return data
  },

  // Context Awareness
  getIDEContext: async (limit: number = 10) => {
    const { data } = await client.get('/api/context/ide', {
      params: { limit },
    })
    return data
  },

  getWorkingMemory: async (limit: number = 7) => {
    const { data } = await client.get('/api/context/working-memory', {
      params: { limit },
    })
    return data
  },

  // Execution Monitoring
  getExecutionTasks: async (status?: string, limit: number = 50) => {
    const { data } = await client.get('/api/execution/tasks', {
      params: { status, limit },
    })
    return data
  },

  getExecutionStatistics: async () => {
    const { data } = await client.get('/api/execution/statistics')
    return data
  },

  // Safety Validation
  getSafetyValidations: async (limit: number = 50) => {
    const { data } = await client.get('/api/safety/validations', {
      params: { limit },
    })
    return data
  },

  getSafetyStatistics: async () => {
    const { data } = await client.get('/api/safety/statistics')
    return data
  },

  // Performance Metrics
  getPerformanceMetrics: async (limit: number = 100) => {
    const { data } = await client.get('/api/performance/metrics', {
      params: { limit },
    })
    return data
  },

  getPerformanceStatistics: async () => {
    const { data } = await client.get('/api/performance/statistics')
    return data
  },
}

export default api
