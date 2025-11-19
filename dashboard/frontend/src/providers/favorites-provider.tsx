'use client'

import { createContext, useContext, useState, useCallback, useEffect, ReactNode } from 'react'

export interface Favorite {
  id: string
  title: string
  path: string
  timestamp: number
}

interface FavoritesContextType {
  favorites: Favorite[]
  addFavorite: (id: string, title: string, path: string) => void
  removeFavorite: (id: string) => void
  isFavorite: (id: string) => boolean
  getFavorites: () => Favorite[]
  toggleFavorite: (id: string, title: string, path: string) => void
}

const FavoritesContext = createContext<FavoritesContextType | undefined>(undefined)

const STORAGE_KEY = 'athena-favorites'

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favorites, setFavorites] = useState<Favorite[]>([])
  const [isLoaded, setIsLoaded] = useState(false)

  // Load favorites from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setFavorites(Array.isArray(parsed) ? parsed : [])
      }
    } catch (error) {
      console.error('Failed to load favorites:', error)
    } finally {
      setIsLoaded(true)
    }
  }, [])

  // Save favorites to localStorage whenever they change
  useEffect(() => {
    if (!isLoaded) return

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(favorites))
    } catch (error) {
      console.error('Failed to save favorites:', error)
    }
  }, [favorites, isLoaded])

  const addFavorite = useCallback((id: string, title: string, path: string) => {
    setFavorites((prev) => {
      // Prevent duplicates
      if (prev.some((fav) => fav.id === id)) {
        return prev
      }

      const newFavorite: Favorite = {
        id,
        title,
        path,
        timestamp: Date.now(),
      }

      // Add to beginning of array (most recent first)
      return [newFavorite, ...prev]
    })
  }, [])

  const removeFavorite = useCallback((id: string) => {
    setFavorites((prev) => prev.filter((fav) => fav.id !== id))
  }, [])

  const isFavorite = useCallback(
    (id: string) => {
      return favorites.some((fav) => fav.id === id)
    },
    [favorites]
  )

  const getFavorites = useCallback(() => {
    return [...favorites]
  }, [favorites])

  const toggleFavorite = useCallback(
    (id: string, title: string, path: string) => {
      if (isFavorite(id)) {
        removeFavorite(id)
      } else {
        addFavorite(id, title, path)
      }
    },
    [isFavorite, removeFavorite, addFavorite]
  )

  return (
    <FavoritesContext.Provider
      value={{
        favorites,
        addFavorite,
        removeFavorite,
        isFavorite,
        getFavorites,
        toggleFavorite,
      }}
    >
      {children}
    </FavoritesContext.Provider>
  )
}

export function useFavorites() {
  const context = useContext(FavoritesContext)
  if (!context) {
    throw new Error('useFavorites must be used within FavoritesProvider')
  }
  return context
}
