import { Brain, Code2, GitBranch } from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import type { ViewMode } from '../../types/playground'

interface Props {
  activeTab: ViewMode
  onChange: (tab: ViewMode) => void
}

const tabs: { key: ViewMode; label: string; Icon: typeof Brain }[] = [
  { key: 'blocks', label: 'Thinking', Icon: Brain },
  { key: 'raw', label: 'Raw', Icon: Code2 },
  { key: 'flow', label: 'Flow', Icon: GitBranch },
]

export function ViewTabBar({ activeTab, onChange }: Props) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 0,
      background: colors.surface,
      borderBottom: `1px solid ${colors.border}`,
      paddingLeft: 16,
      flexShrink: 0,
    }}>
      {tabs.map(({ key, label, Icon }) => {
        const isActive = activeTab === key
        return (
          <button
            key={key}
            onClick={() => onChange(key)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '7px 14px',
              fontSize: 11,
              fontFamily: fonts.mono,
              fontWeight: isActive ? 600 : 400,
              color: isActive ? colors.purple : colors.textMuted,
              background: 'transparent',
              border: 'none',
              borderBottom: isActive ? `2px solid ${colors.purple}` : '2px solid transparent',
              cursor: 'pointer',
              transition: 'color 0.15s, border-color 0.15s',
            }}
          >
            <Icon size={12} />
            {label}
          </button>
        )
      })}
    </div>
  )
}
