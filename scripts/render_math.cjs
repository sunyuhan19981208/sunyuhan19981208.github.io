/* One-time authoring tool. The published site needs neither Node nor MathJax. */
const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const local = createRequire(path.resolve(__dirname, '../.tools/math-authoring/package.json'));
const { mathjax } = local('mathjax-full/js/mathjax.js');
const { TeX } = local('mathjax-full/js/input/tex.js');
const { SVG } = local('mathjax-full/js/output/svg.js');
const { liteAdaptor } = local('mathjax-full/js/adaptors/liteAdaptor.js');
const { RegisterHTMLHandler } = local('mathjax-full/js/handlers/html.js');
const { AllPackages } = local('mathjax-full/js/input/tex/AllPackages.js');
const adaptor = liteAdaptor();
RegisterHTMLHandler(adaptor);
const input = new TeX({ packages: AllPackages, formatError: (_, error) => { throw error; } });
const output = new SVG({ fontCache: 'none' });
const document = mathjax.document('', { InputJax: input, OutputJax: output });
const jobs = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const rendered = {};
for (const job of jobs) {
  try {
    const node = document.convert(job.tex, { display: job.display, em: 18, ex: 9, containerWidth: 720 });
    const markup = adaptor.outerHTML(node);
    if (/data-mjx-error|data-mml-node="merror"/.test(markup)) throw Error('MathJax emitted an error node');
    rendered[job.key] = markup;
  } catch (error) {
    throw new Error(`${job.key}: ${error.message}\n${job.tex}`);
  }
}
fs.writeFileSync(process.argv[3], JSON.stringify(rendered));
console.log(`Typeset ${jobs.length} mathematical expressions with self-contained SVG glyphs.`);
