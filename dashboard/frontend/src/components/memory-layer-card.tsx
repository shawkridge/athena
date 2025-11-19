'use client'

import Link from 'next/link'
import { LucideIcon } from 'lucide-react'
import { cn, formatNumber } from '@/lib/utils'

interface MemoryLayerCardProps {
  name: string
  description: string
  icon: LucideIcon
  color: string
  bgColor: string
  href: string
  stats?: any
}

export function MemoryLayerCard({
  name,
  description,
  icon: Icon,
  color,
  bgColor,
  href,
  stats,
}: MemoryLayerCardProps) {
  // Extract key stat from stats object
  const getKeyMetric = () => {
    if (!stats) return { label: 'No data', value: '-' }

    // Try common stat field names
    if (stats.total_events) return { label: 'Events', value: formatNumber(stats.total_events) }
    if (stats.total_memories) return { label: 'Memories', value: formatNumber(stats.total_memories) }
    if (stats.total_procedures) return { label: 'Procedures', value: formatNumber(stats.total_procedures) }
    if (stats.total_tasks) return { label: 'Tasks', value: formatNumber(stats.total_tasks) }
    if (stats.total_entities) return { label: 'Entities', value: formatNumber(stats.total_entities) }
    if (stats.total_patterns) return { label: 'Patterns', value: formatNumber(stats.total_patterns) }
    if (stats.total_plans) return { label: 'Plans', value: formatNumber(stats.total_plans) }

    return { label: 'Items', value: '-' }
  }

  const metric = getKeyMetric()

  return (
    <Link href={href}>
      <div className="bg-card border rounded-lg p-5 hover:shadow-md transition-all cursor-pointer group">
        <div className="flex items-start justify-between mb-3">
          <div className={cn('p-2 rounded-lg', bgColor)}>
            <Icon className={cn('h-6 w-6', color)} />
          </div>
        </div>

        <h3 className="text-base font-semibold mb-1 group-hover:text-primary transition-colors">
          {name}
        </h3>
        <p className="text-sm text-muted-foreground mb-4 line-clamp-2">{description}</p>

        <div className="flex items-baseline space-x-2">
          <span className="text-2xl font-bold">{metric.value}</span>
          <span className="text-xs text-muted-foreground uppercase">{metric.label}</span>
        </div>
      </div>
    </Link>
  )
}
