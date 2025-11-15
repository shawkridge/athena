import { Card, Stat, RefreshButton } from '@/components/common'
import { useRealtimeData } from '@/hooks'
import { useProject } from '@/context/ProjectContext'

interface GraphStats {
  entities: number
  relationships: number
  communities: number
  density: number
}

interface GraphResponse {
  stats: GraphStats
}

export const KnowledgeGraphPage = () => {
  const { selectedProject } = useProject()

  const apiUrl = selectedProject
    ? `/api/graph/stats?project_id=${selectedProject.id}`
    : '/api/graph/stats'

  const { data, loading, refetch, isConnected } = useRealtimeData<GraphResponse>({
    url: apiUrl,
    dependencies: [selectedProject?.id],
    pollInterval: 5000,
    enabled: true,
  })

  if (loading) return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-50">Layer 5: Knowledge Graph</h1>
          <p className="text-gray-400">
            Entities, relationships, and communities
            {selectedProject && <span className="ml-2 text-blue-400">(Viewing: {selectedProject.name})</span>}
          </p>
        </div>
        <RefreshButton onRefresh={refetch} isConnected={isConnected} isLoading={loading} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Entities" value={data?.stats.entities.toString() || '0'} />
        <Stat label="Relationships" value={data?.stats.relationships.toString() || '0'} />
        <Stat label="Communities" value={data?.stats.communities.toString() || '0'} />
        <Stat label="Density" value={`${(data?.stats.density || 0).toFixed(2)}`} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Graph Visualization</h3>}>
        <div className="h-96 rounded-lg bg-gray-900 flex items-center justify-center text-gray-400">
          Interactive graph visualization placeholder
          <br />
          (Cytoscape integration in progress)
        </div>
      </Card>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Top Communities</h3>}>
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="p-3 rounded bg-gray-700/30">
              <p className="text-gray-50">Community {i}</p>
              <p className="text-xs text-gray-400">{Math.random() * 1000 | 0} entities</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

export default KnowledgeGraphPage
