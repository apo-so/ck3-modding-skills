// Define this function directly in the documented CUA REPL after selecting a tab.
// Do not use new Function/eval or assume CUA exposes CommonJS exports. No browser setup,
// viewport changes, navigation, native input, access workaround or acceptance.
async function captureCssPng(tab, output, options = {}) {
  const fs = await import('node:fs/promises');
  const crypto = await import('node:crypto');
  const viewport = options.viewport;
  if (!Array.isArray(viewport) || viewport.length !== 2) throw Error('EXPECTED_VIEWPORT_REQUIRED');
  const metadata = await tab.playwright.evaluate(selector => {
    const es = selector ? [...document.querySelectorAll(selector)] : [];
    const e = es.length === 1 ? es[0] : null;
    const r = e && e.getBoundingClientRect();
    return {viewport: [innerWidth, innerHeight], dpr: devicePixelRatio,
      scale: visualViewport.scale, fonts: document.fonts.status,
      target: {selector, count: es.length, rect: r ? [r.x, r.y, r.width, r.height] : null}};
  }, options.selector || null);
  if (metadata.viewport.some((v, i) => v !== viewport[i])) throw Error('VIEWPORT_CHANGED');
  if (Math.abs(metadata.scale - 1) > 1e-5 || metadata.fonts !== 'loaded') throw Error('PAGE_NOT_READY_FOR_CAPTURE');
  const purpose = options.purpose || 'native_compare';
  if (purpose === 'native_compare' && Math.abs(metadata.dpr - 1) > 1e-5) throw Error('DPR_OUTSIDE_TESTED_NATIVE_RECIPE');
  if (options.selector && metadata.target.count !== 1) throw Error('TARGET_SELECTOR_NOT_UNIQUE');
  const request = {format: 'png', optimizeForSpeed: true,
    clip: {x: 0, y: 0, width: viewport[0], height: viewport[1], scale: 1},
    captureBeyondViewport: true};
  const cdp = await tab.capabilities.get('cdp');
  const image = await cdp.send('Page.captureScreenshot', request);
  const bytes = Buffer.from(image.data, 'base64');
  if (bytes.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a' ||
      bytes.readUInt32BE(16) !== viewport[0] || bytes.readUInt32BE(20) !== viewport[1]) throw Error('PNG_SHAPE_MISMATCH');
  const receipt = {...metadata, purpose, request, url: await tab.url(),
    image_path: output, image_sha256: crypto.createHash('sha256').update(bytes).digest('hex'),
    css_mapping_verified: false, native_visual_accepted: false};
  // Keep first failure/receipt: never silently replace an evidence file.
  await fs.writeFile(output, bytes, {flag: 'wx'});
  await fs.writeFile(output + '.json', JSON.stringify(receipt, null, 2), {flag: 'wx'});
  return receipt;
}
if (typeof module !== 'undefined' && module.exports) module.exports = {captureCssPng};
