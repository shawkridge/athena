import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function ConsolidationPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/system/consolidation')
        if (resp.ok) setData(await resp.json())
      } catch (error) {
        console.error('Failed to fetch:', error)
      } finally {
        setLoading(false)
      }
    }
    fetch()
  }, [])

  if (loading) return <div className="p-8">Loading...</div>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Consolidation</h1>
        <p className="text-gray-500 mt-2">Pattern extraction and memory compression</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Consolidation Progress</span>
            <Badge>{data?.progress}%</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all"
              style={{ width: `${data?.progress}%` }}
            />
          </div>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Current Phase</p>
              <p className="font-medium capitalize">{data?.currentPhase?.replace(/_/g, ' ')}</p>
            </div>
            <div>
              <p className="text-gray-600">Status</p>
              <p className="font-medium capitalize">{data?.status?.replace(/_/g, ' ')}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Consolidation Metrics</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Events Processed</span>
              <Badge variant="secondary">{data?.metrics?.eventsProcessed?.toLocaleString()}</Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span>Patterns Found</span>
              <Badge variant="secondary">{data?.metrics?.patternsFound}</Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span>Compression Ratio</span>
              <Badge variant="secondary">{data?.metrics?.compressionRatio}x</Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span>Learning Gain</span>
              <Badge variant="secondary">{(data?.metrics?.learningGain * 100).toFixed(0)}%</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Timeline</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Start Time</span>
              <span>{new Date(data?.consolidationCycle?.startTime).toLocaleTimeString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Phase 1</span>
              <span>{data?.consolidationCycle?.phase1_duration}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Phase 2</span>
              <span>{data?.consolidationCycle?.phase2_duration}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
