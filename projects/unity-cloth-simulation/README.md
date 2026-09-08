# Unity 布料模拟

## 项目概述

Unity/C# 网格变形课程项目。代码从三角面索引中提取并去重网格边，根据初始边长进行应变限制，同时维护顶点速度、固定点和球体碰撞，逐帧更新 Mesh 并重算法线。

## 核心实现

- 从 Triangle Index 构建唯一 Edge List；
- 记录每条边的 Rest Length；
- 使用约束迭代限制布料拉伸；
- 使用速度、阻尼和重力更新顶点；
- 处理布料顶点与球体的碰撞；
- 双面 Lambert Surface Shader。

## 代码

- [`cloth_motion.cs`](Assets/Scripts/cloth_motion.cs)：布料约束、速度更新和碰撞处理；
- [`sphere_motion.cs`](Assets/Scripts/sphere_motion.cs)：鼠标拖动球体与旋转摄影机；
- [`cloth_shader.shader`](Assets/Shaders/cloth_shader.shader)：双面布料材质 Shader。

## 当前限制

- 当前仅保留核心代码，没有完整 Unity 工程；
- 原实现包含固定顶点数量和固定固定点等硬编码；
- 场景、材质和贴图未公开，避免发布授权来源不明确的素材；
- 在确认课程/教程引用范围前，不把该项目描述为完全原创算法。

## 后续改进

- 重建最小可运行 Unity 工程和参数控制面板；
- 将固定点、质量、阻尼、重力和迭代次数参数化；
- 增加不同网格分辨率下的 FPS、稳定性与碰撞测试；
- 录制包含参数对比的 30–60 秒技术演示。


