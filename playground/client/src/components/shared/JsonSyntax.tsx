import { colors } from '../../theme/tokens'

interface JsonSyntaxProps {
  value: unknown
  indent?: number
}

export function JsonSyntax({ value, indent = 0 }: JsonSyntaxProps) {
  return <JsonValue value={value} indent={indent} />
}

function JsonValue({ value, indent }: { value: unknown; indent: number }) {
  if (typeof value === 'string') return <span style={{ color: colors.green }}>"{value}"</span>
  if (typeof value === 'number' || typeof value === 'boolean') return <span style={{ color: colors.blue }}>{String(value)}</span>
  if (value === null) return <span style={{ color: colors.textMuted }}>null</span>
  if (Array.isArray(value)) {
    if (value.length === 0) return <span>{'[]'}</span>
    return (
      <>
        {'[\n'}
        {value.map((item, i) => (
          <span key={i}>
            {'  '.repeat(indent + 1)}
            <JsonValue value={item} indent={indent + 1} />
            {i < value.length - 1 ? ',\n' : '\n'}
          </span>
        ))}
        {'  '.repeat(indent)}
        {']'}
      </>
    )
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
    if (entries.length === 0) return <span>{'{}'}</span>
    return (
      <>
        {'{\n'}
        {entries.map(([k, v], i) => (
          <span key={k}>
            {'  '.repeat(indent + 1)}
            <span style={{ color: colors.pink }}>"{k}"</span>
            {': '}
            <JsonValue value={v} indent={indent + 1} />
            {i < entries.length - 1 ? ',\n' : '\n'}
          </span>
        ))}
        {'  '.repeat(indent)}
        {'}'}
      </>
    )
  }
  return <span>{String(value)}</span>
}
