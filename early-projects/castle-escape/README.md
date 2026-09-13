# 古堡逃杀｜Unity 本科游戏作品

本科阶段的 Unity 游戏作品。当前公开材料为历史 Windows 成品：开始界面与主游戏分别保留在两个目录中。

## 项目内容

根据个人经历记录，项目涵盖概念设计、原型迭代、功能开发、测试与打包，涉及角色移动、近战与远程攻击、武器切换、简单技能与装备，以及主菜单、血量、背包和设置等 UI；结合动画事件、受击反馈、镜头、音效、光照与粒子营造战斗和场景氛围。

以上为历史工作记录。本次整理没有重新验证全部玩法，也没有把编译产物当作原始 C# 实现。

## 下载与启动

前往 [GitHub Release：Windows 历史成品](https://github.com/zoeyking-zz/technical-art-portfolio-staging/releases/tag/castle-escape-archive-2026-09-14)，下载 `castle-escape-windows-archive.zip`，完整解压后使用。

```text
开始界面工程/
├── 古堡逃杀_开始界面.exe
├── 古堡逃杀_开始界面_Data/
├── UnityPlayer.dll
└── GameAssembly.dll 等运行依赖
主工程/
├── 古堡逃杀.exe
├── 古堡逃杀_Data/
├── UnityPlayer.dll
└── GameAssembly.dll 等运行依赖
```

- 可分别启动开始界面与主游戏的 `.exe`；请保持各自的 `_Data` 目录与 DLL 在原位置。
- 开始界面能否自动跳转至主游戏尚未验证。若不能跳转，可尝试直接打开 `主工程/古堡逃杀.exe`。
- 当前归档未完成在本机的启动、兼容性和完整流程测试，因此不标记为“已验证可运行”。
- 文件体积、SHA-256 与包含内容见 [归档清单](archive-manifest.json)。下载页同时提供 ZIP 的 SHA-256 校验文件。

## 源码状态

2026-09-14 盘点时，提供的目录包含 `.exe`、`UnityPlayer.dll`、`GameAssembly.dll`、`_Data` 运行资源，以及 `BackUpThisFolder_ButDontShipItWithYourGame` 编译备份。未找到 `Assets/`、`Packages/`、`ProjectSettings/` 或原始 `.cs` 文件。

编译备份中的 `il2cppOutput` 是 Unity 转换生成的 C/C++，`Managed` 中的程序集与 `.pdb` 是构建和调试材料；它们不等同于原始 Unity 编辑器工程。本次发布排除了这些备份及调试符号，保留游戏运行所需的文件。

如后续找回包含 `Assets/` 和 `ProjectSettings/` 的工程，可再补充源代码、Unity 版本、依赖、场景及复现说明。现有成品与源码状态分别记录。

## 许可

此作品供求职展示，未附开源许可证。Unity 运行库及第三方美术、音频等素材的权利归原权利人；发布成品不表示这些依赖或素材由本人创作，也不授予单独提取和再分发素材的许可。
