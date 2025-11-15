import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface DataPoint {
  [key: string]: any
}

interface BarChartComponentProps {
  data: DataPoint[]
  bars: Array<{ key: string; fill?: string; name?: string }>
  xAxisKey: string
}

/**
 * Bar chart component using Recharts
 */
export const BarChartComponent = ({
  data,
  bars,
  xAxisKey,
}: BarChartComponentProps) => {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey={xAxisKey} stroke="#9CA3AF" style={{ fontSize: '12px' }} />
        <YAxis stroke="#9CA3AF" style={{ fontSize: '12px' }} />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
          }}
          labelStyle={{ color: '#F3F4F6' }}
        />
        <Legend />
        {bars.map((bar) => (
          <Bar
            key={bar.key}
            dataKey={bar.key}
            fill={bar.fill || '#3B82F6'}
            name={bar.name || bar.key}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  )
}

export default BarChartComponent
