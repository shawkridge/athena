'use client'

import { formatRelativeTime, truncate, getScoreColor } from '@/lib/utils'
import { Clock } from 'lucide-react'
import type { EpisodicEvent } from '@/lib/api'

interface RecentEventsCardProps {
  events: EpisodicEvent[]
}

export function RecentEventsCard({ events = [] }: RecentEventsCardProps) {
  return (
    <div className="bg-card border rounded-lg p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold">Recent Activity</h3>
        <Clock className="h-5 w-5 text-muted-foreground" />
      </div>

      {events.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <p>No recent activity</p>
        </div>
      ) : (
        <div className="space-y-3">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex items-start space-x-3 p-3 rounded-lg hover:bg-accent transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-medium text-muted-foreground uppercase">
                    {event.event_type}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {formatRelativeTime(event.timestamp)}
                  </span>
                </div>
                <p className="text-sm line-clamp-2">{truncate(event.content, 150)}</p>
                <div className="flex items-center space-x-3 mt-2">
                  <div className="flex items-center space-x-1">
                    <span className="text-xs text-muted-foreground">Importance:</span>
                    <span className={`text-xs font-medium ${getScoreColor(event.importance_score)}`}>
                      {(event.importance_score * 100).toFixed(0)}%
                    </span>
                  </div>
                  {event.session_id && (
                    <span className="text-xs text-muted-foreground">
                      Session: {event.session_id.slice(0, 8)}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
