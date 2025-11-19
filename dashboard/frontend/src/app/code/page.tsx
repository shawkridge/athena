'use client'

import { Code2 } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function CodeIntelligencePage() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-violet-100">
            <Code2 className="h-8 w-8 text-violet-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Code Intelligence</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Code artifacts, symbol tracking, and dependency analysis
            </p>
          </div>
        </div>
      </div>

      {/* Placeholder Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Code Artifacts</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Symbols Tracked</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Dependencies</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Code Quality</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>
      </div>

      {/* Implementation Status */}
      <div className="bg-card border rounded-lg p-8">
        <div className="text-center">
          <Code2 className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-xl font-semibold mb-2">Backend Implementation Needed</h3>
          <p className="text-muted-foreground mb-6">
            Code intelligence subsystem endpoints are not yet implemented in the backend.
          </p>
          <div className="text-sm text-muted-foreground space-y-2">
            <p className="font-medium">Expected Features:</p>
            <ul className="list-disc list-inside space-y-1 max-w-2xl mx-auto">
              <li>Code artifact storage and versioning</li>
              <li>Symbol tracking across codebase</li>
              <li>Dependency graph visualization</li>
              <li>Code quality metrics and analysis</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Expected Sections (disabled) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-50">
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Artifacts</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>Artifact list will appear here once backend is implemented</p>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Dependency Graph</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>Dependency visualization will appear here once backend is implemented</p>
          </div>
        </div>
      </div>
    </div>
  )
}
