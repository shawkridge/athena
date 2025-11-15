import { useState } from 'react'
import { format } from 'date-fns'

interface DateRangeProps {
  startDate: Date | null
  endDate: Date | null
  onDateChange: (start: Date | null, end: Date | null) => void
}

/**
 * Date range picker component
 */
export const DateRange = ({ startDate, endDate, onDateChange }: DateRangeProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const date = e.target.value ? new Date(e.target.value) : null
    onDateChange(date, endDate)
  }

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const date = e.target.value ? new Date(e.target.value) : null
    onDateChange(startDate, date)
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-50 hover:bg-gray-600 transition-colors"
      >
        📅{' '}
        {startDate && endDate
          ? `${format(startDate, 'MMM d')} - ${format(endDate, 'MMM d')}`
          : 'Select range'}
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 bg-gray-800 border border-gray-700 rounded-lg shadow-lg p-4 z-10">
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Start Date</label>
              <input
                type="date"
                value={startDate ? format(startDate, 'yyyy-MM-dd') : ''}
                onChange={handleStartChange}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-50 focus:border-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">End Date</label>
              <input
                type="date"
                value={endDate ? format(endDate, 'yyyy-MM-dd') : ''}
                onChange={handleEndChange}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-gray-50 focus:border-blue-500"
              />
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="w-full px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export default DateRange
