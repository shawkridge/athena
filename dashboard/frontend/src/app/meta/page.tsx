'use client'

import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { formatNumber, getScoreColor } from '@/lib/utils'
import { Gauge } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'
import ReactECharts from 'echarts-for-react'

export default function MetaMemoryPage() {
  const { data: stats } = useQuery({
    queryKey: ['meta-stats'],
    queryFn: api.getMetaStatistics,
  })

  // Quality distribution chart
  const qualityDistributionOption = {
    title: {
      text: 'Memory Quality Distribution',
      left: 'center',
      textStyle: { fontSize: 16, fontWeight: 600 },
    },
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    series: [
      {
        type: 'pie',
        radius: '60%',
        data: [
          { value: stats?.high_quality_count || 0, name: 'High Quality (>0.8)', itemStyle: { color: '#22c55e' } },
          { value: stats?.medium_quality_count || 0, name: 'Medium Quality (0.5-0.8)', itemStyle: { color: '#eab308' } },
          { value: stats?.low_quality_count || 0, name: 'Low Quality (<0.5)', itemStyle: { color: '#ef4444' } },
        ],
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)',
          },
        },
      },
    ],
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-pink-100">
            <Gauge className="h-8 w-8 text-pink-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Meta-Memory</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Quality tracking, expertise assessment, and cognitive load
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Avg Memory Quality</div>
          <div className={`text-2xl font-bold ${getScoreColor(stats?.avg_quality || 0)}`}>
            {((stats?.avg_quality || 0) * 100).toFixed(1)}%
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Assessments</div>
          <div className="text-2xl font-bold">{formatNumber(stats?.total_assessments || 0)}</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Cognitive Load</div>
          <div className={`text-2xl font-bold ${getScoreColor(1 - (stats?.cognitive_load || 0))}`}>
            {((stats?.cognitive_load || 0) * 100).toFixed(0)}%
          </div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Expertise Level</div>
          <div className={`text-2xl font-bold ${getScoreColor(stats?.avg_expertise || 0)}`}>
            {((stats?.avg_expertise || 0) * 100).toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Quality Distribution */}
      <div className="bg-card border rounded-lg p-6">
        <ReactECharts
          option={qualityDistributionOption}
          style={{ height: '350px', width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      </div>

      {/* Quality Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Quality Metrics</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">High Quality Memories</span>
              <span className="text-sm font-medium text-green-600">
                {formatNumber(stats?.high_quality_count || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Medium Quality Memories</span>
              <span className="text-sm font-medium text-yellow-600">
                {formatNumber(stats?.medium_quality_count || 0)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Low Quality Memories</span>
              <span className="text-sm font-medium text-red-600">
                {formatNumber(stats?.low_quality_count || 0)}
              </span>
            </div>
            <div className="pt-3 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Quality Score Range</span>
                <span className="text-sm font-medium">
                  {(stats?.min_quality || 0).toFixed(2)} - {(stats?.max_quality || 0).toFixed(2)}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Cognitive Insights</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Current Cognitive Load</span>
              <span className="text-sm font-medium">
                {((stats?.cognitive_load || 0) * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Working Memory Capacity</span>
              <span className="text-sm font-medium">
                {formatNumber(stats?.working_memory_capacity || 7)} items
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">Context Switches</span>
              <span className="text-sm font-medium">
                {formatNumber(stats?.context_switches || 0)}
              </span>
            </div>
            <div className="pt-3 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Focus Duration</span>
                <span className="text-sm font-medium">
                  {stats?.avg_focus_duration || 0} min
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Expertise Areas */}
      <div className="bg-card border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-4">Expertise Assessment</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Meta-memory tracks your expertise across different domains based on memory quality,
          usage patterns, and successful recalls.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Average Expertise</div>
            <div className={`text-xl font-bold ${getScoreColor(stats?.avg_expertise || 0)}`}>
              {((stats?.avg_expertise || 0) * 100).toFixed(0)}%
            </div>
          </div>
          <div className="p-4 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Tracked Domains</div>
            <div className="text-xl font-bold">{stats?.expertise_domains || 0}</div>
          </div>
          <div className="p-4 bg-secondary rounded-lg">
            <div className="text-sm text-muted-foreground mb-1">Improvement Rate</div>
            <div className="text-xl font-bold text-green-600">
              +{((stats?.expertise_improvement_rate || 0) * 100).toFixed(1)}%
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
