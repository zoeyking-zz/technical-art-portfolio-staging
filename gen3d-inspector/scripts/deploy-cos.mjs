#!/usr/bin/env node
/**
 * Upload dist-static/ to a Tencent Cloud COS bucket.
 *
 *   node scripts/deploy-cos.mjs [--dry-run] [--website] [--cors] [--no-cache-bust]
 *
 * Required environment variables:
 *   COS_SECRET_ID    CAM sub-account SecretId (never the root account key)
 *   COS_SECRET_KEY   CAM sub-account SecretKey
 *   COS_BUCKET       e.g. gen3d-inspector-1250000000
 *   COS_REGION       e.g. ap-guangzhou (mainland) or ap-hongkong (transition)
 *
 * Optional:
 *   COS_PREFIX       key prefix inside the bucket, e.g. gen3d (default: none)
 *   COS_CDN_HOST     printed in the summary, e.g. gen3d.example.com
 *
 * Flags:
 *   --dry-run   list what would be uploaded, touch nothing
 *   --website   also set the bucket's static-website index/error documents
 *   --cors      also apply a CORS rule for GET/HEAD
 *
 * Cache policy (COS has no `_headers` file — headers are per-object metadata,
 * so they are set on every upload):
 *   /_next/static/**   content-hashed, safe to cache for a year
 *   *.woff2            same
 *   index.html + *.html must revalidate, otherwise a new deploy keeps serving
 *                       the old shell
 *   everything else    one hour
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourceDir = path.join(root, 'dist-static');

const args = new Set(process.argv.slice(2));
const dryRun = args.has('--dry-run');

// Credentials live in a git-ignored .env.deploy so the command stays short.
const envFile = path.join(root, '.env.deploy');
if (fs.existsSync(envFile)) {
  try {
    process.loadEnvFile(envFile);
  } catch (error) {
    console.warn(`  deploy-cos: could not read .env.deploy — ${error.message}`);
  }
}

const { COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, COS_REGION } = process.env;
const PREFIX = (process.env.COS_PREFIX ?? '').replace(/^\/+|\/+$/g, '');
const CDN_HOST = process.env.COS_CDN_HOST ?? '';

function fail(message) {
  console.error(`\n  deploy-cos: ${message}\n`);
  process.exit(1);
}

if (!fs.existsSync(sourceDir)) {
  fail('dist-static/ not found — run `node scripts/build-static.mjs` first.');
}

let COS;
try {
  COS = require('cos-nodejs-sdk-v5');
} catch {
  fail(
    'the Tencent Cloud COS SDK is not installed. Run:\n' +
      '    npm install --save-dev cos-nodejs-sdk-v5',
  );
}

const missingEnv = Object.entries({
  COS_SECRET_ID,
  COS_SECRET_KEY,
  COS_BUCKET,
  COS_REGION,
}).filter(([, value]) => !value);
if (missingEnv.length > 0) {
  fail(
    `missing environment variable(s): ${missingEnv.map(([k]) => k).join(', ')}\n` +
      '  Set them in the shell before running, or put them in a git-ignored .env.deploy file.',
  );
}

const CONTENT_TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.rsc': 'text/x-component; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.avif': 'image/avif',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.ttf': 'font/ttf',
  '.txt': 'text/plain; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
};

function contentTypeFor(key) {
  return CONTENT_TYPES[path.extname(key).toLowerCase()] ?? 'application/octet-stream';
}

function cacheControlFor(key) {
  if (key === 'index.html' || key.endsWith('.html')) return 'no-cache';
  if (key.startsWith('_next/static/')) return 'public, max-age=31536000, immutable';
  if (key.endsWith('.woff2') || key.endsWith('.woff')) return 'public, max-age=31536000, immutable';
  return 'public, max-age=3600';
}

function walk(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(dir, entry.name);
    return entry.isDirectory() ? walk(full) : [full];
  });
}

const files = walk(sourceDir)
  .map((file) => path.relative(sourceDir, file).split(path.sep).join('/'))
  .sort();

if (files.length === 0) fail('dist-static/ is empty.');

console.log(`\n  deploy-cos: ${files.length} files -> cos://${COS_BUCKET} (${COS_REGION})`);
if (PREFIX) console.log(`  prefix: ${PREFIX}/`);
if (dryRun) console.log('  DRY RUN — nothing will be written');

const cos = new COS({ SecretId: COS_SECRET_ID, SecretKey: COS_SECRET_KEY });

function uploadOne(key, body) {
  return new Promise((resolve, reject) => {
    cos.putObject(
      {
        Bucket: COS_BUCKET,
        Region: COS_REGION,
        Key: key,
        Body: body,
        ContentType: contentTypeFor(key),
        CacheControl: cacheControlFor(key),
      },
      (err, data) => (err ? reject(err) : resolve(data)),
    );
  });
}

function call(method, params) {
  return new Promise((resolve, reject) => {
    cos[method](params, (err, data) => (err ? reject(err) : resolve(data)));
  });
}

let uploaded = 0;
for (const rel of files) {
  const key = PREFIX ? `${PREFIX}/${rel}` : rel;
  const sizeKb = (fs.statSync(path.join(sourceDir, rel)).size / 1024).toFixed(1);
  if (dryRun) {
    console.log(`    ${key}  (${sizeKb} kB, ${cacheControlFor(rel)})`);
    uploaded += 1;
    continue;
  }
  try {
    await uploadOne(key, fs.readFileSync(path.join(sourceDir, rel)));
  } catch (error) {
    fail(`upload failed for ${key}: ${error?.message ?? error}`);
  }
  uploaded += 1;
  process.stdout.write(`\r    uploaded ${uploaded}/${files.length}  ${key}`.padEnd(100));
}
process.stdout.write('\n');

if (args.has('--website') && !dryRun) {
  const websitePrefix = PREFIX ? `${PREFIX}/` : '';
  await call('putBucketWebsite', {
    Bucket: COS_BUCKET,
    Region: COS_REGION,
    WebsiteConfiguration: {
      IndexDocument: { Suffix: `${websitePrefix}index.html` },
      ErrorDocument: { Key: `${websitePrefix}index.html` },
    },
  });
  console.log('  static website hosting: index -> index.html, error -> index.html');
}

if (args.has('--cors') && !dryRun) {
  const allowed = CDN_HOST ? [`https://${CDN_HOST}`] : ['*'];
  await call('putBucketCors', {
    Bucket: COS_BUCKET,
    Region: COS_REGION,
    CORSRules: [
      {
        AllowedOrigin: allowed,
        AllowedMethod: ['GET', 'HEAD'],
        AllowedHeader: ['*'],
        MaxAgeSeconds: 86400,
      },
    ],
  });
  console.log(`  CORS: GET/HEAD from ${allowed.join(', ')}`);
}

console.log('\n  Done.');
if (CDN_HOST) console.log(`  Visit: https://${CDN_HOST}/`);
console.log(
  '\n  Remaining manual steps (once per bucket, console or API):\n' +
    '    - bind the custom domain to the bucket and to the CDN acceleration domain\n' +
    '    - upload / attach the TLS certificate\n' +
    '    - point DNS at the CDN CNAME\n',
);
