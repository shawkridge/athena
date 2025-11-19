'use client'

import { useEffect, useRef } from 'react'
import type { Entity } from '@/lib/api'

// Dynamically import Cytoscape to avoid SSR issues
let cytoscape: any = null
if (typeof window !== 'undefined') {
  cytoscape = require('cytoscape')
  const coseBilkent = require('cytoscape-cose-bilkent')
  cytoscape.use(coseBilkent)
}

interface GraphVisualizationProps {
  entities: Entity[]
}

export function GraphVisualization({ entities }: GraphVisualizationProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const cyRef = useRef<any>(null)

  useEffect(() => {
    if (!containerRef.current || !cytoscape || entities.length === 0) return

    // Create Cytoscape instance
    const cy = cytoscape({
      container: containerRef.current,
      elements: entities.map((entity) => ({
        data: {
          id: `entity-${entity.id}`,
          label: entity.name,
          type: entity.entity_type,
        },
      })),
      style: [
        {
          selector: 'node',
          style: {
            'background-color': '#06b6d4',
            label: 'data(label)',
            'text-valign': 'center',
            'text-halign': 'center',
            'font-size': '10px',
            'font-weight': 'bold',
            color: '#fff',
            'text-outline-color': '#06b6d4',
            'text-outline-width': 2,
            width: 30,
            height: 30,
          },
        },
        {
          selector: 'node[type="Project"]',
          style: {
            'background-color': '#3b82f6',
            'text-outline-color': '#3b82f6',
          },
        },
        {
          selector: 'node[type="Concept"]',
          style: {
            'background-color': '#a855f7',
            'text-outline-color': '#a855f7',
          },
        },
        {
          selector: 'node[type="Function"]',
          style: {
            'background-color': '#22c55e',
            'text-outline-color': '#22c55e',
          },
        },
        {
          selector: 'edge',
          style: {
            width: 2,
            'line-color': '#cbd5e1',
            'target-arrow-color': '#cbd5e1',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier',
          },
        },
      ],
      layout: {
        name: 'cose-bilkent',
        animate: true,
        animationDuration: 500,
        nodeDimensionsIncludeLabels: true,
        idealEdgeLength: 100,
        nodeRepulsion: 8000,
        numIter: 2500,
        tile: true,
        tilingPaddingVertical: 10,
        tilingPaddingHorizontal: 10,
        gravity: 0.25,
        gravityRange: 3.8,
      },
      userZoomingEnabled: true,
      userPanningEnabled: true,
      boxSelectionEnabled: false,
    })

    cyRef.current = cy

    // Add interactivity
    cy.on('tap', 'node', (evt: any) => {
      const node = evt.target
      console.log('Node clicked:', node.data())
    })

    // Cleanup
    return () => {
      if (cyRef.current) {
        cyRef.current.destroy()
      }
    }
  }, [entities])

  if (!cytoscape) {
    return (
      <div className="h-96 flex items-center justify-center bg-muted/30 rounded-lg">
        <p className="text-muted-foreground">Loading graph visualization...</p>
      </div>
    )
  }

  if (entities.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center bg-muted/30 rounded-lg">
        <p className="text-muted-foreground">No entities to visualize</p>
      </div>
    )
  }

  return (
    <div
      ref={containerRef}
      className="w-full h-96 border rounded-lg bg-background"
      style={{ minHeight: '500px' }}
    />
  )
}
