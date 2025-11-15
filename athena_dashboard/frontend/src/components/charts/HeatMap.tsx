/**
 * Heat map component for time-based patterns
 * Simple implementation using CSS grid and colors
 */

interface HeatMapData {
  date: string
  value: number
}

interface HeatMapProps {
  data: HeatMapData[]
  title?: string
}

const getColor = (value: number, min: number, max: number): string => {
  const percentage = (value - min) / (max - min)

  if (percentage < 0.2) return '#374151'
  if (percentage < 0.4) return '#1E40AF'
  if (percentage < 0.6) return '#3B82F6'
  if (percentage < 0.8) return '#60A5FA'
  return '#93C5FD'
}

export const HeatMap = ({ data, title }: HeatMapProps) => {
  const values = data.map((d) => d.value)
  const min = Math.min(...values)
  const max = Math.max(...values)

  return (
    <div className="w-full">
      {title && <h3 className="text-sm font-semibold text-gray-300 mb-4">{title}</h3>}
      <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(30px, 1fr))' }}>
        {data.map((item, index) => (
          <div
            key={index}
            className="h-8 rounded"
            style={{
              backgroundColor: getColor(item.value, min, max),
            }}
            title={`${item.date}: ${item.value}`}
          />
        ))}
      </div>
      <div className="flex gap-2 mt-4 text-xs text-gray-400">
        <span>Low</span>
        <div className="flex gap-1">
          {['#374151', '#1E40AF', '#3B82F6', '#60A5FA', '#93C5FD'].map((color) => (
            <div
              key={color}
              className="w-4 h-4 rounded"
              style={{ backgroundColor: color }}
            />
          ))}
        </div>
        <span>High</span>
      </div>
    </div>
  )
}

export default HeatMap
