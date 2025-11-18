import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function MetaMemoryPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/memory/meta')
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
        <h1 className="text-3xl font-bold">Meta-Memory</h1>
        <p className="text-gray-500 mt-2">Quality tracking, attention, and cognitive load</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Cognitive Load</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(data?.cognitiveLoad?.current * 100).toFixed(0)}%</div>
            <p className="text-xs text-gray-500 mt-1">{data?.cognitiveLoad?.status}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Memory Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(data?.memoryQuality?.average * 100).toFixed(0)}%</div>
            <p className="text-xs text-gray-500 mt-1">{data?.memoryQuality?.trend}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Quality Change</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{data?.memoryQuality?.recentChange}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Expertise Levels</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(data?.expertise || {}).map(([domain, level]: [string, any]) => (
              <div key={domain} className="flex justify-between text-sm">
                <span className="capitalize">{domain.replace(/_/g, ' ')}</span>
                <Badge variant="secondary">{(Number(level) * 100).toFixed(0)}%</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
