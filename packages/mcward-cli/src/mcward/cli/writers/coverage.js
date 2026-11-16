const theme = document.getElementById('theme');
const prefersDark = matchMedia('(prefers-color-scheme: dark)');
const isDark = () => {
  const pinned = document.documentElement.dataset.theme;
  return pinned ? pinned === 'dark' : prefersDark.matches;
};
const relabel = () => {
  const dark = isDark();
  theme.title = dark ? 'Switch to light mode' : 'Switch to dark mode';
  theme.querySelector('.sun').toggleAttribute('hidden', !dark);
  theme.querySelector('.moon').toggleAttribute('hidden', dark);
};
theme.addEventListener('click', () => {
  document.documentElement.dataset.theme = isDark() ? 'light' : 'dark';
  relabel();
});
prefersDark.addEventListener('change', relabel);
relabel();

const filter = document.getElementById('filter');
filter.addEventListener('input', () => {
  const query = filter.value.toLowerCase();
  for (const fn of document.querySelectorAll('.fn')) {
    fn.hidden = !fn.dataset.name.includes(query);
  }
  for (const group of document.querySelectorAll('.group')) {
    group.hidden = !group.querySelector('.fn:not([hidden])');
    if (query) group.open = !group.hidden;
  }
});

function reveal() {
  const target = location.hash && document.querySelector(location.hash);
  if (target && target.classList.contains('fn')) {
    target.closest('.group').open = true;
    target.open = true;
    target.scrollIntoView();
  }
}
addEventListener('hashchange', reveal);
reveal();

// Syntax colors through the CSS custom highlight API: ranges over the existing
// text nodes, no extra markup. Sources are tokenized when first opened.
if (CSS.highlights) {
  const commandRules = [
    ['cm', /^\s*#.*/g],
    ['sel', /@[a-z]+(?:\[[^\]]*\])?/g],
    ['str', /"(?:\\.|[^"\\])*"|'[^']*'/g],
    ['mac', /\$\(\w+\)/g],
    ['kw', /(?<=^\s*\$?|\brun\s)[a-z][a-z_]*/g],
    ['num', /(?<![\w.-])-?\d[\w.]*|[~^]-?[\d.]*/g],
  ];
  const jsonRules = [
    ['key', /"(?:\\.|[^"\\])*"(?=\s*:)|\b(?:true|false|null)\b/g],
    ['str', /"(?:\\.|[^"\\])*"/g],
    ['num', /-?\d[\w.]*/g],
  ];
  for (const [name] of [...commandRules, ...jsonRules]) {
    if (!CSS.highlights.has(name)) CSS.highlights.set(name, new Highlight());
  }
  for (const status of ['hit', 'guard', 'miss']) CSS.highlights.set(status, new Highlight());

  // Coverage tints for JSON sources: the pre carries non-overlapping character
  // segments, so a condition is marked exactly, even inside a minified line
  function paint(pre) {
    const lines = [...pre.children];
    let offset = 0;
    const starts = lines.map(line => {
      const start = offset;
      offset += (line.firstChild ? line.firstChild.data.length : 0) + 1;
      return start;
    });
    const locate = target => {
      let index = starts.length - 1;
      while (index > 0 && starts[index] > target) index--;
      const length = lines[index].firstChild ? lines[index].firstChild.data.length : 0;
      return [lines[index], Math.min(target - starts[index], length)];
    };
    for (const [start, end, status] of JSON.parse(pre.dataset.marks || '[]')) {
      const range = new Range();
      const [startLine, startColumn] = locate(start);
      const [endLine, endColumn] = locate(end);
      if (startLine.firstChild) range.setStart(startLine.firstChild, startColumn);
      else range.setStart(startLine, 0);
      if (endLine.firstChild) range.setEnd(endLine.firstChild, endColumn);
      else range.setEnd(endLine, 0);
      CSS.highlights.get(status).add(range);
    }
  }

  function tokenize(pre) {
    const rules = pre.classList.contains('json') ? jsonRules : commandRules;
    let continued = false;
    for (const line of pre.children) {
      const node = line.firstChild;
      const continuation = continued;
      continued = node ? /\\\s*$/.test(node.data) : false;
      if (!node) continue;
      const claimed = [];
      for (const [name, rule] of rules) {
        for (const match of node.data.matchAll(rule)) {
          const [start, end] = [match.index, match.index + match[0].length];
          // A continuation line starts mid-command: its first word is no
          // keyword, and a leading # is no comment
          if (continuation && name === 'cm') continue;
          if (continuation && name === 'kw' && !/\brun\s$/.test(node.data.slice(0, start))) {
            continue;
          }
          if (claimed.some(([s, e]) => start < e && end > s)) continue;
          claimed.push([start, end]);
          const range = new Range();
          range.setStart(node, start);
          range.setEnd(node, end);
          CSS.highlights.get(name).add(range);
        }
      }
    }
  }

  for (const fn of document.querySelectorAll('details.fn')) {
    fn.addEventListener('toggle', () => {
      if (fn.open && !fn.dataset.lit) {
        fn.dataset.lit = '1';
        const pre = fn.querySelector('pre');
        tokenize(pre);
        if (pre.dataset.marks) paint(pre);
      }
    });
  }
}
