const stopWords = new Set('about after again along also among another been before being between both could does each either every first from have having here into itself just last like made many more most much must only other over same should some such than that their them then there these they this those through under until upon very want were what when where which while will with within without would your hers ours theirs whom whose most however therefore because'.split(' '));

export function extractGraph(text) {
  const counts = new Map();
  const cooccurrences = new Map();
  const passages = text.slice(0, 120000).split(/[.!?;\n]+/u);
  for (const passage of passages) {
    const words = passage.toLowerCase().match(/\p{L}[\p{L}\p{M}-]{2,39}/gu) ?? [];
    const concepts = [...new Set(words.filter(word => !stopWords.has(word)))].slice(0, 30).sort();
    for (const [index, from] of concepts.entries()) {
      counts.set(from, (counts.get(from) ?? 0) + 1);
      for (const to of concepts.slice(index + 1)) {
        const key = from + '|' + to;
        const edge = cooccurrences.get(key) ?? { from, to, count: 0 };
        edge.count++;
        cooccurrences.set(key, edge);
      }
    }
  }
  const ranked = [...counts].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  const nodes = ranked.slice(0, 45).map(([id, count]) => ({ id, label: id, count }));
  const selected = new Set(nodes.map(node => node.id));
  const edges = [...cooccurrences.values()]
    .filter(edge => selected.has(edge.from) && selected.has(edge.to))
    .sort((a, b) => b.count - a.count)
    .slice(0, 100)
    .map(edge => ({ ...edge, relation: 'Shared passages: ' + edge.count }));
  return { nodes, edges };
}
