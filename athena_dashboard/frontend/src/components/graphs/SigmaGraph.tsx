import React, { useEffect, useState, useCallback, useRef } from 'react'
import { SigmaContainer, useLoadGraph, useRegisterEvents, useSigma } from '@react-sigma/core'
import { DirectedGraph } from 'graphology'
import forceAtlas2 from 'graphology-layout-forceatlas2'
import '@react-sigma/core/lib/style.css'

/**
 * Data types matching the backend API response
 */
interface GraphNode {
  id: string
  label: string
  type?: string
  value?: number
  community?: number
  color?: string
  size?: number
}

interface GraphEdge {
  id: string
  source: string
  target: string
  weight?: number
  type?: string
}

interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
  metadata?: {
    total_nodes_in_graph: number
    total_edges_in_graph: number
    rendered_limit: number
  }
}

/**
 * Component for loading graph data into Sigma
 */
const GraphLoader: React.FC<{
  data: GraphData
  onLoaded?: () => void
  colorByType?: boolean
}> = ({ data, onLoaded, colorByType = true }) => {
  const loadGraph = useLoadGraph()
  const graphRef = useRef<DirectedGraph | null>(null)

  useEffect(() => {
    if (!data.nodes.length) return

    const graph = new DirectedGraph()
    graphRef.current = graph

    // Color map for different node types
    const colorMap: Record<string, string> = {
      'entity': '#3b82f6',      // blue
      'concept': '#8b5cf6',     // purple
      'relation': '#ec4899',    // pink
      'attribute': '#14b8a6',   // teal
      'default': '#6b7280',     // gray
    }

    // Calculate node sizes based on value or community size
    const maxValue = Math.max(...data.nodes.map(n => n.value || 1), 1)

    // Add nodes
    data.nodes.forEach((node) => {
      const size = Math.max(5, Math.min(20, (node.value || 10) / maxValue * 20))
      const nodeType = node.type?.toLowerCase() || 'default'
      const color = node.color || colorMap[nodeType] || colorMap['default']

      graph.addNode(node.id, {
        label: node.label,
        size,
        color,
        // Store type info in metadata but don't set as 'type' (Sigma limitation)
        // This prevents "could not find a suitable program for node type" errors
        nodeType: nodeType,  // Custom property for filtering/styling in JS
        community: node.community || 0,
      })
    })

    // Add edges
    data.edges.forEach((edge) => {
      try {
        graph.addEdge(edge.source, edge.target, {
          weight: edge.weight || 1,
          type: edge.type || 'default',
        })
      } catch (e) {
        // Skip edges with missing nodes
        console.debug(`Skipping edge ${edge.id}: ${e}`)
      }
    })

    // Apply ForceAtlas2 layout
    forceAtlas2.assign(graph, {
      iterations: 50,
      settings: {
        gravity: 1,
        scalingRatio: 10,
        slowDown: 2,
        outboundAttractionDistribution: false,
      },
    })

    // Load the graph
    loadGraph(graph)
    onLoaded?.()
  }, [loadGraph, data, onLoaded])

  return null
}

/**
 * Component for handling graph events and interactions
 */
interface GraphEventsProps {
  onNodeClick?: (nodeId: string, nodeLabel: string) => void
  onNodeHover?: (nodeId: string | null) => void
}

const GraphEvents: React.FC<GraphEventsProps> = ({ onNodeClick, onNodeHover }) => {
  const registerEvents = useRegisterEvents()
  const sigma = useSigma()
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  useEffect(() => {
    registerEvents({
      clickNode: (event) => {
        const nodeId = event.node
        const nodeData = sigma.getGraph().getNodeAttributes(nodeId)
        setSelectedNode(nodeId)
        onNodeClick?.(nodeId, nodeData.label || nodeId)
      },
      enterNode: (event) => {
        const nodeId = event.node
        sigma.getGraph().setNodeAttribute(nodeId, 'highlighted', true)
        onNodeHover?.(nodeId)
        sigma.refresh()
      },
      leaveNode: (event) => {
        const nodeId = event.node
        sigma.getGraph().setNodeAttribute(nodeId, 'highlighted', false)
        onNodeHover?.(null)
        sigma.refresh()
      },
      clickStage: () => {
        setSelectedNode(null)
      },
    })
  }, [registerEvents, sigma, onNodeClick, onNodeHover])

  return null
}

/**
 * Component for graph controls (zoom, reset, etc.)
 */
const GraphControls: React.FC = () => {
  const sigma = useSigma()

  const handleReset = useCallback(() => {
    sigma.getCamera().animatedReset({ duration: 600 })
  }, [sigma])

  const handleZoomIn = useCallback(() => {
    const camera = sigma.getCamera()
    const state = camera.getState()
    const newZoom = Math.min(state.zoom * 1.2, 4)
    camera.setState({ ...state, zoom: newZoom }, { duration: 300 })
  }, [sigma])

  const handleZoomOut = useCallback(() => {
    const camera = sigma.getCamera()
    const state = camera.getState()
    const newZoom = Math.max(state.zoom * 0.8, 0.1)
    camera.setState({ ...state, zoom: newZoom }, { duration: 300 })
  }, [sigma])

  return (
    <div className="absolute bottom-4 right-4 flex gap-2 z-10">
      <button
        onClick={handleZoomIn}
        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition"
        title="Zoom in"
      >
        +
      </button>
      <button
        onClick={handleZoomOut}
        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition"
        title="Zoom out"
      >
        −
      </button>
      <button
        onClick={handleReset}
        className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm transition"
        title="Reset view"
      >
        Reset
      </button>
    </div>
  )
}

/**
 * Component for node search/filter
 */
interface GraphSearchProps {
  nodes: GraphNode[]
  onSearch?: (results: GraphNode[]) => void
  onSelect?: (nodeId: string, nodeLabel?: string) => void
}

const GraphSearch: React.FC<GraphSearchProps> = ({ nodes, onSearch, onSelect }) => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<GraphNode[]>([])
  const [showResults, setShowResults] = useState(false)

  const handleSearch = useCallback((q: string) => {
    setQuery(q)
    if (q.trim()) {
      const filtered = nodes.filter(node =>
        node.label.toLowerCase().includes(q.toLowerCase()) ||
        node.id.toLowerCase().includes(q.toLowerCase())
      )
      setResults(filtered.slice(0, 10)) // Limit to 10 results
      setShowResults(true)
      onSearch?.(filtered)
    } else {
      setResults([])
      setShowResults(false)
    }
  }, [nodes, onSearch])

  const handleSelectResult = (node: GraphNode) => {
    setQuery(node.label)
    setShowResults(false)
    onSelect?.(node.id, node.label)
  }

  return (
    <div className="absolute top-4 left-4 z-10">
      <div className="relative">
        <input
          type="text"
          placeholder="Search nodes..."
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          className="bg-gray-800 text-white px-3 py-2 rounded border border-gray-600 focus:border-blue-500 focus:outline-none"
        />
        {showResults && results.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-600 rounded max-h-48 overflow-y-auto">
            {results.map((node) => (
              <button
                key={node.id}
                onClick={() => handleSelectResult(node)}
                className="w-full text-left px-3 py-2 hover:bg-gray-700 border-b border-gray-700 last:border-b-0 text-sm text-gray-200"
              >
                {node.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Main SigmaGraph component
 */
interface SigmaGraphProps {
  data: GraphData
  loading?: boolean
  onNodeClick?: (nodeId: string, nodeLabel: string) => void
  onNodeHover?: (nodeId: string | null) => void
  height?: string
  colorByType?: boolean
}

const SigmaGraphInner: React.FC<Omit<SigmaGraphProps, 'data'> & { data: GraphData }> = ({
  data,
  loading,
  onNodeClick,
  onNodeHover,
  colorByType = true,
}) => {
  const [loaded, setLoaded] = useState(false)
  const sigma = useSigma()

  const handleNodeClick = useCallback((nodeId: string, nodeLabel: string) => {
    // Animate camera to node
    const graph = sigma.getGraph()
    const node = graph.getNodeAttributes(nodeId)

    // Calculate zoom to fit the node in view
    const camera = sigma.getCamera()
    const state = camera.getState()
    const padding = 0.5

    camera.animate(
      {
        x: node.x || 0,
        y: node.y || 0,
        zoom: Math.max(state.zoom, 1),
      },
      { duration: 600 }
    )
    onNodeClick?.(nodeId, nodeLabel)
  }, [sigma, onNodeClick])

  return (
    <>
      <GraphLoader
        data={data}
        onLoaded={() => setLoaded(true)}
        colorByType={colorByType}
      />
      <GraphEvents
        onNodeClick={handleNodeClick}
        onNodeHover={onNodeHover}
      />
      <GraphControls />
      <GraphSearch
        nodes={data.nodes}
        onSelect={handleNodeClick}
      />
      {loading && (
        <div className="absolute inset-0 bg-black bg-opacity-30 flex items-center justify-center rounded">
          <div className="text-white text-sm">Loading graph...</div>
        </div>
      )}
    </>
  )
}

export const SigmaGraph: React.FC<SigmaGraphProps> = ({
  data,
  loading,
  onNodeClick,
  onNodeHover,
  height = '400px',
  colorByType = true,
}) => {
  return (
    <div style={{ height, width: '100%', position: 'relative' }} className="rounded-lg bg-gray-900 border border-gray-700 overflow-hidden">
      <SigmaContainer
        style={{ height: '100%', width: '100%' }}
        settings={{
          renderEdgeLabels: false,
          defaultNodeColor: '#666',
          defaultEdgeColor: '#999',
          labelFont: 'Arial',
          labelSize: 14,
          labelDensity: 0.07,
          labelGridCellSize: 60,
          labelRenderedSizeThreshold: 8,
          enableEdgeEvents: false,
        }}
      >
        <SigmaGraphInner
          data={data}
          loading={loading}
          onNodeClick={onNodeClick}
          onNodeHover={onNodeHover}
          colorByType={colorByType}
        />
      </SigmaContainer>
    </div>
  )
}

export default SigmaGraph
export type { GraphData, GraphNode, GraphEdge }
