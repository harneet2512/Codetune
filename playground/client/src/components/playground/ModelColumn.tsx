import { colors, fonts, modelColors, verdictColors } from '../../theme/tokens'
import { BlockTrace } from './BlockTrace'
import { RawView } from './RawView'
import { FlowView } from './FlowView'
import { StatsFooter } from './StatsFooter'
import type { Trace } from '../../data/tasks'
import type { Block } from '../../data/blocks'
import type { ViewMode } from '../../types/playground'
import type { UseBlockAnimationReturn } from '../../hooks/useBlockAnimation'

interface Props {
  modelKey: 'base' | 'sft' | 'grpo'
  trace: Trace
  blocks: Block[]
  viewMode: ViewMode
  blockState: UseBlockAnimationReturn
  isLast?: boolean
}

export function ModelColumn({ modelKey, trace, blocks, viewMode, blockState, isLast }: Props) {
  const meta = modelColors[modelKey]
  const vc = verdictColors[trace.verdict] || verdictColors.fail

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      minWidth: 0,
      background: 'rgba(255,255,255,0.015)',
      borderRadius: 10,
      border: `1px solid ${colors.border}`,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 14px',
        borderBottom: `1px solid ${colors.border}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: meta.color,
            boxShadow: `0 0 6px ${meta.color}66`,
            flexShrink: 0,
          }} />
          <span style={{
            fontSize: 13,
            fontWeight: 700,
            color: colors.text,
            fontFamily: fonts.mono,
          }}>
            {meta.label}
          </span>
          <span style={{
            fontSize: 10,
            color: colors.textMuted,
            fontFamily: fonts.mono,
            marginLeft: 2,
          }}>
            {meta.desc}
          </span>

          {/* Sources counter */}
          {blockState.sourceCount > 0 && (
            <span style={{
              fontSize: 9,
              fontFamily: fonts.mono,
              color: colors.textMuted,
              marginLeft: 6,
            }}>
              sources: {blockState.sourceCount}
            </span>
          )}
        </div>

        {/* Verdict badge — only shows after animation finishes */}
        {!blockState.isAnimating && (
          <span style={{
            fontSize: 9,
            fontWeight: 700,
            fontFamily: fonts.mono,
            padding: '2px 7px',
            borderRadius: 3,
            background: vc.bg,
            color: vc.color,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
          }}>
            {trace.verdict === 'correct' ? 'Pass' : trace.verdict.charAt(0).toUpperCase() + trace.verdict.slice(1)}
          </span>
        )}
      </div>

      {/* Content area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {viewMode === 'blocks' && (
          <BlockTrace
            blocks={blocks}
            completedBlocks={blockState.completedBlocks}
            activeBlock={blockState.activeBlock}
            activeField={blockState.activeField}
            charIndex={blockState.charIndex}
            isAnimating={blockState.isAnimating}
            sourceTags={blockState.sourceTags}
          />
        )}
        {viewMode === 'raw' && (
          <RawView rawTrace={trace.raw_trace} />
        )}
        {viewMode === 'flow' && (
          <FlowView
            nodes={trace.nodes}
            accentColor={meta.color}
            visibleBlockIds={blockState.visibleBlockIds}
          />
        )}
      </div>

      {/* Footer stats */}
      <StatsFooter trace={trace} />
    </div>
  )
}
