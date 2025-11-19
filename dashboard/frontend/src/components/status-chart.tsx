'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface StatusData {
  name: string
  value: number
  color?: string
}

interface StatusChartProps {
  data: StatusData[]
  title?: string
  height?: number
}

export function StatusChart({ data, title = 'Status Distribution', height = 300 }: StatusChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    const chart = echarts.init(chartRef.current)

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
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        left: 'left',
        top: 'middle',
      },
      series: [
        {
          type: 'pie',
          radius: ['40%', '70%'],
          avoidLabelOverlap: false,
          itemStyle: {
            borderRadius: 8,
            borderColor: '#fff',
            borderWidth: 2,
          },
          label: {
            show: false,
            position: 'center',
          },
          emphasis: {
            label: {
              show: true,
              fontSize: 16,
              fontWeight: 'bold',
            },
          },
          labelLine: {
            show: false,
          },
          data: data.map((item) => ({
            name: item.name,
            value: item.value,
            itemStyle: item.color ? { color: item.color } : undefined,
          })),
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
  }, [data, title])

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
