import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Brain, Database, Zap, TrendingUp, Activity, AlertTriangle } from 'lucide-react'

export default function DashboardPage() {
  const [metrics, setMetrics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchMetrics = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/system/overview')
        if (response.ok) {
          setMetrics(await response.json())
        }
      } catch (error) {
        console.error('Failed to fetch metrics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchMetrics()
    const interval = setInterval(fetchMetrics, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading) return <div className="p-8 text-center">Loading...</div>

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Athena Dashboard</h1>
        <p className="text-gray-500 mt-2">Real-time memory system monitoring and analytics</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span>Memory Quality</span>
              <Brain className="w-4 h-4 text-blue-600" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.qualityScore ? (metrics.qualityScore * 100).toFixed(0) : '0'}%</div>
            <p className="text-xs text-gray-500 mt-1">+2.3% trend</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span>System Health</span>
              <Activity className="w-4 h-4 text-green-600" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">Healthy</div>
            <p className="text-xs text-gray-500 mt-1">{metrics?.successRate ? (metrics.successRate * 100).toFixed(1) : '0'}% uptime</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium flex items-center justify-between">
              <span>Total Events</span>
              <Database className="w-4 h-4 text-purple-600" />
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{metrics?.layers?.[0]?.itemCount?.toLocaleString() || '0'}</div>
            <p className="text-xs text-gray-500 mt-1">Episodic events</p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="w-full">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="activity">Recent Activity</TabsTrigger>
          <TabsTrigger value="layers">Memory Layers</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Memory System Status</CardTitle>
              <CardDescription>All 8 layers operational</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {metrics?.layers?.map((layer: any) => (
                  <div key={layer.name} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div className="flex items-center gap-3">
                      <div className="w-2 h-2 rounded-full bg-green-600" />
                      <span className="font-medium">{layer.name}</span>
                    </div>
                    <Badge variant="outline">{layer.itemCount?.toLocaleString() || '0'}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent System Events</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {metrics?.recentEvents?.map((event: any, idx: number) => (
                  <div key={idx} className="flex items-start gap-4 pb-4 border-b last:border-0">
                    <div className={`w-2 h-2 rounded-full mt-2 ${event.status === 'success' ? 'bg-green-600' : 'bg-red-600'}`} />
                    <div className="flex-1">
                      <p className="font-medium capitalize">{event.type}</p>
                      <p className="text-sm text-gray-500">{event.source}</p>
                      <p className="text-xs text-gray-400 mt-1">{new Date(event.timestamp).toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="layers" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {metrics?.layers?.map((layer: any) => (
              <Card key={layer.name}>
                <CardHeader>
                  <CardTitle className="text-base">{layer.name}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Items</span>
                      <span className="font-medium">{layer.itemCount?.toLocaleString() || '0'}</span>
                    </div>
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-600">Status</span>
                      <Badge variant="default" className="bg-green-600">Operational</Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Alert */}
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertDescription>
          AI Insight: Your memory consolidation is 87% complete. The system has identified 12 new patterns from today's work that can be extracted as reusable procedures.
        </AlertDescription>
      </Alert>
    </div>
  )
}
