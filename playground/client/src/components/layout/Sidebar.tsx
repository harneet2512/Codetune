import { useState } from 'react'
import {
  Terminal,
  BarChart3,
  Cpu,
  Plug,
  GitBranch,
  Mail,
  FileText,
  Database,
  Target,
  Plus,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { colors, fonts, modelColors } from '../../theme/tokens'
import { ProfileMenu } from './ProfileMenu'
import type { View } from '../../App'
import type { AppMode, AppModeState } from '../../hooks/useAppMode'

interface SidebarProps {
  activeView: View
  onViewChange: (view: View) => void
  collapsed: boolean
  onToggleCollapse: () => void
  width: number
  appState: AppModeState
  onModeChange: (mode: AppMode) => void
}

const navItems: { view: View; label: string; icon: typeof Terminal }[] = [
  { view: 'playground', label: 'Playground', icon: Terminal },
  { view: 'eval', label: 'Eval Dashboard', icon: BarChart3 },
  { view: 'models', label: 'Models', icon: Cpu },
  { view: 'connectors', label: 'Connectors', icon: Plug },
]

interface ConnectorDef {
  label: string
  icon: typeof GitBranch
  color: string
  tools: number
  connected: boolean
}

const connectorList: ConnectorDef[] = [
  { label: 'GitHub', icon: GitBranch, color: '#e2e0e6', tools: 5, connected: true },
  { label: 'Gmail', icon: Mail, color: '#ea4335', tools: 4, connected: true },
  { label: 'Google Drive', icon: FileText, color: '#4285f4', tools: 4, connected: true },
  { label: 'Confluence', icon: Database, color: '#1868db', tools: 3, connected: false },
  { label: 'Jira', icon: Target, color: '#0052cc', tools: 4, connected: false },
]

const modelList: { key: keyof typeof modelColors; label: string }[] = [
  { key: 'base', label: 'Qwen 2.5 7B' },
  { key: 'sft', label: 'Qwen 2.5 7B + SFT' },
  { key: 'grpo', label: 'Qwen 2.5 7B + GRPO' },
]

export function Sidebar({
  activeView,
  onViewChange,
  collapsed,
  onToggleCollapse,
  width,
  appState,
  onModeChange,
}: SidebarProps) {
  const [hoveredConnector, setHoveredConnector] = useState<string | null>(null)

  const sectionTitle = (text: string) =>
    !collapsed ? (
      <div
        style={{
          fontSize: 9,
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.1em',
          color: colors.textFaintest,
          padding: '16px 14px 6px',
          fontFamily: fonts.mono,
        }}
      >
        {text}
      </div>
    ) : null

  return (
    <aside
      style={{
        width,
        minWidth: width,
        height: '100vh',
        background: colors.surface,
        borderRight: `1px solid ${colors.border}`,
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Logo */}
      <div
        style={{
          padding: collapsed ? '16px 10px' : '16px 14px',
          borderBottom: `1px solid ${colors.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          minHeight: 56,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 7,
            background: 'linear-gradient(135deg, #a78bfa, #7c3aed)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: fonts.mono,
            fontWeight: 700,
            fontSize: 15,
            color: '#fff',
            flexShrink: 0,
            boxShadow: '0 2px 12px rgba(167,139,250,0.3)',
          }}
        >
          C
        </div>
        {!collapsed && (
          <div style={{ overflow: 'hidden' }}>
            <div
              style={{
                fontFamily: fonts.mono,
                fontWeight: 800,
                fontSize: 14,
                color: colors.text,
                lineHeight: 1.2,
              }}
            >
              CodeTune
            </div>
            <div
              style={{
                fontSize: 9,
                fontWeight: 500,
                textTransform: 'uppercase',
                letterSpacing: '0.04em',
                color: colors.textMuted,
                fontFamily: fonts.mono,
              }}
            >
              POST-TRAINING LAB
            </div>
          </div>
        )}
      </div>

      {/* Workspace Nav */}
      {sectionTitle('Workspace')}
      <nav style={{ padding: '0 6px 4px' }}>
        {navItems.map(({ view, label, icon: Icon }) => {
          const active = activeView === view
          return (
            <button
              key={view}
              onClick={() => onViewChange(view)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                width: '100%',
                padding: collapsed ? '8px 10px' : '8px 10px',
                border: 'none',
                background: active ? 'rgba(167,139,250,0.1)' : 'transparent',
                color: active ? colors.purple : colors.textTertiary,
                cursor: 'pointer',
                fontSize: 12,
                fontFamily: fonts.mono,
                fontWeight: 500,
                textAlign: 'left',
                transition: 'all 0.15s ease',
                borderRadius: 6,
              }}
              onMouseEnter={(e) => {
                if (!active) {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.04)'
                  e.currentTarget.style.color = colors.text
                }
              }}
              onMouseLeave={(e) => {
                if (!active) {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.color = colors.textTertiary
                }
              }}
            >
              <Icon size={14} style={{ flexShrink: 0 }} />
              {!collapsed && label}
            </button>
          )
        })}
      </nav>

      {/* Models */}
      {sectionTitle('Models')}
      <div style={{ padding: collapsed ? '4px 0' : '0 8px 4px' }}>
        {modelList.map(({ key, label }) => {
          const mc = modelColors[key]
          return (
            <div
              key={key}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: collapsed ? '4px 16px' : '4px 8px',
                fontSize: 11,
                color: colors.textSecondary,
                fontFamily: fonts.mono,
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: mc.color,
                  boxShadow: `0 0 4px ${mc.color}66`,
                  flexShrink: 0,
                }}
              />
              {!collapsed && <span>{label}</span>}
            </div>
          )
        })}
      </div>

      {/* Connectors */}
      {sectionTitle('Connectors')}
      <div style={{ padding: collapsed ? '4px 0' : '0 8px 4px', display: 'flex', flexDirection: 'column', gap: 4 }}>
        {connectorList.map(({ label, icon: Icon, color, tools, connected }) => {
          const isHovered = hoveredConnector === label
          return (
            <div
              key={label}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: collapsed ? '6px 10px' : '10px 12px',
                borderRadius: 8,
                border: `1px solid ${connected ? (isHovered ? `${color}60` : `${color}30`) : colors.border}`,
                background: connected ? (isHovered ? `${color}12` : `${color}08`) : 'transparent',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
              onMouseEnter={() => setHoveredConnector(label)}
              onMouseLeave={() => setHoveredConnector(null)}
            >
              {/* Icon container */}
              <div
                style={{
                  width: 32,
                  height: 32,
                  borderRadius: 8,
                  background: `${color}18`,
                  border: `1px solid ${color}30`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Icon size={16} color={color} />
              </div>
              {!collapsed && (
                <>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: colors.text,
                        fontFamily: fonts.mono,
                        lineHeight: 1.2,
                      }}
                    >
                      {label}
                    </div>
                    <div
                      style={{
                        fontSize: 10,
                        color: colors.textMuted,
                        fontFamily: fonts.mono,
                      }}
                    >
                      {tools} tools
                    </div>
                  </div>
                  {/* Status dot */}
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: connected ? colors.green : colors.textFaintest,
                      boxShadow: connected ? `0 0 4px ${colors.green}66` : 'none',
                      flexShrink: 0,
                    }}
                  />
                </>
              )}
            </div>
          )
        })}

        {/* Add connector button */}
        {!collapsed && (
          <button
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 6,
              width: '100%',
              padding: 8,
              border: '1px dashed rgba(255,255,255,0.1)',
              borderRadius: 6,
              background: 'transparent',
              color: colors.textMuted,
              fontFamily: fonts.mono,
              fontSize: 10,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'
              e.currentTarget.style.color = colors.textTertiary
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'
              e.currentTarget.style.color = colors.textMuted
            }}
          >
            <Plus size={11} />
            Add connector
          </button>
        )}
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Profile Menu */}
      {!collapsed && (
        <ProfileMenu appState={appState} onModeChange={onModeChange} />
      )}
      {collapsed && (
        <div style={{
          padding: '12px 10px', borderTop: `1px solid ${colors.border}`,
          display: 'flex', justifyContent: 'center',
        }}>
          <div style={{
            width: 24, height: 24, borderRadius: '50%',
            background: 'linear-gradient(135deg, #7c3aed, #a78bfa)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 10, fontWeight: 700, color: '#fff', fontFamily: fonts.mono,
          }}>H</div>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={onToggleCollapse}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '10px',
          border: 'none',
          borderTop: `1px solid ${colors.border}`,
          background: 'transparent',
          color: colors.textMuted,
          cursor: 'pointer',
          transition: 'color 0.15s ease',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = colors.text
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = colors.textMuted
        }}
      >
        {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  )
}
