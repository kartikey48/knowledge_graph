/** Pack disconnected components using their settled, label-inclusive bounds. */
export function packComponents(nodes, edges, bounds, aspect) {
  const adjacent = new Map(nodes.map(({ id }) => [id, []]));
  for (const { from, to } of edges) {
    adjacent.get(from).push(to);
    adjacent.get(to).push(from);
  }
  const seen = new Set();
  const groups = [];
  const gap = 65;
  for (const { id } of nodes) {
    if (seen.has(id)) continue;
    const ids = [id];
    seen.add(id);
    let left = Infinity, top = Infinity, right = -Infinity, bottom = -Infinity;
    for (const member of ids) {
      const box = bounds(member);
      left = Math.min(left, box.left);
      top = Math.min(top, box.top);
      right = Math.max(right, box.right);
      bottom = Math.max(bottom, box.bottom);
      for (const next of adjacent.get(member)) {
        if (!seen.has(next)) {
          seen.add(next);
          ids.push(next);
        }
      }
    }
    groups.push({ ids, left, top, width: right - left + gap, height: bottom - top + gap });
  }
  groups.sort((a, b) => b.height - a.height);
  const area = groups.reduce((sum, g) => sum + g.width * g.height, 0);
  const limit = Math.max(...groups.map(g => g.width), Math.sqrt(area * aspect));
  const offsets = new Map();
  let x = 0, y = 0, rowHeight = 0;
  for (const group of groups) {
    if (x && x + group.width > limit) {
      x = 0;
      y += rowHeight;
      rowHeight = 0;
    }
    for (const id of group.ids) offsets.set(id, { x: x - group.left, y: y - group.top });
    x += group.width;
    rowHeight = Math.max(rowHeight, group.height);
  }
  return offsets;
}
