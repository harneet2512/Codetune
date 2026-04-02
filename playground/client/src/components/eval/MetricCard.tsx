import { colors, fonts } from '../../theme/tokens'
import { Sparkline } from '../shared/Sparkline'

interface MetricCardProps {
  label: string
  value: string
  change: string
  changeColor: string
  sparklineData: number[]
  color: string
}

export function MetricCard({ label, value, change, changeColor, sparklineData, color }: MetricCardProps) {
  return (
    <div
      style={{
        background: colors.surface,
        border: `1px solid ${colors.border}`,
        borderRadius: 10,
        padding: 16,
        flex: 1,
        minWidth: 160,
      }}
    >
      <div
        style={{
          fontSize: 9,
          fontFamily: fonts.mono,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.06em',
          color: colors.textMuted,
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <div>
          <div
            style={{
              fontSize: 28,
              fontFamily: fonts.mono,
              fontWeight: 800,
              color,
              lineHeight: 1,
              marginBottom: 4,
            }}
          >
            {value}
          </div>
          <div
            style={{
              fontSize: 11,
              fontFamily: fonts.mono,
              fontWeight: 600,
              color: changeColor,
              lineHeight: 1.2,
            }}
          >
            {change}
          </div>
        </div>
        <div style={{ opacity: 0.7 }}>
          <Sparkline data={sparklineData} color={color} width={80} height={24} />
        </div>
      </div>
    </div>
  )
}
