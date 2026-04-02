import { colors, fonts } from '../theme/tokens'
import { TrainingFlow } from '../components/models/TrainingFlow'

export function ModelsPage() {
  return (
    <div style={{ padding: '24px 28px', maxWidth: 800 }}>
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
          Model Registry
        </h1>
        <p style={{ color: colors.textMuted, fontSize: 12, fontFamily: fonts.mono, margin: 0 }}>
          Training lineage and version history
        </p>
      </div>

      <TrainingFlow />
    </div>
  )
}
