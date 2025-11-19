'use client'

import { Shield } from 'lucide-react'
import { ScopeBadge } from '@/components/scope-badge'

export default function SafetyValidationPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-red-100">
            <Shield className="h-8 w-8 text-red-600" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-3xl font-bold tracking-tight">Safety Validation</h1>
              <ScopeBadge scope="global" />
            </div>
            <p className="text-muted-foreground mt-1">
              Code safety checks, vulnerability scanning, and violation tracking
            </p>
          </div>
        </div>
      </div>

      {/* Placeholder Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Total Validations</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Vulnerabilities</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Violations</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>

        <div className="bg-card border rounded-lg p-5">
          <div className="text-sm text-muted-foreground mb-1">Safety Score</div>
          <div className="text-2xl font-bold text-muted-foreground">-</div>
        </div>
      </div>

      {/* Implementation Status */}
      <div className="bg-card border rounded-lg p-8">
        <div className="text-center">
          <Shield className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <h3 className="text-xl font-semibold mb-2">Backend Implementation Needed</h3>
          <p className="text-muted-foreground mb-6">
            Safety Validation subsystem endpoints are not yet implemented in the backend.
          </p>
          <div className="text-sm text-muted-foreground space-y-2">
            <p className="font-medium">Expected Features:</p>
            <ul className="list-disc list-inside space-y-1 max-w-2xl mx-auto">
              <li>Code safety validation and rule enforcement</li>
              <li>Vulnerability scanning and detection</li>
              <li>Violation tracking and remediation</li>
              <li>Safety pattern recognition and alerting</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Expected Sections (disabled) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 opacity-50">
        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Recent Scans</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>Scan history will appear here once backend is implemented</p>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-4">Active Violations</h3>
          <div className="text-center py-8 text-muted-foreground">
            <p>Violation list will appear here once backend is implemented</p>
          </div>
        </div>
      </div>
    </div>
  )
}
