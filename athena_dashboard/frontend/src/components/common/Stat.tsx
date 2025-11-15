/**
 * Stat Card Component - Display a single metric
 */

import { ReactNode } from 'react'

interface StatProps {
  label: string
  value: string | number
  unit?: string
  icon?: ReactNode
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
}

const colorClasses = {
  blue: 'from-blue-500 to-cyan-500',
  green: 'from-green-500 to-emerald-500',
  yellow: 'from-yellow-500 to-orange-500',
  red: 'from-red-500 to-pink-500',
  purple: 'from-purple-500 to-pink-500',
}

const bgClasses = {
  blue: 'bg-blue-900/20',
  green: 'bg-green-900/20',
  yellow: 'bg-yellow-900/20',
  red: 'bg-red-900/20',
  purple: 'bg-purple-900/20',
}

export const Stat = ({
  label,
  value,
  unit,
  icon,
  color = 'blue',
  trend,
  trendValue,
}: StatProps) => {
  return (
    <div className={`rounded-lg border border-gray-700 ${bgClasses[color]} p-6`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-gray-400">{label}</p>
          <div className="mt-2 flex items-baseline gap-2">
            <p className="text-3xl font-bold text-gray-50">{value}</p>
            {unit && <p className="text-sm text-gray-400">{unit}</p>}
          </div>

          {trend && trendValue && (
            <p
              className={`mt-2 text-sm font-medium ${
                trend === 'up'
                  ? 'text-green-400'
                  : trend === 'down'
                    ? 'text-red-400'
                    : 'text-gray-400'
              }`}
            >
              {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trendValue}
            </p>
          )}
        </div>

        {icon && (
          <div className={`text-4xl ${icon}`}>
          </div>
        )}
      </div>
    </div>
  )
}

export default Stat
