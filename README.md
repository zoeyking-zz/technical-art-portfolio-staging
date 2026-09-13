# Technical Art & Real-Time Graphics — Selected Work

个人技术美术、角色动画工具与实时图形作品集。近期项目放在仓库顶层，本科及早期项目统一收录于 [early-projects](early-projects/)。

## 近期项目

| 项目 | 内容 | 入口 |
|---|---|---|
| [Gen3D Asset Factory](gen3d-asset-factory/) | Blender 静态资产检查、规范命名、GLB 导出与重新导入核对；0.2.0 预览版 | [安装包](gen3d-asset-factory/dist/gen3d_factory-0.2.0.zip) · [测试记录](gen3d-asset-factory/docs/testing.md) |

## 本科与早期项目

| 项目 | 技术关键词 | 当前材料 | 状态 |
|---|---|---|---|
| [古堡逃杀](early-projects/castle-escape/) | Unity、C#、角色交互、UI、氛围表现 | [Windows 历史成品下载](https://github.com/zoeyking-zz/technical-art-portfolio-staging/releases/tag/castle-escape-archive-2026-09-14) | 包含开始界面和主游戏；尚未找回原始 Unity 工程 |
| [Blender 实时动捕与虚拟角色工具](early-projects/blender-realtime-mocap/) | Blender、Python、Motion Capture、Facial Animation | 案例说明、演示关键画面；完整视频可按需提供 | 可作为案例展示；源码已无法找回 |
| [Unity 布料模拟](early-projects/unity-cloth-simulation/) | Unity、C#、Mesh、Constraint、Collision、Shader | 核心脚本与 Shader | 代码样本；场景与贴图未公开 |
| [OpenGL 光照与相机交互](early-projects/opengl-lighting-demo/) | C++、OpenGL、GLSL、Phong、GLFW、GLEW | 源码、Shader、GIF | 早期课程项目；依赖与贴图未打包 |

## 文件组织

```text
technical-art-portfolio-staging/
├── README.md
├── gen3d-asset-factory/       # 近期项目：源码、文档、安装包与演示
├── early-projects/           # 本科及早期作品统一归档
│   ├── README.md
│   ├── castle-escape/
│   ├── blender-realtime-mocap/
│   ├── unity-cloth-simulation/
│   └── opengl-lighting-demo/
└── PUBLICATION_CHECKLIST.md
```

新做的项目直接添加到仓库顶层，每个项目自带 README、代码、演示和使用说明。大型游戏成品通过 Releases 下载，仓库保留项目介绍及文件校验清单。目录调整于 2026-09-14 完成；原 `projects/...` 路径已迁移至上述位置。

## 说明

- 早期项目用于展示技术积累，不代表当前全部专业能力。
- Gen3D Asset Factory 保留其目录内的 GPL-3.0-or-later 许可证；该许可不适用于其他项目。
- 《古堡逃杀》发布的是保留必要 Unity 运行依赖的历史成品，未包含编译备份、调试符号，也不声称是可编辑源码工程。
- Blender 项目历史记录中的性能数字来自项目当时的测试与复盘；由于原工程已遗失，目前无法重新运行验证。
- 演示中的第三方角色、场景和动作素材只用于说明技术流程，不作为个人创作成果主张。
- 本仓库未附统一开源许可证。除非子项目另有说明，内容仅供作品展示，不授予复制、修改或再分发许可。第三方引擎、库和美术素材的权利归原权利人。

## Portfolio Case Study 结构

每个项目尽量按以下结构呈现：

1. 项目目标与问题背景；
2. 个人贡献与技术方案；
3. 可查看的演示或源码；
4. 已知限制与后续改进方向。
