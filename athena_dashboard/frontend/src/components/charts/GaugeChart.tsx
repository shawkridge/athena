/**
 * Gauge chart component for health/quality metrics
 */

interface GaugeChartProps {
  value: number // 0-100
  max?: number
  title?: string
  color?: 'success' | 'warning' | 'error'
}

const getGaugeColor = (value: number, color?: string): string => {
  if (color) {
    const colorMap: Record<string, string> = {
      success: '#10B981',
      warning: '#F59E0B',
      error: '#EF4444',
    }
    return colorMap[color] || '#3B82F6'
  }

  if (value >= 80) return '#10B981'
  if (value >= 60) return '#F59E0B'
  return '#EF4444'
}

export const GaugeChart = ({
  value,
  max = 100,
  title,
  color,
}: GaugeChartProps) => {
  const percentage = Math.min(100, (value / max) * 100)
  const gaugeColor = getGaugeColor(percentage, color)

  return (
    <div className="flex flex-col items-center justify-center">
      {title && <p className="text-sm text-gray-400 mb-4">{title}</p>}

      <div className="relative w-32 h-32">
        {/* Background circle */}
        <svg className="w-full h-full" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke="#374151"
            strokeWidth="8"
          />
          {/* Progress circle */}
          <circle
            cx="50"
            cy="50"
            r="45"
            fill="none"
            stroke={gaugeColor}
            strokeWidth="8"
            strokeDasharray={`${2 * Math.PI * 45}`}
            strokeDashoffset={`${2 * Math.PI * 45 * (1 - percentage / 100)}`}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.3s ease' }}
          />
        </svg>

        {/* Center value */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="text-center">
            <p className="text-2xl font-bold text-gray-50">{Math.round(percentage)}</p>
            <p className="text-xs text-gray-400">%</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default GaugeChart
