import { Card, Stat, RefreshButton } from '@/components/common'
import { CytoscapeGraph, GraphData } from '@/components/graphs/CytoscapeGraph'
import { useRealtimeData } from '@/hooks'
import { useProject } from '@/context/ProjectContext'
import { useState } from 'react'

interface GraphStats {
  entities: number
  relationships: number
  communities: number
  density: number
}

interface GraphResponse {
  stats: GraphStats
}

interface VisualizationResponse {
  nodes: Array<{ id: string; label: string; type?: string; value?: number; community?: number }>
  edges: Array<{ id: string; source: string; target: string; weight?: number; type?: string }>
  metadata?: {
    total_nodes_in_graph: number
    total_edges_in_graph: number
    rendered_limit: number
  }
}

export const KnowledgeGraphPage = () => {
  const { selectedProject } = useProject()
  const [selectedNode, setSelectedNode] = useState<any>(null)

  // Fetch stats
  const statsUrl = selectedProject
    ? `/api/graph/stats?project_id=${selectedProject.id}`
    : '/api/graph/stats'

  const {
    data: statsData,
    loading: statsLoading,
    refetch: refetchStats,
    isConnected: statsConnected,
  } = useRealtimeData<GraphResponse>({
    url: statsUrl,
    dependencies: [selectedProject?.id],
    pollInterval: 5000,
    enabled: true,
  })

  // Fetch visualization data
  const vizUrl = selectedProject
    ? `/api/graph/visualization?project_id=${selectedProject.id}&limit=200`
    : '/api/graph/visualization?limit=200'

  const {
    data: vizData,
    loading: vizLoading,
    refetch: refetchViz,
    isConnected: vizConnected,
  } = useRealtimeData<VisualizationResponse>({
    url: vizUrl,
    dependencies: [selectedProject?.id],
    pollInterval: 10000,
    enabled: true,
  })

  const handleRefresh = async () => {
    await refetchStats()
    await refetchViz()
  }

  const graphData: GraphData = {
    nodes: vizData?.nodes || [],
    edges: vizData?.edges || [],
  }

  const loading = statsLoading || vizLoading
  const isConnected = statsConnected && vizConnected

  if (loading && !statsData && !vizData) {
    return <div className="p-6 animate-pulse h-64 bg-gray-800 rounded" />
  }

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
        <RefreshButton onRefresh={handleRefresh} isConnected={isConnected} isLoading={loading} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Stat label="Entities" value={statsData?.stats.entities.toString() || '0'} />
        <Stat label="Relationships" value={statsData?.stats.relationships.toString() || '0'} />
        <Stat label="Communities" value={statsData?.stats.communities.toString() || '0'} />
        <Stat label="Density" value={`${(statsData?.stats.density || 0).toFixed(2)}`} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Graph Visualization</h3>}>
        <CytoscapeGraph
          data={graphData}
          loading={vizLoading}
          onNodeClick={(node) => setSelectedNode(node)}
          height="600px"
        />
        {vizData?.metadata && (
          <div className="mt-4 p-3 bg-gray-800 rounded text-xs text-gray-400 space-y-1">
            <p>Total nodes in graph: {vizData.metadata.total_nodes_in_graph}</p>
            <p>Total relationships: {vizData.metadata.total_edges_in_graph}</p>
            <p>Rendered limit: {vizData.metadata.rendered_limit}</p>
          </div>
        )}
      </Card>

      {selectedNode && (
        <Card header={<h3 className="text-lg font-semibold text-gray-50">Selected Entity</h3>}>
          <div className="space-y-2">
            <div>
              <p className="text-xs text-gray-400">ID</p>
              <p className="text-gray-50 font-mono">{selectedNode.id}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Name</p>
              <p className="text-gray-50">{selectedNode.label}</p>
            </div>
            <div>
              <p className="text-xs text-gray-400">Type</p>
              <p className="text-gray-50">{selectedNode.type || 'unknown'}</p>
            </div>
            {selectedNode.community !== undefined && (
              <div>
                <p className="text-xs text-gray-400">Community</p>
                <p className="text-gray-50">{selectedNode.community}</p>
              </div>
            )}
          </div>
        </Card>
      )}

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Graph Statistics</h3>}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="p-3 bg-gray-800 rounded">
            <p className="text-xs text-gray-400 mb-1">Rendered Nodes</p>
            <p className="text-2xl font-bold text-blue-400">{graphData.nodes.length}</p>
          </div>
          <div className="p-3 bg-gray-800 rounded">
            <p className="text-xs text-gray-400 mb-1">Rendered Relationships</p>
            <p className="text-2xl font-bold text-green-400">{graphData.edges.length}</p>
          </div>
        </div>
      </Card>
    </div>
  )
}

export default KnowledgeGraphPage
