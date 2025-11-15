import {
  PieChart,
  Pie,
  Cell,
  Legend,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface DataPoint {
  name: string
  value: number
}

interface PieChartComponentProps {
  data: DataPoint[]
  colors?: string[]
}

const defaultColors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

/**
 * Pie chart component using Recharts
 */
export const PieChartComponent = ({
  data,
  colors = defaultColors,
}: PieChartComponentProps) => {
  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, value }) => `${name}: ${value}`}
          outerRadius={120}
          fill="#3B82F6"
          dataKey="value"
        >
          {data.map((_, index) => (
            <Cell
              key={`cell-${index}`}
              fill={colors[index % colors.length]}
            />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1F2937',
            border: '1px solid #374151',
          }}
          labelStyle={{ color: '#F3F4F6' }}
        />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )
}

export default PieChartComponent
