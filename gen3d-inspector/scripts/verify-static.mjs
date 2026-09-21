#!/usr/bin/env node
/**
 * Serve dist-static/ locally and check the packaged bundle actually works.
 *
 *   node scripts/verify-static.mjs
 *
 * This is a pre-flight check, not a substitute for testing against the real
 * CDN: it catches the failure modes that a static export can introduce —
 * missing hashed assets, a shell HTML that references files that were never
 * emitted, and metadata still pointing at the previous domain.
 *
 * Uses node:http for its own requests on purpose. The global fetch() picks up
 * HTTP_PROXY on this machine, which would send a 127.0.0.1 request to the
 * local proxy and hang.
 */

import fs from 'node:fs';
import http from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir = path.join(root, 'dist-static');

if (!fs.existsSync(path.join(dir, 'index.html'))) {
  console.error('\n  verify-static: dist-static/index.html not found — run `npm run build:static` first.\n');
  process.exit(1);
}

const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json',
  '.rsc': 'text/x-component; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.woff2': 'font/woff2',
};

const server = http.createServer((req, res) => {
  const urlPath = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
  const candidates = [
    path.join(dir, urlPath),
    path.join(dir, urlPath, 'index.html'),
  ];
  const file = candidates.find((candidate) => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
  if (!file) {
    res.writeHead(404, { 'content-type': 'text/plain' });
    res.end('not found');
    return;
  }
  res.writeHead(200, {
    'content-type': CONTENT_TYPES[path.extname(file).toLowerCase()] ?? 'application/octet-stream',
    'cache-control': file.endsWith('index.html') ? 'no-cache' : 'public, max-age=31536000, immutable',
  });
  res.end(fs.readFileSync(file));
});

function get(port, urlPath) {
  return new Promise((resolve, reject) => {
    const req = http.get({ host: '127.0.0.1', port, path: urlPath }, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body }));
    });
    req.on('error', reject);
    req.setTimeout(10000, () => req.destroy(new Error('timeout')));
  });
}

await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
const port = server.address().port;
console.log(`\n  verify-static: serving dist-static/ on http://127.0.0.1:${port}\n`);

const results = [];
function check(label, ok, detail = '') {
  results.push({ label, ok, detail });
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${label}${detail ? `  ${detail}` : ''}`);
}

// Advisories do not fail the run: they flag things that are fine while the
// bundle is still being built against the pre-migration setup.
function warn(label, detail) {
  console.log(`  WARN  ${label}  ${detail}`);
}

try {
  const index = await get(port, '/');
  check('GET /', index.status === 200, `status=${index.status}, ${index.body.length} bytes`);
  check('shell has the app title', index.body.includes('<title>Gen3D Inspector</title>'));
  check('shell is cache-revalidating', index.headers['cache-control'] === 'no-cache', index.headers['cache-control']);

  const refs = [...new Set([...index.body.matchAll(/(?:src|href)="(\/_next\/[^"]+)"/g)].map((m) => m[1]))];
  let assetFailures = 0;
  for (const ref of refs) {
    const res = await get(port, ref);
    if (res.status !== 200 || res.body.length === 0) {
      assetFailures += 1;
      check(`GET ${ref}`, false, `status=${res.status}`);
    }
  }
  check(`all ${refs.length} hashed assets referenced by the shell`, assetFailures === 0);

  check('GET /og.png', (await get(port, '/og.png')).status === 200);
  check('GET /favicon.svg', (await get(port, '/favicon.svg')).status === 200);
  check('GET /404.html', (await get(port, '/404.html')).status === 200);

  const ogImage = index.body.match(/og:image" content="([^"]*)"/)?.[1] ?? '';
  if (ogImage.includes('chatgpt.site')) {
    warn('og:image still points at the old domain', ogImage);
  } else {
    check('og:image uses the new domain', true, ogImage);
  }
} finally {
  server.close();
}

const failed = results.filter((result) => !result.ok).length;
console.log(`\n  ${results.length - failed}/${results.length} checks passed\n`);
process.exit(failed > 0 ? 1 : 0);
