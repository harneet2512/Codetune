import { colors } from '../../theme/tokens'

interface ProgressBarProps {
  value: number
  color: string
  height?: number
}

export function ProgressBar({ value, color, height = 4 }: ProgressBarProps) {
  return (
    <div
      style={{
        width: '100%',
        height,
        background: colors.surfaceElevated,
        borderRadius: height / 2,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          width: `${Math.min(100, Math.max(0, value))}%`,
          height: '100%',
          background: color,
          borderRadius: height / 2,
          transition: 'width 0.3s ease',
        }}
      />
    </div>
  )
}
