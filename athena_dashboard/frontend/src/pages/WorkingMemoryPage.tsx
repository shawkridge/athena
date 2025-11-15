import { Card } from '@/components/common/Card'
import { GaugeChart } from '@/components/charts/GaugeChart'
import { Badge } from '@/components/common/Badge'
import { useAPI } from '@/hooks'

interface WorkingItem {
  id: string
  title: string
  age: string
  importance: number
}

interface WorkingResponse {
  items: WorkingItem[]
  cognitive: { load: number; capacity: number }
}

export const WorkingMemoryPage = () => {
  const { data, loading } = useAPI<WorkingResponse>('/api/working-memory/current')

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Working Memory</h1>
        <p className="text-gray-400">Current 7±2 items, cognitive load</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="flex items-center justify-center">
          <GaugeChart
            value={(data?.cognitive.load || 0) / (data?.cognitive.capacity || 100) * 100}
            title="Cognitive Load"
          />
        </Card>

        <Card header={<h3 className="text-lg font-semibold text-gray-50">Current Items ({data?.items.length || 0}/9)</h3>}>
          <div className="space-y-2">
            {data?.items.map((item) => (
              <div key={item.id} className="p-2 rounded bg-gray-700/30 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-gray-50">{item.title}</span>
                  <Badge variant={item.importance > 70 ? 'error' : 'info'}>{item.age}</Badge>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}

export default WorkingMemoryPage
