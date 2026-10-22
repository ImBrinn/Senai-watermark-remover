// Regenerates maths_sample.pdf: SenAI-style working written in MathML and
// printed by headless Chrome with only the Liberation fonts, which is what
// leaves SenAI's PDFs with empty boxes for the degree sign, the multiplication
// dot and the "implies" arrow, and with sentences set as maths italic with no
// spaces. tests/test_repair.py checks that all of it is put right.
//
// Chrome is given only the Liberation fonts (as on SenAI's servers), so it
// has no fallback for the symbols they lack.
//
//   npm install playwright   (or use a global install via NODE_PATH)
//   node tests/fixtures/make_maths_sample.cjs [liberation font folder]
const fs = require("fs");
const os = require("os");
const path = require("path");
const { chromium } = require("playwright");

const fontDir = process.argv[2] || "/usr/share/fonts/truetype/liberation";
const confDir = fs.mkdtempSync(path.join(os.tmpdir(), "fonts-"));
fs.writeFileSync(path.join(confDir, "fonts.conf"), `<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig><dir>${fontDir}</dir><cachedir>${confDir}/cache</cachedir></fontconfig>`);

// A sentence the way SenAI writes it inside maths: every letter its own
// <mi>, so Chrome sets it in italic and drops the spaces.
const squashed = (text) =>
  [...text].map((c) => (c === " " ? "" : /\d/.test(c) ? `<mn>${c}</mn>` : /[a-z]/i.test(c) ? `<mi>${c}</mi>` : `<mo>${c}</mo>`)).join("");

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body { font-family: "Liberation Sans", Arial, sans-serif; margin: 0; color: #111; }
  h1 { font-size: 22px; margin: 0 0 12px; }
  .work { font-family: "Liberation Serif", serif; color: #333; font-size: 15px; }
  .work div { margin: 4px 0; }
  math { font-family: "Liberation Serif", serif; }
  /* Italic from the font rather than Unicode's maths letters, as in SenAI's PDFs. */
  mi { text-transform: none; font-style: italic; }
</style></head><body>
  <h1>SenAI Maths</h1>
  <div class="work">
    <div>Angles in a triangle sum to <math><msup><mn>180</mn><mo>∘</mo></msup></math>.</div>
    <div><math><mi>p</mi><mo>=</mo><msup><mn>180</mn><mo>∘</mo></msup><mo>−</mo><msup><mn>115</mn><mo>∘</mo></msup><mo>=</mo><msup><mn>65</mn><mo>∘</mo></msup></math>.</div>
    <div>Prime factors: <math><mn>6</mn><mo>=</mo><mn>2</mn><mo>⋅</mo><mn>3</mn></math>.</div>
    <div><math><mn>700</mn><mo>=</mo><mn>2</mn><mo>×</mo><mn>350</mn><mspace width="0.2778em"></mspace><mo>⟹</mo><mspace width="0.2778em"></mspace><mn>700</mn><mo>=</mo><msup><mn>2</mn><mn>2</mn></msup><mo>×</mo><mn>175</mn></math></div>
    <div><math>${squashed("An isosceles triangle has two equal sides.")}</math></div>
    <div><math>${squashed("Thus there are 2 equal angles.")}</math></div>
    <div><math><mi>x</mi><mo>=</mo><mn>60</mn></math> stays as it is.</div>
  </div>
</body></html>`;

(async () => {
  const browser = await chromium.launch({
    env: { ...process.env, FONTCONFIG_FILE: path.join(confDir, "fonts.conf") },
  });
  const page = await browser.newPage();
  await page.setContent(html);
  await page.pdf({
    path: path.join(__dirname, "maths_sample.pdf"),
    format: "A4",
    margin: { top: "68px", bottom: "68px", left: "68px", right: "68px" },
    displayHeaderFooter: true,
    headerTemplate: "<div></div>",
    footerTemplate: `<div style="font-size:11px;color:#464646;width:100%;margin:0 68px;
      display:flex;justify-content:space-between;font-family:'Liberation Sans',Arial">
      <span>senai.uk</span><span class="pageNumber"></span></div>`,
  });
  await browser.close();
})();
