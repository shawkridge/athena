import { useState } from 'react'
import { Card } from '@/components/common/Card'
import { SearchBar } from '@/components/common/SearchBar'
import { Filter, type FilterOption } from '@/components/common/Filter'
import { Stat } from '@/components/common/Stat'
import { useAPI } from '@/hooks'
import { Badge } from '@/components/common/Badge'

interface SemanticMemory {
  id: string
  content: string
  domain: string
  quality: number
  lastAccessed: string
}

interface SemanticResponse {
  memories: SemanticMemory[]
  total: number
  stats: {
    totalMemories: number
    avgQuality: number
    domains: Array<{ name: string; count: number }>
  }
}

export const SemanticMemoryPage = () => {
  const [search, setSearch] = useState('')
  const [domains, setDomains] = useState<string[]>([])

  const queryParams = new URLSearchParams({
    search,
    ...(domains.length > 0 && { domains: domains.join(',') }),
  })

  const { data, loading } = useAPI<SemanticResponse>(
    `/api/semantic/search?${queryParams}`
  )

  if (loading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-800 rounded w-1/3" />
          <div className="h-48 bg-gray-800 rounded" />
        </div>
      </div>
    )
  }

  const domainOptions: FilterOption[] =
    data?.stats.domains.map((d) => ({
      value: d.name,
      label: `${d.name} (${d.count})`,
    })) || []

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-50">Layer 2: Semantic Memory</h1>
        <p className="text-gray-400">Knowledge search and quality metrics</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Stat label="Total Memories" value={data?.stats.totalMemories.toLocaleString() || '0'} />
        <Stat label="Avg Quality" value={`${Math.round(data?.stats.avgQuality || 0)}%`} />
        <Stat label="Domains" value={data?.stats.domains.length.toString() || '0'} />
      </div>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Search & Filter</h3>}>
        <div className="space-y-4">
          <SearchBar onSearch={setSearch} placeholder="Search knowledge..." />
          <Filter
            label="Domain"
            options={domainOptions}
            selected={domains}
            onChange={setDomains}
          />
        </div>
      </Card>

      <Card header={<h3 className="text-lg font-semibold text-gray-50">Results</h3>}>
        <div className="space-y-3">
          {data?.memories.length ? (
            data.memories.map((memory) => (
              <div
                key={memory.id}
                className="p-4 rounded-lg border border-gray-700 bg-gray-800/50 hover:bg-gray-800"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <Badge variant="info">{memory.domain}</Badge>
                    <p className="text-gray-50 mt-2">{memory.content}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <span>Quality: {memory.quality}%</span>
                  <span>{memory.lastAccessed}</span>
                </div>
              </div>
            ))
          ) : (
            <div className="text-center py-8 text-gray-400">No results found</div>
          )}
        </div>
      </Card>
    </div>
  )
}

export default SemanticMemoryPage
