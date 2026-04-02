import { useRef, useEffect } from 'react'
import { colors, fonts } from '../../theme/tokens'
import type { ThinkingLine } from '../../data/thinking'

interface Props {
  lines: ThinkingLine[]
  displayedLines: ThinkingLine[]
  currentLineIndex: number
  charIndex: number
  isAnimating: boolean
}

const lineStyles: Record<ThinkingLine['type'], {
  color: string
  bg?: string
  prefix?: string
  fontWeight?: number
}> = {
  think: {
    color: colors.thinking,
  },
  strong: {
    color: colors.text,
    fontWeight: 600,
  },
  tool_call: {
    color: colors.pink,
    bg: colors.pinkBg,
    prefix: '',
  },
  observe: {
    color: colors.green,
    bg: colors.greenBg,
    prefix: '',
  },
  conclusion: {
    color: colors.text, // overridden per line
  },
  error: {
    color: colors.red,
  },
  separator: {
    color: 'transparent',
  },
}

function getConclusionStyle(text: string): { color: string; bg: string } {
  if (text.startsWith('\u2713')) return { color: colors.green, bg: colors.greenBg }
  if (text.startsWith('\u2717')) return { color: colors.red, bg: colors.redBg }
  if (text.startsWith('!')) return { color: colors.amber, bg: colors.amberBg }
  return { color: colors.text, bg: 'transparent' }
}

function ThinkingLineElement({ line }: { line: ThinkingLine }) {
  if (line.type === 'separator') {
    return (
      <div style={{
        height: 1,
        background: 'rgba(255,255,255,0.04)',
        margin: '6px 0',
      }} />
    )
  }

  const style = lineStyles[line.type]
  let color = style.color
  let bg = style.bg || 'transparent'

  if (line.type === 'conclusion') {
    const cs = getConclusionStyle(line.text)
    color = cs.color
    bg = cs.bg
  }

  return (
    <div style={{
      color,
      background: bg,
      fontWeight: style.fontWeight || 400,
      padding: bg !== 'transparent' ? '3px 8px' : '1px 0',
      borderRadius: bg !== 'transparent' ? 3 : 0,
      margin: '1px 0',
      lineHeight: 1.7,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    }}>
      {style.prefix != null ? style.prefix : ''}{line.text}
    </div>
  )
}

function PartialLine({ line, charIndex }: { line: ThinkingLine; charIndex: number }) {
  if (line.type === 'separator') {
    return (
      <div style={{
        height: 1,
        background: 'rgba(255,255,255,0.04)',
        margin: '6px 0',
      }} />
    )
  }

  const style = lineStyles[line.type]
  let color = style.color
  let bg = style.bg || 'transparent'

  if (line.type === 'conclusion') {
    const cs = getConclusionStyle(line.text)
    color = cs.color
    bg = cs.bg
  }

  const prefix = style.prefix != null ? style.prefix : ''
  const partialText = line.text.slice(0, charIndex)

  return (
    <div style={{
      color,
      background: bg,
      fontWeight: style.fontWeight || 400,
      padding: bg !== 'transparent' ? '3px 8px' : '1px 0',
      borderRadius: bg !== 'transparent' ? 3 : 0,
      margin: '1px 0',
      lineHeight: 1.7,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
    }}>
      {prefix}{partialText}
      <span style={{
        display: 'inline-block',
        width: '1.5px',
        height: '1em',
        background: colors.purple,
        marginLeft: 1,
        verticalAlign: 'text-bottom',
        animation: 'cursor-blink 0.8s step-end infinite',
      }} />
      <style>{`
        @keyframes cursor-blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}

export function ThinkingView({ lines, displayedLines, currentLineIndex, charIndex, isAnimating }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [displayedLines, charIndex])

  const currentLine = isAnimating && currentLineIndex >= 0 && currentLineIndex < lines.length
    ? lines[currentLineIndex]
    : null

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: 14,
        background: colors.bg,
        fontFamily: fonts.mono,
        fontSize: 11,
        lineHeight: 1.7,
        scrollbarWidth: 'thin',
        scrollbarColor: `${colors.textMuted} transparent`,
      }}
    >
      {displayedLines.map((line, i) => (
        <ThinkingLineElement key={i} line={line} />
      ))}

      {currentLine && (
        <PartialLine line={currentLine} charIndex={charIndex} />
      )}

      {/* Empty state */}
      {displayedLines.length === 0 && !isAnimating && (
        <div style={{
          color: colors.textMuted,
          fontSize: 11,
          fontStyle: 'italic',
          padding: '20px 0',
          textAlign: 'center',
        }}>
          Press Run to start the thinking animation
        </div>
      )}
    </div>
  )
}
