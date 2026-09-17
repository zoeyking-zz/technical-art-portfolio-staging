'use client';

import { ChangeEvent, DragEvent, useCallback, useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { MTLLoader } from 'three/addons/loaders/MTLLoader.js';
import { OBJLoader } from 'three/addons/loaders/OBJLoader.js';
import { PLYLoader } from 'three/addons/loaders/PLYLoader.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';
import { SparkRenderer, SplatMesh } from '@sparkjsdev/spark';
import {
  Activity,
  Axis3D,
  Box,
  Boxes,
  Braces,
  Check,
  ChevronRight,
  CircleAlert,
  CircleCheck,
  Download,
  FileBox,
  FileWarning,
  Focus,
  FolderOpen,
  Grid3X3,
  Info,
  Layers3,
  LoaderCircle,
  Maximize2,
  Orbit,
  Play,
  RotateCcw,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Triangle,
  Upload,
  X,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

type Phase = 'demo' | 'loading' | 'ready' | 'error';
type IssueLevel = 'pass' | 'warning' | 'error' | 'info';

type AssetStats = {
  name: string;
  format: string;
  sizeBytes: number;
  nodes: number;
  meshes: number;
  points: number;
  vertices: number;
  triangles: number;
  materials: number;
  textures: number;
  animations: number;
  dimensions: [number, number, number];
};

type InspectionIssue = {
  level: IssueLevel;
  title: string;
  detail: string;
};

type SceneNode = {
  name: string;
  type: string;
  depth: number;
};

type Runtime = {
  scene: THREE.Scene;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  renderer: THREE.WebGLRenderer;
  root: THREE.Object3D | null;
  mixer: THREE.AnimationMixer | null;
  splatRenderer: SparkRenderer;
  grid: THREE.GridHelper;
  axes: THREE.AxesHelper;
  bounds: THREE.Box3 | null;
  loadObject: (root: THREE.Object3D, animations: THREE.AnimationClip[], metadata: FileMetadata) => void;
  resetCamera: () => void;
};

type FileMetadata = {
  name: string;
  format: string;
  sizeBytes: number;
  missingDependencies?: string[];
  bounds?: THREE.Box3;
  sourceBounds?: THREE.Box3;
  gaussianSplats?: number;
};

type PlyHeaderInfo = {
  faceCount: number;
  vertexCount: number;
  isGaussianSplat: boolean;
};

const BASE_GRID_SIZE = 20;

const DEMO_STATS: AssetStats = {
  name: 'Diagnostic Knot',
  format: 'PROCEDURAL DEMO',
  sizeBytes: 0,
  nodes: 2,
  meshes: 1,
  points: 0,
  vertices: 4025,
  triangles: 7680,
  materials: 1,
  textures: 0,
  animations: 0,
  dimensions: [2.93, 2.42, 1.37],
};

const DEMO_ISSUES: InspectionIssue[] = [
  { level: 'pass', title: 'Geometry is renderable', detail: 'Position and normal buffers are present.' },
  { level: 'pass', title: 'Coordinates are finite', detail: 'No NaN or Infinity values were detected.' },
  { level: 'info', title: 'Procedural demo asset', detail: 'Open local files to run a real inspection.' },
];

const FORMAT_ADAPTERS = [
  { id: 'gltf', label: 'glTF / GLB', status: 'ready', copy: 'Runtime scenes, PBR materials, skins, morphs and animation.', limit: 'Extensions depend on the browser loader.' },
  { id: 'fbx', label: 'FBX', status: 'ready', copy: 'DCC exchange for meshes, rigs and baked animation.', limit: 'Complex materials and constraints may be reduced.' },
  { id: 'obj', label: 'OBJ + MTL', status: 'ready', copy: 'Static polygon geometry with optional material libraries.', limit: 'Select the OBJ, MTL and textures together.' },
  { id: 'ply', label: 'PLY / 3DGS', status: 'ready', copy: 'Polygon meshes, point clouds and Graphdeco Gaussian splats.', limit: '3DGS uses splat scale, rotation, opacity and spherical harmonics.' },
  { id: 'stl', label: 'STL', status: 'ready', copy: 'Triangulated manufacturing geometry.', limit: 'No standard unit, UV or PBR material data.' },
  { id: 'usd', label: 'USD / Alembic / STEP', status: 'roadmap', copy: 'Scene composition, geometry cache and CAD B-Rep.', limit: 'Requires dedicated WASM or server conversion.' },
] as const;

const MAIN_EXTENSIONS = new Set(['glb', 'gltf', 'fbx', 'obj', 'ply', 'stl']);
const FILE_ACCEPT = '.glb,.gltf,.fbx,.obj,.mtl,.ply,.stl,.bin,.png,.jpg,.jpeg,.webp,.ktx2,.tga';

function extensionOf(name: string) {
  return name.split('.').pop()?.toLowerCase() ?? '';
}

function basename(path: string) {
  return decodeURIComponent(path.split(/[\\/]/).pop() ?? path).split(/[?#]/)[0].toLowerCase();
}

function formatBytes(bytes: number) {
  if (!bytes) return 'generated';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}

function formatCount(value: number) {
  return new Intl.NumberFormat('en-US', { notation: value > 99999 ? 'compact' : 'standard', maximumFractionDigits: 1 }).format(value);
}

function parsePlyHeader(header: string): PlyHeaderInfo {
  const properties = new Set(
    [...header.matchAll(/^property\s+\S+\s+(\S+)\s*$/gim)].map((match) => match[1].toLowerCase()),
  );
  return {
    faceCount: Number(header.match(/^element\s+face\s+(\d+)/im)?.[1] ?? 0),
    vertexCount: Number(header.match(/^element\s+vertex\s+(\d+)/im)?.[1] ?? 0),
    isGaussianSplat: ['x', 'y', 'z', 'f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity', 'scale_0', 'scale_1', 'scale_2', 'rot_0', 'rot_1', 'rot_2', 'rot_3'].every((property) => properties.has(property)),
  };
}

function niceCeiling(value: number) {
  const safeValue = Math.max(value, 0.0001);
  const magnitude = 10 ** Math.floor(Math.log10(safeValue));
  const normalized = safeValue / magnitude;
  const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
  return step * magnitude;
}

function quantile(sorted: number[], percentile: number) {
  return sorted[Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * percentile)))];
}

function getRobustSplatBounds(splats: SplatMesh, splatCount: number) {
  const axes: [number[], number[], number[]] = [[], [], []];
  const stride = Math.max(1, Math.ceil(splatCount / 200000));
  splats.forEachSplat((index, center, _scales, _quaternion, opacity) => {
    if (index % stride || opacity < 0.01 || !Number.isFinite(center.x + center.y + center.z)) return;
    axes[0].push(center.x);
    axes[1].push(center.y);
    axes[2].push(center.z);
  });
  if (axes[0].length < 32) return splats.getBoundingBox(true);
  axes.forEach((axis) => axis.sort((a, b) => a - b));
  const min = new THREE.Vector3(quantile(axes[0], 0.01), quantile(axes[1], 0.01), quantile(axes[2], 0.01));
  const max = new THREE.Vector3(quantile(axes[0], 0.99), quantile(axes[1], 0.99), quantile(axes[2], 0.99));
  const padding = max.clone().sub(min).multiplyScalar(0.06);
  return new THREE.Box3(min.sub(padding), max.add(padding));
}

function fitRuntimeToBounds(runtime: Runtime, bounds: THREE.Box3) {
  if (bounds.isEmpty()) return;
  const size = bounds.getSize(new THREE.Vector3());
  const sphere = bounds.getBoundingSphere(new THREE.Sphere());
  const radius = Math.max(sphere.radius, 0.001);
  const horizontalExtent = Math.max(size.x, size.z, size.y * 0.35, radius * 0.75, 0.1);
  const gridSize = niceCeiling(horizontalExtent * 1.6);
  const gridOffset = Math.max(gridSize / 400, radius / 1000, 0.0001);

  runtime.bounds = bounds.clone();
  runtime.grid.scale.setScalar(gridSize / BASE_GRID_SIZE);
  runtime.grid.position.set(sphere.center.x, bounds.min.y - gridOffset, sphere.center.z);
  runtime.axes.position.copy(runtime.grid.position);

  runtime.controls.target.copy(sphere.center);
  runtime.camera.position.copy(sphere.center).add(new THREE.Vector3(radius * 1.8, radius * 1.25, radius * 2.15));
  runtime.camera.near = Math.max(radius / 2000, 0.0001);
  runtime.camera.far = Math.max(radius * 200, 100);
  runtime.camera.updateProjectionMatrix();
  runtime.controls.update();

  if (runtime.scene.fog instanceof THREE.FogExp2) {
    runtime.scene.fog.density = 0.05 / Math.max(radius, 0.25);
  }
}

function disposeObject(root: THREE.Object3D) {
  if (root instanceof SplatMesh) {
    root.dispose();
    return;
  }
  root.traverse((object) => {
    const mesh = object as THREE.Mesh;
    mesh.geometry?.dispose?.();
    const materials = Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : [];
    materials.forEach((material) => {
      Object.values(material).forEach((value) => {
        if (value instanceof THREE.Texture) value.dispose();
      });
      material.dispose();
    });
  });
}

function buildSceneNodes(root: THREE.Object3D): SceneNode[] {
  const result: SceneNode[] = [];
  const walk = (node: THREE.Object3D, depth: number) => {
    if (result.length >= 80) return;
    result.push({ name: node.name || `${node.type}_${result.length}`, type: node.type, depth });
    node.children.forEach((child) => walk(child, depth + 1));
  };
  walk(root, 0);
  return result;
}

function inspectObject(root: THREE.Object3D, animations: THREE.AnimationClip[], metadata: FileMetadata) {
  if (metadata.gaussianSplats) {
    const size = (metadata.sourceBounds ?? metadata.bounds)?.getSize(new THREE.Vector3()) ?? new THREE.Vector3();
    const frameSize = metadata.bounds?.getSize(new THREE.Vector3()) ?? size;
    const hasSpatialOutliers = Math.max(size.x / Math.max(frameSize.x, 0.0001), size.y / Math.max(frameSize.y, 0.0001), size.z / Math.max(frameSize.z, 0.0001)) > 3;
    return {
      stats: {
        name: metadata.name,
        format: 'PLY · 3DGS',
        sizeBytes: metadata.sizeBytes,
        nodes: 1,
        meshes: 0,
        points: 1,
        vertices: metadata.gaussianSplats,
        triangles: 0,
        materials: 1,
        textures: 0,
        animations: 0,
        dimensions: [size.x, size.y, size.z] as [number, number, number],
      },
      issues: [
        { level: 'pass' as const, title: 'Gaussian splats are renderable', detail: `${formatCount(metadata.gaussianSplats)} anisotropic splats were decoded by the WebGL2 renderer.` },
        { level: 'pass' as const, title: 'Graphdeco schema detected', detail: 'Scale, rotation, opacity and spherical-harmonic color attributes are active.' },
        ...(hasSpatialOutliers ? [{ level: 'info' as const, title: 'Robust camera framing', detail: 'The camera and grid frame the central 98% of visible splats; full source bounds remain in the report.' }] : []),
        ...(metadata.sizeBytes > 100 * 1024 ** 2 ? [{ level: 'warning' as const, title: 'Large source file', detail: 'The source exceeds 100 MB and may cause high peak memory use.' }] : []),
      ],
      nodes: [{ name: metadata.name, type: 'GaussianSplats', depth: 0 }],
    };
  }
  let nodes = 0;
  let meshes = 0;
  let points = 0;
  let vertices = 0;
  let triangles = 0;
  let nonFinite = 0;
  let missingNormals = 0;
  let texturedWithoutUv = 0;
  const materials = new Set<string>();
  const textures = new Set<string>();

  root.traverse((object) => {
    nodes += 1;
    const drawable = object as THREE.Mesh | THREE.Points;
    if (drawable instanceof THREE.Mesh) meshes += 1;
    if (drawable instanceof THREE.Points) points += 1;
    const geometry = drawable.geometry;
    if (!geometry?.attributes?.position) return;
    const position = geometry.attributes.position;
    vertices += position.count;
    if (drawable instanceof THREE.Mesh) {
      triangles += geometry.index ? Math.floor(geometry.index.count / 3) : Math.floor(position.count / 3);
      if (!geometry.attributes.normal) missingNormals += 1;
    }
    const array = position.array;
    for (let index = 0; index < array.length; index += 1) {
      if (!Number.isFinite(array[index])) nonFinite += 1;
    }
    const objectMaterials = Array.isArray(drawable.material) ? drawable.material : drawable.material ? [drawable.material] : [];
    let hasTexture = false;
    objectMaterials.forEach((material) => {
      materials.add(material.uuid);
      Object.values(material).forEach((value) => {
        if (value instanceof THREE.Texture) {
          textures.add(value.uuid);
          hasTexture = true;
        }
      });
    });
    if (hasTexture && !geometry.attributes.uv) texturedWithoutUv += 1;
  });

  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3();
  if (!box.isEmpty()) box.getSize(size);
  const stats: AssetStats = {
    name: metadata.name,
    format: metadata.format.toUpperCase(),
    sizeBytes: metadata.sizeBytes,
    nodes,
    meshes,
    points,
    vertices,
    triangles,
    materials: materials.size,
    textures: textures.size,
    animations: animations.length,
    dimensions: [size.x, size.y, size.z],
  };

  const issues: InspectionIssue[] = [];
  if (!meshes && !points) issues.push({ level: 'error', title: 'No renderable geometry', detail: 'The scene contains no mesh or point primitives.' });
  else issues.push({ level: 'pass', title: 'Renderable geometry found', detail: `${meshes} mesh objects and ${points} point objects are available.` });
  if (nonFinite) issues.push({ level: 'error', title: 'Non-finite coordinates', detail: `${nonFinite} position values are NaN or Infinity.` });
  else issues.push({ level: 'pass', title: 'Coordinates are finite', detail: 'All loaded position values are finite.' });
  if (missingNormals) issues.push({ level: 'warning', title: 'Normals are missing', detail: `${missingNormals} mesh objects require generated normals for stable lighting.` });
  else if (meshes) issues.push({ level: 'pass', title: 'Normals are present', detail: 'Every mesh exposes a normal attribute.' });
  if (texturedWithoutUv) issues.push({ level: 'warning', title: 'Texture without UV', detail: `${texturedWithoutUv} textured objects have no primary UV attribute.` });
  if (triangles > 250000) issues.push({ level: 'warning', title: 'High triangle count', detail: `${formatCount(triangles)} triangles exceed the web review budget of 250K.` });
  if (metadata.sizeBytes > 100 * 1024 ** 2) issues.push({ level: 'warning', title: 'Large source file', detail: 'The source exceeds 100 MB and may cause high peak memory use.' });
  metadata.missingDependencies?.forEach((path) => issues.push({ level: 'warning', title: 'Missing dependency', detail: path }));
  if (metadata.format === 'ply' && points > 0 && meshes === 0) issues.push({ level: 'info', title: 'Vertex-only PLY', detail: 'Rendered as points. This is not assumed to be a triangle mesh.' });
  return { stats, issues, nodes: buildSceneNodes(root) };
}

function issueIcon(level: IssueLevel) {
  if (level === 'error') return <FileWarning className="size-3.5" />;
  if (level === 'warning') return <CircleAlert className="size-3.5" />;
  if (level === 'info') return <Info className="size-3.5" />;
  return <Check className="size-3.5" />;
}

export function AssetWorkbench() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const runtimeRef = useRef<Runtime | null>(null);
  const [phase, setPhase] = useState<Phase>('demo');
  const [stats, setStats] = useState<AssetStats>(DEMO_STATS);
  const [issues, setIssues] = useState<InspectionIssue[]>(DEMO_ISSUES);
  const [sceneNodes, setSceneNodes] = useState<SceneNode[]>([
    { name: 'Diagnostic Knot', type: 'Group', depth: 0 },
    { name: 'TorusKnot_Mesh', type: 'Mesh', depth: 1 },
  ]);
  const [selectedFormat, setSelectedFormat] = useState('gltf');
  const [dragging, setDragging] = useState(false);
  const [wireframe, setWireframe] = useState(false);
  const [gridVisible, setGridVisible] = useState(true);
  const [axesVisible, setAxesVisible] = useState(false);
  const [message, setMessage] = useState('Demo asset ready · files stay in this browser');
  const [activeTab, setActiveTab] = useState<'inspect' | 'scene' | 'checks'>('inspect');

  const loadIntoViewer = useCallback((root: THREE.Object3D, animations: THREE.AnimationClip[], metadata: FileMetadata) => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    if (runtime.root) {
      runtime.scene.remove(runtime.root);
      disposeObject(runtime.root);
    }
    runtime.mixer?.stopAllAction();
    root.name ||= metadata.name;
    runtime.root = root;
    runtime.scene.add(root);
    const box = metadata.bounds?.clone() ?? new THREE.Box3().setFromObject(root);
    fitRuntimeToBounds(runtime, box);
    if (animations.length) {
      runtime.mixer = new THREE.AnimationMixer(root);
      runtime.mixer.clipAction(animations[0]).play();
    } else runtime.mixer = null;
    const inspection = inspectObject(root, animations, metadata);
    setStats(inspection.stats);
    setIssues(inspection.issues);
    setSceneNodes(inspection.nodes);
    setWireframe(false);
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: 'high-performance' });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090d10);
    scene.fog = new THREE.FogExp2(0x090d10, 0.028);
    const splatRenderer = new SparkRenderer({ renderer, sortRadial: false, minPixelRadius: 0.35 });
    scene.add(splatRenderer);
    const camera = new THREE.PerspectiveCamera(42, 1, 0.01, 1000);
    camera.position.set(4.8, 3.4, 5.4);
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.065;
    controls.target.set(0, 0.4, 0);
    controls.update();
    scene.add(new THREE.HemisphereLight(0xddeeff, 0x14181c, 2.25));
    const key = new THREE.DirectionalLight(0xfff2d6, 4.8);
    key.position.set(5, 7, 5);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x87bfff, 2.1);
    rim.position.set(-5, 3, -4);
    scene.add(rim);
    const grid = new THREE.GridHelper(BASE_GRID_SIZE, 40, 0x617482, 0x26323a);
    grid.position.y = -1.6;
    const gridMaterial = grid.material as THREE.Material;
    gridMaterial.transparent = true;
    gridMaterial.opacity = 0.72;
    gridMaterial.depthWrite = false;
    scene.add(grid);
    const axes = new THREE.AxesHelper(2);
    axes.visible = false;
    scene.add(axes);
    const demoRoot = new THREE.Group();
    demoRoot.name = 'Diagnostic Knot';
    const material = new THREE.MeshStandardMaterial({ color: 0xa7f35d, roughness: 0.3, metalness: 0.12 });
    const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(1.15, 0.36, 160, 24), material);
    knot.name = 'TorusKnot_Mesh';
    knot.rotation.x = -0.35;
    demoRoot.add(knot);
    scene.add(demoRoot);
    const resetCamera = () => {
      const runtime = runtimeRef.current;
      if (runtime?.bounds) fitRuntimeToBounds(runtime, runtime.bounds);
    };
    runtimeRef.current = { scene, camera, controls, renderer, root: demoRoot, mixer: null, splatRenderer, grid, axes, bounds: null, loadObject: loadIntoViewer, resetCamera };
    fitRuntimeToBounds(runtimeRef.current, new THREE.Box3().setFromObject(demoRoot));
    const clock = new THREE.Clock();
    let frame = 0;
    const resize = () => {
      const width = Math.max(canvas.clientWidth, 1);
      const height = Math.max(canvas.clientHeight, 1);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
    };
    const render = () => {
      resize();
      if (runtimeRef.current?.root === demoRoot) demoRoot.rotation.y += 0.0015;
      runtimeRef.current?.mixer?.update(clock.getDelta());
      controls.update();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(render);
    };
    render();
    return () => {
      cancelAnimationFrame(frame);
      controls.dispose();
      if (runtimeRef.current?.root) disposeObject(runtimeRef.current.root);
      splatRenderer.dispose();
      renderer.dispose();
      runtimeRef.current = null;
    };
  }, [loadIntoViewer]);

  const processFiles = useCallback(async (incoming: File[]) => {
    const mainFiles = incoming.filter((file) => MAIN_EXTENSIONS.has(extensionOf(file.name)));
    if (!mainFiles.length) {
      setPhase('error');
      setMessage('No supported 3D file found in this selection');
      return;
    }
    const main = mainFiles[0];
    const extension = extensionOf(main.name);
    setSelectedFormat(extension === 'glb' ? 'gltf' : extension);
    setPhase('loading');
    setMessage(`Parsing ${main.name} locally…`);
    const fileMap = new Map(incoming.map((file) => [file.name.toLowerCase(), file]));
    const objectUrls = new Map<File, string>();
    const missing = new Set<string>();
    const urlFor = (file: File) => {
      let url = objectUrls.get(file);
      if (!url) {
        url = URL.createObjectURL(file);
        objectUrls.set(file, url);
      }
      return url;
    };
    const manager = new THREE.LoadingManager();
    manager.setURLModifier((url) => {
      if (/^(blob:|data:|https?:)/i.test(url)) return url;
      const dependency = fileMap.get(basename(url));
      if (dependency) return urlFor(dependency);
      missing.add(url);
      return url;
    });
    manager.onError = (url) => missing.add(url);
    try {
      let root: THREE.Object3D;
      let animations: THREE.AnimationClip[] = [];
      if (extension === 'glb' || extension === 'gltf') {
        const gltf = await new GLTFLoader(manager).loadAsync(urlFor(main));
        root = gltf.scene;
        animations = gltf.animations;
      } else if (extension === 'fbx') {
        const fbx = await new FBXLoader(manager).loadAsync(urlFor(main));
        root = fbx;
        animations = fbx.animations;
      } else if (extension === 'obj') {
        const objLoader = new OBJLoader(manager);
        const mtl = incoming.find((file) => extensionOf(file.name) === 'mtl');
        if (mtl) {
          const creator = new MTLLoader(manager).parse(await mtl.text(), '');
          creator.preload();
          objLoader.setMaterials(creator);
        }
        root = await objLoader.loadAsync(urlFor(main));
      } else if (extension === 'ply') {
        const header = await main.slice(0, 65536).text();
        const ply = parsePlyHeader(header);
        if (ply.isGaussianSplat) {
          const splats = new SplatMesh({
            fileBytes: await main.arrayBuffer(),
            fileName: main.name,
            extSplats: true,
            raycastable: false,
          });
          await splats.initialized;
          splats.name = main.name;
          root = splats;
          const sourceBounds = splats.getBoundingBox(false);
          const bounds = getRobustSplatBounds(splats, ply.vertexCount);
          loadIntoViewer(root, [], {
            name: main.name,
            format: extension,
            sizeBytes: incoming.reduce((sum, file) => sum + file.size, 0),
            bounds,
            sourceBounds,
            gaussianSplats: ply.vertexCount,
          });
          setPhase('ready');
          setMessage(`${main.name} loaded · ${formatCount(ply.vertexCount)} Gaussian splats`);
          return;
        }
        const geometry = await new PLYLoader(manager).loadAsync(urlFor(main));
        if (ply.faceCount > 0) {
          geometry.computeVertexNormals();
          root = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xb8c5cf, vertexColors: geometry.hasAttribute('color'), roughness: 0.72, side: THREE.DoubleSide }));
        } else {
          geometry.computeBoundingBox();
          const diagonal = geometry.boundingBox?.getSize(new THREE.Vector3()).length() ?? 1;
          root = new THREE.Points(geometry, new THREE.PointsMaterial({ color: 0xa7f35d, vertexColors: geometry.hasAttribute('color'), size: Math.max(diagonal / 650, 0.001), sizeAttenuation: true }));
        }
        root.name = main.name;
      } else {
        const geometry = await new STLLoader(manager).loadAsync(urlFor(main));
        geometry.computeVertexNormals();
        root = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: 0xb9c4cc, roughness: 0.6, metalness: 0.08 }));
        root.name = main.name;
      }
      loadIntoViewer(root, animations, { name: main.name, format: extension, sizeBytes: incoming.reduce((sum, file) => sum + file.size, 0), missingDependencies: [...missing] });
      setPhase('ready');
      setMessage(`${main.name} loaded · ${incoming.length} local file${incoming.length === 1 ? '' : 's'} resolved`);
    } catch (error) {
      setPhase('error');
      setMessage(error instanceof Error ? error.message : 'The asset could not be parsed');
    } finally {
      window.setTimeout(() => objectUrls.forEach((url) => URL.revokeObjectURL(url)), 1500);
    }
  }, [loadIntoViewer]);

  const handleInput = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files?.length) void processFiles(Array.from(event.target.files));
    event.target.value = '';
  };

  const handleDrop = (event: DragEvent<HTMLElement>) => {
    event.preventDefault();
    setDragging(false);
    void processFiles(Array.from(event.dataTransfer.files));
  };

  const toggleWireframe = () => {
    const next = !wireframe;
    runtimeRef.current?.root?.traverse((object) => {
      const mesh = object as THREE.Mesh;
      if (!(mesh instanceof THREE.Mesh)) return;
      const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      materials.forEach((material) => {
        if ('wireframe' in material) (material as THREE.MeshStandardMaterial).wireframe = next;
      });
    });
    setWireframe(next);
  };

  const toggleGrid = () => {
    const next = !gridVisible;
    if (runtimeRef.current) runtimeRef.current.grid.visible = next;
    setGridVisible(next);
  };

  const toggleAxes = () => {
    const next = !axesVisible;
    if (runtimeRef.current) runtimeRef.current.axes.visible = next;
    setAxesVisible(next);
  };

  const exportReport = () => {
    const status = issues.some((issue) => issue.level === 'error') ? 'ERROR' : issues.some((issue) => issue.level === 'warning') ? 'WARNING' : 'PASS';
    const report = { schema: 'gen3d-inspector-report@1', generatedAt: new Date().toISOString(), status, asset: stats, issues, note: 'Browser-side inspection; visual approval and source DCC validation are still required.' };
    const url = URL.createObjectURL(new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${stats.name.replace(/[^a-z0-9._-]+/gi, '_')}_inspection.json`;
    link.click();
    URL.revokeObjectURL(url);
    setMessage('Inspection report downloaded');
  };

  const selectedAdapter = FORMAT_ADAPTERS.find((adapter) => adapter.id === selectedFormat) ?? FORMAT_ADAPTERS[0];
  const severity = issues.some((issue) => issue.level === 'error') ? 'error' : issues.some((issue) => issue.level === 'warning') ? 'warning' : 'pass';

  return (
    // oxlint-disable-next-line jsx-a11y/no-noninteractive-element-interactions -- The workspace accepts native file drag events while all actions remain keyboard-accessible.
    <main className="app-shell" onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) setDragging(false); }} onDrop={handleDrop}>
      <input ref={inputRef} type="file" accept={FILE_ACCEPT} multiple className="sr-only" onChange={handleInput} aria-label="Open 3D asset files" />
      <header className="app-header">
        <div className="brand-lockup">
          <span className="brand-mark"><Box className="size-4" /></span>
          <div><p className="brand-title">Gen3D Inspector</p><p className="micro-label">ASSET WORKBENCH · LOCAL ONLY</p></div>
        </div>
        <div className="header-actions">
          <div className="privacy-note"><ShieldCheck className="size-3.5" /><span>Files never leave your device</span></div>
          <Button variant="outline" size="sm" onClick={exportReport} disabled={phase === 'loading'}><Download />Report</Button>
          <Button size="sm" onClick={() => inputRef.current?.click()}><Upload />Open asset</Button>
        </div>
      </header>

      <section className="workbench-grid">
        <aside className="left-panel panel-surface">
          <div className="panel-section">
            <p className="eyebrow">INPUT</p>
            <button onClick={() => inputRef.current?.click()} className={`drop-zone ${dragging ? 'is-dragging' : ''}`}>
              <span className="drop-icon">{phase === 'loading' ? <LoaderCircle className="size-5 animate-spin" /> : <FolderOpen className="size-5" />}</span>
              <span className="mt-3 text-sm font-medium">{dragging ? 'Release to inspect' : phase === 'loading' ? 'Reading asset…' : 'Drop a 3D asset'}</span>
              <span className="mt-1.5 font-mono text-[9px] leading-relaxed text-muted-foreground">MAIN FILE + TEXTURES + DEPENDENCIES</span>
              <span className="mt-3 rounded border border-white/8 bg-black/20 px-2 py-1 font-mono text-[9px] text-zinc-400">GLB · FBX · OBJ · PLY · STL</span>
            </button>
          </div>
          <div className="panel-section grow min-h-0">
            <div className="flex items-center justify-between"><p className="eyebrow">FORMAT ADAPTERS</p><span className="micro-label">6 MODULES</span></div>
            <div className="mt-2 h-[260px] overflow-y-auto lg:h-[calc(100vh-440px)]">
              <div className="space-y-1 pr-2">
                {FORMAT_ADAPTERS.map((adapter) => (
                  <button key={adapter.id} onClick={() => setSelectedFormat(adapter.id)} className={`adapter-row ${selectedFormat === adapter.id ? 'is-selected' : ''}`}>
                    <span className="flex min-w-0 items-center gap-2"><FileBox className="size-3.5 shrink-0 text-muted-foreground" /><span className="truncate">{adapter.label}</span></span>
                    {adapter.status === 'ready' ? <CircleCheck className="size-3.5 shrink-0 text-primary" /> : <span className="rounded bg-white/5 px-1.5 py-0.5 font-mono text-[8px] text-zinc-500">ROADMAP</span>}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="format-note">
            <div className="flex items-center justify-between"><p className="font-mono text-[10px] font-medium text-zinc-200">{selectedAdapter.label}</p><ChevronRight className="size-3 text-primary" /></div>
            <p className="mt-2 text-[11px] leading-relaxed text-zinc-400">{selectedAdapter.copy}</p>
            <p className="mt-2 border-t border-white/6 pt-2 text-[10px] leading-relaxed text-zinc-600">{selectedAdapter.limit}</p>
          </div>
        </aside>

        <section className="viewport-panel">
          <canvas ref={canvasRef} aria-label="Interactive 3D asset viewport. Drag to orbit, wheel to zoom." className="viewport-canvas" />
          <div className="viewport-topbar">
            <div className="flex min-w-0 items-center gap-2"><Badge className="max-w-[250px] truncate bg-black/60 font-mono text-[9px] text-zinc-200 backdrop-blur">{stats.name}</Badge><Badge variant="outline" className="border-white/10 bg-black/35 font-mono text-[9px] text-zinc-400">{stats.format}</Badge></div>
            <Badge variant="outline" className={`status-badge status-${severity}`}>{severity.toUpperCase()}</Badge>
          </div>
          <div className="viewport-hint"><Orbit className="size-3" />DRAG TO ORBIT · SCROLL TO ZOOM · RIGHT-DRAG TO PAN</div>
          <div className="viewport-toolbar" role="toolbar" aria-label="Viewport controls">
            <Button size="icon-sm" variant={wireframe ? 'secondary' : 'ghost'} onClick={toggleWireframe} aria-label="Toggle wireframe" title="Wireframe"><Triangle /></Button>
            <Button size="icon-sm" variant={gridVisible ? 'secondary' : 'ghost'} onClick={toggleGrid} aria-label="Toggle grid" title="Grid"><Grid3X3 /></Button>
            <Button size="icon-sm" variant={axesVisible ? 'secondary' : 'ghost'} onClick={toggleAxes} aria-label="Toggle axes" title="Axes"><Axis3D /></Button>
            <span className="mx-0.5 h-4 w-px bg-white/10" />
            <Button size="icon-sm" variant="ghost" onClick={() => runtimeRef.current?.resetCamera()} aria-label="Frame asset" title="Frame asset"><Focus /></Button>
            <Button size="icon-sm" variant="ghost" onClick={() => runtimeRef.current?.resetCamera()} aria-label="Reset camera" title="Reset camera"><RotateCcw /></Button>
          </div>
          {phase === 'loading' && <div className="loading-overlay"><LoaderCircle className="size-6 animate-spin text-primary" /><p>Parsing asset</p><span>Geometry and dependencies stay in your browser</span></div>}
          {phase === 'error' && <div className="error-overlay"><CircleAlert className="size-6 text-destructive" /><p>Could not open this asset</p><span>{message}</span><Button size="sm" variant="outline" onClick={() => inputRef.current?.click()}>Try another file</Button></div>}
          {dragging && <div className="drag-overlay"><Upload className="size-8" /><p>Drop files to inspect</p><span>Include companion textures, MTL and BIN files</span></div>}
        </section>

        <aside className="right-panel panel-surface">
          <div className="asset-summary">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0"><p className="eyebrow">ACTIVE ASSET</p><h1 className="mt-2 truncate text-[15px] font-medium" title={stats.name}>{stats.name}</h1></div>
              <div className={`score-ring score-${severity}`}>{severity === 'pass' ? <Check /> : severity === 'warning' ? <CircleAlert /> : <X />}</div>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5"><Badge variant="outline" className="meta-badge">{stats.format}</Badge><Badge variant="outline" className="meta-badge">{formatBytes(stats.sizeBytes)}</Badge>{stats.animations > 0 && <Badge variant="outline" className="meta-badge"><Play className="size-2.5" /> {stats.animations} clips</Badge>}</div>
          </div>
          <div className="min-h-0 flex-1">
            <div className="tabs-strip" role="tablist" aria-label="Asset details">
              {(['inspect', 'scene', 'checks'] as const).map((tab) => <button key={tab} role="tab" aria-selected={activeTab === tab} className={activeTab === tab ? 'is-active' : ''} onClick={() => setActiveTab(tab)}>{tab[0].toUpperCase() + tab.slice(1)}</button>)}
            </div>
            {activeTab === 'inspect' && <section role="tabpanel" className="h-[calc(100vh-198px)] overflow-y-auto"><div className="p-4">
                <div className="metric-grid">
                  <Metric icon={<Boxes />} label="Meshes" value={formatCount(stats.meshes)} />
                  <Metric icon={<Activity />} label={stats.format.includes('3DGS') ? 'Splats' : 'Vertices'} value={formatCount(stats.vertices)} />
                  <Metric icon={<Triangle />} label="Triangles" value={formatCount(stats.triangles)} />
                  <Metric icon={<Layers3 />} label="Materials" value={formatCount(stats.materials)} />
                  <Metric icon={<Sparkles />} label="Textures" value={formatCount(stats.textures)} />
                  <Metric icon={<Braces />} label="Nodes" value={formatCount(stats.nodes)} />
                </div>
                <div className="data-block"><div className="flex items-center justify-between"><p className="eyebrow">BOUNDS</p><Maximize2 className="size-3 text-zinc-600" /></div><div className="mt-3 grid grid-cols-3 gap-2">{stats.dimensions.map((value, index) => <div key={index}><p className="micro-label">{['X', 'Y', 'Z'][index]}</p><p className="mt-1 font-mono text-xs">{value.toFixed(value >= 100 ? 0 : 2)}</p></div>)}</div><p className="mt-2 text-[9px] text-zinc-600">Scene units are interpreted, not guaranteed physical units.</p></div>
                <div className="data-block"><div className="flex items-center justify-between"><p className="eyebrow">QUICK VERDICT</p><ScanSearch className="size-3 text-primary" /></div><p className="mt-3 text-xs leading-relaxed text-zinc-400">{severity === 'pass' ? 'No blocking issues detected by the implemented browser checks.' : severity === 'warning' ? 'The asset renders, but one or more delivery assumptions need review.' : 'A blocking structural problem was detected.'}</p><p className="mt-2 text-[9px] leading-relaxed text-zinc-600">PASS covers implemented rules only. It is not artistic approval.</p></div>
              </div></section>}
            {activeTab === 'scene' && <section role="tabpanel" className="h-[calc(100vh-198px)] overflow-y-auto"><div className="p-3">
                <div className="mb-2 flex items-center justify-between px-1"><p className="eyebrow">SCENE GRAPH</p><span className="micro-label">{sceneNodes.length} SHOWN</span></div>
                {sceneNodes.map((node, index) => <div key={`${node.name}-${index}`} className="scene-row" style={{ paddingLeft: `${8 + Math.min(node.depth, 5) * 14}px` }}><span className="tree-line" /><span className="scene-icon">{node.type.includes('Mesh') ? <Triangle /> : node.type.includes('Point') ? <Sparkles /> : <Box />}</span><span className="min-w-0"><span className="block truncate text-[11px] text-zinc-300">{node.name}</span><span className="block font-mono text-[8px] uppercase text-zinc-600">{node.type}</span></span></div>)}
              </div></section>}
            {activeTab === 'checks' && <section role="tabpanel" className="h-[calc(100vh-198px)] overflow-y-auto"><div className="p-3">
                <div className="mb-2 flex items-center justify-between px-1"><p className="eyebrow">AUTOMATED CHECKS</p><span className="micro-label">{issues.length} RESULTS</span></div>
                <div className="space-y-1.5">{issues.map((issue, index) => <div key={`${issue.title}-${index}`} className={`issue-card issue-${issue.level}`}><span className="issue-icon">{issueIcon(issue.level)}</span><div><p className="text-[11px] font-medium text-zinc-200">{issue.title}</p><p className="mt-1 text-[10px] leading-relaxed text-zinc-500">{issue.detail}</p></div></div>)}</div>
                <div className="mt-3 rounded-md border border-white/6 bg-black/15 p-3"><p className="font-mono text-[9px] text-zinc-500">NOT CHECKED YET</p><p className="mt-1.5 text-[10px] leading-relaxed text-zinc-600">Self-intersection, UV overlap, visual equivalence, shader intent and source-file constraints.</p></div>
              </div></section>}
          </div>
        </aside>
      </section>

      <footer className="status-bar">
        <div className="flex min-w-0 items-center gap-2"><span className={`status-dot status-${severity}`} /><span className="truncate">{message}</span></div>
        <div className="hidden items-center gap-5 sm:flex"><span>WebGL 2</span><span>{formatCount(stats.triangles)} TRI</span><span>{formatCount(stats.vertices)} {stats.format.includes('3DGS') ? 'SPLATS' : 'VTX'}</span></div>
      </footer>
    </main>
  );
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="metric-card"><span className="metric-icon">{icon}</span><div><p className="micro-label">{label}</p><p className="mt-1 text-base font-medium tabular-nums">{value}</p></div></div>;
}

