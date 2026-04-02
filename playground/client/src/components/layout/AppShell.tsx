import { useState, type ReactNode } from 'react'
import { colors } from '../../theme/tokens'
import { Sidebar } from './Sidebar'
import type { View } from '../../App'
import type { AppMode, AppModeState } from '../../hooks/useAppMode'

interface AppShellProps {
  children: ReactNode
  activeView: View
  onViewChange: (view: View) => void
  appState: AppModeState
  onModeChange: (mode: AppMode) => void
}

export function AppShell({ children, activeView, onViewChange, appState, onModeChange }: AppShellProps) {
  const [collapsed, setCollapsed] = useState(false)
  const sidebarWidth = collapsed ? 52 : 230

  return (
    <div
      style={{
        display: 'flex',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        background: colors.bg,
      }}
    >
      <Sidebar
        activeView={activeView}
        onViewChange={onViewChange}
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((c) => !c)}
        width={sidebarWidth}
        appState={appState}
        onModeChange={onModeChange}
      />
      <main
        style={{
          flex: 1,
          overflow: 'auto',
          background: colors.bg,
          minWidth: 0,
        }}
      >
        {children}
      </main>
    </div>
  )
}
