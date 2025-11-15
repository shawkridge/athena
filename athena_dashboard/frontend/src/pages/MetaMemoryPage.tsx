import { Card } from '@/components/common/Card'
import { GaugeChart } from '@/components/charts/GaugeChart'
import { useAPI } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface MetaResponse {
  quality: number
  expertise: { domain: string; score: number }[]
  attention: { layer: string; allocation: number }[]
}

export const MetaMemoryPage = () => {
  const { selectedProject } = useProject()

  const apiUrl = selectedProject
    ? `/api/meta/quality?project_id=${selectedProject.id}`
    : '/api/meta/quality'

  const { data, loading } = useAPI<MetaResponse>(apiUrl, [selectedProject?.id])

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Layer 6: Meta-Memory</h1>
        <p className="text-gray-400">
          Quality metrics and system awareness
          {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="flex items-center justify-center">
          <GaugeChart value={data?.quality || 0} title="Overall Quality" />
        </Card>

        <Card header={<h3 className="text-lg font-semibold text-gray-50">Layer Attention</h3>}>
          <div className="space-y-3">
            {data?.attention.map((item) => (
              <div key={item.layer} className="flex justify-between">
                <span className="text-gray-400">{item.layer}</span>
                <div className="h-2 bg-gray-700 rounded w-24 overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: `${item.allocation}%` }} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Domain Expertise</h3>}>
        <div className="grid grid-cols-2 gap-4">
          {data?.expertise.map((item) => (
            <div key={item.domain} className="p-3 rounded bg-gray-700/30">
              <p className="text-gray-50 font-medium">{item.domain}</p>
              <p className="text-2xl font-bold text-blue-400">{Math.round(item.score)}%</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default MetaMemoryPage
