'use client'

import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { useOrchestrationStore } from '@/stores/orchestration-store'
import { AgentCard } from '@/components/orchestration/agent-card'
import { TaskQueue } from '@/components/orchestration/task-queue'
import { OrchestrationMetricsComponent } from '@/components/orchestration/orchestration-metrics'
import { Zap, Send } from 'lucide-react'

export default function OrchestrationPage() {
  const store = useOrchestrationStore()
  const [taskInput, setTaskInput] = useState('')
  const [priority, setPriority] = useState(5)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Fetch agents
  const { data: agentsData, isLoading: agentsLoading } = useQuery({
    queryKey: ['orchestration-agents'],
    queryFn: api.getOrchestrationAgents,
    refetchInterval: 3000, // Refresh every 3 seconds
  })

  // Fetch tasks
  const { data: tasksData, isLoading: tasksLoading } = useQuery({
    queryKey: ['orchestration-tasks'],
    queryFn: () => api.getOrchestrationTasks(),
    refetchInterval: 3000,
  })

  // Fetch metrics
  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ['orchestration-metrics'],
    queryFn: api.getOrchestrationMetrics,
    refetchInterval: 3000,
  })

  // Update store when data changes
  useEffect(() => {
    if (agentsData?.agents) {
      store.setAgents(agentsData.agents)
    }
  }, [agentsData, store])

  useEffect(() => {
    if (tasksData?.tasks) {
      store.setTasks(tasksData.tasks)
    }
  }, [tasksData, store])

  useEffect(() => {
    if (metricsData) {
      store.setMetrics(metricsData)
    }
  }, [metricsData, store])

  // WebSocket for real-time updates
  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(
      `${protocol}//${window.location.host}/ws/orchestration`
    )

    ws.onopen = () => {
      store.setWsConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data)
        if (message.type === 'orchestration_update') {
          // Update metrics from WebSocket
          if (message.agents && message.tasks) {
            store.setMetrics({
              agents: {
                total: message.agents.total,
                idle: message.agents.idle,
                busy: message.agents.busy,
                failed: message.agents.failed,
                stale: 0,
              },
              tasks: {
                pending: message.tasks.pending,
                in_progress: message.tasks.in_progress,
                completed: message.tasks.completed,
                total:
                  message.tasks.pending +
                  message.tasks.in_progress +
                  message.tasks.completed,
              },
              progress: {
                percent:
                  ((message.tasks.completed /
                    (message.tasks.pending +
                      message.tasks.in_progress +
                      message.tasks.completed)) *
                    100) ||
                  0,
                completed: message.tasks.completed,
                total:
                  message.tasks.pending +
                  message.tasks.in_progress +
                  message.tasks.completed,
              },
              health: {
                stale_agents: 0,
                failed_agents: message.agents.failed,
                status:
                  message.agents.failed === 0 ? 'healthy' : 'degraded',
              },
            })
          }
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onerror = () => {
      store.setWsConnected(false)
    }

    ws.onclose = () => {
      store.setWsConnected(false)
    }

    return () => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close()
      }
    }
  }, [store])

  const handleSubmitTask = async () => {
    if (!taskInput.trim()) return

    setIsSubmitting(true)
    try {
      const result = await api.submitOrchestrationTask(taskInput, priority)
      if (result.task_id) {
        setTaskInput('')
        setPriority(5)
        // Refresh tasks
        setTimeout(() => {
          window.location.reload()
        }, 500)
      }
    } catch (error) {
      console.error('Failed to submit task:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const isLoading = agentsLoading || tasksLoading || metricsLoading

  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-blue-100 p-3 rounded-lg">
            <Zap className="w-6 h-6 text-blue-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Orchestration</h1>
            <p className="text-sm text-gray-500">
              Multi-Agent Task Coordination & Monitoring
            </p>
          </div>
        </div>

        {/* WebSocket Status */}
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              store.wsConnected ? 'bg-green-500' : 'bg-gray-300'
            }`}
          />
          <span className="text-xs font-medium text-gray-600">
            {store.wsConnected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Metrics Overview */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          System Status
        </h2>
        <OrchestrationMetricsComponent
          metrics={store.metrics}
          isLoading={isLoading}
        />
      </div>

      {/* Task Submission */}
      <div className="bg-white p-6 rounded-lg border border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Submit New Task
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Task Description
            </label>
            <textarea
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              placeholder="Describe the task for agents to execute..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              rows={3}
              maxLength={2000}
            />
            <p className="text-xs text-gray-500 mt-1">
              {taskInput.length}/2000 characters
            </p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value={1}>Low (1)</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={4}>4</option>
                <option value={5} selected>
                  Normal (5)
                </option>
                <option value={6}>6</option>
                <option value={7}>7</option>
                <option value={8}>8</option>
                <option value={9}>9</option>
                <option value={10}>High (10)</option>
              </select>
            </div>
          </div>

          <button
            onClick={handleSubmitTask}
            disabled={isSubmitting || !taskInput.trim()}
            className="w-full bg-blue-600 text-white font-medium py-3 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
          >
            <Send className="w-4 h-4" />
            {isSubmitting ? 'Submitting...' : 'Submit Task'}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Agents */}
        <div className="lg:col-span-1">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Agents ({store.agents.length})
          </h2>
          <div className="space-y-3">
            {isLoading ? (
              [...Array(3)].map((_, i) => (
                <div key={i} className="bg-gray-100 rounded-lg h-24 animate-pulse" />
              ))
            ) : store.agents.length === 0 ? (
              <p className="text-sm text-gray-500 text-center py-8">
                No agents available
              </p>
            ) : (
              store.agents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  isSelected={store.selectedAgentId === agent.id}
                  onSelect={(id) => store.setSelectedAgent(id)}
                />
              ))
            )}
          </div>
        </div>

        {/* Tasks Queue */}
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Task Queue ({store.tasks.length})
          </h2>
          <div className="max-h-[600px] overflow-y-auto">
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => (
                  <div
                    key={i}
                    className="bg-gray-100 rounded-lg h-16 animate-pulse"
                  />
                ))}
              </div>
            ) : (
              <TaskQueue
                tasks={store.tasks}
                onSelectTask={(id) => store.setSelectedTask(id)}
                selectedTaskId={store.selectedTaskId}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
