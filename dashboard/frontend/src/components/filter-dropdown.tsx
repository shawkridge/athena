import { Filter, X } from 'lucide-react'
import { useState } from 'react'

interface FilterOption {
  value: string
  label: string
}

interface FilterDropdownProps {
  label: string
  options: FilterOption[]
  value: string
  onChange: (value: string) => void
  className?: string
}

export function FilterDropdown({
  label,
  options,
  value,
  onChange,
  className = ''
}: FilterDropdownProps) {
  const [isOpen, setIsOpen] = useState(false)

  const selectedOption = options.find(opt => opt.value === value)

  const handleClear = (e: React.MouseEvent) => {
    e.stopPropagation()
    onChange('')
    setIsOpen(false)
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-4 py-2 border rounded-md hover:bg-accent transition-colors"
      >
        <Filter className="h-4 w-4 text-muted-foreground" />
        <span className="text-sm">
          {label}: {selectedOption?.label || 'All'}
        </span>
        {value && (
          <X
            className="h-3 w-3 text-muted-foreground hover:text-foreground"
            onClick={handleClear}
          />
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-48 bg-white border rounded-md shadow-lg z-20">
            <div className="py-1">
              <button
                onClick={() => {
                  onChange('')
                  setIsOpen(false)
                }}
                className="w-full px-4 py-2 text-left text-sm hover:bg-accent transition-colors"
              >
                All
              </button>
              {options.map((option) => (
                <button
                  key={option.value}
                  onClick={() => {
                    onChange(option.value)
                    setIsOpen(false)
                  }}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-accent transition-colors ${
                    value === option.value ? 'bg-accent font-medium' : ''
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
