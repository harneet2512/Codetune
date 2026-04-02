import { colors, fonts } from '../../theme/tokens'
import type { ModelDef } from '../../data/models'

interface ModelCardProps {
  model: ModelDef
}

function MetricBlock({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ flex: 1 }}>
      <div
        style={{
          fontSize: 9,
          fontFamily: fonts.mono,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: colors.textFaintest,
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontSize: 18,
          fontFamily: fonts.mono,
          fontWeight: 800,
          color,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
    </div>
  )
}

export function ModelCard({ model }: ModelCardProps) {
  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        padding: 20,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <span
          style={{
            fontSize: 15,
            fontFamily: fonts.mono,
            fontWeight: 700,
            color: colors.text,
          }}
        >
          {model.fullLabel}
        </span>
        <span
          style={{
            fontSize: 9,
            fontFamily: fonts.mono,
            fontWeight: 700,
            padding: '2px 7px',
            borderRadius: 4,
            background: `${model.tagColor}20`,
            color: model.tagColor,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}
        >
          {model.tag}
        </span>
      </div>

      {/* Description */}
      <div
        style={{
          fontSize: 12,
          fontFamily: fonts.mono,
          color: colors.textTertiary,
          marginBottom: 16,
          lineHeight: 1.4,
        }}
      >
        {model.desc}
      </div>

      {/* Metrics row */}
      <div style={{ display: 'flex', gap: 20 }}>
        <MetricBlock label="Accuracy" value={`${model.accuracy}%`} color={model.color} />
        <MetricBlock label="Tool Precision" value={`${model.toolPrecision}%`} color={model.color} />
        <MetricBlock label="Restraint" value={`${model.restraint}%`} color={model.color} />
      </div>
    </div>
  )
}
