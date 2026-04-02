import { colors, fonts } from '../../theme/tokens'

export function ConnectorHero() {
  return (
    <div style={{ marginBottom: 24 }}>
      <h1
        style={{
          fontFamily: fonts.mono,
          fontSize: 18,
          fontWeight: 800,
          color: colors.text,
          margin: '0 0 4px 0',
        }}
      >
        Connectors
      </h1>
      <div
        style={{
          fontFamily: fonts.mono,
          fontSize: 12,
          color: colors.textMuted,
          marginBottom: 6,
        }}
      >
        17 tool schemas across 5 services
      </div>
      <div
        style={{
          fontSize: 11,
          fontFamily: fonts.mono,
          color: colors.textTertiary,
          lineHeight: 1.5,
        }}
      >
        Real developer tool schemas with typed parameters. Models learn when to call each tool,
        what arguments to pass, and when not to call anything.
      </div>
    </div>
  )
}
