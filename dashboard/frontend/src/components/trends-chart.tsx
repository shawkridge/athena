'use client'

import { useEffect, useRef, useMemo } from 'react'
import * as echarts from 'echarts'
import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { cn } from '@/lib/utils'

interface TrendData {
  timestamp: string | Date
  value: number
}

interface TrendsChartProps {
  data: TrendData[]
  title?: string
  yAxisLabel?: string
  height?: number
  showTrendIndicator?: boolean
  className?: string
}

type TrendDirection = 'increasing' | 'decreasing' | 'stable'

export function TrendsChart({
  data,
  title = 'Trends',
  yAxisLabel = 'Value',
  height = 300,
  showTrendIndicator = true,
  className,
}: TrendsChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)

  // Calculate trend direction and percentage change
  const trendAnalysis = useMemo(() => {
    if (!data || data.length < 2) {
      return {
        direction: 'stable' as TrendDirection,
        percentageChange: 0,
        color: '#6b7280',
      }
    }

    // Use first half vs second half for trend calculation
    const midpoint = Math.floor(data.length / 2)
    const firstHalf = data.slice(0, midpoint)
    const secondHalf = data.slice(midpoint)

    const firstAvg = firstHalf.reduce((sum, d) => sum + d.value, 0) / firstHalf.length
    const secondAvg = secondHalf.reduce((sum, d) => sum + d.value, 0) / secondHalf.length

    const change = secondAvg - firstAvg
    const percentageChange = firstAvg !== 0 ? (change / Math.abs(firstAvg)) * 100 : 0

    let direction: TrendDirection = 'stable'
    let color = '#6b7280' // gray

    if (Math.abs(percentageChange) < 2) {
      direction = 'stable'
      color = '#6b7280' // gray
    } else if (percentageChange > 0) {
      direction = 'increasing'
      color = '#22c55e' // green
    } else {
      direction = 'decreasing'
      color = '#ef4444' // red
    }

    return { direction, percentageChange, color }
  }, [data])

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    const chart = echarts.init(chartRef.current)

    const timestamps = data.map((d) =>
      typeof d.timestamp === 'string' ? new Date(d.timestamp) : d.timestamp
    )
    const values = data.map((d) => d.value)

    const option = {
      tooltip: {
        trigger: 'axis',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: 'transparent',
        textStyle: {
          color: '#fff',
        },
        formatter: (params: any) => {
          const param = params[0]
          const date = timestamps[param.dataIndex]
          return `
            <div style="font-size: 12px;">
              <div style="margin-bottom: 4px; opacity: 0.8;">${date.toLocaleString()}</div>
              <div style="font-weight: 600;">${yAxisLabel}: ${param.value.toFixed(2)}</div>
            </div>
          `
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: '10%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: timestamps.map((t) => t.toLocaleTimeString()),
        boundaryGap: false,
        axisLine: {
          lineStyle: {
            color: '#e5e7eb',
          },
        },
        axisLabel: {
          color: '#6b7280',
          fontSize: 11,
        },
      },
      yAxis: {
        type: 'value',
        name: yAxisLabel,
        nameTextStyle: {
          color: '#6b7280',
          fontSize: 12,
        },
        axisLine: {
          show: false,
        },
        axisTick: {
          show: false,
        },
        axisLabel: {
          color: '#6b7280',
          fontSize: 11,
        },
        splitLine: {
          lineStyle: {
            color: '#f3f4f6',
            type: 'dashed',
          },
        },
      },
      series: [
        {
          type: 'line',
          data: values,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: {
            color: trendAnalysis.color,
            width: 2,
          },
          itemStyle: {
            color: trendAnalysis.color,
            borderWidth: 2,
            borderColor: '#fff',
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: trendAnalysis.color + '40' },
              { offset: 1, color: trendAnalysis.color + '00' },
            ]),
          },
          emphasis: {
            focus: 'series',
            itemStyle: {
              shadowBlur: 10,
              shadowColor: trendAnalysis.color,
            },
          },
        },
      ],
    }

    chart.setOption(option)

    const handleResize = () => chart.resize()
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.dispose()
    }
  }, [data, yAxisLabel, trendAnalysis.color])

  const getTrendIcon = () => {
    switch (trendAnalysis.direction) {
      case 'increasing':
        return <TrendingUp className="h-4 w-4" />
      case 'decreasing':
        return <TrendingDown className="h-4 w-4" />
      default:
        return <Minus className="h-4 w-4" />
    }
  }

  const getTrendText = () => {
    const abs = Math.abs(trendAnalysis.percentageChange)
    const sign = trendAnalysis.percentageChange >= 0 ? '+' : '-'
    return `${sign}${abs.toFixed(1)}%`
  }

  if (!data || data.length === 0) {
    return (
      <div
        className={cn(
          'flex items-center justify-center bg-muted/30 rounded-lg border',
          className
        )}
        style={{ height: `${height}px` }}
      >
        <p className="text-sm text-muted-foreground">No trend data available</p>
      </div>
    )
  }

  return (
    <div className={cn('relative', className)}>
      {/* Header with title and trend indicator */}
      {(title || showTrendIndicator) && (
        <div className="flex items-center justify-between mb-3">
          {title && <h3 className="text-sm font-medium text-foreground">{title}</h3>}
          {showTrendIndicator && (
            <div
              className={cn(
                'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium',
                trendAnalysis.direction === 'increasing' &&
                  'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400',
                trendAnalysis.direction === 'decreasing' &&
                  'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400',
                trendAnalysis.direction === 'stable' &&
                  'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-400'
              )}
            >
              {getTrendIcon()}
              <span>{getTrendText()}</span>
            </div>
          )}
        </div>
      )}

      {/* Chart */}
      <div ref={chartRef} style={{ height: `${height}px`, width: '100%' }} />
    </div>
  )
}
