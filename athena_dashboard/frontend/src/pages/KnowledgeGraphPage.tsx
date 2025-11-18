import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function KnowledgeGraphPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/memory/graph')
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
        <h1 className="text-3xl font-bold">Knowledge Graph</h1>
        <p className="text-gray-500 mt-2">Entities, relationships, and communities</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Entities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.itemCount?.toLocaleString()}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Communities</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.communityCount}</div>
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
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Top Concepts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data?.topConcepts?.map((concept: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div>
                  <p className="font-medium">{concept.name}</p>
                  <p className="text-xs text-gray-500">Degree: {concept.degree}</p>
                </div>
                <Badge variant="secondary">{(concept.importance * 100).toFixed(0)}%</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
