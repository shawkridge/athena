/**
 * Task Dependency Graph Visualization
 *
 * Displays task dependencies as an interactive graph showing:
 * - Task nodes with status indicators
 * - Dependency edges showing blocking relationships
 * - Task metadata (complexity, effort)
 */

import React, { useMemo, useState } from 'react'
import { EnrichedTask } from '@/types/phase3'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'

interface DependencyGraphComponentProps {
  tasks: EnrichedTask[]
}

interface GraphNode {
  id: string | number
  label: string
  status: string
  blocked: boolean
  complexity?: number
}

interface GraphEdge {
  from: string | number
  to: string | number
  type: 'blocks' | 'related' | 'enables'
}

/**
 * Dependency Graph Component
 */
export const DependencyGraphComponent: React.FC<DependencyGraphComponentProps> = ({ tasks }) => {
  const [selectedTask, setSelectedTask] = useState<string | number | null>(null)

  const { nodes, edges } = useMemo(() => {
    const nodes: GraphNode[] = tasks.map((task) => ({
      id: task.id,
      label: (task.content || task.title || 'Untitled').substring(0, 30),
      status: task.status,
      blocked: task.blocked || false,
      complexity: task.complexity_score,
    }))

    const edges: GraphEdge[] = []
    tasks.forEach((task) => {
      // Add blocking edges (dependencies)
      if (task.dependencies && task.dependencies.length > 0) {
        task.dependencies.forEach((depId) => {
          edges.push({
            from: depId,
            to: task.id,
            type: 'blocks',
          })
        })
      }
    })

    return { nodes, edges }
  }, [tasks])

  if (nodes.length === 0) {
    return (
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Task Dependencies</h3>}>
        <p className="text-gray-400 text-center py-6">No tasks to display</p>
      </Card>
    )
  }

  // Calculate simple layout (grid-based instead of force-directed for stability)
  const layout = useMemo(() => {
    const positionMap = new Map<string | number, { x: number; y: number }>()
    const cols = Math.ceil(Math.sqrt(nodes.length))
    const spacing = 120

    nodes.forEach((node, idx) => {
      const col = idx % cols
      const row = Math.floor(idx / cols)
      positionMap.set(node.id, {
        x: col * spacing + 60,
        y: row * spacing + 60,
      })
    })

    return positionMap
  }, [nodes])

  const getNodeColor = (node: GraphNode) => {
    if (node.blocked) return '#dc2626' // red
    if (node.status === 'completed') return '#16a34a' // green
    if (node.status === 'in_progress' || node.status === 'active') return '#2563eb' // blue
    return '#6366f1' // indigo
  }

  const viewWidth = Math.ceil(Math.sqrt(nodes.length)) * 120 + 100
  const viewHeight = Math.ceil(nodes.length / Math.sqrt(nodes.length)) * 120 + 100

  return (
    <Card
      header={
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-50">Task Dependencies</h3>
          <span className="text-xs text-gray-400">
            {nodes.length} tasks · {edges.length} dependencies
          </span>
        </div>
      }
    >
      <div className="bg-gray-900/50 rounded border border-gray-700 overflow-x-auto p-4">
        <svg width={Math.min(viewWidth, 800)} height={Math.min(viewHeight, 600)} className="mx-auto">
          {/* Draw edges first (behind nodes) */}
          {edges.map((edge, idx) => {
            const from = layout.get(edge.from)
            const to = layout.get(edge.to)
            if (!from || !to) return null

            const strokeColor =
              edge.type === 'blocks' ? '#ef4444' : edge.type === 'enables' ? '#10b981' : '#6b7280'

            return (
              <g key={`edge-${idx}`}>
                {/* Arrow line */}
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={strokeColor}
                  strokeWidth="2"
                  markerEnd={`url(#arrowhead-${edge.type})`}
                  opacity="0.6"
                />
                {/* Label */}
                <text
                  x={(from.x + to.x) / 2}
                  y={(from.y + to.y) / 2 - 5}
                  textAnchor="middle"
                  fontSize="11"
                  fill="#9ca3af"
                  opacity="0.7"
                >
                  {edge.type}
                </text>
              </g>
            )
          })}

          {/* Arrow markers */}
          <defs>
            <marker
              id="arrowhead-blocks"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" fill="#ef4444" />
            </marker>
            <marker
              id="arrowhead-enables"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" fill="#10b981" />
            </marker>
            <marker
              id="arrowhead-related"
              markerWidth="10"
              markerHeight="10"
              refX="9"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 10 3, 0 6" fill="#6b7280" />
            </marker>
          </defs>

          {/* Draw nodes */}
          {nodes.map((node) => {
            const pos = layout.get(node.id)
            if (!pos) return null

            const isSelected = selectedTask === node.id
            const nodeColor = getNodeColor(node)

            return (
              <g
                key={`node-${node.id}`}
                onClick={() => setSelectedTask(isSelected ? null : node.id)}
                style={{ cursor: 'pointer' }}
              >
                {/* Node circle */}
                <circle
                  cx={pos.x}
                  cy={pos.y}
                  r={isSelected ? 35 : 28}
                  fill={nodeColor}
                  opacity={isSelected ? 1 : 0.8}
                  stroke={isSelected ? '#fbbf24' : '#4b5563'}
                  strokeWidth={isSelected ? 3 : 2}
                  className="transition-all"
                />

                {/* Node label */}
                <text
                  x={pos.x}
                  y={pos.y - 5}
                  textAnchor="middle"
                  fontSize="12"
                  fontWeight="600"
                  fill="white"
                  className="pointer-events-none"
                >
                  {node.label.substring(0, 15)}
                </text>

                {/* Status indicator */}
                <text
                  x={pos.x}
                  y={pos.y + 10}
                  textAnchor="middle"
                  fontSize="10"
                  fill="white"
                  opacity="0.8"
                  className="pointer-events-none"
                >
                  {node.status.substring(0, 3).toUpperCase()}
                </text>

                {/* Complexity badge (if selected) */}
                {isSelected && node.complexity && (
                  <text
                    x={pos.x}
                    y={pos.y + 28}
                    textAnchor="middle"
                    fontSize="10"
                    fill="#fbbf24"
                    className="pointer-events-none"
                  >
                    C:{node.complexity}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>

      {/* Legend */}
      <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-red-600" />
          <span className="text-gray-400">Blocked</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-600" />
          <span className="text-gray-400">Completed</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-600" />
          <span className="text-gray-400">Active</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-indigo-600" />
          <span className="text-gray-400">Pending</span>
        </div>
      </div>

      {/* Selected task details */}
      {selectedTask && (
        <div className="mt-4 p-3 rounded bg-gray-700/30 border border-gray-700">
          <p className="text-sm text-gray-400">
            Selected: <span className="text-gray-50 font-semibold">{selectedTask}</span>
          </p>
          <p className="text-xs text-gray-500 mt-1">Click to deselect</p>
        </div>
      )}
    </Card>
  )
}

export default DependencyGraphComponent
