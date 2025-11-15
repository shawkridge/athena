import { useState } from 'react'

export interface FilterOption {
  value: string
  label: string
}

interface FilterProps {
  label: string
  options: FilterOption[]
  selected: string[]
  onChange: (selected: string[]) => void
}

/**
 * Multi-select filter component
 */
export const Filter = ({ label, options, selected, onChange }: FilterProps) => {
  const [isOpen, setIsOpen] = useState(false)

  const handleToggle = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value))
    } else {
      onChange([...selected, value])
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-50 hover:bg-gray-600 transition-colors"
      >
        {label} ({selected.length})
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-10">
          {options.map((option) => (
            <label
              key={option.value}
              className="flex items-center gap-3 px-4 py-2 hover:bg-gray-700/50 cursor-pointer"
            >
              <input
                type="checkbox"
                checked={selected.includes(option.value)}
                onChange={() => handleToggle(option.value)}
                className="rounded"
              />
              <span className="text-gray-300">{option.label}</span>
            </label>
          ))}
        </div>
      )}
    </div>
  )
}

export default Filter
