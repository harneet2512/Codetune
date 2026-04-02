import { useState, useCallback } from 'react'

export type AppMode = 'demo' | 'live'

export interface ModelEndpointStatus {
  status: 'not_configured' | 'cold' | 'warm' | 'offline'
}

export interface AppModeState {
  mode: AppMode
  modelStatus: ModelEndpointStatus
  connectedApis: number
  totalApis: number
}

export interface UseAppModeReturn {
  state: AppModeState
  setMode: (mode: AppMode) => void
  setModelStatus: (status: ModelEndpointStatus) => void
}

export function useAppMode(): UseAppModeReturn {
  const [state, setState] = useState<AppModeState>({
    mode: 'demo',
    modelStatus: { status: 'not_configured' },
    connectedApis: 0,
    totalApis: 5,
  })

  const setMode = useCallback((mode: AppMode) => {
    setState(prev => ({ ...prev, mode }))
  }, [])

  const setModelStatus = useCallback((modelStatus: ModelEndpointStatus) => {
    setState(prev => ({ ...prev, modelStatus }))
  }, [])

  return { state, setMode, setModelStatus }
}
