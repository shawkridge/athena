/**
 * Predictions Chart Component
 *
 * Displays Phase 3c data: Effort predictions with confidence intervals
 */

interface Prediction {
  task_id: string
  task_type: string
  predicted_effort_minutes: number
  confidence: number
  range: {
    optimistic: number
    expected: number
    pessimistic: number
  }
  historical_accuracy: number
  bias_factor: number
}

interface PredictionsChartProps {
  predictions: Prediction[]
  loading?: boolean
}

export const PredictionsChart = ({ predictions, loading }: PredictionsChartProps) => {
  if (loading) {
    return (
      <div className="space-y-3">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 bg-gray-700/30 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  if (!predictions || predictions.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400">
        No predictions available yet. Complete some tasks to train the model.
      </div>
    )
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'text-green-400'
    if (confidence > 0.6) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getBiasLabel = (bias: number) => {
    if (bias > 1.1) return 'Underestimating'
    if (bias < 0.9) return 'Overestimating'
    return 'Accurate'
  }

  return (
    <div className="space-y-4">
      {predictions.map((pred) => (
        <div key={pred.task_id} className="p-4 bg-gray-700/20 border border-gray-700/30 rounded">
          <div className="flex items-start justify-between mb-3">
            <div>
              <p className="font-medium text-gray-50">{pred.task_id}</p>
              <p className="text-xs text-gray-400 capitalize">{pred.task_type}</p>
            </div>
            <div className="text-right">
              <p className={`text-sm font-semibold ${getConfidenceColor(pred.confidence)}`}>
                {Math.round(pred.confidence * 100)}% confident
              </p>
              <p className="text-xs text-gray-500">{pred.historical_accuracy}% historical accuracy</p>
            </div>
          </div>

          {/* Effort Prediction Range */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-2 text-sm">
              <span className="text-gray-400">Effort estimate:</span>
              <span className="text-gray-50 font-semibold">{pred.expected} minutes</span>
            </div>

            {/* Range Visualization */}
            <div className="relative h-8 bg-gray-800/50 rounded overflow-hidden">
              {/* Background bar */}
              <div className="absolute inset-0 flex items-center">
                <div className="w-full h-1 bg-gray-700/50" />
              </div>

              {/* Range bar */}
              <div className="absolute inset-0 flex items-center px-2">
                <div
                  className="relative h-6 bg-gradient-to-r from-blue-500/30 to-blue-500/10 rounded border border-blue-500/30"
                  style={{
                    left: `${(pred.range.optimistic / 300) * 100}%`,
                    width: `${((pred.range.pessimistic - pred.range.optimistic) / 300) * 100}%`,
                  }}
                >
                  {/* Expected marker */}
                  <div
                    className="absolute top-1/2 -translate-y-1/2 w-1 h-full bg-blue-400"
                    style={{ left: `${((pred.expected - pred.range.optimistic) / (pred.range.pessimistic - pred.range.optimistic)) * 100}%` }}
                  />
                </div>
              </div>

              {/* Labels */}
              <div className="absolute inset-0 flex items-center justify-between px-2 text-xs font-semibold text-gray-400 pointer-events-none">
                <span>{pred.range.optimistic}m</span>
                <span>{pred.range.pessimistic}m</span>
              </div>
            </div>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-2 text-sm">
            <div className="p-2 bg-gray-800/30 rounded">
              <p className="text-xs text-gray-500">Optimistic</p>
              <p className="text-gray-50 font-medium">{pred.range.optimistic}m</p>
            </div>
            <div className="p-2 bg-gray-800/30 rounded border border-blue-500/20">
              <p className="text-xs text-gray-500">Expected</p>
              <p className="text-blue-400 font-medium">{pred.range.expected}m</p>
            </div>
            <div className="p-2 bg-gray-800/30 rounded">
              <p className="text-xs text-gray-500">Pessimistic</p>
              <p className="text-gray-50 font-medium">{pred.range.pessimistic}m</p>
            </div>
          </div>

          {/* Bias Information */}
          {pred.bias_factor !== 1.0 && (
            <div className="mt-3 p-2 bg-amber-500/10 border border-amber-500/20 rounded text-sm text-amber-300">
              {getBiasLabel(pred.bias_factor)}: estimates are ~{Math.round((Math.abs(pred.bias_factor - 1) * 100))}%{' '}
              {pred.bias_factor > 1 ? 'lower' : 'higher'} than actual
            </div>
          )}
        </div>
      ))}

      {/* Legend */}
      <div className="mt-4 p-3 bg-gray-700/10 rounded border border-gray-700/30 text-xs text-gray-400">
        <p className="font-semibold mb-2">How to read predictions:</p>
        <ul className="space-y-1">
          <li>• <strong>Confidence:</strong> How reliable the prediction is based on historical data</li>
          <li>• <strong>Range:</strong> Optimistic (best case) to Pessimistic (worst case) estimates</li>
          <li>• <strong>Bias:</strong> Whether the model tends to over/underestimate for this task type</li>
        </ul>
      </div>
    </div>
  )
}
