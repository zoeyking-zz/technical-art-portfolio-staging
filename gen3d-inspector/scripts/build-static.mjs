#!/usr/bin/env node
/**
 * Build the plain static bundle that gets uploaded to object storage.
 *
 *   node scripts/build-static.mjs
 *
 * Output: dist-static/
 *   index.html + hashed assets only. Cloudflare/Workers-specific files that
 *   have no meaning on a plain object-storage host are stripped out.
 *
 * Two non-obvious things this script exists to handle:
 *
 * 1. Static export is switched on through GEN3D_STATIC_EXPORT (see
 *    next.config.ts). Exporting the mode inline is not portable across
 *    PowerShell, cmd and bash, so the env is set here instead.
 *
 * 2. `output: 'export'` makes vinext prerender every route, and prerendering
 *    boots a throwaway HTTP server on 127.0.0.1 and fetches from it. On a
 *    machine where HTTP_PROXY points at a local proxy with an empty NO_PROXY,
 *    that loopback request is sent to the proxy and the build hangs forever
 *    with no output. We pin NO_PROXY to localhost for the child process.
 *
 * The domain the bundle advertises (og:image, twitter:image) comes from
 * NEXT_PUBLIC_SITE_URL. Set it in .env.deploy or pass --site-url=…
 */

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const clientDir = path.join(root, 'dist', 'client');
const outDir = path.join(root, 'dist-static');

// One git-ignored file holds everything that changes per deployment, so the
// whole workflow stays `npm run deploy:cos`.
loadDeployEnv();

function loadDeployEnv() {
  const envFile = path.join(root, '.env.deploy');
  if (!fs.existsSync(envFile)) return;
  try {
    process.loadEnvFile(envFile);
  } catch (error) {
    console.warn(`  build-static: could not read .env.deploy — ${error.message}`);
  }
}

const siteUrl = (
  process.argv
    .slice(2)
    .find((arg) => arg.startsWith('--site-url='))
    ?.slice('--site-url='.length) ??
  process.env.NEXT_PUBLIC_SITE_URL ??
  ''
)
  .trim()
  .replace(/\/+$/, '');

const basePathArg = process.argv
  .slice(2)
  .find((arg) => arg.startsWith('--base-path='))
  ?.slice('--base-path='.length);
const basePath = basePathArg
  ? `/${basePathArg.replace(/^\/+|\/+$/g, '')}`
  : '';

// Files under dist/client that only make sense to a Workers/Pages-style host.
const EXCLUDED = new Set([
  '.assetsignore',
  '_headers',
  '_redirects',
  '.vite',
  'vinext-client-entry-manifest.json',
  'wrangler.json',
]);

function fail(message) {
  console.error(`\n  build-static: ${message}\n`);
  process.exit(1);
}

console.log('\n  build-static: static export (output: "export")');
console.log(
  siteUrl
    ? `  site url: ${siteUrl}\n`
    : '  site url: (unset — og:image keeps the default domain; pass --site-url=https://…)\n',
);
if (basePath) console.log(`  base path: ${basePath}\n`);

const childEnv = {
  ...process.env,
  GEN3D_STATIC_EXPORT: '1',
  NO_PROXY: '127.0.0.1,localhost,::1',
  no_proxy: '127.0.0.1,localhost,::1',
};
if (siteUrl) childEnv.NEXT_PUBLIC_SITE_URL = siteUrl;

const build = spawnSync(
  process.execPath,
  [path.join(root, 'node_modules', 'vinext', 'dist', 'cli.js'), 'build'],
  {
    cwd: root,
    stdio: 'inherit',
    env: childEnv,
  },
);

if (build.status !== 0) fail(`vinext build exited with code ${build.status}`);

const indexPath = path.join(clientDir, 'index.html');
if (!fs.existsSync(indexPath)) {
  fail(
    'dist/client/index.html was not produced — the export did not prerender the root route.',
  );
}

console.log('\n  build-static: packaging dist-static/\n');

fs.rmSync(outDir, { recursive: true, force: true });
fs.cpSync(clientDir, outDir, {
  recursive: true,
  filter: (src) => {
    const rel = path.relative(clientDir, src);
    if (rel === '') return true;
    const top = rel.split(path.sep)[0];
    return !EXCLUDED.has(top);
  },
});

// GitHub Pages project sites live below /<repository>/, while this viewer is
// deliberately built for a domain root (which is also what COS uses). Vinext
// cannot currently static-export a root route with Next's basePath enabled,
// so the Pages build keeps the portable root output and prefixes only its
// public asset URLs after export. This app has no server routes or API calls.
if (basePath) rewritePublicUrls(outDir, basePath);

// Sanity checks on the packaged output: the shell HTML and the JS/CSS payload
// the browser needs to boot the viewer.
const html = fs.readFileSync(indexPath, 'utf-8');
const referenced = [...html.matchAll(/(?:src|href)="([^"]*\/_next\/[^"]+)"/g)].map(
  (m) => m[1],
);
const missing = referenced.filter(
  (url) => {
    const bundlePath = basePath && url.startsWith(`${basePath}/`) ? url.slice(basePath.length) : url;
    return !fs.existsSync(path.join(outDir, decodeURIComponent(bundlePath.slice(1))));
  },
);
if (missing.length > 0) {
  fail(`index.html references ${missing.length} asset(s) that are not present: ${missing.join(', ')}`);
}

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

const files = walk(outDir);
const bytes = files.reduce((sum, file) => sum + fs.statSync(file).size, 0);

console.log(`  ${files.length} files, ${(bytes / 1024 / 1024).toFixed(2)} MB`);
console.log(`  output: ${outDir}`);
console.log(`  assets referenced by index.html: ${referenced.length}, all present\n`);
console.log('  Next: node scripts/deploy-cos.mjs   (needs COS_* environment variables)\n');

function rewritePublicUrls(dir, prefix) {
  const textExtensions = new Set(['.html', '.css', '.js', '.rsc', '.json']);
  for (const file of walk(dir)) {
    if (!textExtensions.has(path.extname(file).toLowerCase())) continue;
    const source = fs.readFileSync(file, 'utf8');
    const rewritten = source
      .replace(/(["'])\/_next\//g, `$1${prefix}/_next/`)
      .replace(/url\(\/_next\//g, `url(${prefix}/_next/`)
      .replace(/(["'])\/(favicon\.svg|og\.png|404\.html)(?=["'])/g, `$1${prefix}/$2`);
    if (rewritten !== source) fs.writeFileSync(file, rewritten);
  }
}

