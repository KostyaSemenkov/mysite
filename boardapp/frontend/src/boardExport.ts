import { getNodesBounds, getViewportForBounds, type Edge, type Node } from '@xyflow/react'

export async function downloadBoardPng(viewport: HTMLElement, nodes: Node[], edges: Edge[], filename: string) {
  // библиотека тяжёлая и нужна только для экспорта — грузим в момент скачивания
  const { toPng } = await import('html-to-image')
  const nodeIds = new Set(nodes.map(({ id }) => id))
  const edgeIds = new Set(edges.filter(({ source, target }) =>
    nodeIds.has(source) && nodeIds.has(target),
  ).map(({ id }) => id))
  const bounds = getNodesBounds(nodes)
  const width = Math.ceil(bounds.width) + 200
  const height = Math.ceil(bounds.height) + 200
  const vp = getViewportForBounds(bounds, width, height, 0.4, 2, 100)
  const dataUrl = await toPng(viewport, {
    backgroundColor: '#ffffff',
    width,
    height,
    filter: (element) => {
      if (!(element instanceof Element)) return true
      if (element.matches('.react-flow__node')) return nodeIds.has(element.getAttribute('data-id') ?? '')
      if (element.matches('.react-flow__edge')) return edgeIds.has(element.getAttribute('data-id') ?? '')
      if (element.matches('.board-edge-label')) return edgeIds.has(element.getAttribute('data-edge-id') ?? '')
      return !element.matches([
        'button', '.edge-label-edit', '.edge-label-tools', '.color-dots', '.zone-tools',
        '.react-flow__handle', '.react-flow__resize-control', '.react-flow__nodesselection',
      ].join(','))
    },
    style: {
      width: `${width}px`,
      height: `${height}px`,
      transform: `translate(${vp.x}px, ${vp.y}px) scale(${vp.zoom})`,
    },
  })
  const link = document.createElement('a')
  link.download = filename
  link.href = dataUrl
  link.click()
}
