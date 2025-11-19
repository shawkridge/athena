'use client'

import { Play } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function ExecutionMonitoringPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-emerald-100">
            <Play className="h-8 w-8 text-emerald-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Execution Monitoring</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Task execution, workflow orchestration, and queue management
            </p>
          </div>
        </div>
      </div>

      {/* Placeholder Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Active Tasks</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Queued Tasks</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Completed</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Success Rate</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>
      </div>

      {/* Implementation Status */}
      <div className="bg-card border rounded-lg p-8">
        <div className="text-center">
          <Play className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-xl font-semibold mb-2">Backend Implementation Needed</h3>
          <p className="text-muted-foreground mb-6">
            Execution Monitoring subsystem endpoints are not yet implemented in the backend.
          </p>
          <div className="text-sm text-muted-foreground space-y-2">
            <p className="font-medium">Expected Features:</p>
            <ul className="list-disc list-inside space-y-1 max-w-2xl mx-auto">
              <li>Real-time task execution monitoring</li>
              <li>Workflow orchestration and visualization</li>
              <li>Queue management and prioritization</li>
              <li>Execution history and performance tracking</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Expected Sections (disabled) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-50">
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Active Executions</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>Execution list will appear here once backend is implemented</p>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Workflow Status</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>Workflow visualization will appear here once backend is implemented</p>
          </div>
        </div>
      </div>
    </div>
  )
}
