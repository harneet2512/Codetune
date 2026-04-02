import { useState } from 'react'
import {
  GitBranch,
  Mail,
  FileText,
  Database,
  Target,
  ChevronRight,
} from 'lucide-react'
import { colors, fonts } from '../../theme/tokens'
import type { Connector } from '../../data/connectors'

const iconMap: Record<string, React.ComponentType<{ size?: number; color?: string }>> = {
  GitBranch,
  Mail,
  FileText,
  Database,
  Target,
}

interface ConnectorCardProps {
  connector: Connector
}

function JsonValue({ value, indent }: { value: unknown; indent: number }) {
  if (typeof value === 'string') return <span style={{ color: colors.green }}>"{value}"</span>
  if (typeof value === 'number' || typeof value === 'boolean') return <span style={{ color: colors.blue }}>{String(value)}</span>
  if (Array.isArray(value)) {
    return (
      <>
        {'['}
        {value.map((item, i) => (
          <span key={i}>
            <JsonValue value={item} indent={indent + 1} />
            {i < value.length - 1 ? ', ' : ''}
          </span>
        ))}
        {']'}
      </>
    )
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
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

export function ConnectorCard({ connector }: ConnectorCardProps) {
  const [schemaExpanded, setSchemaExpanded] = useState(false)
  const Icon = iconMap[connector.icon] || Database
  const { color, connected } = connector

  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${connected ? `${color}25` : colors.border}`,
        borderRadius: 10,
        padding: 20,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 10,
            background: `${color}18`,
            border: `1px solid ${color}30`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
          }}
        >
          <Icon size={20} color={color} />
        </div>
        <div style={{ flex: 1 }}>
          <span style={{ fontSize: 15, fontWeight: 700, fontFamily: fonts.mono, color: colors.text }}>
            {connector.service}
          </span>
        </div>
        <span
          style={{
            fontSize: 10,
            fontFamily: fonts.mono,
            color: connected ? colors.green : colors.textTertiary,
          }}
        >
          {connected ? 'Connected' : 'Available'}
        </span>
        <span
          style={{
            fontSize: 10,
            fontFamily: fonts.mono,
            padding: '3px 8px',
            borderRadius: 4,
            background: 'rgba(255,255,255,0.06)',
            color: colors.textSecondary,
          }}
        >
          {connector.tools.length} tools
        </span>
      </div>

      {/* Tool list */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.04)', margin: '14px 0', paddingTop: 14 }}>
        {connector.tools.map((tool, i) => (
          <div
            key={tool.name}
            style={{
              padding: '8px 0',
              borderBottom: i < connector.tools.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
              display: 'flex',
              alignItems: 'baseline',
              gap: 16,
            }}
          >
            <span style={{ fontSize: 11, fontWeight: 600, fontFamily: fonts.mono, color: colors.pink, minWidth: 180, flexShrink: 0 }}>
              {tool.name}
            </span>
            <span style={{ fontSize: 11, fontFamily: fonts.mono, color: colors.textTertiary }}>
              {tool.description}
            </span>
          </div>
        ))}
      </div>

      {/* Schema section */}
      {connector.schema && (
        <div>
          <button
            onClick={() => setSchemaExpanded(!schemaExpanded)}
            style={{
              background: 'none',
              border: 'none',
              padding: 0,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              fontSize: 10,
              fontFamily: fonts.mono,
              color: colors.purple,
            }}
          >
            <ChevronRight
              size={12}
              style={{
                transform: schemaExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                transition: 'transform 0.15s ease',
              }}
            />
            View full JSON schema
          </button>
          {schemaExpanded && (
            <pre
              style={{
                marginTop: 10,
                padding: 14,
                borderRadius: 6,
                background: 'rgba(0,0,0,0.2)',
                border: '1px solid rgba(255,255,255,0.04)',
                fontSize: 10,
                fontFamily: fonts.mono,
                lineHeight: 1.6,
                overflowX: 'auto',
                color: colors.textSecondary,
              }}
            >
              <JsonValue value={connector.schema} indent={0} />
            </pre>
          )}
        </div>
      )}
    </div>
  )
}
