import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  type Node,
  type Edge,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { PlaygroundFlowNode } from './FlowNode'
import { colors } from '../../theme/tokens'
import type { TraceNode } from '../../data/tasks'

const nodeTypes = { flowNode: PlaygroundFlowNode }

const accentMap: Record<string, string> = {
  think: colors.purple,
  tool_call: colors.pink,
  observe: colors.green,
  observation: colors.green,
  answer: colors.blue,
  error: colors.red,
  failure_terminal: colors.red,
  warning_terminal: colors.amber,
}

interface Props {
  nodes: TraceNode[]
  accentColor: string
  visibleBlockIds?: Set<string>
}

export function FlowView({ nodes, accentColor, visibleBlockIds }: Props) {
  const onSelect = useCallback((_id: string) => {}, [])

  const flowNodes: Node[] = useMemo(() => {
    const result: Node[] = []
    let y = 0
    let i = 0
    while (i < nodes.length) {
      const n = nodes[i]
      const isToolCall = n.type === 'tool_call'
      const hasObserve = i + 1 < nodes.length &&
        (nodes[i + 1].type === 'observation' || (nodes[i + 1].type as string) === 'observe')

      if (isToolCall && hasObserve) {
        result.push({
          id: n.id,
          type: 'flowNode',
          position: { x: -115, y },
          data: {
            nodeType: n.type,
            title: n.title,
            summary: n.summary,
            decision: n.decision,
            isSelected: false,
            onClick: () => onSelect(n.id),
          },
          draggable: false,
        })
        const obs = nodes[i + 1]
        result.push({
          id: obs.id,
          type: 'flowNode',
          position: { x: 115, y },
          data: {
            nodeType: obs.type,
            title: obs.title,
            summary: obs.summary,
            decision: obs.decision,
            isSelected: false,
            onClick: () => onSelect(obs.id),
          },
          draggable: false,
        })
        y += 100
        i += 2
      } else {
        result.push({
          id: n.id,
          type: 'flowNode',
          position: { x: 0, y },
          data: {
            nodeType: n.type,
            title: n.title,
            summary: n.summary,
            decision: n.decision,
            isSelected: false,
            onClick: () => onSelect(n.id),
          },
          draggable: false,
        })
        y += 100
        i++
      }
    }
    return result
  }, [nodes, onSelect])

  const edges: Edge[] = useMemo(() => {
    const result: Edge[] = []
    // Group into rows by y position
    const rows: Node[][] = []
    let currentY = -1
    for (const n of flowNodes) {
      if (n.position.y !== currentY) {
        rows.push([])
        currentY = n.position.y
      }
      rows[rows.length - 1].push(n)
    }

    // Horizontal edges within rows
    for (const row of rows) {
      if (row.length > 1) {
        result.push({
          id: `e-${row[0].id}-${row[1].id}`,
          source: row[0].id,
          target: row[1].id,
          animated: true,
          style: { stroke: accentMap[row[1].data.nodeType as string] || accentColor, strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, width: 10, height: 10, color: accentMap[row[1].data.nodeType as string] || accentColor },
        })
      }
    }

    // Vertical edges between rows
    for (let r = 1; r < rows.length; r++) {
      const prevRow = rows[r - 1]
      const currRow = rows[r]
      const src = prevRow.length > 1 ? prevRow[1] : prevRow[0]
      const tgt = currRow[0]
      result.push({
        id: `ev-${src.id}-${tgt.id}`,
        source: src.id,
        target: tgt.id,
        animated: true,
        style: { stroke: accentMap[tgt.data.nodeType as string] || accentColor, strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, width: 10, height: 10, color: accentMap[tgt.data.nodeType as string] || accentColor },
      })
    }

    return result
  }, [flowNodes, accentColor])

  return (
    <div style={{
      flex: 1,
      background: colors.bg,
    }}>
      <ReactFlow
        nodes={flowNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={1.2}
        panOnScroll
        zoomOnScroll={false}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        style={{ background: 'transparent' }}
      />
    </div>
  )
}
