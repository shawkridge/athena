import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function ProspectiveMemoryPage() {
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetch = async () => {
      try {
        const resp = await fetch('http://localhost:8000/api/memory/prospective')
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
        <h1 className="text-3xl font-bold">Prospective Memory</h1>
        <p className="text-gray-500 mt-2">Tasks, goals, and future-oriented items</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Active</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.taskBreakdown?.active}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.taskBreakdown?.completed}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Overdue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{data?.taskBreakdown?.overdue}</div>
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
          <CardTitle>Upcoming Tasks</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {data?.upcomingTasks?.map((task: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <div>
                  <p className="font-medium">{task.name}</p>
                  <p className="text-xs text-gray-500">Due {new Date(task.dueDate).toLocaleDateString()}</p>
                </div>
                <Badge>{task.priority}</Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
