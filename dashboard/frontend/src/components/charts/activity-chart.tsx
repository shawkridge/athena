'use client'

import { useQuery } from '@tanstack/react-query'
import ReactECharts from 'echarts-for-react'
import { api } from '@/lib/api'
import { TrendingUp } from 'lucide-react'

export function ActivityChart() {
  const { data: systemStatus } = useQuery({
    queryKey: ['system-status'],
    queryFn: api.getSystemStatus,
  })

  // Generate mock time series data for demonstration
  // In production, this would come from a dedicated endpoint
  const generateMockData = () => {
    const now = new Date()
    const data: { time: string; episodic: number; semantic: number; graph: number }[] = []

    for (let i = 23; i >= 0; i--) {
      const time = new Date(now.getTime() - i * 60 * 60 * 1000)
      data.push({
        time: time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        episodic: Math.floor(Math.random() * 100) + 50,
        semantic: Math.floor(Math.random() * 80) + 30,
        graph: Math.floor(Math.random() * 60) + 20,
      })
    }

    return data
  }

  const data = generateMockData()

  const option = {
    title: {
      text: 'System Activity (Last 24 Hours)',
      left: 'left',
      textStyle: {
        fontSize: 16,
        fontWeight: 600,
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross',
      },
    },
    legend: {
      data: ['Episodic Events', 'Semantic Queries', 'Graph Operations'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '15%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: data.map((d) => d.time),
      axisLabel: {
        rotate: 45,
        interval: 2,
      },
    },
    yAxis: {
      type: 'value',
      name: 'Operations',
    },
    series: [
      {
        name: 'Episodic Events',
        type: 'line',
        smooth: true,
        data: data.map((d) => d.episodic),
        itemStyle: { color: '#3b82f6' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.05)' },
            ],
          },
        },
      },
      {
        name: 'Semantic Queries',
        type: 'line',
        smooth: true,
        data: data.map((d) => d.semantic),
        itemStyle: { color: '#a855f7' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(168, 85, 247, 0.3)' },
              { offset: 1, color: 'rgba(168, 85, 247, 0.05)' },
            ],
          },
        },
      },
      {
        name: 'Graph Operations',
        type: 'line',
        smooth: true,
        data: data.map((d) => d.graph),
        itemStyle: { color: '#06b6d4' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(6, 182, 212, 0.3)' },
              { offset: 1, color: 'rgba(6, 182, 212, 0.05)' },
            ],
          },
        },
      },
    ],
  }

  return (
    <div className="bg-card border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">Activity Trends</h3>
        </div>
        <div className="text-sm text-muted-foreground">Real-time monitoring</div>
      </div>

      <ReactECharts
        option={option}
        style={{ height: '300px', width: '100%' }}
        opts={{ renderer: 'canvas' }}
        notMerge={true}
        lazyUpdate={true}
      />
    </div>
  )
}
