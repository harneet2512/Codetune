import { useState } from 'react'
import { Play, RotateCcw, Send } from 'lucide-react'
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
  Hard: { color: colors.red, bg: colors.redBg },
  Medium: { color: colors.amber, bg: colors.amberBg },
  Easy: { color: colors.green, bg: colors.greenBg },
  Custom: { color: colors.purple, bg: colors.purpleBg },
}

export function PromptBar({
  prompt, difficulty, category, isRunning, isCustom,
  customPrompt, onRun, onReset, onCustomPromptChange, onCustomSubmit,
}: Props) {
  const dc = difficultyColors[difficulty] || difficultyColors.Medium

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '8px 16px',
      background: colors.surface,
      borderBottom: `1px solid ${colors.border}`,
      flexShrink: 0,
      gap: 12,
    }}>
      {isCustom ? (
        /* Free-text input mode */
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
          <span style={{
            fontSize: 9, fontFamily: fonts.mono, fontWeight: 700,
            padding: '2px 6px', borderRadius: 3,
            background: colors.purpleBg, color: colors.purple,
            textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0,
          }}>
            Custom
          </span>
          <input
            type="text"
            value={customPrompt}
            onChange={e => onCustomPromptChange(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && customPrompt.trim()) onCustomSubmit() }}
            placeholder="Type your own prompt..."
            style={{
              flex: 1,
              background: colors.bg,
              border: `1px solid ${colors.border}`,
              borderRadius: 5,
              padding: '6px 10px',
              fontSize: 12,
              fontFamily: fonts.mono,
              color: colors.text,
              outline: 'none',
              minWidth: 0,
            }}
          />
        </div>
      ) : (
        /* Preset task display */
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0, flex: 1 }}>
          <span style={{
            fontSize: 9, fontFamily: fonts.mono, fontWeight: 700,
            padding: '2px 6px', borderRadius: 3,
            background: dc.bg, color: dc.color,
            textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0,
          }}>
            {difficulty}
          </span>
          <span style={{
            fontSize: 9, fontFamily: fonts.mono, fontWeight: 600,
            padding: '2px 6px', borderRadius: 3,
            background: colors.purpleBg, color: colors.purple,
            textTransform: 'uppercase', letterSpacing: '0.05em', flexShrink: 0,
          }}>
            {category}
          </span>
          <span style={{
            fontSize: 12, fontFamily: fonts.mono, color: colors.text,
            whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', minWidth: 0,
          }}>
            {prompt}
          </span>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0 }}>
        {isCustom ? (
          <button
            onClick={onCustomSubmit}
            disabled={!customPrompt.trim() || isRunning}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '5px 12px', borderRadius: 5, border: 'none',
              background: customPrompt.trim() ? colors.purpleDark : colors.textMuted,
              color: '#fff', fontSize: 11, fontFamily: fonts.mono, fontWeight: 600,
              cursor: customPrompt.trim() ? 'pointer' : 'default',
              opacity: isRunning ? 0.7 : 1,
            }}
          >
            <Send size={11} />
            Send
          </button>
        ) : (
          <button
            onClick={onRun}
            disabled={isRunning}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '5px 12px', borderRadius: 5, border: 'none',
              background: colors.purpleDark, color: '#fff',
              fontSize: 11, fontFamily: fonts.mono, fontWeight: 600,
              cursor: isRunning ? 'default' : 'pointer',
              opacity: isRunning ? 0.7 : 1,
              animation: isRunning ? 'pulse-opacity 1.5s ease-in-out infinite' : undefined,
            }}
          >
            <Play size={11} fill="#fff" />
            {isRunning ? 'Running...' : 'Run'}
          </button>
        )}

        <button
          onClick={onReset}
          style={{
            display: 'flex', alignItems: 'center', gap: 4,
            padding: '5px 10px', borderRadius: 5,
            border: `1px solid ${colors.border}`,
            background: 'transparent', color: colors.textSecondary,
            fontSize: 11, fontFamily: fonts.mono, fontWeight: 500, cursor: 'pointer',
          }}
        >
          <RotateCcw size={11} />
          Reset
        </button>
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
