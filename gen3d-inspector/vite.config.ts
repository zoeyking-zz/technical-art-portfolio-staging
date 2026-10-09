import fs from 'node:fs';
import path from 'node:path';
import { sites } from '@openai/sites-vite-plugin';
import tailwindcss from '@tailwindcss/postcss';
import vinext from 'vinext';
import { defineConfig } from 'vite';

const SITE_CREATOR_PLACEHOLDER_DATABASE_ID =
  '00000000-0000-4000-8000-000000000000';

// `.openai/hosting.json` is intentionally not committed: it identifies the
// private Sites project and is irrelevant to static hosts. Sites builds have
// the file, while GitHub Pages builds safely use these empty bindings.
const hostingConfigPath = path.resolve('.openai/hosting.json');
const hostingConfig = fs.existsSync(hostingConfigPath)
  ? JSON.parse(fs.readFileSync(hostingConfigPath, 'utf8')) as { d1?: string | null; r2?: string | null }
  : { d1: null, r2: null };
const { d1, r2 } = hostingConfig;

// macOS Seatbelt blocks FSEvents, so Codex previews need polling for HMR.
const isCodexSeatbeltSandbox = process.env.CODEX_SANDBOX === 'seatbelt';
const isStaticExport = process.env.GEN3D_STATIC_EXPORT === '1';

const localBindingConfig = {
  main: 'vinext/server/fetch-handler',
  compatibility_flags: ['nodejs_compat'],
  d1_databases: d1
    ? [
        {
          binding: d1,
          database_name: 'site-creator-d1',
          database_id: SITE_CREATOR_PLACEHOLDER_DATABASE_ID,
        },
      ]
    : [],
  r2_buckets: r2
    ? [
        {
          binding: r2,
          bucket_name: 'site-creator-r2',
        },
      ]
    : [],
};

export default defineConfig(async () => {
  // Keep Wrangler and Miniflare state project-local. These are non-secret tool
  // settings; application environment belongs in ignored `.env*` files.
  process.env.WRANGLER_WRITE_LOGS ??= 'false';
  process.env.WRANGLER_LOG_PATH ??= '.wrangler/logs';
  process.env.MINIFLARE_REGISTRY_PATH ??= '.wrangler/registry';

  const sharedConfig = {
    css: { postcss: { plugins: [tailwindcss()] } },
    server: isCodexSeatbeltSandbox
      ? { watch: { useFsEvents: false, usePolling: true } }
      : undefined,
  };

  // A portable bundle has no Workers runtime and must not invoke the Sites
  // plugin, which copies the private `.openai/hosting.json` file. This keeps
  // GitHub Pages and object-storage builds independent from Sites.
  if (isStaticExport) {
    return { ...sharedConfig, plugins: [vinext()] };
  }

  // Wrangler snapshots its log path while the Cloudflare plugin is imported.
  const { cloudflare } = await import('@cloudflare/vite-plugin');

  return {
    ...sharedConfig,
    plugins: [
      vinext(),
      sites(),
      cloudflare({
        viteEnvironment: { name: 'rsc', childEnvironments: ['ssr'] },
        config: localBindingConfig,
      }),
    ],
  };
});

