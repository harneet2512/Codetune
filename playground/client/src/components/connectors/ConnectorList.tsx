import { useState } from 'react'
import {
  GitBranch, Mail, FileText, Database, Target, Plus, Loader2,
} from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import { connectors } from '../../data/connectors'
import type { WorkbenchState } from '../../hooks/useConnectorWorkbench'
import type { RecentCall } from '../../data/blocks'

const iconMap: Record<string, React.ComponentType<{ size?: number; color?: string; style?: React.CSSProperties }>> = {
  GitBranch, Mail, FileText, Database, Target,
}

interface Props {
  state: WorkbenchState
  onSelect: (service: string) => void
  onConnect: (service: string) => void
  onDisconnect: (service: string) => void
}

export function ConnectorList({ state, onSelect, onConnect, onDisconnect }: Props) {
  const [hovered, setHovered] = useState<string | null>(null)

  return (
    <div style={{
      width: 320, minWidth: 320, height: '100%', display: 'flex', flexDirection: 'column',
      borderRight: `1px solid ${colors.border}`, overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{ padding: 16, borderBottom: `1px solid ${colors.border}` }}>
        <div style={{ fontSize: 15, fontWeight: 700, fontFamily: fonts.mono, color: colors.text }}>
          Connectors
        </div>
        <div style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textMuted, marginTop: 2 }}>
          5 services, 17 tools
        </div>
      </div>

      {/* Connector cards */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {connectors.map((c) => {
          const status = state.connectionStatus[c.service]
          const isSelected = state.selectedConnectorId === c.service
          const isHovered = hovered === c.service
          const Icon = iconMap[c.icon] || Database
          const isConnected = status === 'connected'
          const isConnecting = status === 'connecting'

          return (
            <div
              key={c.service}
              onClick={() => onSelect(c.service)}
              onMouseEnter={() => setHovered(c.service)}
              onMouseLeave={() => setHovered(null)}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '10px 12px', borderRadius: 8, cursor: 'pointer',
                border: isSelected
                  ? `1px solid rgba(167,139,250,0.3)`
                  : `1px solid ${isConnected ? `${c.color}${isHovered ? '40' : '20'}` : colors.border}`,
                borderLeft: isSelected ? `3px solid ${colors.purple}` : undefined,
                background: isSelected
                  ? 'rgba(167,139,250,0.04)'
                  : isConnected ? `${c.color}08` : 'transparent',
                transition: 'all 0.15s ease',
              }}
            >
              {/* Icon */}
              <div style={{
                width: 36, height: 36, borderRadius: 8,
                background: `${c.color}${isConnected ? '18' : '10'}`,
                border: `1px solid ${isConnected ? `${c.color}30` : `${c.color}25`}`,
                borderStyle: isConnected ? 'solid' : 'dashed',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Icon
                  size={16}
                  color={c.color}
                  style={{
                    opacity: isConnected ? 1 : 0.4,
                    animation: isConnecting ? 'pulse-icon 0.8s ease-in-out infinite' : undefined,
                  }}
                />
              </div>

              {/* Text */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{
                  fontSize: 13, fontWeight: 600, fontFamily: fonts.mono,
                  color: isConnected ? colors.text : colors.textMuted,
                }}>
                  {c.service}
                </div>
                <div style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textFaintest }}>
                  {c.tools.length} tools{isConnected ? '' : ' available'}
                </div>
                {isConnected && isHovered && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDisconnect(c.service) }}
                    style={{
                      background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                      fontSize: 9, fontFamily: fonts.mono, color: colors.textFaintest,
                      marginTop: 1,
                    }}
                  >
                    Disconnect
                  </button>
                )}
              </div>

              {/* Right side: status or connect button */}
              {isConnecting ? (
                <Loader2 size={14} color={c.color} style={{ animation: 'spin 1s linear infinite', flexShrink: 0 }} />
              ) : isConnected ? (
                <div style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: colors.green, boxShadow: `0 0 6px ${colors.green}60`, flexShrink: 0,
                }} />
              ) : (
                <button
                  onClick={(e) => { e.stopPropagation(); onConnect(c.service) }}
                  style={{
                    fontSize: 10, fontWeight: 600, fontFamily: fonts.mono,
                    padding: '4px 12px', borderRadius: 5,
                    border: `1px solid ${c.color}40`, background: isHovered ? `${c.color}15` : 'transparent',
                    color: c.color, cursor: 'pointer', flexShrink: 0,
                    transition: 'all 0.15s ease',
                  }}
                >
                  Connect
                </button>
              )}
            </div>
          )
        })}

        {/* Add connector */}
        <button style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
          width: '100%', padding: 8, border: '1px dashed rgba(255,255,255,0.1)',
          borderRadius: 6, background: 'transparent', color: colors.textMuted,
          fontFamily: fonts.mono, fontSize: 10, cursor: 'pointer',
          transition: 'all 0.15s ease',
        }}>
          <Plus size={11} />
          Add connector
        </button>
      </div>

      {/* Recent Calls */}
      <div style={{ borderTop: `1px solid ${colors.border}`, padding: '10px 14px' }}>
        <div style={{
          fontSize: 9, fontWeight: 700, fontFamily: fonts.mono, color: colors.textFaintest,
          textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 6,
        }}>
          Recent Calls
        </div>
        {state.recentCalls.slice(0, 4).map((call: RecentCall, i: number) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0',
          }}>
            <div style={{
              width: 4, height: 4, borderRadius: '50%', background: colors.green, flexShrink: 0,
            }} />
            <span style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.pink, flex: 1 }}>
              {call.tool}
            </span>
            <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textFaintest }}>
              {call.latency}
            </span>
            <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textFaintest }}>
              {call.timestamp}
            </span>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes pulse-icon {
          0%, 100% { opacity: 0.4; }
          50% { opacity: 0.8; }
        }
      `}</style>
    </div>
  )
}
