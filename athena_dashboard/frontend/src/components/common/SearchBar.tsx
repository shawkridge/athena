import { useState } from 'react'
import { useDebounce } from '@/hooks'

interface SearchBarProps {
  onSearch: (query: string) => void
  placeholder?: string
  debounceDelay?: number
}

/**
 * Debounced search input component
 */
export const SearchBar = ({
  onSearch,
  placeholder = 'Search...',
  debounceDelay = 300,
}: SearchBarProps) => {
  const [value, setValue] = useState('')
  const debouncedValue = useDebounce(value, debounceDelay)

  // Call onSearch when debounced value changes
  const handleChange = (newValue: string) => {
    setValue(newValue)
  }

  // Trigger search when debounced value changes
  useState(() => {
    onSearch(debouncedValue)
  }, [debouncedValue, onSearch])

  return (
    <div className="relative">
      <input
        type="text"
        value={value}
        onChange={(e) => handleChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-gray-50 placeholder-gray-400 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
      />
      {value && (
        <button
          onClick={() => setValue('')}
          className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-300"
        >
          ✕
        </button>
      )}
    </div>
  )
}

export default SearchBar
