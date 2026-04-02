import { useRef, useEffect } from 'react'
import { colors, fonts } from '../../theme/tokens'
import { Block as BlockComponent } from './Block'
import type { Block } from '../../data/blocks'

interface BlockTraceProps {
  blocks: Block[]
  completedBlocks: Block[]
  activeBlock: Block | null
  activeField: 'title' | 'detail'
  charIndex: number
  isAnimating: boolean
  sourceTags: string[]
}

export function BlockTrace({
  blocks,
  completedBlocks,
  activeBlock,
  activeField,
  charIndex,
  isAnimating,
  sourceTags,
}: BlockTraceProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight
    }
  }, [completedBlocks, charIndex])

  const hasContent = completedBlocks.length > 0 || activeBlock !== null

  return (
    <div
      ref={containerRef}
      style={{
        flex: 1,
        overflowY: 'auto',
        padding: 10,
        background: colors.bg,
        fontFamily: fonts.mono,
        fontSize: 11,
        lineHeight: 1.7,
        position: 'relative',
      }}
    >
      {/* Source tags floating in top-right */}
      {sourceTags.length > 0 && (
        <div
          style={{
            position: 'sticky',
            top: 0,
            float: 'right',
            display: 'flex',
            flexDirection: 'column',
            gap: 3,
            zIndex: 2,
            paddingBottom: 4,
          }}
        >
          {sourceTags.map((tag) => (
            <span
              key={tag}
              style={{
                fontSize: 8,
                fontFamily: fonts.mono,
                fontWeight: 600,
                color: colors.purple,
                background: 'rgba(167,139,250,0.08)',
                padding: '1px 6px',
                borderRadius: 3,
                whiteSpace: 'nowrap',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Completed blocks */}
      {completedBlocks.map((block) => (
        <BlockComponent
          key={block.id}
          block={block}
          isActive={false}
          charIndex={0}
          activeField="title"
          isNested={!!block.parentId}
          fadeIn={false}
        />
      ))}

      {/* Active block (currently typing) */}
      {activeBlock && (
        <BlockComponent
          key={`active-${activeBlock.id}`}
          block={activeBlock}
          isActive={true}
          charIndex={charIndex}
          activeField={activeField}
          isNested={!!activeBlock.parentId}
          fadeIn={true}
        />
      )}

      {/* Empty state */}
      {!hasContent && !isAnimating && (
        <div
          style={{
            color: colors.textMuted,
            fontSize: 11,
            fontStyle: 'italic',
            padding: '20px 0',
            textAlign: 'center',
          }}
        >
          Press Run to start the trace animation
        </div>
      )}
    </div>
  )
}
