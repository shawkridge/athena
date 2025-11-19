'use client'

import { FileSearch } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function ResearchPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-cyan-100">
            <FileSearch className="h-8 w-8 text-cyan-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Research</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Multi-source research, pattern analysis, and credibility assessment
            </p>
          </div>
        </div>
      </div>

      {/* Placeholder Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Research Tasks</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Sources Analyzed</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Patterns Found</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Avg Credibility</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>
      </div>

      {/* Implementation Status */}
      <div className="bg-card border rounded-lg p-8">
        <div className="text-center">
          <FileSearch className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-xl font-semibold mb-2">Backend Implementation Needed</h3>
          <p className="text-muted-foreground mb-6">
            Research subsystem endpoints are not yet implemented in the backend.
          </p>
          <div className="text-sm text-muted-foreground space-y-2">
            <p className="font-medium">Expected Features:</p>
            <ul className="list-disc list-inside space-y-1 max-w-2xl mx-auto">
              <li>Multi-source research task tracking</li>
              <li>Pattern extraction across sources</li>
              <li>Source credibility assessment</li>
              <li>Research synthesis and summarization</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Expected Sections (disabled) */}
      <div className="bg-card border rounded-lg p-6 opacity-50">
        <h3 className="text-lg font-semibold mb-4">Research Tasks</h3>
        <div className="text-center py-8 text-muted-foreground">
          <p>Task list will appear here once backend is implemented</p>
        </div>
      </div>
    </div>
  )
}
