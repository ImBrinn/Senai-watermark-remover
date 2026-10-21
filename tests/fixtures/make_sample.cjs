// Regenerates senai_sample.pdf, a stand-in for a real SenAI export, rendered
// the same way SenAI does it (headless Chrome -> Skia PDF): "SenAI Maths"
// title on page 1 and a senai.uk footer with a page number on every page.
//
//   npm install playwright   (or use a global install via NODE_PATH)
//   node tests/fixtures/make_sample.cjs
const path = require("path");
const { chromium } = require("playwright");

const questions = [];
for (let i = 1; i <= 24; i++) {
  const id = `${Math.ceil(i / 6)}${"ABCDEF"[(i - 1) % 6]}`;
  questions.push(`
    <div class="q"><span class="id">${id}</span><div>
      <b>${i * 7}</b>
      <div class="work"><small>WORKING</small><br>
        ${i} &times; 7 = ${i * 7}<br>The Senate of senators agrees: x<sup>2</sup> = ${i * i}
      </div></div></div>`);
}

const html = `<!doctype html><html><head><meta charset="utf-8"><style>
  body { font-family: "Liberation Sans", Arial, sans-serif; margin: 0; color: #111; }
  h1 { font-size: 22px; margin: 0 0 12px; }
  .meta b { display: inline-block; min-width: 0; }
  .meta span { background: #f3f3f3; border-radius: 4px; padding: 1px 4px; }
  hr { border: 0; border-top: 1px solid #111; margin: 16px 0; }
  .q { display: flex; gap: 24px; padding: 12px 0; border-bottom: 1px solid #ececec; }
  .id { color: #888; font-weight: bold; width: 24px; }
  .work { border-left: 3px solid #e5e5e5; padding-left: 12px; margin-top: 8px;
          font-family: "Liberation Serif", serif; }
</style></head><body>
  <h1>SenAI Maths</h1>
  <div class="meta"><b>Name:</b> <span>Homework due Monday 2nd November 8am</span></div>
  <div class="meta"><b>Questions Completed:</b> <span>24</span></div>
  <div class="meta"><b>Generated:</b> <span>19 October 2026</span></div>
  <hr>
  ${questions.join("")}
</body></html>`;

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(html);
  await page.pdf({
    path: path.join(__dirname, "senai_sample.pdf"),
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
