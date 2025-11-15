import { Card } from '@/components/common/Card'
import { Stat } from '@/components/common/Stat'
import { Badge } from '@/components/common/Badge'
import { useAPI } from '@/hooks'

interface Skill {
  id: string
  name: string
  category: string
  effectiveness: number
  executions: number
  lastUsed: string
}

interface ProceduralResponse {
  skills: Skill[]
  stats: {
    totalSkills: number
    avgEffectiveness: number
    totalExecutions: number
  }
}

export const ProceduralMemoryPage = () => {
  const { data, loading } = useAPI<ProceduralResponse>('/api/procedural/skills')

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse h-64 bg-gray-800 rounded" />
      </div>
    )
  }

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Layer 3: Procedural Memory</h1>
        <p className="text-gray-400">Learned skills and workflows</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat label="Total Skills" value={data?.stats.totalSkills.toString() || '0'} />
        <Stat label="Avg Effectiveness" value={`${Math.round(data?.stats.avgEffectiveness || 0)}%`} />
        <Stat label="Total Executions" value={data?.stats.totalExecutions.toLocaleString() || '0'} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Skills Library</h3>}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-2 px-3 text-gray-400">Skill</th>
                <th className="text-left py-2 px-3 text-gray-400">Category</th>
                <th className="text-left py-2 px-3 text-gray-400">Effectiveness</th>
                <th className="text-left py-2 px-3 text-gray-400">Executions</th>
              </tr>
            </thead>
            <tbody>
              {data?.skills.map((skill) => (
                <tr key={skill.id} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-2 px-3 text-gray-50">{skill.name}</td>
                  <td className="py-2 px-3"><Badge>{skill.category}</Badge></td>
                  <td className="py-2 px-3">
                    <div className="h-2 bg-gray-700 rounded w-20 overflow-hidden">
                      <div className="h-full bg-green-500" style={{ width: `${skill.effectiveness}%` }} />
                    </div>
                  </td>
                  <td className="py-2 px-3 text-gray-50">{skill.executions}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}

export default ProceduralMemoryPage
