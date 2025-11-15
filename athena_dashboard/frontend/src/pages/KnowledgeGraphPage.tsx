import { Card, Stat, RefreshButton } from '@/components/common'
import { useRealtimeData } from '@/hooks'
import { useProject } from '@/context/ProjectContext'
import { useState } from 'react'
import SigmaGraph, { GraphData } from '@/components/graphs/SigmaGraph'

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
  const [selectedNode, setSelectedNode] = useState<{ id: string; label: string } | null>(null)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)

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

  // Fetch visualization data with higher limit for better visualization
  const vizUrl = selectedProject
    ? `/api/graph/visualization?project_id=${selectedProject.id}&limit=500`
    : '/api/graph/visualization?limit=500'

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

  const loading = statsLoading || vizLoading
  const isConnected = statsConnected && vizConnected

  // Prepare graph data for Sigma.js
  const graphData: GraphData | null = vizData
    ? {
        nodes: vizData.nodes,
        edges: vizData.edges,
        metadata: vizData.metadata,
      }
    : null

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

      {selectedNode && (
        <div className="bg-blue-900 border border-blue-700 rounded p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Selected Node</p>
              <p className="text-lg font-semibold text-blue-300">{selectedNode.label}</p>
              <p className="text-xs text-gray-500 mt-1">ID: {selectedNode.id}</p>
            </div>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-gray-400 hover:text-gray-200"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Graph Visualization</h3>}>
        {graphData && graphData.nodes.length > 0 ? (
          <>
            <SigmaGraph
              data={graphData}
              loading={loading}
              onNodeClick={(nodeId, nodeLabel) => {
                setSelectedNode({ id: nodeId, label: nodeLabel })
              }}
              onNodeHover={setHoveredNode}
              height="600px"
              colorByType={true}
            />
            <div className="mt-4 pt-4 border-t border-gray-700 text-xs text-gray-400">
              <p>
                Showing <strong>{graphData.nodes.length}</strong> of{' '}
                <strong>{graphData.metadata?.total_nodes_in_graph || graphData.nodes.length}</strong> entities
              </p>
              <p>
                Showing <strong>{graphData.edges.length}</strong> of{' '}
                <strong>{graphData.metadata?.total_edges_in_graph || graphData.edges.length}</strong> relationships
              </p>
            </div>
          </>
        ) : (
          <div className="h-96 rounded-lg bg-gray-900 flex items-center justify-center text-gray-400 border border-gray-700 p-6">
            <div className="text-center space-y-4">
              <p className="text-lg">No graph data available</p>
              <p className="text-sm text-gray-500">
                The knowledge graph will appear here once data is available.
              </p>
            </div>
          </div>
        )}
      </Card>

    </div>
  )
}

export default KnowledgeGraphPage
