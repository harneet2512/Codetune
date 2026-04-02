import { useState } from 'react'
import { ChevronUp, Play, Zap, Settings, Info } from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import type { AppMode, AppModeState } from '../../hooks/useAppMode'

interface ProfileMenuProps {
  appState: AppModeState
  onModeChange: (mode: AppMode) => void
}

export function ProfileMenu({ appState, onModeChange }: ProfileMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const isLive = appState.mode === 'live'

  return (
    <div style={{ position: 'relative' }}>
      {/* Popover menu (appears upward) */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            onClick={() => setIsOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 98 }}
          />
          <div
            style={{
              position: 'absolute',
              bottom: '100%',
              left: 8,
              right: 8,
              marginBottom: 4,
              background: 'rgba(18,16,22,0.98)',
              border: `1px solid rgba(255,255,255,0.08)`,
              borderRadius: 10,
              boxShadow: '0 -8px 30px rgba(0,0,0,0.4)',
              padding: 8,
              zIndex: 99,
            }}
          >
            {/* Mode toggle */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px' }}>
              <span style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textTertiary }}>Mode</span>
              <div style={{
                display: 'flex', background: 'rgba(255,255,255,0.04)', borderRadius: 6, padding: 2,
              }}>
                <button
                  onClick={() => onModeChange('demo')}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '4px 10px', borderRadius: 5, border: 'none',
                    background: !isLive ? 'rgba(167,139,250,0.15)' : 'transparent',
                    color: !isLive ? colors.purple : colors.textMuted,
                    fontSize: 10, fontFamily: fonts.mono, fontWeight: 600,
                    cursor: 'pointer', transition: 'all 0.15s ease',
                  }}
                >
                  <Play size={10} />
                  Demo
                </button>
                <button
                  onClick={() => onModeChange('live')}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 4,
                    padding: '4px 10px', borderRadius: 5, border: 'none',
                    background: isLive ? 'rgba(52,211,153,0.15)' : 'transparent',
                    color: isLive ? colors.green : colors.textMuted,
                    fontSize: 10, fontFamily: fonts.mono, fontWeight: 600,
                    cursor: 'pointer', transition: 'all 0.15s ease',
                  }}
                >
                  <Zap size={10} />
                  Live
                </button>
              </div>
            </div>

            {/* Endpoint status (live mode only) */}
            {isLive && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px' }}>
                <span style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textTertiary }}>Model</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textSecondary }}>
                    {appState.modelStatus.status === 'warm' ? 'HuggingFace T4' : 'Warming up...'}
                  </span>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: appState.modelStatus.status === 'warm' ? colors.green
                      : appState.modelStatus.status === 'cold' ? colors.amber
                      : colors.red,
                    animation: appState.modelStatus.status === 'cold' ? 'pulse-dot 1s ease-in-out infinite' : undefined,
                  }} />
                </div>
              </div>
            )}

            {/* API status (live mode only) */}
            {isLive && (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 8px' }}>
                <span style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textTertiary }}>APIs</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textSecondary }}>
                    {appState.connectedApis}/{appState.totalApis} connected
                  </span>
                  <div style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: appState.connectedApis > 0 ? colors.green : colors.textFaintest,
                  }} />
                </div>
              </div>
            )}

            {/* Separator */}
            <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '4px 0' }} />

            {/* Settings */}
            <button style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '6px 8px', border: 'none', background: 'transparent',
              color: colors.textTertiary, fontSize: 11, fontFamily: fonts.mono,
              cursor: 'pointer', borderRadius: 4, transition: 'all 0.15s ease',
            }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.color = colors.text }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = colors.textTertiary }}
            >
              <Settings size={14} />
              Settings
            </button>

            {/* About */}
            <button style={{
              display: 'flex', alignItems: 'center', gap: 8, width: '100%',
              padding: '6px 8px', border: 'none', background: 'transparent',
              color: colors.textTertiary, fontSize: 11, fontFamily: fonts.mono,
              cursor: 'pointer', borderRadius: 4, transition: 'all 0.15s ease',
            }}
              onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; e.currentTarget.style.color = colors.text }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = colors.textTertiary }}
            >
              <Info size={14} />
              About CodeTune
            </button>
          </div>
        </>
      )}

      {/* Collapsed profile row (always visible) */}
      <div
        onClick={() => setIsOpen(!isOpen)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '12px 14px', cursor: 'pointer',
          borderTop: `1px solid ${colors.border}`,
          transition: 'background 0.15s ease',
        }}
        onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
        onMouseLeave={e => { e.currentTarget.style.background = 'transparent' }}
      >
        {/* Avatar */}
        <div style={{
          width: 28, height: 28, borderRadius: '50%',
          background: 'linear-gradient(135deg, #7c3aed, #a78bfa)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 12, fontWeight: 700, color: '#fff', flexShrink: 0,
          fontFamily: fonts.mono,
        }}>
          H
        </div>
        <span style={{ fontSize: 12, fontWeight: 600, fontFamily: fonts.mono, color: colors.text, flex: 1 }}>
          Harneet
        </span>
        <span style={{
          fontSize: 9, fontFamily: fonts.mono, fontWeight: 700,
          padding: '2px 6px', borderRadius: 3,
          background: isLive ? 'rgba(52,211,153,0.15)' : 'rgba(167,139,250,0.15)',
          color: isLive ? colors.green : colors.purple,
          textTransform: 'uppercase', letterSpacing: '0.04em',
        }}>
          {appState.mode}
        </span>
        <ChevronUp
          size={12}
          style={{
            color: colors.textMuted,
            transform: isOpen ? 'rotate(0deg)' : 'rotate(180deg)',
            transition: 'transform 0.15s ease',
          }}
        />
      </div>

      <style>{`
        @keyframes pulse-dot {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}
