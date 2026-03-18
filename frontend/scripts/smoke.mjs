import puppeteer from 'puppeteer';

const url = process.argv[2] ?? 'http://127.0.0.1:15173';
const screenshotPath = process.argv[3] ?? 'puppeteer-smoke.png';

const browser = await puppeteer.launch({ headless: 'new' });
const page = await browser.newPage({ viewport: { width: 1600, height: 1400 } });

await page.goto(url, { waitUntil: 'networkidle0' });
await page.screenshot({ path: screenshotPath, fullPage: true });

const summary = await page.evaluate(() => ({
  path: window.location.pathname,
  heatmapFrames: document.querySelectorAll('.heatmap-frame').length,
  svgCount: document.querySelectorAll('.heatmap-frame svg').length,
  rectCount: document.querySelectorAll('.heatmap-frame svg rect').length,
  textCount: document.querySelectorAll('.heatmap-frame svg text').length,
}));

console.log(JSON.stringify(summary, null, 2));

await browser.close();
