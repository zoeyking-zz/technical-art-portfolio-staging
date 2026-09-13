# Gen3D Asset Factory

Blender 静态资产检查与 GLB 交付插件，当前版本 0.2.0。

开发和测试环境：Windows、Blender 5.2.1 LTS、自带 Python 3.13.13。不需要安装第三方 Python 包或连接在线服务。

## 使用

1. 在 Blender 的 Preferences → Add-ons 中选择 Install from Disk，安装插件 ZIP 并启用。
2. 在 3D Viewport 按 N，打开 Gen3D 面板。
3. 点击 Create Demo Scene，生成工具柜和三个故障方块。扫描结果应为 `17 assets | 3 errors | 0 warnings`。这里按网格对象计数：柜子有 14 个部件。
4. 选择问题行，点击 Select Problem Object 定位对象。修改后重新扫描。
5. 指定 Report folder，点击 Save HTML + JSON Report 保存结果。

也可以先用 Blender 导入自己的模型，在对象模式选中网格后点击 Scan Selected Meshes。

## 导出

只选中需要交付的静态网格。Preview Names 显示副本名称；Export Verified GLB 会重新检查输入，在临时场景中复制对象和网格、规范副本名称、导出 GLB，再重新导入核对。

检查项包括对象验证 ID、三角面数、世界空间包围盒、已使用材质槽数，以及内嵌资源引用。原件不改名；结束时清理临时数据并恢复选区。

- `BLOCKED`：输入不满足交付条件，未导出。
- `FAILED`：导出或复验失败。保留的 `candidate.glb` 只能用于诊断。
- `VERIFIED`：已实施的检查通过，输出 `asset.glb`。
- `VERIFIED_WITH_WARNINGS`：检查通过，但仍有用户接受的警告。

默认阻止普通警告，命名警告可以在副本中处理。勾选允许警告交付不会放行 Error 或不支持的特性。

## PLY 检查

在 PLY file or folder 中填写文件或目录，点击 Inspect PLY Input。目录只扫描当前层的 `.ply`。

支持 vertex-only、little-endian、float32 的 Graphdeco-like 高斯数据。检查字段、数据长度、有限数值、点数、包围盒和零长度旋转参数。其他结构返回 Unsupported；不对高斯数据运行网格 UV 规则。

## 限制

自动修改只涉及副本命名，不会修复拓扑、展开 UV 或替换材质。交付暂限静态网格和简单的 Principled、图片、切线法线、UV 材质路径。修改器、形态键、动画、实例、程序材质、节点组等会阻止交付。

复验不比较材质参数、贴图像素或渲染效果，不能把 VERIFIED 当成视觉验收结论。检查在 Blender 主线程运行，大文件可能使界面暂时无响应。

## 许可证

本插件按 GPL-3.0-or-later 分发，见 LICENSE。演示资产由随附脚本生成，不包含第三方模型和科研数据。代码开发使用了 AI 辅助。
