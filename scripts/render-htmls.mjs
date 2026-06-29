import { chromium } from 'playwright';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const docsDir = path.resolve(__dirname, '../docs');

const files = [
  'x-banner-0.3pct.html',
  'x-visual-token-ratio.html',
  'x-visual-compare.html',
  'x-visual-component-cost.html',
];

(async () => {
  const browser = await chromium.launch();
  for (const file of files) {
    const htmlPath = path.join(docsDir, file);
    const pngPath = htmlPath.replace('.html', '.png');
    const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
    await page.goto('file://' + htmlPath, { waitUntil: 'networkidle' });
    await page.waitForTimeout(500);
    await page.screenshot({ path: pngPath, fullPage: true });
    console.log(`✅ ${file} → ${path.basename(pngPath)}`);
    await page.close();
  }
  await browser.close();
  console.log('🎉 All done.');
})();
