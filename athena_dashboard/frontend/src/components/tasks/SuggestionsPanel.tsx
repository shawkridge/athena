/**
 * Suggestions Panel Component
 *
 * Displays Phase 3b data: Suggested next tasks based on workflow patterns
 */

import { Badge } from '@/components/common/Badge'

interface Suggestion {
  task_id: string
  task_name: string
  reason: string
  confidence: number
  pattern_frequency: number
  expected_next_task: string | null
}

interface SuggestionsPanelProps {
  suggestions: Suggestion[]
  maturity: 'low' | 'medium' | 'high'
  loading?: boolean
}

export const SuggestionsPanel = ({ suggestions, maturity, loading }: SuggestionsPanelProps) => {
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-700/30 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  const getMaturityColor = (mat: string) => {
    switch (mat) {
      case 'high':
        return 'text-green-400'
      case 'medium':
        return 'text-yellow-400'
      case 'low':
      default:
        return 'text-gray-400'
    }
  }

  const getMaturityDescription = (mat: string) => {
    switch (mat) {
      case 'high':
        return 'Process is well-established with consistent patterns'
      case 'medium':
        return 'Some patterns observed but more data needed'
      case 'low':
      default:
        return 'Not enough data to make confident recommendations'
    }
  }

  return (
    <div className="space-y-4">
      {/* Process Maturity Card */}
      <div className="p-4 bg-gradient-to-r from-gray-700/30 to-gray-700/10 border border-gray-700/30 rounded">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-gray-400 mb-1">Process Maturity</p>
            <p className={`text-xl font-bold capitalize ${getMaturityColor(maturity)}`}>
              {maturity}
            </p>
            <p className="text-xs text-gray-500 mt-1">{getMaturityDescription(maturity)}</p>
          </div>
          <div className="text-4xl opacity-20">
            {maturity === 'high' && '✓'}
            {maturity === 'medium' && '◐'}
            {maturity === 'low' && '○'}
          </div>
        </div>
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 ? (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-gray-300 px-1">Recommended Next Tasks</h3>
          {suggestions.map((suggestion, index) => (
            <div
              key={suggestion.task_id}
              className={`p-4 rounded border transition ${
                index === 0
                  ? 'bg-blue-500/10 border-blue-500/30'
                  : 'bg-gray-700/20 border-gray-700/30 hover:border-gray-600/50'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {index === 0 && (
                      <span className="text-lg">🎯</span>
                    )}
                    <p className="font-medium text-gray-50">{suggestion.task_name}</p>
                  </div>
                  <p className="text-sm text-gray-400 mt-1">{suggestion.reason}</p>
                </div>
                <div className="text-right ml-2">
                  <p className={`text-lg font-bold ${
                    suggestion.confidence > 0.8 ? 'text-green-400' :
                    suggestion.confidence > 0.6 ? 'text-yellow-400' :
                    'text-gray-400'
                  }`}>
                    {Math.round(suggestion.confidence * 100)}%
                  </p>
                  <p className="text-xs text-gray-500">confidence</p>
                </div>
              </div>

              {/* Pattern Details */}
              <div className="flex items-center gap-2 text-xs text-gray-400">
                <span>Pattern frequency: {Math.round(suggestion.pattern_frequency * 100)}%</span>
                {suggestion.expected_next_task && (
                  <>
                    <span className="text-gray-600">•</span>
                    <span>Then: {suggestion.expected_next_task}</span>
                  </>
                )}
              </div>

              {/* Confidence Indicators */}
              <div className="mt-3">
                <div className="relative h-1.5 bg-gray-700/30 rounded overflow-hidden">
                  <div
                    className={`h-full rounded transition ${
                      suggestion.confidence > 0.8 ? 'bg-green-500' :
                      suggestion.confidence > 0.6 ? 'bg-yellow-500' :
                      'bg-gray-500'
                    }`}
                    style={{ width: `${suggestion.confidence * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="p-8 text-center text-gray-400">
          <p>Not enough data to make suggestions yet.</p>
          <p className="text-sm mt-2">Complete more tasks to build pattern recognition.</p>
        </div>
      )}

      {/* How It Works */}
      <div className="mt-6 p-3 bg-purple-500/10 border border-purple-500/20 rounded text-sm text-purple-300">
        <p className="font-semibold mb-1">How Suggestions Work:</p>
        <ul className="text-xs space-y-1 text-purple-200/80">
          <li>• Analyzes historical task sequences</li>
          <li>• Recommends tasks that typically follow current task</li>
          <li>• Confidence increases with data consistency</li>
          <li>• Updated as you complete more tasks</li>
        </ul>
      </div>
    </div>
  )
}
