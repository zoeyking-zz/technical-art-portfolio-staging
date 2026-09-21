import type { NextConfig } from 'next';

// Set GEN3D_STATIC_EXPORT=1 to emit a plain static bundle at `dist/client`
// (index.html + hashed assets) that can be uploaded to object storage such as
// Tencent Cloud COS. The default Sites/Cloudflare build is left untouched.
const isStaticExport = process.env.GEN3D_STATIC_EXPORT === '1';

const nextConfig: NextConfig = isStaticExport ? { output: 'export' } : {};

export default nextConfig;
