import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function SemanticMemoryPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/memory/semantic')
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
        <h1 className="text-3xl font-bold">Semantic Memory</h1>
        <p className="text-gray-500 mt-2">Learned facts and insights</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Total Facts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.itemCount}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Quality</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.health?.quality}%</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Storage Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.health?.storageSize}</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Topic Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {Object.entries(data?.topicBreakdown || {}).map(([topic, count]: [string, any]) => (
              <div key={topic} className="flex justify-between text-sm">
                <span className="capitalize">{topic.replace(/_/g, ' ')}</span>
                <Badge variant="secondary">{count}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
