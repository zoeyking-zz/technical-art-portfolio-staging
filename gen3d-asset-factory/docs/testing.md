# 测试记录

版本 0.2.0。测试环境为 Windows、Blender 5.2.1 LTS 和内置 Python 3.13.13。

2026-09-13 在待发布目录中重新运行，两组测试均正常退出，安装包校验通过。[本次断言结果](test-results.json)保留了检查名称，去除了本机路径。运行中有 Blender 缩略图写入和内置资源相对路径警告；预览图仍正常生成。

## 运行

在仓库顶层的 `gen3d-asset-factory` 目录执行下列命令。Windows 中如果 Blender 不在 PATH 内，用 `& '本机的 blender.exe 路径'` 替换命令开头的 `blender`。

```sh
blender --background --factory-startup --python-exit-code 1 --python scripts/test_gen3d_blender.py
blender --background --factory-startup --python-exit-code 1 --python scripts/test_gen3d_delivery.py
python scripts/build_gen3d.py
blender --command extension validate Gen3D_build/gen3d_factory-0.2.0.zip
```

脚本失败时返回非零退出码。检查测试的汇总位于 `Gen3D_build/test_summary.json`，交付测试的汇总位于 `Gen3D_build/delivery_tests/test_summary.json`。报告中可能包含本机路径，公开前需要检查。

## 覆盖范围

`test_gen3d_blender.py` 默认执行 27 项断言，覆盖演示生成、预期缺陷、边界与平铺 UV 配置、缺失和不支持的 PLY、合成高斯数据、报告转义、GLB 往返，以及插件注销后重新注册。

`test_gen3d_delivery.py` 执行 32 项断言，覆盖命名冲突、原件保护、阻止不合格输入、图片嵌入、静态父级与镜像缩放，以及两条故障路径：导出函数抛出异常，重新导入后的顶点被人为移动。失败后检查临时数据清理和源场景恢复。

这些数字是脚本断言数，不是独立真实资产数量，也不是覆盖率。一次完整运行必须同时满足脚本汇总通过和进程正常退出；检查脚本在末尾还会渲染预览图。

## 外部 PLY

默认只使用合成高斯样本。可通过环境变量 `GEN3D_TEST_PLY_DIR` 指定自己的目录。配置了不存在或空的目录会直接失败；未配置时，外部数据分支标记为 SKIPPED。

外部数据分支检查报告是否覆盖全部输入、扫描是否保持文件内容不变，以及是否错误套用了 UV 规则。它不会把所有输入都要求为 PASS，也不代表完成了数据集质量评估。科研数据不随项目分发。

## 尚未验证

- 真实 AIGC 模型上的误报和漏报。
- 材质参数、纹理像素和固定灯光渲染的一致性。
- 大批量资产的耗时、内存占用及主线程阻塞情况。
- 其他 Blender 版本、操作系统和复杂材质节点。

目前的截图和统计用于说明工具行为，不用于声称美术质量提升或生产效率提升。
