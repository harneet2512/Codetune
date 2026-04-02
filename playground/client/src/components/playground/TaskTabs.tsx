import { useRef, useEffect } from 'react'
import { colors, fonts } from '../../theme/tokens'

interface TaskTab {
  id: string
  title: string
}

interface Props {
  tasks: TaskTab[]
  activeId: string
  onSelect: (id: string) => void
}

export function TaskTabs({ tasks, activeId, onSelect }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (activeRef.current && scrollRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
    }
  }, [activeId])

  return (
    <div
      ref={scrollRef}
      style={{
        display: 'flex',
        alignItems: 'center',
        background: colors.surface,
        borderBottom: `1px solid ${colors.border}`,
        overflowX: 'auto',
        overflowY: 'hidden',
        flexShrink: 0,
        scrollbarWidth: 'none',
      }}
    >
      {tasks.map(t => {
        const isActive = t.id === activeId
        return (
          <button
            key={t.id}
            ref={isActive ? activeRef : undefined}
            onClick={() => onSelect(t.id)}
            style={{
              padding: '8px 14px',
              fontSize: 11,
              fontFamily: fonts.mono,
              fontWeight: isActive ? 600 : 400,
              color: isActive ? colors.text : colors.textMuted,
              background: 'transparent',
              border: 'none',
              borderBottom: isActive ? `2px solid ${colors.purple}` : '2px solid transparent',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'color 0.15s, border-color 0.15s',
              letterSpacing: '-0.01em',
            }}
          >
            {t.title}
          </button>
        )
      })}
      {/* Custom prompt tab */}
      <button
        onClick={() => onSelect('__custom__')}
        style={{
          padding: '8px 14px',
          fontSize: 11,
          fontFamily: fonts.mono,
          fontWeight: activeId === '__custom__' ? 600 : 400,
          color: activeId === '__custom__' ? colors.purple : colors.textMuted,
          background: 'transparent',
          border: 'none',
          borderBottom: activeId === '__custom__' ? `2px solid ${colors.purple}` : '2px solid transparent',
          cursor: 'pointer',
          whiteSpace: 'nowrap',
          letterSpacing: '-0.01em',
        }}
      >
        + Custom Prompt
      </button>
    </div>
  )
}
