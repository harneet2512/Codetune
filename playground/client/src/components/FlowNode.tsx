import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'

const accentMap: Record<string, string> = {
  think: 'var(--think)',
  tool_call: 'var(--tool)',
  observe: 'var(--observe)',
  observation: 'var(--observe)',
  answer: 'var(--grpo)',
  error: 'var(--error)',
  failure_terminal: 'var(--error)',
  warning_terminal: 'var(--sft)',
}

const iconMap: Record<string, string> = {
  think: '◆',
  tool_call: '▶',
  observe: '●',
  observation: '●',
  answer: '✓',
  error: '✗',
  failure_terminal: '✗',
  warning_terminal: '!',
}

interface FlowNodeData {
  nodeType: string
  title: string
  summary: string
  decision?: string
  isSelected: boolean
  onClick: () => void
  [key: string]: unknown
}

function FlowNodeInner({ data }: NodeProps & { data: FlowNodeData }) {
  const { nodeType, title, summary, decision, isSelected, onClick } = data
  const accent = accentMap[nodeType] || 'var(--text3)'
  const icon = iconMap[nodeType] || '●'
  const isTerminal = nodeType === 'answer' || nodeType === 'error' || nodeType === 'failure_terminal' || nodeType === 'warning_terminal'

  return (
    <>
      <Handle type="target" position={Position.Top} style={{ opacity: 0, width: 1, height: 1 }} />
      <div
        onClick={onClick}
        style={{
          width: 220,
          padding: '8px 10px',
          background: isSelected ? 'var(--surface3)' : 'var(--surface2)',
          border: `1px solid ${isSelected ? accent : 'var(--border)'}`,
          borderRadius: 8,
          cursor: 'pointer',
          transition: 'all 0.15s',
          animation: isSelected ? 'pulse 2s infinite' : undefined,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
          <span style={{ color: accent, fontSize: 8, lineHeight: 1 }}>{icon}</span>
          <span style={{
            fontSize: 9, fontWeight: 600, textTransform: 'uppercase',
            letterSpacing: '0.06em', color: accent,
          }}>
            {nodeType.replace('_', ' ')}
          </span>
        </div>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text)', marginBottom: 2, lineHeight: 1.3 }}>
          {title}
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--text2)', lineHeight: 1.35 }}>
          {summary}
        </div>
        {decision && (
          <div style={{
            fontSize: 10, color: accent, marginTop: 4, fontStyle: 'italic',
            opacity: 0.85,
          }}>
            → {decision}
          </div>
        )}
        {isTerminal && (
          <div style={{
            marginTop: 5, padding: '2px 6px', borderRadius: 4,
            background: `${accent}`,
            color: '#000', fontSize: 9, fontWeight: 700,
            display: 'inline-block', textTransform: 'uppercase',
          }}>
            {nodeType === 'answer' ? 'DONE' : nodeType === 'warning_terminal' ? 'PARTIAL' : 'FAIL'}
          </div>
        )}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 1, height: 1 }} />
    </>
  )
}

export const FlowNodeComponent = memo(FlowNodeInner)
