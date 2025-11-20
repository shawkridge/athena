'use client'

import { Agent } from '@/stores/orchestration-store'
import { Badge } from '@/components/ui/badge'
import { Zap, Clock } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

interface AgentCardProps {
  agent: Agent
  isSelected?: boolean
  onSelect?: (agentId: string) => void
}

const statusColors = {
  idle: 'bg-gray-100 text-gray-800',
  busy: 'bg-blue-100 text-blue-800',
  failed: 'bg-red-100 text-red-800',
}

const statusIcons = {
  idle: '⊘',
  busy: '⚡',
  failed: '✕',
}

export function AgentCard({ agent, isSelected, onSelect }: AgentCardProps) {
  return (
    <div
      onClick={() => onSelect?.(agent.id)}
      className={`p-4 rounded-lg border-2 cursor-pointer transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-200 hover:border-gray-300 bg-white'
      }`}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <h3 className="font-semibold text-sm truncate">{agent.id}</h3>
          <p className="text-xs text-gray-500 capitalize">{agent.type}</p>
        </div>
        <Badge
          variant="outline"
          className={`ml-2 ${statusColors[agent.status] || statusColors.idle}`}
        >
          {statusIcons[agent.status]} {agent.status}
        </Badge>
      </div>

      <div className="space-y-2 text-xs">
        {agent.current_task_id && (
          <div className="flex items-center gap-2">
            <Zap className="w-3 h-3 text-yellow-500" />
            <span className="text-gray-700">
              Task: {agent.current_task_id}
            </span>
          </div>
        )}

        {agent.last_heartbeat && (
          <div className="flex items-center gap-2">
            <Clock className="w-3 h-3 text-gray-400" />
            <span className="text-gray-600">
              {formatDistanceToNow(new Date(agent.last_heartbeat), {
                addSuffix: true,
              })}
            </span>
          </div>
        )}

        <div className="flex gap-2 flex-wrap mt-3">
          {agent.capabilities?.slice(0, 2).map((cap) => (
            <Badge
              key={cap}
              variant="secondary"
              className="text-xs bg-gray-100 text-gray-700"
            >
              {cap}
            </Badge>
          ))}
          {agent.capabilities && agent.capabilities.length > 2 && (
            <Badge variant="secondary" className="text-xs">
              +{agent.capabilities.length - 2}
            </Badge>
          )}
        </div>

        <div className="pt-2 border-t border-gray-100 mt-3">
          <p className="text-gray-600">
            <span className="font-semibold">{agent.tasks_completed}</span> tasks
            completed
          </p>
        </div>
      </div>
    </div>
  )
}
