import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function SystemHealthPage() {
  const [health, setHealth] = useState<any>(null)
  const [perf, setPerf] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const [healthResp, perfResp] = await Promise.all([
          fetch('http://localhost:8000/api/system/health'),
          fetch('http://localhost:8000/api/system/performance'),
        ])
        if (healthResp.ok) setHealth(await healthResp.json())
        if (perfResp.ok) setPerf(await perfResp.json())
      } catch (error) {
        console.error('Failed to fetch:', error)
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  if (loading) return <div className="p-8">Loading...</div>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">System Health</h1>
        <p className="text-gray-500 mt-2">Performance metrics and resource utilization</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold capitalize">{health?.status}</div>
            <p className="text-xs text-gray-500 mt-1">{health?.uptime}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Success Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(health?.successRate * 100).toFixed(1)}%</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Cache Hit Rate</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(perf?.cacheHitRate * 100).toFixed(0)}%</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Memory Layers Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {health?.layers?.map((layer: any) => (
              <div key={layer.name} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-green-600" />
                  <span className="font-medium">{layer.name}</span>
                </div>
                <Badge variant="secondary">{layer.itemCount?.toLocaleString() || '0'}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Resource Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>CPU</span>
                <span className="font-medium">{perf?.cpuUsage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${perf?.cpuUsage}%` }} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Memory</span>
                <span className="font-medium">{perf?.memoryUsage}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-amber-600 h-2 rounded-full" style={{ width: `${perf?.memoryUsage}%` }} />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Query Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span>P50 Latency</span>
              <Badge variant="secondary">{perf?.queryLatency?.p50}ms</Badge>
            </div>
            <div className="flex justify-between">
              <span>P95 Latency</span>
              <Badge variant="secondary">{perf?.queryLatency?.p95}ms</Badge>
            </div>
            <div className="flex justify-between">
              <span>P99 Latency</span>
              <Badge variant="secondary">{perf?.queryLatency?.p99}ms</Badge>
            </div>
            <div className="flex justify-between mt-3 pt-3 border-t">
              <span>QPS</span>
              <Badge variant="secondary">{perf?.throughput?.queriesPerSecond}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
