export const colors = {
  bg: '#0e0c11',
  surface: 'rgba(255,255,255,0.02)',
  surfaceElevated: '#1c1826',
  surfaceDark: 'rgba(0,0,0,0.15)',
  border: 'rgba(255,255,255,0.06)',
  borderHover: 'rgba(255,255,255,0.10)',
  text: '#e2e0e6',
  textSecondary: '#c4bfce',
  textTertiary: '#8b8594',
  textMuted: '#6b6574',
  textFaintest: '#4a4453',
  thinking: '#c4bfce',
  purple: '#a78bfa',
  purpleDark: '#7c3aed',
  purpleBg: 'rgba(167,139,250,0.08)',
  red: '#f87171',
  redBg: 'rgba(248,113,113,0.08)',
  amber: '#fbbf24',
  amberBg: 'rgba(251,191,36,0.08)',
  green: '#34d399',
  greenBg: 'rgba(52,211,153,0.08)',
  pink: '#f472b6',
  pinkBg: 'rgba(244,114,182,0.08)',
  blue: '#60a5fa',
  blueBg: 'rgba(96,165,250,0.08)',
} as const

export const fonts = {
  mono: "'JetBrains Mono', monospace",
} as const

export const modelColors = {
  base: { color: colors.red, bg: colors.redBg, label: 'Base', desc: 'Untrained' },
  sft: { color: colors.amber, bg: colors.amberBg, label: 'SFT', desc: 'Supervised' },
  grpo: { color: colors.green, bg: colors.greenBg, label: 'GRPO', desc: 'RL-tuned' },
} as const

export const verdictColors = {
  pass: { color: colors.green, bg: colors.greenBg },
  correct: { color: colors.green, bg: colors.greenBg },
  partial: { color: colors.amber, bg: colors.amberBg },
  fail: { color: colors.red, bg: colors.redBg },
} as const
