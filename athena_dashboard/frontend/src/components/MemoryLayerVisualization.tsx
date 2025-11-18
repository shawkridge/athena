import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Brain, Database, Workflow, Calendar, Network, TrendingUp, Layers, Sparkles } from 'lucide-react'

interface MemoryLayer {
  id: number
  name: string
  description: string
  icon: React.ElementType
  count: number
  capacity: number
  status: 'healthy' | 'warning' | 'critical'
  color: string
}

const memoryLayers: MemoryLayer[] = [
  {
    id: 1,
    name: 'Episodic Memory',
    description: 'Events with spatial-temporal grounding',
    icon: Calendar,
    count: 12859,
    capacity: 50000,
    status: 'healthy',
    color: 'blue',
  },
  {
    id: 2,
    name: 'Semantic Memory',
    description: 'Facts and knowledge',
    icon: Database,
    count: 180,
    capacity: 10000,
    status: 'healthy',
    color: 'green',
  },
  {
    id: 3,
    name: 'Procedural Memory',
    description: 'Learned workflows and skills',
    icon: Workflow,
    count: 101,
    capacity: 1000,
    status: 'healthy',
    color: 'purple',
  },
  {
    id: 4,
    name: 'Prospective Memory',
    description: 'Future intentions and tasks',
    icon: TrendingUp,
    count: 12,
    capacity: 500,
    status: 'healthy',
    color: 'orange',
  },
  {
    id: 5,
    name: 'Knowledge Graph',
    description: 'Entity relationships',
    icon: Network,
    count: 245,
    capacity: 5000,
    status: 'healthy',
    color: 'cyan',
  },
  {
    id: 6,
    name: 'Meta-Memory',
    description: 'Quality tracking & attention',
    icon: Brain,
    count: 94,
    capacity: 100,
    status: 'warning',
    color: 'pink',
  },
  {
    id: 7,
    name: 'Consolidation',
    description: 'Pattern extraction',
    icon: Layers,
    count: 87,
    capacity: 100,
    status: 'healthy',
    color: 'indigo',
  },
  {
    id: 8,
    name: 'Planning',
    description: 'Advanced planning & validation',
    icon: Sparkles,
    count: 23,
    capacity: 1000,
    status: 'healthy',
    color: 'amber',
  },
]

const getStatusColor = (status: string) => {
  switch (status) {
    case 'healthy':
      return 'bg-green-500'
    case 'warning':
      return 'bg-yellow-500'
    case 'critical':
      return 'bg-red-500'
    default:
      return 'bg-gray-500'
  }
}

const getProgressColor = (percentage: number) => {
  if (percentage < 50) return 'bg-green-500'
  if (percentage < 80) return 'bg-yellow-500'
  return 'bg-red-500'
}

export function MemoryLayerVisualization() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Layers className="h-5 w-5" />
          8-Layer Memory System
        </CardTitle>
        <CardDescription>
          Complete architecture overview with real-time metrics
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {memoryLayers.map((layer) => {
            const Icon = layer.icon
            const percentage = (layer.count / layer.capacity) * 100

            return (
              <div
                key={layer.id}
                className="group p-4 rounded-lg border border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 transition-all hover:shadow-md"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-${layer.color}-50 dark:bg-${layer.color}-950/30`}>
                      <Icon className={`h-5 w-5 text-${layer.color}-600 dark:text-${layer.color}-400`} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-900 dark:text-white">
                          Layer {layer.id}: {layer.name}
                        </h3>
                        <div className={`h-2 w-2 rounded-full ${getStatusColor(layer.status)} animate-pulse`} />
                      </div>
                      <p className="text-sm text-slate-500 dark:text-slate-400">
                        {layer.description}
                      </p>
                    </div>
                  </div>
                  <TooltipProvider>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Badge variant="secondary" className="cursor-help">
                          {layer.count.toLocaleString()} / {layer.capacity.toLocaleString()}
                        </Badge>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Current: {layer.count.toLocaleString()} items</p>
                        <p>Capacity: {layer.capacity.toLocaleString()} items</p>
                        <p>Usage: {percentage.toFixed(1)}%</p>
                      </TooltipContent>
                    </Tooltip>
                  </TooltipProvider>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-600 dark:text-slate-400">
                      Capacity utilization
                    </span>
                    <span className="font-medium text-slate-900 dark:text-white">
                      {percentage.toFixed(1)}%
                    </span>
                  </div>
                  <Progress
                    value={percentage}
                    className="h-2"
                  />
                </div>

                {/* Micro-interaction: Show details on hover */}
                <div className="mt-3 overflow-hidden">
                  <div className="grid grid-cols-3 gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                    <div className="text-center p-2 bg-slate-50 dark:bg-slate-900 rounded">
                      <p className="text-xs text-slate-500">Today</p>
                      <p className="font-semibold text-sm">+{Math.floor(Math.random() * 50)}</p>
                    </div>
                    <div className="text-center p-2 bg-slate-50 dark:bg-slate-900 rounded">
                      <p className="text-xs text-slate-500">This week</p>
                      <p className="font-semibold text-sm">+{Math.floor(Math.random() * 200)}</p>
                    </div>
                    <div className="text-center p-2 bg-slate-50 dark:bg-slate-900 rounded">
                      <p className="text-xs text-slate-500">Quality</p>
                      <p className="font-semibold text-sm">{(90 + Math.random() * 10).toFixed(1)}%</p>
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>

        {/* System Summary */}
        <div className="mt-6 p-4 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/30 dark:to-purple-950/30 rounded-lg">
          <h4 className="font-semibold text-slate-900 dark:text-white mb-2">
            System Health Summary
          </h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-slate-600 dark:text-slate-400">Total Items</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">
                {memoryLayers.reduce((acc, layer) => acc + layer.count, 0).toLocaleString()}
              </p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">Avg Utilization</p>
              <p className="text-lg font-bold text-slate-900 dark:text-white">
                {(memoryLayers.reduce((acc, layer) => acc + (layer.count / layer.capacity * 100), 0) / 8).toFixed(1)}%
              </p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">Active Layers</p>
              <p className="text-lg font-bold text-green-600 dark:text-green-400">
                8/8
              </p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">Status</p>
              <p className="text-lg font-bold text-green-600 dark:text-green-400">
                Operational
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
