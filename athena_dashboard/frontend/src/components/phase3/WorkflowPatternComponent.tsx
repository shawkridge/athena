/**
 * Workflow Pattern Analyzer Component
 *
 * Displays discovered workflow patterns showing:
 * - Typical task sequences
 * - Transition frequencies and confidence
 * - Process maturity assessment
 * - Pattern recommendations
 */

import React, { useState } from 'react'
import { useSuggestions } from '@/hooks/usePhase3'
import { Card } from '@/components/common/Card'
import { Badge } from '@/components/common/Badge'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface WorkflowPatternComponentProps {
  projectId?: number
  completedTaskId?: number
}

/**
 * Workflow Pattern Component
 */
export const WorkflowPatternComponent: React.FC<WorkflowPatternComponentProps> = ({
  projectId,
  completedTaskId,
}) => {
  const { suggestions, loading, processMaturity } = useSuggestions(
    completedTaskId,
    projectId,
    5
  )
  const [expandedTask, setExpandedTask] = useState<string | null>(null)

  if (loading) {
    return (
      <Card header={<h3 className="text-lg font-semibold text-gray-50">Workflow Patterns</h3>}>
        <div className="animate-pulse space-y-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-700 rounded" />
          ))}
        </div>
      </Card>
    )
  }

  const maturityColor: Record<string, string> = {
    high: 'success',
    medium: 'warning',
    low: 'error',
  }

  // Prepare data for visualization
  const chartData = suggestions.map((s) => ({
    name: (s.task_name || s.task_id).toString().substring(0, 20),
    confidence: (s.confidence || 0) * 100,
    frequency: (s.pattern_frequency || 0) * 100,
  }))

  return (
    <Card
      header={
        <div className="flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-50">Workflow Patterns</h3>
          <Badge variant={maturityColor[processMaturity]}>
            {processMaturity.toUpperCase()} Maturity
          </Badge>
        </div>
      }
    >
      {suggestions.length === 0 ? (
        <div className="p-6 text-center text-gray-400">
          <p>Not enough data to identify patterns</p>
          <p className="text-xs mt-2">Complete more tasks to discover workflow patterns</p>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Pattern visualization chart */}
          {chartData.length > 0 && (
            <div className="bg-gray-900/30 rounded p-4 h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis dataKey="name" stroke="#9ca3af" style={{ fontSize: '12px' }} />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                    }}
                    labelStyle={{ color: '#e5e7eb' }}
                  />
                  <Legend wrapperStyle={{ color: '#9ca3af' }} />
                  <Bar dataKey="confidence" fill="#3b82f6" name="Confidence %" />
                  <Bar dataKey="frequency" fill="#10b981" name="Frequency %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Suggestions list */}
          <div className="space-y-2">
            <h4 className="text-sm font-semibold text-gray-50 mb-3">Recommended Next Tasks</h4>
            {suggestions.map((suggestion, idx) => (
              <div
                key={idx}
                className="p-3 rounded bg-gray-700/20 border border-gray-700/50 cursor-pointer hover:bg-gray-700/30 transition-colors"
                onClick={() =>
                  setExpandedTask(expandedTask === suggestion.task_id ? null : suggestion.task_id)
                }
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="text-gray-50 font-medium">{suggestion.task_name}</p>
                    <p className="text-xs text-gray-400 mt-1">{suggestion.reason}</p>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <div className="text-xs">
                      <span className="text-gray-400">Confidence: </span>
                      <span className="text-blue-400 font-semibold">
                        {(suggestion.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="text-xs">
                      <span className="text-gray-400">Frequency: </span>
                      <span className="text-green-400 font-semibold">
                        {(suggestion.pattern_frequency * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>

                {/* Expanded details */}
                {expandedTask === suggestion.task_id && (
                  <div className="mt-3 pt-3 border-t border-gray-700 text-xs text-gray-400 space-y-1">
                    <p>
                      <span className="text-gray-500">Pattern Type: </span>
                      {suggestion.expected_next_task
                        ? 'Sequential'
                        : 'Alternative'}
                    </p>
                    <p>
                      <span className="text-gray-500">Why: </span>
                      Based on {(suggestion.pattern_frequency * 100).toFixed(0)}% of similar task sequences
                    </p>
                    <p className="mt-2">
                      <button className="text-blue-400 hover:text-blue-300 underline">
                        Start this task →
                      </button>
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Process maturity insights */}
          <div className="mt-4 p-3 rounded bg-gray-700/20 border border-gray-700/50">
            <h4 className="text-sm font-semibold text-gray-50 mb-2">Process Maturity</h4>
            <div className="space-y-1 text-xs text-gray-400">
              {processMaturity === 'high' && (
                <>
                  <p>✓ Strong consistent patterns detected</p>
                  <p>✓ High confidence in recommendations</p>
                  <p>✓ Process is well-established</p>
                </>
              )}
              {processMaturity === 'medium' && (
                <>
                  <p>◇ Some patterns emerging</p>
                  <p>◇ Moderate confidence in suggestions</p>
                  <p>◇ More data needed for optimization</p>
                </>
              )}
              {processMaturity === 'low' && (
                <>
                  <p>○ Insufficient pattern data</p>
                  <p>○ Process still being established</p>
                  <p>○ Complete more tasks for recommendations</p>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}

export default WorkflowPatternComponent
