const path = require('path');
const fs = require('fs');
const zlib = require('zlib');

// ── Re-render both PNGs fresh ──
async function render(browser, htmlFile, pngFile) {
  const page = await browser.newPage({ viewport: { width: 1200, height: 672 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(__dirname, htmlFile), { waitUntil: 'networkidle' });
  await page.waitForTimeout(900);
  await page.screenshot({ path: path.resolve(__dirname, pngFile), clip: { x: 0, y: 0, width: 1200, height: 672 } });
  await page.close();
}

// ── Minimal PNG decoder (pure Node; PIL binary is broken in this venv) ──
function decodePNG(fp) {
  const buf = fs.readFileSync(fp);
  let off = 8, width, height, colorType; const idat = [];
  while (off < buf.length) {
    const len = buf.readUInt32BE(off);
    const type = buf.toString('ascii', off + 4, off + 8);
    const data = buf.slice(off + 8, off + 8 + len);
    if (type === 'IHDR') { width = data.readUInt32BE(0); height = data.readUInt32BE(4); colorType = data[9]; }
    else if (type === 'IDAT') idat.push(data);
    off += 12 + len;
  }
  const raw = zlib.inflateSync(Buffer.concat(idat));
  const bpp = colorType === 6 ? 4 : colorType === 2 ? 3 : 1;
  const stride = width * bpp, px = Buffer.alloc(height * stride);
  let di = 0, prev = new Array(stride).fill(0);
  for (let y = 0; y < height; y++) {
    const filter = raw[di++];
    const row = raw.slice(di, di + stride); di += stride;
    const recon = Buffer.alloc(stride);
    for (let x = 0; x < stride; x++) {
      const a = x >= bpp ? recon[x - bpp] : 0, b = y > 0 ? prev[x] : 0, c = y > 0 && x >= bpp ? prev[x - bpp] : 0;
      let v = row[x];
      if (filter === 1) v = (v + a) & 255;
      else if (filter === 2) v = (v + b) & 255;
      else if (filter === 3) v = (v + ((a + b) >> 1)) & 255;
      else if (filter === 4) { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); v = (v + (pa <= pb && pa <= pc ? a : (pb <= pc ? b : c))) & 255; }
      recon[x] = v;
    }
    recon.copy(px, y * stride); prev = recon;
  }
  const get = (x, y) => { const i = y * stride + x * bpp; return [px[i], px[i + 1], px[i + 2]]; };
  return { width, height, get };
}

async function main() {
  const { chromium } = require('playwright');
  const browser = await chromium.launch();
  await render(browser, 'maybank-redesign-ad.html', 'maybank-redesign-ad.png');
  await render(browser, 'cover-mockup.html', 'cover-mockup.png');
  await browser.close();

  // per-target corner expectation (cover is a presentation slide on #e9e7e1)
  const targets = [
    { file: 'maybank-redesign-ad.png',  corner: [247, 246, 243] }, // paper #f7f6f3
    { file: 'cover-mockup.png',         corner: [233, 231, 225] }, // stage #e9e7e1
  ];
  let allPass = true;
  for (const { file, corner } of targets) {
    const img = decodePNG(path.resolve(__dirname, file));
    const cornerOK = [img.get(2, 2), img.get(1197, 2), img.get(5, 668)].every(p => p.every((c, i) => Math.abs(c - corner[i]) < 6));
    const nearTeal = p => Math.abs(p[0] - 14) < 50 && Math.abs(p[1] - 110) < 40 && Math.abs(p[2] - 92) < 45;
    let teal = 0;
    for (let y = 540; y < 660; y += 4) for (let x = 60; x < 470; x += 4) if (nearTeal(img.get(x, y))) teal++;
    const seen = new Set();
    for (let y = 0; y < img.height; y += 2) for (let x = 0; x < img.width; x += 2) seen.add(img.get(x, y).join(','));
    const ok = img.width === 1200 && img.height === 672 && cornerOK && teal > 20 && seen.size > 300;
    allPass = allPass && ok;
    console.log(`${file}: ${img.width}x${img.height} corners=${cornerOK} tealCTA=${teal>20?teal:'FAIL'} unique=${seen.size} => ${ok?'PASS':'FAIL'}`);
  }
  console.log(allPass ? 'ALL_PASS' : 'SOME_FAIL');
  process.exit(allPass ? 0 : 1);
}
main().catch(e => { console.error(e); process.exit(1); });
