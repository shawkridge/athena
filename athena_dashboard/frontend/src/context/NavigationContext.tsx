import React, { createContext, useContext, useState, ReactNode } from 'react'

interface NavigationContextType {
  currentPage: string
  setCurrentPage: (page: string) => void
  isSidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

const NavigationContext = createContext<NavigationContextType | undefined>(undefined)

export function NavigationProvider({ children }: { children: ReactNode }) {
  const [currentPage, setCurrentPage] = useState('overview')
  const [isSidebarOpen, setSidebarOpen] = useState(true)

  return (
    <NavigationContext.Provider
      value={{
        currentPage,
        setCurrentPage,
        isSidebarOpen,
        setSidebarOpen,
      }}
    >
      {children}
    </NavigationContext.Provider>
  )
}

export function useNavigation() {
  const context = useContext(NavigationContext)
  if (context === undefined) {
    throw new Error('useNavigation must be used within NavigationProvider')
  }
  return context
}
