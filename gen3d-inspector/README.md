# Gen3D Inspector

一个面向技术美术作品审查的、本地优先的多格式 3D 资产浏览与自动检查工具。

**Live demo:** https://gen3d-inspector.zoeyking0675.chatgpt.site/

## Highlights

- 在浏览器本地读取资产，不上传用户选择的模型文件。
- 支持 GLB/glTF、FBX、OBJ/MTL、PLY 和 STL。
- 自动统计节点、网格、顶点、三角形、材质、贴图、动画与包围盒。
- 识别 Graphdeco 3DGS PLY，并用 Spark/Three.js 读取位置、尺度、旋转、不透明度和球谐颜色进行真正的 Gaussian Splat 渲染。
- 用可见 splat 的稳健分位数自动取景，避免极端离群点把主体压成黑点。
- 地面网格、相机近远裁剪面与雾密度随资产尺度动态调整。
- 可导出 JSON 检查报告。

## Stack

- React 19 + TypeScript
- Three.js
- [Spark](https://sparkjs.dev/) for WebGL2 Gaussian splatting
- Vinext/Vite + Tailwind CSS

## Run locally

Requirements: Node.js 22.13 or newer.

```bash
npm install
npm run dev
```

Open `http://localhost:3000`, then select one main model file together with any sidecar textures, buffers or MTL files it references.

Production build:

```bash
npm run build
```

## 3DGS behavior

Graphdeco PLY files are detected from the presence of `f_dc_*`, `opacity`, `scale_*` and `rot_*` vertex properties. They are rendered as anisotropic Gaussian splats rather than fixed-size points. Camera framing uses the central 98% of visible splat centers when spatial outliers are present, while the inspection report retains full source bounds.

### Why the old preview looked black

A Graphdeco 3DGS `.ply` is a vertex-only container whose appearance depends on per-splat scale, rotation, opacity and spherical-harmonic coefficients. A conventional `PLYLoader` only exposes it as points, so the result can look black, tiny or empty. Gen3D Inspector detects that schema and routes it through Spark's depth-sorted Gaussian renderer. Ordinary mesh and point-cloud PLY files continue through the standard Three.js loader.

### Adaptive viewport

Every loaded asset produces a bounds-driven viewport configuration:

- the camera target, distance, near/far planes and fog density scale with the asset;
- the ground grid is centered in X/Z and placed just below the asset's minimum Y;
- 3DGS scenes use robust central bounds for framing so isolated floaters do not hide the subject;
- the full source bounds remain available in the inspection statistics.

## Architecture

```text
Local files
   │
   ├─ glTF / FBX / OBJ / STL ── Three.js loaders ──┐
   ├─ mesh or point PLY ─────── PLYLoader ─────────┤
   └─ Graphdeco 3DGS PLY ────── Spark SplatMesh ───┤
                                                    ▼
                                      shared scene + adaptive framing
                                                    │
                                      inspection stats + JSON report
```

All selected asset bytes stay in browser memory; there is no model upload endpoint.

## Scope and limitations

- FBX constraints and complex DCC materials may be reduced by browser loaders.
- OBJ dependencies must be selected together with the OBJ file.
- USD, Alembic and STEP are documented as roadmap formats because they require dedicated WASM parsers or conversion services.
- Browser checks are structural QA, not an artistic approval or a replacement for source-DCC validation.
- Sample 3D assets are not included in this repository.

No third-party model or training data is bundled with this source.

