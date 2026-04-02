import { useState } from 'react'
import { AppShell } from './components/layout/AppShell'
import { useAppMode } from './hooks/useAppMode'
import { PlaygroundPage } from './pages/PlaygroundPage'
import { EvalPage } from './pages/EvalPage'
import { ModelsPage } from './pages/ModelsPage'
import { ConnectorsPage } from './pages/ConnectorsPage'

export type View = 'playground' | 'eval' | 'models' | 'connectors'

export default function App() {
  const [view, setView] = useState<View>('playground')
  const { state: appState, setMode } = useAppMode()

  return (
    <AppShell activeView={view} onViewChange={setView} appState={appState} onModeChange={setMode}>
      {view === 'playground' && <PlaygroundPage appMode={appState.mode} />}
      {view === 'eval' && <EvalPage />}
      {view === 'models' && <ModelsPage />}
      {view === 'connectors' && <ConnectorsPage />}
    </AppShell>
  )
}
