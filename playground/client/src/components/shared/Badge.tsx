import { fonts } from '../../theme/tokens'

interface BadgeProps {
  label: string
  color: string
  bg: string
}

export function Badge({ label, color, bg }: BadgeProps) {
  return (
    <span
      style={{
        display: 'inline-block',
        fontSize: 9,
        fontFamily: fonts.mono,
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        padding: '2px 6px',
        borderRadius: 3,
        color,
        background: bg,
        lineHeight: 1.4,
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}
