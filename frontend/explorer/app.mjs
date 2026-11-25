import { packComponents } from './spacing.mjs';
import { extractGraph } from './extract.mjs';



const get = id => document.getElementById(id);

const status = message => { get('status').textContent = message; };

let graph = { nodes: [], edges: [] };

let network;



function element(tag, value) {

  const result = document.createElement(tag);

  result.textContent = value;

  return result;

}



function conceptButton(id) {

  const button = element('button', id);

  button.type = 'button';

  button.onclick = () => {

    selectConcept(id);

  };

  return button;

}



function showConcept(id) {

  const panel = get('details');

  panel.replaceChildren(element('h3', id));

  const neighbors = document.createElement('ul');

  for (const edge of graph.edges.filter(edge => edge.from === id || edge.to === id)) {

    const item = document.createElement('li');

    item.append(conceptButton(edge.from === id ? edge.to : edge.from), element('p', edge.relation));

    if (edge.evidence?.length) {

      const evidence = document.createElement('details');

      evidence.append(element('summary', 'View source passages'));

      for (const passage of edge.evidence) evidence.append(element('blockquote', passage));

      item.append(evidence);

    }

    neighbors.append(item);

  }

  panel.append(neighbors.children.length ? neighbors : element('p', 'No connections in this view.'));

}



function showResults() {

  const query = get('search').value.trim().toLowerCase();

  const matches = graph.nodes.filter(node => node.label.toLowerCase().includes(query));

  get('results').replaceChildren(...(matches.length

    ? matches.map(node => conceptButton(node.id))

    : [element('p', 'No matching concepts.')]));

}



let focusId;

let fullView = false;



function selectConcept(id) {

  focusId = id;

  if (fullView) {

    network.selectNodes([id]);

    network.focus(id, { scale: Math.max(network.getScale(), 0.8), animation: true });

  } else {

    draw();

  }

  showConcept(id);

}



function render(data) {

  graph = data;

  const degree = new Map(data.nodes.map(node => [node.id, 0]));

  for (const { from, to } of data.edges) {

    degree.set(from, degree.get(from) + 1);

    degree.set(to, degree.get(to) + 1);

  }

  focusId = [...degree].sort((a, b) => b[1] - a[1])[0][0];

  fullView = false;

  draw();

  showConcept(focusId);

  get('search').value = '';

  showResults();

}



function draw() {

  network?.destroy();

  const ranked = graph.edges.filter(edge => edge.from === focusId || edge.to === focusId)

    .sort((a, b) => (b.count ?? 1) - (a.count ?? 1));

  const neighbors = [...new Set(ranked.map(edge => edge.from === focusId ? edge.to : edge.from))].slice(0, 6);

  const narrow = get('graph').clientWidth < 520;
  const positions = new Map([[focusId, { x: narrow && neighbors.length ? -83 : 0, y: 0 }]]);

  neighbors.forEach((id, index) => {

    const angle = 2 * Math.PI * index / neighbors.length - Math.PI / 2;

    positions.set(id, narrow
      ? { x: 83, y: (index - (neighbors.length - 1) / 2) * 105 }
      : { x: 225 * Math.cos(angle), y: 155 * Math.sin(angle) });

  });

  const data = fullView ? graph : {

    nodes: graph.nodes.filter(node => positions.has(node.id)),

    edges: neighbors.map(id => ranked.find(edge => edge.from === id || edge.to === id))

  };

  get('view').textContent = fullView ? 'Focus view' : 'Full graph';

  const colors = ['#a998ff', '#68d9c4', '#f4bc88', '#8ab8ff'];

  network = new window.vis.Network(get('graph'), {

    nodes: new window.vis.DataSet(data.nodes.map((node, index) => ({

      ...node,

      ...(fullView ? { shape: 'box', margin: 9, widthConstraint: { maximum: 155 },
        font: { color: '#10131e', size: 19, strokeWidth: 0 } } : { ...positions.get(node.id), shape: 'box', widthConstraint: { maximum: narrow ? 124 : 166 }, margin: 10,
        borderWidth: node.id === focusId ? 4 : 1,

        font: { color: '#10131e', size: node.id === focusId ? 24 : 21, strokeWidth: 0 } }),

      color: colors[(node.id.length + index) % colors.length],

      size: Math.min(24, 10 + (node.count ?? 1))

    }))),

    edges: new window.vis.DataSet(data.edges.map(edge => ({

      from: edge.from, to: edge.to, width: Math.min(2.5, edge.count ?? 1)

    })))

  }, {

    layout: { improvedLayout: false, randomSeed: 48 },

    nodes: { shape: 'dot', font: { color: '#f3f5ff', size: 21, strokeWidth: 4, strokeColor: '#131827' } },

    edges: { color: { color: '#7183a7', highlight: '#e0d9ff', inherit: false }, smooth: false },

    interaction: { navigationButtons: false, hideEdgesOnDrag: true },

    physics: fullView ? {
      solver: 'barnesHut',
      barnesHut: { gravitationalConstant: -6500, centralGravity: 0.13,
        springLength: 240, springConstant: 0.025, damping: 0.32, avoidOverlap: 1 },
      stabilization: { iterations: 650, fit: false }
    } : false

  });

  if (fullView) {
    const canvas = get('graph');
    const settled = network;
    settled.once('stabilizationIterationsDone', () => {
      if (network !== settled) return;
      settled.setOptions({ physics: false });
      const coordinates = settled.getPositions();
      const offsets = packComponents(data.nodes, data.edges, id => settled.getBoundingBox(id),
        canvas.clientWidth / Math.max(1, canvas.clientHeight));
      for (const [id, offset] of offsets) {
        settled.moveNode(id, coordinates[id].x + offset.x, coordinates[id].y + offset.y);
      }
      settled.fit();
      if (settled.getScale() < 0.8) settled.focus(focusId, { scale: 0.8 });
    });
  }
  network.on('click', event => {

    if (event.nodes.length) selectConcept(event.nodes[0]);

  });

  get('counts').textContent = fullView

    ? graph.nodes.length + ' concepts  /  ' + graph.edges.length + ' connections'

    : 'Focused on ' + focusId + '  /  ' + neighbors.length + ' of ' +

      new Set(ranked.map(edge => edge.from === focusId ? edge.to : edge.from)).size + ' neighbors';

  get('legend').textContent = fullView
    ? 'Drag empty space to explore. Select a concept to highlight its edges, or use Fit graph for an overview.'
    : 'The outlined concept is your focus. Each line connects it to a related concept. Select a neighbor to explore.';
  if (!fullView) fitGraph();

}



get('view').onclick = () => {

  if (!graph.nodes.length) return;

  fullView = !fullView;

  draw();

};



async function loadSample() {

  const response = await fetch('./sample.json');

  if (!response.ok) throw new Error('The sample graph could not be loaded.');

  render(await response.json());

  status('Showing an example from the repository’s health equity dataset.');

}



async function pdfText(file) {

  if (file.size > 20 * 1024 * 1024) throw new Error('Choose a PDF under 20 MB.');

  const pdfjs = await import('./pdfjs/pdf.mjs');

  pdfjs.GlobalWorkerOptions.workerSrc = new URL('./pdfjs/pdf.worker.mjs', import.meta.url).href;

  const task = pdfjs.getDocument({ data: await file.arrayBuffer(), isEvalSupported: false });

  try {

    const document = await task.promise;

    if (document.numPages > 100) throw new Error('Choose a PDF with 100 pages or fewer.');

    const pages = [];

    let length = 0;

    for (let number = 1; number <= document.numPages && length < 120000; number++) {

      status('Reading PDF page ' + number + ' of ' + document.numPages + '…');

      const page = await document.getPage(number);

      const content = await page.getTextContent();

      const text = content.items.map(item => item.str ? item.str + (item.hasEOL ? '\n' : ' ') : '').join('');

      pages.push(text.slice(0, 120000 - length));

      length += text.length;

      page.cleanup();

    }

    const text = pages.join('\n');

    if (!text.trim()) throw new Error('No selectable text was found. Try a text-based PDF or paste the text.');

    return text;

  } finally {

    await task.destroy().catch(() => {});

  }

}



async function run(action) {

  const controls = ['sample', 'generate', 'pdf', 'source'].map(get);

  controls.forEach(control => { control.disabled = true; });

  try {

    await action();

  } catch (error) {

    status(error.message || 'Could not load the graph.');

  } finally {

    controls.forEach(control => { control.disabled = false; });

  }

}



get('source').oninput = () => {

  if (get('source').value.trim()) {

    get('pdf').value = '';

    get('file-note').textContent = 'Text-based PDFs · up to 20 MB and 100 pages';

  }

};

get('pdf').onchange = () => {

  const file = get('pdf').files[0];

  if (file) {

    get('source').value = '';

    get('file-note').textContent = file.name;

  }

};

get('sample').onclick = () => run(loadSample);

get('generate').onclick = () => run(async () => {

  const file = get('pdf').files[0];

  const source = file ? await pdfText(file) : get('source').value.trim();

  const data = extractGraph(source);

  if (data.nodes.length < 2) throw new Error('Add a longer passage with at least two distinct terms.');

  render(data);

  status('Graph generated from up to 120,000 characters.');

});

get('search').oninput = showResults;

function fitGraph() {
  if (!network) return;
  if (fullView) return network.fit();
  network.redraw();
  const boxes = Object.keys(network.getPositions()).map(id => network.getBoundingBox(id));
  const left = Math.min(...boxes.map(box => box.left));
  const top = Math.min(...boxes.map(box => box.top));
  const right = Math.max(...boxes.map(box => box.right));
  const bottom = Math.max(...boxes.map(box => box.bottom));
  const canvas = get('graph');
  const scale = Math.min(2.5, (canvas.clientWidth - 32) / Math.max(1, right - left),
    (canvas.clientHeight - 40) / Math.max(1, bottom - top));
  network.moveTo({ position: { x: (left + right) / 2, y: (top + bottom) / 2 }, scale: Math.max(0.1, scale) });
}
get('fit').onclick = fitGraph;
for (const [id, multiplier] of [['zoom-in', 1.3], ['zoom-out', 1 / 1.3]]) {
  get(id).onclick = () => {
    if (network) network.moveTo({ scale: Math.max(0.08, Math.min(5, network.getScale() * multiplier)) });
  };
}
let previousWidth = 0;
new ResizeObserver(([entry]) => {
  const width = Math.round(entry.contentRect.width);
  if (width !== previousWidth && graph.nodes.length && !fullView) draw();
  previousWidth = width;
}).observe(get('graph'));

get('export').onclick = () => {

  if (!graph.nodes.length) return;

  const url = URL.createObjectURL(new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' }));

  const link = element('a', '');

  link.href = url;

  link.download = 'knowledge-graph.json';

  link.click();

  setTimeout(() => URL.revokeObjectURL(url), 1000);

};

run(loadSample);

