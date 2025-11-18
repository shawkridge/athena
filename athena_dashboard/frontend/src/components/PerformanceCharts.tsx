import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { AreaChart, BarChart, Activity, Zap, Clock, TrendingUp } from 'lucide-react'

// Mock data for charts (in production, this would come from the API)
const generateMockData = (days: number) => {
  return Array.from({ length: days }, (_, i) => ({
    date: new Date(Date.now() - (days - i) * 24 * 60 * 60 * 1000).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
    events: Math.floor(Math.random() * 200) + 50,
    consolidations: Math.floor(Math.random() * 10) + 2,
    quality: Math.floor(Math.random() * 15) + 85,
    latency: Math.floor(Math.random() * 50) + 20,
  }))
}

const last7Days = generateMockData(7)
const last30Days = generateMockData(30)

export function PerformanceCharts() {
  return (
    <div className="space-y-6">
      {/* Performance Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[
          {
            label: 'Avg Response Time',
            value: '24ms',
            change: '-12%',
            trend: 'down',
            icon: Zap,
            color: 'green',
          },
          {
            label: 'Events/Day',
            value: '142',
            change: '+8%',
            trend: 'up',
            icon: Activity,
            color: 'blue',
          },
          {
            label: 'Memory Quality',
            value: '94%',
            change: '+2%',
            trend: 'up',
            icon: TrendingUp,
            color: 'purple',
          },
          {
            label: 'Uptime',
            value: '99.9%',
            change: 'stable',
            trend: 'stable',
            icon: Clock,
            color: 'cyan',
          },
        ].map((metric, idx) => {
          const Icon = metric.icon
          return (
            <Card key={idx}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between mb-2">
                  <Icon className={`h-4 w-4 text-${metric.color}-600`} />
                  <Badge
                    variant={metric.trend === 'up' || metric.trend === 'stable' ? 'default' : 'secondary'}
                    className="text-xs"
                  >
                    {metric.change}
                  </Badge>
                </div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {metric.value}
                </p>
                <p className="text-xs text-slate-500 mt-1">{metric.label}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Charts */}
      <Tabs defaultValue="7days" className="space-y-4">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="7days">Last 7 Days</TabsTrigger>
            <TabsTrigger value="30days">Last 30 Days</TabsTrigger>
          </TabsList>
        </div>

        <TabsContent value="7days" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Events Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Daily Events</CardTitle>
                <CardDescription>Episodic events stored per day</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {last7Days.map((day, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-16">{day.date}</span>
                      <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-blue-500 to-purple-500 h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                          style={{ width: `${(day.events / 250) * 100}%` }}
                        >
                          <span className="text-xs font-semibold text-white">
                            {day.events}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Quality Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Memory Quality Score</CardTitle>
                <CardDescription>Quality metrics over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {last7Days.map((day, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-16">{day.date}</span>
                      <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-green-500 to-emerald-500 h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                          style={{ width: `${day.quality}%` }}
                        >
                          <span className="text-xs font-semibold text-white">
                            {day.quality}%
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Consolidations Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Consolidation Runs</CardTitle>
                <CardDescription>Pattern extraction activity</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {last7Days.map((day, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-16">{day.date}</span>
                      <div className="flex gap-1">
                        {Array.from({ length: day.consolidations }).map((_, i) => (
                          <div
                            key={i}
                            className="w-8 h-6 bg-gradient-to-t from-purple-500 to-pink-500 rounded"
                          />
                        ))}
                      </div>
                      <span className="text-sm font-semibold text-slate-900 dark:text-white">
                        {day.consolidations}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Latency Chart */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Response Latency</CardTitle>
                <CardDescription>Average query response time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {last7Days.map((day, idx) => (
                    <div key={idx} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-16">{day.date}</span>
                      <div className="flex-1 bg-slate-100 dark:bg-slate-800 rounded-full h-6 overflow-hidden">
                        <div
                          className="bg-gradient-to-r from-orange-500 to-red-500 h-full rounded-full flex items-center justify-end pr-2 transition-all duration-500"
                          style={{ width: `${(day.latency / 100) * 100}%` }}
                        >
                          <span className="text-xs font-semibold text-white">
                            {day.latency}ms
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="30days" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">30-Day Trend Overview</CardTitle>
              <CardDescription>Extended performance metrics</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-64 flex items-end gap-1">
                {last30Days.map((day, idx) => (
                  <div
                    key={idx}
                    className="flex-1 bg-gradient-to-t from-blue-500 to-purple-500 rounded-t hover:from-blue-600 hover:to-purple-600 transition-all cursor-pointer group relative"
                    style={{ height: `${(day.events / 250) * 100}%` }}
                  >
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-slate-900 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
                      {day.date}: {day.events} events
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
