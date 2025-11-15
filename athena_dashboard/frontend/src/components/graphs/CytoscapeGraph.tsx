/**
 * CytoscapeGraph Component
 * Interactive network visualization for knowledge graphs using Cytoscape
 */

import { useEffect, useRef, useState } from 'react'
import cytoscape from 'cytoscape'
import cose from 'cytoscape-cose-bilkent'

// Register the CoSE layout algorithm
cytoscape.use(cose as any)

export interface GraphNode {
  id: string
  label: string
  type?: string
  value?: number
  community?: number
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  weight?: number
  type?: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

interface CytoscapeGraphProps {
  data: GraphData
  loading?: boolean
  onNodeClick?: (node: GraphNode) => void
  onEdgeClick?: (edge: GraphEdge) => void
  height?: string
  communityColors?: Record<number, string>
}

const defaultCommunityColors: Record<number, string> = {
  0: '#3B82F6', // blue
  1: '#10B981', // green
  2: '#F59E0B', // amber
  3: '#EF4444', // red
  4: '#8B5CF6', // purple
  5: '#EC4899', // pink
  6: '#14B8A6', // teal
  7: '#F97316', // orange
}

const getNodeColor = (community?: number): string => {
  if (community === undefined || community === null) {
    return '#6B7280' // gray
  }
  return defaultCommunityColors[community % Object.keys(defaultCommunityColors).length] || '#6B7280'
}

export const CytoscapeGraph = ({
  data,
  loading = false,
  onNodeClick,
  onEdgeClick,
  height = '500px',
  communityColors = defaultCommunityColors,
}: CytoscapeGraphProps) => {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<cytoscape.Core | null>(null)
  const [selectedNode, setSelectedNode] = useState<string | null>(null)

  useEffect(() => {
    if (!containerRef.current || !data || loading) return

    // Convert data to Cytoscape format
    const elements = [
      ...data.nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label || node.id,
          type: node.type || 'default',
          value: node.value || 1,
          community: node.community,
        },
      })),
      ...data.edges.map((edge) => ({
        data: {
          id: edge.id,
          source: edge.source,
          target: edge.target,
          weight: edge.weight || 1,
          type: edge.type || 'default',
        },
      })),
    ]

    const cytoscapeStyles = [
      {
        selector: 'node',
        style: {
          'background-color': (ele: any) => getNodeColor(ele.data('community')),
          'label': 'data(label)',
          'text-opacity': 0.9,
          'text-valign': 'center',
          'text-halign': 'center',
          'text-background-color': '#000000',
          'text-background-opacity': 0.8,
          'text-background-padding': '3px',
          'text-background-shape': 'roundrectangle',
          'font-size': '10px',
          'width': (ele: any) => Math.max(20, Math.min(60, ele.data('value') * 2)),
          'height': (ele: any) => Math.max(20, Math.min(60, ele.data('value') * 2)),
          'border-width': '2px',
          'border-color': '#ffffff',
          'opacity': 0.9,
        },
      },
      {
        selector: 'node:selected',
        style: {
          'border-color': '#ffff00',
          'border-width': '3px',
          'opacity': 1,
        },
      },
      {
        selector: 'node:hover',
        style: {
          'opacity': 1,
          'border-width': '3px',
          'border-color': '#ffffff',
        },
      },
      {
        selector: 'edge',
        style: {
          'line-color': (ele: any) => {
            const weight = ele.data('weight') || 1
            const opacity = Math.min(weight / 5, 1)
            return `rgba(107, 114, 128, ${opacity})`
          },
          'target-arrow-color': 'rgba(107, 114, 128, 0.5)',
          'target-arrow-shape': 'triangle',
          'width': (ele: any) => Math.min((ele.data('weight') || 1) * 1.5, 4),
          'curve-style': 'bezier',
          'opacity': 0.6,
        },
      },
    ]

    // Initialize or update Cytoscape
    if (!cyRef.current) {
      try {
        cyRef.current = cytoscape({
          container: containerRef.current,
          elements,
          style: cytoscapeStyles,
          layout: {
            name: 'cose-bilkent',
            directed: false,
            animate: true,
            animationDuration: 1000,
            fit: true,
            padding: 30,
            nodeDimensionsIncludeLabels: true,
            gravity: 0.05,
            gravityRange: 200,
            tile: true,
            tilingPaddingVertical: 10,
            tilingPaddingHorizontal: 10,
          } as any,
        })

        // Add event handlers
        cyRef.current.on('tap', 'node', (evt) => {
          const node = evt.target
          setSelectedNode(node.id())
          if (onNodeClick) {
            const nodeData = data.nodes.find((n) => n.id === node.id())
            if (nodeData) {
              onNodeClick(nodeData)
            }
          }
        })

        cyRef.current.on('tap', 'edge', (evt) => {
          const edge = evt.target
          if (onEdgeClick) {
            const edgeData = data.edges.find((e) => e.id === edge.id())
            if (edgeData) {
              onEdgeClick(edgeData)
            }
          }
        })

        cyRef.current.on('tap', (evt) => {
          if (evt.target === cyRef.current) {
            setSelectedNode(null)
          }
        })

        // Add hover effects for better interactivity
        cyRef.current.on('mouseover', 'node', (evt) => {
          const node = evt.target
          node.style('opacity', 1)
        })

        cyRef.current.on('mouseout', 'node', (evt) => {
          const node = evt.target
          if (!node.selected()) {
            node.style('opacity', 0.9)
          }
        })

        cyRef.current.on('mouseover', 'edge', (evt) => {
          const edge = evt.target
          edge.style('line-color', '#ffffff')
          edge.style('opacity', 1)
        })

        cyRef.current.on('mouseout', 'edge', (evt) => {
          const edge = evt.target
          edge.style('line-color', (ele: any) => {
            const weight = ele.data('weight') || 1
            const opacity = Math.min(weight / 5, 1)
            return `rgba(107, 114, 128, ${opacity})`
          })
          edge.style('opacity', 0.6)
        })
      } catch (error) {
        console.error('Failed to initialize Cytoscape:', error)
      }
    } else {
      // Update existing instance
      try {
        cyRef.current.elements().remove()
        cyRef.current.add(elements)
        cyRef.current.layout({
          name: 'cose-bilkent',
          directed: false,
          animate: true,
          animationDuration: 1000,
          fit: true,
          padding: 30,
          nodeDimensionsIncludeLabels: true,
          gravity: 0.05,
          gravityRange: 200,
        } as any).run()
      } catch (error) {
        console.error('Failed to update Cytoscape:', error)
      }
    }

    // Cleanup on unmount - improved to handle React's DOM updates
    return () => {
      if (cyRef.current) {
        try {
          // Don't call destroy during React's cleanup - just nullify reference
          // This prevents "removeChild" errors when React is still managing the DOM
          cyRef.current = null
        } catch (error) {
          console.error('Error during Cytoscape cleanup:', error)
          cyRef.current = null
        }
      }
    }
  }, [data, loading, onNodeClick, onEdgeClick])

  if (loading) {
    return (
      <div
        ref={containerRef}
        className="w-full rounded-lg bg-gray-900 flex items-center justify-center"
        style={{ height }}
      >
        <div className="text-center space-y-2">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400" />
          <p className="text-gray-400">Loading graph visualization...</p>
        </div>
      </div>
    )
  }

  if (!data.nodes || data.nodes.length === 0) {
    return (
      <div
        ref={containerRef}
        className="w-full rounded-lg bg-gray-900 flex items-center justify-center"
        style={{ height }}
      >
        <p className="text-gray-400">No graph data available</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div
        ref={containerRef}
        className="w-full rounded-lg bg-gray-900 border border-gray-700"
        style={{ height }}
      />
      {selectedNode && (
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-sm">
          <p className="text-gray-400">
            Selected: <span className="text-blue-400 font-mono">{selectedNode}</span>
          </p>
        </div>
      )}
      <div className="text-xs text-gray-500 space-y-1">
        <p>Nodes: {data.nodes.length} | Edges: {data.edges.length}</p>
        <p className="text-gray-600">Click nodes to select | Scroll to zoom | Drag to pan</p>
      </div>
    </div>
  )
}

export default CytoscapeGraph
