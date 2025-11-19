'use client'

import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn, formatNumber } from '@/lib/utils'

interface QuickStatsCardProps {
  title: string
  value: number
  previousValue?: number
  icon?: LucideIcon
  iconColor?: string
  iconBgColor?: string
  format?: 'number' | 'percentage' | 'decimal'
  className?: string
  trend?: 'positive' | 'negative' | 'neutral'
  showTrend?: boolean
}

export function QuickStatsCard({
  title,
  value,
  previousValue,
  icon: Icon,
  iconColor = 'text-blue-600',
  iconBgColor = 'bg-blue-100 dark:bg-blue-900/30',
  format = 'number',
  className,
  trend,
  showTrend = true,
}: QuickStatsCardProps) {
  // Calculate trend if previousValue is provided and trend is not explicitly set
  const calculatedTrend = (() => {
    if (trend) return trend

    if (previousValue === undefined || previousValue === value) {
      return 'neutral'
    }

    return value > previousValue ? 'positive' : 'negative'
  })()

  // Calculate percentage change
  const percentageChange = (() => {
    if (previousValue === undefined || previousValue === 0) return 0

    const change = value - previousValue
    return (change / Math.abs(previousValue)) * 100
  })()

  // Format the value based on format type
  const formatValue = (val: number): string => {
    switch (format) {
      case 'percentage':
        return `${val.toFixed(1)}%`
      case 'decimal':
        return val.toFixed(2)
      case 'number':
      default:
        return formatNumber(val)
    }
  }

  // Get trend icon
  const getTrendIcon = () => {
    switch (calculatedTrend) {
      case 'positive':
        return <TrendingUp className="h-3.5 w-3.5" />
      case 'negative':
        return <TrendingDown className="h-3.5 w-3.5" />
      default:
        return <Minus className="h-3.5 w-3.5" />
    }
  }

  // Get trend color classes
  const getTrendColorClasses = () => {
    switch (calculatedTrend) {
      case 'positive':
        return 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20'
      case 'negative':
        return 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
      default:
        return 'text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50'
    }
  }

  return (
    <div
      className={cn(
        'bg-card border rounded-lg p-4 transition-all hover:shadow-md',
        className
      )}
    >
      {/* Header with icon */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-muted-foreground">{title}</h3>
        {Icon && (
          <div className={cn('p-2 rounded-lg', iconBgColor)}>
            <Icon className={cn('h-4 w-4', iconColor)} />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="mb-2">
        <p className="text-2xl font-bold text-foreground">{formatValue(value)}</p>
      </div>

      {/* Trend indicator */}
      {showTrend && previousValue !== undefined && (
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
              getTrendColorClasses()
            )}
          >
            {getTrendIcon()}
            <span>
              {percentageChange >= 0 ? '+' : ''}
              {percentageChange.toFixed(1)}%
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            from {formatValue(previousValue)}
          </span>
        </div>
      )}

      {/* No trend indicator */}
      {(!showTrend || previousValue === undefined) && (
        <div className="h-5" /> // Spacer to maintain consistent height
      )}
    </div>
  )
}
