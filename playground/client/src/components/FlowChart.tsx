import { useMemo, useCallback } from 'react'
import {
  ReactFlow,
  type Node,
  type Edge,
  MarkerType,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { FlowNodeComponent } from './FlowNode'
import type { TraceNode } from '../types'

const nodeTypes = { flowNode: FlowNodeComponent }

const accentMap: Record<string, string> = {
  think: '#6e9eff',
  tool_call: '#f59e0b',
  observe: '#22c55e',
  observation: '#22c55e',
  answer: '#22c55e',
  error: '#ef4444',
  failure_terminal: '#ef4444',
  warning_terminal: '#f59e0b',
}

interface Props {
  nodes: TraceNode[]
  visibleCount: number
  selectedId: string | null
  onSelect: (id: string) => void
  accentColor: string
}

export function FlowChart({ nodes, visibleCount, selectedId, onSelect, accentColor }: Props) {
  const visible = nodes.slice(0, visibleCount)

  // Layout nodes with branching: tool_call + observe pairs go side by side
  const flowNodes: Node[] = useMemo(() => {
    const result: Node[] = []
    let y = 0
    let i = 0
    while (i < visible.length) {
      const n = visible[i]
      const isToolCall = n.type === 'tool_call'
      const hasObserve = i + 1 < visible.length &&
        (visible[i + 1].type === 'observe' || visible[i + 1].type === 'observation')

      if (isToolCall && hasObserve) {
        // Branch: tool_call on left, observation on right
        result.push({
          id: n.id,
          type: 'flowNode',
          position: { x: -125, y },
          data: {
            nodeType: n.type,
            title: n.title,
            summary: n.summary,
            decision: n.decision,
            isSelected: n.id === selectedId,
            onClick: () => onSelect(n.id),
          },
          draggable: false,
        })
        const obs = visible[i + 1]
        result.push({
          id: obs.id,
          type: 'flowNode',
          position: { x: 125, y },
          data: {
            nodeType: obs.type,
            title: obs.title,
            summary: obs.summary,
            decision: (obs as TraceNode).decision,
            isSelected: obs.id === selectedId,
            onClick: () => onSelect(obs.id),
          },
          draggable: false,
        })
        y += 110
        i += 2
      } else {
        // Center node
        result.push({
          id: n.id,
          type: 'flowNode',
          position: { x: 0, y },
          data: {
            nodeType: n.type,
            title: n.title,
            summary: n.summary,
            decision: n.decision,
            isSelected: n.id === selectedId,
            onClick: () => onSelect(n.id),
          },
          draggable: false,
        })
        y += 110
        i++
      }
    }
    return result
  }, [visible, selectedId, onSelect])

  const edges: Edge[] = useMemo(() => {
    const result: Edge[] = []
    for (let i = 1; i < flowNodes.length; i++) {
      const prev = flowNodes[i - 1]
      const curr = flowNodes[i]
      // Connect sequential nodes
      const isSameRow = prev.position.y === curr.position.y
      if (isSameRow) {
        // Horizontal edge between tool_call and observe
        result.push({
          id: `e-${prev.id}-${curr.id}`,
          source: prev.id,
          target: curr.id,
          sourceHandle: undefined,
          targetHandle: undefined,
          animated: true,
          style: { stroke: accentMap[curr.data.nodeType as string] || accentColor, strokeWidth: 1.5 },
          markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color: accentMap[curr.data.nodeType as string] || accentColor },
        })
      }
    }
    // Vertical connections between rows
    const rows: Node[][] = []
    let currentY = -1
    for (const n of flowNodes) {
      if (n.position.y !== currentY) {
        rows.push([])
        currentY = n.position.y
      }
      rows[rows.length - 1].push(n)
    }
    for (let r = 1; r < rows.length; r++) {
      const prevRow = rows[r - 1]
      const currRow = rows[r]
      // Connect last of prev row to first of current row (or center)
      const src = prevRow.length > 1 ? prevRow[1] : prevRow[0]
      const tgt = currRow[0]
      result.push({
        id: `ev-${src.id}-${tgt.id}`,
        source: src.id,
        target: tgt.id,
        animated: true,
        style: { stroke: accentMap[tgt.data.nodeType as string] || accentColor, strokeWidth: 1.5 },
        markerEnd: { type: MarkerType.ArrowClosed, width: 12, height: 12, color: accentMap[tgt.data.nodeType as string] || accentColor },
      })
    }
    return result
  }, [flowNodes, accentColor])

  return (
    <div style={{ height: '100%', width: '100%' }}>
      <ReactFlow
        nodes={flowNodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.4}
        maxZoom={1.2}
        panOnScroll
        zoomOnScroll={false}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
      />
    </div>
  )
}
