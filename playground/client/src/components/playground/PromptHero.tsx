import { useState } from 'react'
import { Play, RotateCcw, Send, Activity } from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'

interface Props {
  prompt: string
  difficulty: string
  category: string
  isRunning: boolean
  isCustom: boolean
  customPrompt: string
  onRun: () => void
  onReset: () => void
  onCustomPromptChange: (val: string) => void
  onCustomSubmit: () => void
}

const difficultyColors: Record<string, { color: string; bg: string }> = {
  Hard: { color: colors.red, bg: 'rgba(248,113,113,0.15)' },
  Medium: { color: colors.amber, bg: 'rgba(251,191,36,0.15)' },
  Easy: { color: colors.green, bg: 'rgba(52,211,153,0.15)' },
  Custom: { color: colors.purple, bg: 'rgba(167,139,250,0.12)' },
}

export function PromptHero({
  prompt, difficulty, category, isRunning, isCustom,
  customPrompt, onRun, onReset, onCustomPromptChange, onCustomSubmit,
}: Props) {
  const [isFocused, setIsFocused] = useState(false)
  const dc = difficultyColors[difficulty] || difficultyColors.Medium

  const displayPrompt = isCustom ? customPrompt : prompt

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.03)',
        border: `1px solid ${isFocused ? 'rgba(167,139,250,0.3)' : 'rgba(255,255,255,0.08)'}`,
        borderRadius: 12,
        padding: '16px 20px',
        margin: '10px 8px',
        flexShrink: 0,
        transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
        boxShadow: isFocused
          ? '0 0 0 1px rgba(167,139,250,0.3), 0 4px 20px rgba(167,139,250,0.08)'
          : 'none',
      }}
    >
      {/* Row 1: Badges */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <span
          style={{
            fontSize: 9, fontFamily: fonts.mono, fontWeight: 700,
            padding: '3px 8px', borderRadius: 4,
            background: dc.bg, color: dc.color,
            textTransform: 'uppercase', letterSpacing: '0.08em',
          }}
        >
          {difficulty}
        </span>
        <span
          style={{
            fontSize: 9, fontFamily: fonts.mono, fontWeight: 700,
            padding: '3px 8px', borderRadius: 4,
            background: 'rgba(167,139,250,0.12)', color: colors.purple,
            textTransform: 'uppercase', letterSpacing: '0.08em',
          }}
        >
          {category}
        </span>
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 5, height: 5, borderRadius: '50%', background: colors.green, display: 'inline-block' }} />
          <span style={{ fontSize: 9, fontFamily: fonts.mono, color: colors.textMuted }}>Qwen 2.5 7B</span>
        </span>
      </div>

      {/* Row 2: Input */}
      {isCustom ? (
        <textarea
          value={customPrompt}
          onChange={e => onCustomPromptChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && customPrompt.trim()) { e.preventDefault(); onCustomSubmit() } }}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Describe a task to run across all three models..."
          rows={2}
          style={{
            width: '100%',
            fontSize: 14, fontFamily: fonts.mono, fontWeight: 500,
            color: colors.text, background: 'transparent',
            border: 'none', outline: 'none', resize: 'none',
            padding: '10px 0', lineHeight: 1.5,
          }}
        />
      ) : (
        <div
          style={{
            fontSize: 14, fontFamily: fonts.mono, fontWeight: 500,
            color: colors.text, padding: '10px 0', lineHeight: 1.5,
            minHeight: 42,
          }}
        >
          {displayPrompt}
        </div>
      )}

      {/* Row 3: Actions */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontSize: 10, fontFamily: fonts.mono, color: colors.textFaintest }}>
          3 models × 1 task
        </span>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            onClick={onReset}
            style={{
              display: 'flex', alignItems: 'center', gap: 4,
              padding: '6px 12px', borderRadius: 6,
              border: `1px solid rgba(255,255,255,0.1)`,
              background: 'transparent', color: colors.textTertiary,
              fontSize: 11, fontFamily: fonts.mono, fontWeight: 500, cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <RotateCcw size={11} />
            Reset
          </button>

          {isCustom ? (
            <button
              onClick={onCustomSubmit}
              disabled={!customPrompt.trim() || isRunning}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 20px', borderRadius: 8, border: 'none',
                background: customPrompt.trim() && !isRunning
                  ? 'linear-gradient(135deg, #7c3aed, #a78bfa)'
                  : 'rgba(167,139,250,0.15)',
                color: '#fff', fontSize: 12, fontFamily: fonts.mono, fontWeight: 700,
                cursor: customPrompt.trim() && !isRunning ? 'pointer' : 'default',
                boxShadow: customPrompt.trim() && !isRunning ? '0 2px 12px rgba(124,58,237,0.3)' : 'none',
                transition: 'all 0.15s ease',
              }}
            >
              <Send size={12} />
              Send
            </button>
          ) : (
            <button
              onClick={onRun}
              disabled={isRunning}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 20px', borderRadius: 8, border: 'none',
                background: isRunning
                  ? 'rgba(167,139,250,0.15)'
                  : 'linear-gradient(135deg, #7c3aed, #a78bfa)',
                color: '#fff', fontSize: 12, fontFamily: fonts.mono, fontWeight: 700,
                cursor: isRunning ? 'default' : 'pointer',
                boxShadow: isRunning ? 'none' : '0 2px 12px rgba(124,58,237,0.3)',
                transition: 'all 0.15s ease',
                animation: isRunning ? 'pulse-opacity 1.5s ease-in-out infinite' : undefined,
              }}
            >
              {isRunning ? <Activity size={14} /> : <Play size={14} fill="#fff" />}
              {isRunning ? 'Running...' : 'Run All Models'}
            </button>
          )}
        </div>
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
