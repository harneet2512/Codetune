import { colors, fonts } from '../../theme/tokens'
import { blockStyles, blockBadgeBg, type Block as BlockType, type BlockType as BType } from '../../data/blocks'

interface BlockProps {
  block: BlockType
  isActive: boolean
  charIndex: number
  activeField: 'title' | 'detail'
  isNested: boolean
  fadeIn: boolean
}

export function Block({ block, isActive, charIndex, activeField, isNested, fadeIn }: BlockProps) {
  const style = blockStyles[block.type]
  const badgeBg = blockBadgeBg[block.type]

  const titleText = isActive && activeField === 'title'
    ? block.title.slice(0, charIndex)
    : block.title

  const detailText = isActive
    ? (activeField === 'detail' ? (block.detail ?? '').slice(0, charIndex) : (activeField === 'title' ? '' : block.detail))
    : block.detail

  const showCursor = isActive

  return (
    <div
      style={{
        padding: '7px 10px',
        background: style.bg,
        borderLeft: `2px solid ${style.color}25`,
        borderRadius: 4,
        marginBottom: 2,
        marginLeft: isNested ? 20 : 0,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 8,
        animation: fadeIn ? 'blockFadeIn 400ms cubic-bezier(0.16, 1, 0.3, 1) forwards' : undefined,
        transition: 'background 0.15s ease',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = `${style.color}12`
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = style.bg
      }}
    >
      {/* Status icon */}
      <span
        style={{
          fontSize: 11,
          fontFamily: fonts.mono,
          color: style.color,
          flexShrink: 0,
          lineHeight: '18px',
          width: 14,
          textAlign: 'center',
        }}
      >
        {style.icon}
      </span>

      {/* Type badge */}
      <span
        style={{
          fontSize: 9,
          fontFamily: fonts.mono,
          fontWeight: 700,
          letterSpacing: '0.08em',
          color: style.color,
          background: badgeBg,
          padding: '1px 5px',
          borderRadius: 3,
          flexShrink: 0,
          lineHeight: '16px',
        }}
      >
        {style.badgeLabel}
      </span>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: 12,
            fontFamily: fonts.mono,
            fontWeight: 600,
            color: colors.text,
            lineHeight: '18px',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-word',
          }}
        >
          {titleText}
          {showCursor && activeField === 'title' && <Cursor />}
        </div>
        {(detailText || (isActive && activeField === 'detail')) && (
          <div
            style={{
              fontSize: 10.5,
              fontFamily: fonts.mono,
              color: colors.textTertiary,
              lineHeight: 1.4,
              marginTop: 2,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {detailText}
            {showCursor && activeField === 'detail' && <Cursor />}
          </div>
        )}
      </div>

      <style>{`
        @keyframes blockFadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}

function Cursor() {
  return (
    <span
      style={{
        display: 'inline-block',
        width: '1.5px',
        height: '1em',
        background: colors.purple,
        marginLeft: 1,
        verticalAlign: 'text-bottom',
        animation: 'cursorBlink 0.8s step-end infinite',
      }}
    />
  )
}
