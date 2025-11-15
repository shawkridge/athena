import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface DataPoint {
  [key: string]: any
  timestamp?: string
  date?: string
  time?: string
}

interface TimeSeriesChartProps {
  data: DataPoint[]
  lines: Array<{ key: string; stroke?: string; name?: string }>
  xAxisKey?: string
}

/**
 * Time series line chart component using Recharts
 */
export const TimeSeriesChart = ({
  data,
  lines,
  xAxisKey = 'timestamp',
}: TimeSeriesChartProps) => {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis
          dataKey={xAxisKey}
          stroke="#9CA3AF"
          style={{ fontSize: '12px' }}
        />
        <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
          }}
          labelStyle={{ color: '#F3F4F6' }}
        />
        <Legend />
        {lines.map((line) => (
          <Line
            key={line.key}
            type="monotone"
            dataKey={line.key}
            stroke={line.stroke || '#3B82F6'}
            name={line.name || line.key}
            dot={false}
            strokeWidth={2}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

export default TimeSeriesChart
