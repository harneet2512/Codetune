import { useMemo } from 'react'
import { colors, fonts } from '../../theme/tokens'

interface Props {
  rawTrace: string
}

interface Segment {
  text: string
  color: string
}

function highlightTrace(raw: string): Segment[] {
  const segments: Segment[] = []
  const regex = /(<\/?(?:think|tool_call|observation|answer)>)/g
  let lastIndex = 0
  let currentColor = colors.textSecondary

  const tagColors: Record<string, string> = {
    '<think>': colors.purple,
    '</think>': colors.purple,
    '<tool_call>': colors.pink,
    '</tool_call>': colors.pink,
    '<observation>': colors.green,
    '</observation>': colors.green,
    '<answer>': colors.blue,
    '</answer>': colors.blue,
  }

  const contentColors: Record<string, string> = {
    think: colors.thinking,
    tool_call: colors.pink,
    observation: colors.green,
    answer: colors.blue,
  }

  let match: RegExpExecArray | null
  let activeTag: string | null = null

  while ((match = regex.exec(raw)) !== null) {
    // Text before this tag
    if (match.index > lastIndex) {
      const text = raw.slice(lastIndex, match.index)
      segments.push({ text, color: activeTag ? contentColors[activeTag] || currentColor : currentColor })
    }

    const tag = match[1]
    segments.push({ text: tag, color: tagColors[tag] || colors.textMuted })

    // Track open/close
    if (tag.startsWith('</')) {
      activeTag = null
    } else {
      const tagName = tag.slice(1, -1)
      activeTag = tagName
    }

    lastIndex = match.index + match[0].length
  }

  // Remaining text
  if (lastIndex < raw.length) {
    segments.push({ text: raw.slice(lastIndex), color: activeTag ? contentColors[activeTag] || currentColor : currentColor })
  }

  return segments
}

function highlightJson(text: string, baseColor: string): Segment[] {
  // Basic JSON key highlighting
  const segments: Segment[] = []
  const jsonKeyRegex = /"([^"]+)"\s*:/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = jsonKeyRegex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ text: text.slice(lastIndex, match.index), color: baseColor })
    }
    segments.push({ text: `"${match[1]}"`, color: colors.purple })
    segments.push({ text: ':', color: colors.textMuted })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    segments.push({ text: text.slice(lastIndex), color: baseColor })
  }

  return segments.length > 0 ? segments : [{ text, color: baseColor }]
}

export function RawView({ rawTrace }: Props) {
  const segments = useMemo(() => {
    const traceSegments = highlightTrace(rawTrace)
    // Further highlight JSON within segments
    const result: Segment[] = []
    for (const seg of traceSegments) {
      if (seg.text.includes('"') && seg.text.includes(':')) {
        result.push(...highlightJson(seg.text, seg.color))
      } else {
        result.push(seg)
      }
    }
    return result
  }, [rawTrace])

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: 14,
      background: colors.bg,
      fontFamily: fonts.mono,
      fontSize: 11,
      lineHeight: 1.7,
      scrollbarWidth: 'thin',
      scrollbarColor: `${colors.textMuted} transparent`,
    }}>
      <pre style={{
        margin: 0,
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        fontFamily: 'inherit',
        fontSize: 'inherit',
        lineHeight: 'inherit',
      }}>
        {segments.map((seg, i) => (
          <span key={i} style={{ color: seg.color }}>{seg.text}</span>
        ))}
      </pre>
    </div>
  )
}
