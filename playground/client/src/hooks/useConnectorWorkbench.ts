import { useReducer, useEffect, useRef, useCallback } from 'react'
import { connectors, type Connector } from '../data/connectors'
import { recentCalls, type RecentCall } from '../data/blocks'

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface WorkbenchState {
  selectedConnectorId: string | null
  connectionStatus: Record<string, 'disconnected' | 'connecting' | 'connected'>
  expandedTools: Set<string>
  toolInputs: Record<string, Record<string, string>>
  toolResponses: Record<string, { typing: boolean; text: string; done: boolean }>
  recentCalls: RecentCall[]
}

type Action =
  | { type: 'SELECT_CONNECTOR'; id: string }
  | { type: 'CONNECT_START'; service: string }
  | { type: 'CONNECT_DONE'; service: string }
  | { type: 'DISCONNECT'; service: string }
  | { type: 'TOGGLE_TOOL'; tool: string }
  | { type: 'SET_INPUT'; tool: string; param: string; value: string }
  | { type: 'RUN_TOOL'; tool: string }
  | { type: 'TOOL_RESPONSE'; tool: string; text: string }
  | { type: 'TYPING_DONE'; tool: string }

function initState(): WorkbenchState {
  const status: Record<string, string> = {}
  const inputs: Record<string, Record<string, string>> = {}

  for (const c of connectors) {
    status[c.service] = c.connected ? 'connected' : 'disconnected'
    for (const tool of c.tools) {
      inputs[tool.name] = { ...tool.exampleValues }
    }
  }

  return {
    selectedConnectorId: connectors.find(c => c.connected)?.service ?? null,
    connectionStatus: status as Record<string, 'disconnected' | 'connecting' | 'connected'>,
    expandedTools: new Set(),
    toolInputs: inputs,
    toolResponses: {},
    recentCalls: [...recentCalls],
  }
}

function reducer(state: WorkbenchState, action: Action): WorkbenchState {
  switch (action.type) {
    case 'SELECT_CONNECTOR':
      return { ...state, selectedConnectorId: action.id }
    case 'CONNECT_START':
      return { ...state, connectionStatus: { ...state.connectionStatus, [action.service]: 'connecting' } }
    case 'CONNECT_DONE':
      return {
        ...state,
        connectionStatus: { ...state.connectionStatus, [action.service]: 'connected' },
        selectedConnectorId: action.service,
      }
    case 'DISCONNECT':
      return { ...state, connectionStatus: { ...state.connectionStatus, [action.service]: 'disconnected' } }
    case 'TOGGLE_TOOL': {
      const next = new Set(state.expandedTools)
      if (next.has(action.tool)) next.delete(action.tool)
      else next.add(action.tool)
      return { ...state, expandedTools: next }
    }
    case 'SET_INPUT':
      return {
        ...state,
        toolInputs: {
          ...state.toolInputs,
          [action.tool]: { ...state.toolInputs[action.tool], [action.param]: action.value },
        },
      }
    case 'RUN_TOOL':
      return {
        ...state,
        toolResponses: { ...state.toolResponses, [action.tool]: { typing: true, text: '', done: false } },
      }
    case 'TOOL_RESPONSE':
      return {
        ...state,
        toolResponses: { ...state.toolResponses, [action.tool]: { typing: true, text: action.text, done: false } },
        recentCalls: [
          { tool: action.tool, latency: `${Math.floor(Math.random() * 200 + 100)}ms`, timestamp: 'just now' },
          ...state.recentCalls.slice(0, 3),
        ],
      }
    case 'TYPING_DONE':
      return {
        ...state,
        toolResponses: {
          ...state.toolResponses,
          [action.tool]: { ...state.toolResponses[action.tool], typing: false, done: true },
        },
      }
    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useConnectorWorkbench() {
  const [state, dispatch] = useReducer(reducer, undefined, initState)
  const timers = useRef<number[]>([])

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      for (const t of timers.current) clearTimeout(t)
    }
  }, [])

  const connect = useCallback((service: string) => {
    dispatch({ type: 'CONNECT_START', service })
    const t = window.setTimeout(() => {
      dispatch({ type: 'CONNECT_DONE', service })
    }, 1500)
    timers.current.push(t)
  }, [])

  const disconnect = useCallback((service: string) => {
    dispatch({ type: 'DISCONNECT', service })
  }, [])

  const runTool = useCallback((toolName: string, connector: Connector) => {
    const tool = connector.tools.find(t => t.name === toolName)
    if (!tool) return

    dispatch({ type: 'RUN_TOOL', tool: toolName })

    const t1 = window.setTimeout(() => {
      dispatch({ type: 'TOOL_RESPONSE', tool: toolName, text: tool.mockResponse.data })
    }, 800)
    timers.current.push(t1)

    const t2 = window.setTimeout(() => {
      dispatch({ type: 'TYPING_DONE', tool: toolName })
    }, 800 + tool.mockResponse.data.length * 8)
    timers.current.push(t2)
  }, [])

  return { state, dispatch, connect, disconnect, runTool }
}
