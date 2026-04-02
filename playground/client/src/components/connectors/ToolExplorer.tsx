import { useState, useEffect, useRef } from 'react'
import {
  GitBranch, Mail, FileText, Database, Target,
  ChevronRight, Play,
} from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import { connectors, type Connector } from '../../data/connectors'
import type { WorkbenchState } from '../../hooks/useConnectorWorkbench'

const iconMap: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  GitBranch, Mail, FileText, Database, Target,
}

interface Props {
  state: WorkbenchState
  dispatch: React.Dispatch<any>
  onConnect: (service: string) => void
  onRunTool: (toolName: string, connector: Connector) => void
}

export function ToolExplorer({ state, dispatch, onConnect, onRunTool }: Props) {
  const connector = connectors.find(c => c.service === state.selectedConnectorId)
  if (!connector) {
    return (
      <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 13, fontFamily: fonts.mono, color: colors.textMuted }}>
            Select a connector to explore its tools
          </div>
        </div>
      </div>
    )
  }

  const status = state.connectionStatus[connector.service]
  const isConnected = status === 'connected'
  const Icon = iconMap[connector.icon] || Database

  if (!isConnected) {
    return <ConnectionPrompt connector={connector} onConnect={onConnect} />
  }

  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Icon size={24} color={connector.color} />
          <span style={{ fontSize: 15, fontWeight: 700, fontFamily: fonts.mono, color: colors.text }}>
            {connector.service}
          </span>
          <span style={{
            fontSize: 9, fontFamily: fonts.mono, fontWeight: 600, color: colors.green,
            background: 'rgba(52,211,153,0.1)', padding: '2px 8px', borderRadius: 4,
          }}>
            Connected
          </span>
          <span style={{
            marginLeft: 'auto', fontSize: 10, fontFamily: fonts.mono,
            background: 'rgba(255,255,255,0.06)', padding: '3px 8px', borderRadius: 4,
            color: colors.textSecondary,
          }}>
            {connector.tools.length} tools
          </span>
        </div>
        <div style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textTertiary, marginTop: 6 }}>
          {connector.description}
        </div>
      </div>

      {/* Tool cards */}
      <div style={{ padding: '8px 0' }}>
        {connector.tools.map((tool) => {
          const isExpanded = state.expandedTools.has(tool.name)
          const response = state.toolResponses[tool.name]
          const [isHovered, setIsHovered] = useState(false)

          return (
            <div key={tool.name} style={{ borderBottom: `1px solid rgba(255,255,255,0.03)` }}>
              {/* Collapsed row */}
              <div
                onClick={() => dispatch({ type: 'TOGGLE_TOOL', tool: tool.name })}
                onMouseEnter={() => setIsHovered(true)}
                onMouseLeave={() => setIsHovered(false)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '12px 20px',
                  cursor: 'pointer', transition: 'background 0.15s ease',
                  background: isHovered ? 'rgba(255,255,255,0.02)' : 'transparent',
                }}
              >
                <ChevronRight
                  size={12}
                  style={{
                    color: colors.textMuted, flexShrink: 0,
                    transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                    transition: 'transform 0.15s ease',
                  }}
                />
                <span style={{ fontSize: 12, fontWeight: 600, fontFamily: fonts.mono, color: colors.pink }}>
                  {tool.name}
                </span>
                <span style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textTertiary, flex: 1 }}>
                  {tool.description}
                </span>
                {isHovered && !isExpanded && (
                  <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.purple, flexShrink: 0 }}>
                    Try it →
                  </span>
                )}
              </div>

              {/* Expanded: parameters + response */}
              {isExpanded && (
                <div style={{ padding: '0 20px 16px 44px' }}>
                  {/* Parameters */}
                  {tool.parameters.length > 0 && (
                    <>
                      <div style={{
                        fontSize: 9, fontWeight: 700, fontFamily: fonts.mono, color: colors.textMuted,
                        textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 8, marginTop: 4,
                      }}>
                        Parameters
                      </div>
                      {tool.parameters.map((param) => (
                        <div key={param.name} style={{ marginBottom: 10 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                            <span style={{ fontSize: 11, fontFamily: fonts.mono, fontWeight: 600, color: colors.pink }}>
                              {param.name}
                            </span>
                            <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textMuted }}>
                              {param.type}
                            </span>
                            <span style={{
                              fontSize: 9, fontFamily: fonts.mono, fontWeight: 700,
                              padding: '1px 4px', borderRadius: 2,
                              background: param.required ? 'rgba(248,113,113,0.15)' : 'rgba(255,255,255,0.06)',
                              color: param.required ? colors.red : colors.textMuted,
                            }}>
                              {param.required ? 'required' : 'optional'}
                            </span>
                          </div>
                          <input
                            type="text"
                            value={state.toolInputs[tool.name]?.[param.name] ?? ''}
                            onChange={(e) => dispatch({ type: 'SET_INPUT', tool: tool.name, param: param.name, value: e.target.value })}
                            style={{
                              width: '100%', padding: '8px 12px', borderRadius: 6,
                              background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
                              fontFamily: fonts.mono, fontSize: 11, color: colors.text,
                              outline: 'none',
                            }}
                            placeholder={param.description}
                          />
                          <div style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textFaintest, marginTop: 3 }}>
                            {param.description}
                          </div>
                        </div>
                      ))}
                    </>
                  )}

                  {/* Run button */}
                  <button
                    onClick={() => onRunTool(tool.name, connector)}
                    disabled={response?.typing}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 6, marginTop: 4,
                      padding: '8px 16px', borderRadius: 6, border: 'none',
                      background: response?.typing
                        ? 'rgba(167,139,250,0.15)'
                        : 'linear-gradient(135deg, #7c3aed, #a78bfa)',
                      color: '#fff', fontSize: 12, fontFamily: fonts.mono, fontWeight: 700,
                      cursor: response?.typing ? 'default' : 'pointer',
                      boxShadow: response?.typing ? 'none' : '0 2px 8px rgba(124,58,237,0.3)',
                      transition: 'all 0.15s ease',
                      animation: response?.typing ? 'pulse-opacity 1s ease-in-out infinite' : undefined,
                    }}
                  >
                    <Play size={12} fill="#fff" />
                    {response?.typing ? 'Executing...' : 'Run Tool'}
                  </button>

                  {/* Response */}
                  {response && response.text && (
                    <ResponseCard response={response} tool={tool} />
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <style>{`
        @keyframes pulse-opacity {
          0%, 100% { opacity: 0.7; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  )
}

function ResponseCard({ response, tool }: { response: { typing: boolean; text: string; done: boolean }; tool: any }) {
  const [displayedChars, setDisplayedChars] = useState(0)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    if (!response.text) return
    if (response.done) {
      setDisplayedChars(response.text.length)
      return
    }

    setDisplayedChars(0)
    let chars = 0
    let lastTime = 0

    function tick(now: number) {
      if (!lastTime) lastTime = now
      if (now - lastTime >= 8) {
        lastTime = now
        chars += 2
        setDisplayedChars(Math.min(chars, response.text.length))
        if (chars >= response.text.length) return
      }
      rafRef.current = requestAnimationFrame(tick)
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [response.text, response.done])

  const text = response.text.slice(0, displayedChars)
  const isSuccess = tool.mockResponse?.success !== false

  return (
    <div style={{ marginTop: 12 }}>
      <div style={{
        fontSize: 9, fontWeight: 700, fontFamily: fonts.mono, color: colors.textMuted,
        textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6,
      }}>
        Response
      </div>
      <pre style={{
        padding: '12px 16px', borderRadius: 6,
        background: isSuccess ? 'rgba(52,211,153,0.04)' : 'rgba(248,113,113,0.04)',
        borderLeft: `2px solid ${isSuccess ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)'}`,
        fontFamily: fonts.mono, fontSize: 10, lineHeight: 1.5,
        color: colors.textSecondary, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        margin: 0,
      }}>
        {text}
      </pre>
      <div style={{ display: 'flex', gap: 12, marginTop: 6, alignItems: 'center' }}>
        <span style={{
          fontSize: 9, fontFamily: fonts.mono, color: colors.textFaintest,
          background: 'rgba(255,255,255,0.04)', padding: '1px 6px', borderRadius: 3,
        }}>
          Mock response
        </span>
        <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textMuted }}>
          Response time: {(tool.mockResponse?.latencyMs / 1000).toFixed(2)}s
        </span>
        <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textFaintest, fontStyle: 'italic' }}>
          This is the data format models see during training
        </span>
      </div>
    </div>
  )
}

function ConnectionPrompt({ connector, onConnect }: { connector: Connector; onConnect: (s: string) => void }) {
  const Icon = iconMap[connector.icon] || Database

  return (
    <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
      <div style={{ textAlign: 'center', maxWidth: 320 }}>
        <div style={{ marginBottom: 16, opacity: 0.6 }}>
          <Icon size={48} color={connector.color} />
        </div>
        <div style={{ fontSize: 14, fontWeight: 600, fontFamily: fonts.mono, color: colors.text, marginBottom: 12 }}>
          Connect {connector.service} to access {connector.tools.length} tools
        </div>
        <div style={{ marginBottom: 16 }}>
          {connector.tools.map((t) => (
            <div key={t.name} style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textMuted, padding: '2px 0' }}>
              {t.name}
            </div>
          ))}
        </div>
        <button
          onClick={() => onConnect(connector.service)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '10px 24px', borderRadius: 8, border: 'none',
            background: `linear-gradient(135deg, ${connector.color}cc, ${connector.color})`,
            color: '#fff', fontSize: 13, fontFamily: fonts.mono, fontWeight: 700,
            cursor: 'pointer', boxShadow: `0 2px 12px ${connector.color}30`,
          }}
        >
          Connect {connector.service}
        </button>
        <div style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textFaintest, marginTop: 10 }}>
          Uses OAuth 2.0. CodeTune requests read-only access.
        </div>
      </div>
    </div>
  )
}
