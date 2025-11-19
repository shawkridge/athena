import type { Metadata } from 'next'
import './globals.css'
import { Providers } from './providers'
import { MainNav } from '@/components/layout/main-nav'
import { Sidebar } from '@/components/layout/sidebar'

export const metadata: Metadata = {
  title: 'Athena Dashboard - Memory System Monitor',
  description: 'Real-time monitoring and management for Athena memory system - 8 layers, 60+ modules',
  keywords: ['athena', 'memory', 'dashboard', 'monitoring', 'episodic', 'semantic', 'procedural'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="font-sans antialiased">
        <Providers>
          <div className="flex h-screen overflow-hidden">
            {/* Sidebar */}
            <Sidebar />

            {/* Main content */}
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Top navigation */}
              <MainNav />

              {/* Page content */}
              <main className="flex-1 overflow-y-auto bg-background p-6">
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  )
}
