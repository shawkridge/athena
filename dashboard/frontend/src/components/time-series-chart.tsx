'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface TimeSeriesData {
  timestamp: string | Date
  value: number
}

interface TimeSeriesChartProps {
  data: TimeSeriesData[]
  title?: string
  yAxisLabel?: string
  height?: number
  color?: string
}

export function TimeSeriesChart({
  data,
  title = 'Time Series',
  yAxisLabel = 'Value',
  height = 300,
  color = '#3b82f6',
}: TimeSeriesChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    const chart = echarts.init(chartRef.current)

    const timestamps = data.map((d) =>
      typeof d.timestamp === 'string' ? new Date(d.timestamp) : d.timestamp
    )
    const values = data.map((d) => d.value)

    const option = {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 14,
          fontWeight: 'normal',
        },
      },
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const param = params[0]
          return `${param.name}<br/>${yAxisLabel}: ${param.value.toFixed(2)}`
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: timestamps.map((t) => t.toLocaleTimeString()),
        boundaryGap: false,
      },
      yAxis: {
        type: 'value',
        name: yAxisLabel,
        nameTextStyle: {
          fontSize: 12,
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
            color: color,
            width: 2,
          },
          itemStyle: {
            color: color,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: color + '40' },
              { offset: 1, color: color + '00' },
            ]),
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
  }, [data, title, yAxisLabel, color])

  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center bg-muted/30 rounded-lg"
        style={{ height: `${height}px` }}
      >
        <p className="text-sm text-muted-foreground">No data available</p>
      </div>
    )
  }

  return <div ref={chartRef} style={{ height: `${height}px`, width: '100%' }} />
}
