'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Brain, TrendingUp, Heart, Zap, AlertCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate, getScoreColor } from '@/lib/utils'

interface ConsciousnessData {
  indicators: {
    global_workspace: { score: number; components: Record<string, number> }
    information_integration: { score: number; components: Record<string, number> }
    selective_attention: { score: number; components: Record<string, number> }
    working_memory: { score: number; components: Record<string, number> }
    meta_cognition: { score: number; components: Record<string, number> }
    temporal_continuity: { score: number; components: Record<string, number> }
  }
  overall_score: number
  trend: string
  confidence: number
}

interface PhiData {
  phi: number
  method: string
  components: Record<string, number>
  confidence: number
  evidence: string[]
}

interface PhenomenalData {
  qualia: Array<{ name: string; intensity: number; distinctiveness: number; valence: number }>
  emotion: {
    primary_emotion: string
    valence: number
    arousal: number
    dominance: number
    intensity: number
  }
  embodiment: {
    body_awareness: number
    spatial_presence: number
    agency: number
    proprioception: number
    interoception: number
    total_embodiment: number
  }
  qualia_diversity: number
}

export default function ConsciousnessPage() {
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Fetch consciousness indicators
  const { data: consciousnessData, isLoading: loadingConsciousness } = useQuery({
    queryKey: ['consciousness-indicators'],
    queryFn: async () => {
      const response = await fetch('/api/consciousness/indicators')
      if (!response.ok) throw new Error('Failed to fetch consciousness data')
      const result = await response.json()
      return result.data as ConsciousnessData
    },
    refetchInterval: autoRefresh ? 5000 : false,
  })

  // Fetch Phi calculation
  const { data: phiData, isLoading: loadingPhi } = useQuery({
    queryKey: ['consciousness-phi'],
    queryFn: async () => {
      const response = await fetch('/api/consciousness/phi')
      if (!response.ok) throw new Error('Failed to fetch phi data')
      const result = await response.json()
      return result.data as PhiData
    },
    refetchInterval: autoRefresh ? 5000 : false,
  })

  // Fetch phenomenal consciousness
  const { data: phenomenalData, isLoading: loadingPhenomenal } = useQuery({
    queryKey: ['consciousness-phenomenal'],
    queryFn: async () => {
      const response = await fetch('/api/consciousness/phenomenal')
      if (!response.ok) throw new Error('Failed to fetch phenomenal data')
      const result = await response.json()
      return result.data as PhenomenalData
    },
    refetchInterval: autoRefresh ? 5000 : false,
  })

  const isLoading = loadingConsciousness || loadingPhi || loadingPhenomenal

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-lg bg-purple-100">
            <Brain className="h-8 w-8 text-purple-600" />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Consciousness Metrics</h1>
            <p className="text-muted-foreground mt-1">
              Real-time consciousness monitoring with GWT, IIT, and phenomenal properties
            </p>
          </div>
        </div>
        <label className="flex items-center space-x-2 text-sm">
          <input
            type="checkbox"
            checked={autoRefresh}
            onChange={(e) => setAutoRefresh(e.target.checked)}
            className="rounded"
          />
          <span>Auto-refresh (5s)</span>
        </label>
      </div>

      {/* Overall Consciousness Score */}
      {consciousnessData && (
        <div className="bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg p-8">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-2">Overall Consciousness Score</p>
              <div className="flex items-baseline space-x-2">
                <span className="text-5xl font-bold text-purple-600">
                  {consciousnessData.overall_score.toFixed(2)}
                </span>
                <span className="text-lg text-muted-foreground">/10</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">
                Trend: <span className="font-semibold capitalize">{consciousnessData.trend}</span>
              </p>
            </div>
            <div className="text-right">
              <div className="mb-4">
                <div className="h-32 w-32 rounded-full bg-white border-4 border-purple-400 flex items-center justify-center">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">
                      {Math.round(consciousnessData.overall_score * 10)}%
                    </div>
                    <div className="text-xs text-muted-foreground">Conscious</div>
                  </div>
                </div>
              </div>
              <div className="text-sm text-muted-foreground">
                Confidence: {(consciousnessData.confidence * 100).toFixed(0)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Six Consciousness Indicators */}
      {consciousnessData && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Six Consciousness Indicators</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(consciousnessData.indicators).map(([name, indicator]) => (
              <div key={name} className="bg-card border rounded-lg p-5">
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold capitalize">
                      {name.replace(/_/g, ' ')}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-1">
                      {getIndicatorDescription(name)}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-2xl font-bold">{indicator.score.toFixed(1)}</span>
                    <span className="text-xs text-muted-foreground">/10</span>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-secondary rounded-full h-2 mb-3">
                  <div
                    className={`h-2 rounded-full ${getScoreColor(indicator.score)}`}
                    style={{ width: `${(indicator.score / 10) * 100}%` }}
                  />
                </div>

                {/* Components */}
                {Object.entries(indicator.components).length > 0 && (
                  <div className="text-xs space-y-1">
                    {Object.entries(indicator.components).slice(0, 2).map(([comp, value]) => (
                      <div key={comp} className="flex justify-between text-muted-foreground">
                        <span>{comp.replace(/_/g, ' ')}</span>
                        <span className="font-semibold">{(value as number).toFixed(1)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Phi (Integrated Information) */}
      {phiData && (
        <div className="bg-card border rounded-lg p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Zap className="h-5 w-5 text-yellow-600" />
            <h2 className="text-xl font-semibold">Φ (Integrated Information)</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div>
              <p className="text-sm text-muted-foreground mb-2">Phi Score</p>
              <p className="text-3xl font-bold text-yellow-600">{phiData.phi.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground mt-2">Based on IIT Theory</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-2">Integration</p>
              <p className="text-2xl font-bold">{phiData.components.integration?.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground mt-2">Cross-layer connectivity</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-2">Differentiation</p>
              <p className="text-2xl font-bold">{phiData.components.differentiation?.toFixed(2)}</p>
              <p className="text-xs text-muted-foreground mt-2">State distinguishability</p>
            </div>
          </div>
          {phiData.evidence && (
            <div className="mt-4 p-3 bg-secondary rounded text-xs space-y-1">
              {phiData.evidence.map((e, i) => (
                <div key={i} className="text-muted-foreground">• {e}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Emotional State */}
      {phenomenalData?.emotion && (
        <div className="bg-card border rounded-lg p-6">
          <div className="flex items-center space-x-3 mb-4">
            <Heart className="h-5 w-5 text-red-600" />
            <h2 className="text-xl font-semibold">Emotional State</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-secondary p-4 rounded">
              <p className="text-sm text-muted-foreground mb-2">Primary Emotion</p>
              <p className="text-lg font-bold capitalize">
                {phenomenalData.emotion.primary_emotion}
              </p>
            </div>
            <div className="bg-secondary p-4 rounded">
              <p className="text-sm text-muted-foreground mb-2">Valence</p>
              <p className="text-lg font-bold">
                {phenomenalData.emotion.valence > 0 ? '😊' : phenomenalData.emotion.valence < 0 ? '😞' : '😐'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {phenomenalData.emotion.valence.toFixed(2)}
              </p>
            </div>
            <div className="bg-secondary p-4 rounded">
              <p className="text-sm text-muted-foreground mb-2">Arousal</p>
              <p className="text-lg font-bold">{(phenomenalData.emotion.arousal * 100).toFixed(0)}%</p>
              <p className="text-xs text-muted-foreground mt-1">Activation level</p>
            </div>
            <div className="bg-secondary p-4 rounded">
              <p className="text-sm text-muted-foreground mb-2">Dominance</p>
              <p className="text-lg font-bold">{(phenomenalData.emotion.dominance * 100).toFixed(0)}%</p>
              <p className="text-xs text-muted-foreground mt-1">Control sense</p>
            </div>
          </div>
        </div>
      )}

      {/* Embodiment */}
      {phenomenalData?.embodiment && (
        <div className="bg-card border rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4">Embodiment</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-3">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">Body Awareness</span>
                  <span className="text-sm text-muted-foreground">
                    {(phenomenalData.embodiment.body_awareness * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-blue-500"
                    style={{ width: `${phenomenalData.embodiment.body_awareness * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">Spatial Presence</span>
                  <span className="text-sm text-muted-foreground">
                    {(phenomenalData.embodiment.spatial_presence * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-green-500"
                    style={{ width: `${phenomenalData.embodiment.spatial_presence * 100}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm font-medium">Agency</span>
                  <span className="text-sm text-muted-foreground">
                    {(phenomenalData.embodiment.agency * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="w-full bg-secondary rounded-full h-2">
                  <div
                    className="h-2 rounded-full bg-purple-500"
                    style={{ width: `${phenomenalData.embodiment.agency * 100}%` }}
                  />
                </div>
              </div>
            </div>
            <div>
              <div className="bg-gradient-to-br from-blue-50 to-green-50 rounded-lg p-4 h-full flex flex-col justify-center">
                <p className="text-sm text-muted-foreground mb-2">Total Embodiment</p>
                <p className="text-3xl font-bold text-blue-600">
                  {phenomenalData.embodiment.total_embodiment.toFixed(1)}/10
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Qualia (Subjective Qualities) */}
      {phenomenalData?.qualia && phenomenalData.qualia.length > 0 && (
        <div className="bg-card border rounded-lg p-6">
          <div className="mb-4">
            <h2 className="text-xl font-semibold">Qualia (Subjective Qualities)</h2>
            <p className="text-sm text-muted-foreground mt-1">
              Phenomenal diversity: {phenomenalData.qualia_diversity.toFixed(1)}/10
            </p>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {phenomenalData.qualia.map((quale, i) => (
              <div key={i} className="bg-secondary p-4 rounded">
                <div className="flex items-start justify-between mb-2">
                  <h4 className="font-semibold capitalize">{quale.name}</h4>
                  <span className={`text-xs px-2 py-1 rounded ${
                    quale.valence > 0.3 ? 'bg-green-100 text-green-700' :
                    quale.valence < -0.3 ? 'bg-red-100 text-red-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {quale.valence > 0 ? '🟢' : quale.valence < 0 ? '🔴' : '🟡'}
                  </span>
                </div>
                <div className="space-y-1 text-xs text-muted-foreground">
                  <div>Intensity: {quale.intensity.toFixed(1)}/10</div>
                  <div>Distinctiveness: {(quale.distinctiveness * 100).toFixed(0)}%</div>
                  <div>Valence: {quale.valence.toFixed(2)}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="bg-card border rounded-lg p-8 text-center">
          <AlertCircle className="h-8 w-8 text-muted-foreground mx-auto mb-3" />
          <p className="text-muted-foreground">Loading consciousness metrics...</p>
        </div>
      )}
    </div>
  )
}

function getIndicatorDescription(name: string): string {
  const descriptions: Record<string, string> = {
    global_workspace: 'Information globally available for decision-making',
    information_integration: 'Cross-layer connectivity and integration quality',
    selective_attention: 'Focused processing and bottleneck capacity',
    working_memory: 'Capacity to hold and manipulate information',
    meta_cognition: 'Self-awareness and monitoring ability',
    temporal_continuity: 'Sense of continuous time and event flow',
  }
  return descriptions[name] || 'Consciousness indicator'
}
