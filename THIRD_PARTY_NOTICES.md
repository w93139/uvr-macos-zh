# 来源与第三方许可

## Ultimate Vocal Remover

- 项目：https://github.com/Anjok07/ultimatevocalremovergui
- 被适配的应用：官方 v5.6 arm64 DMG；兼容性由 README 所列可执行文件 SHA-256 限定。
- 源码参考快照：`4e2f28e02f0c2d69d926facd0186a379bb7799ac`。
- 上游声明：MIT；`gui_data/constants.py` 包含 `Copyright (c) 2022 Ultimate Vocal Remover` 和 MIT 全文。本项目 LICENSE 保留其归属及许可文本。
- 本仓库不重新分发 UVR 原程序、图标、模型或原归档；安装器在用户已经安装的副本上工作。

## 社区中文文本参考

- https://github.com/jensenli-cn/Ultimate-Vocal-Removergui-
  - 检查快照：`158b97231e343366b6120fa3ec3c4d6222d3e9dc`。
- https://github.com/taozhiyu/ultimatevocalremovergui_zh
  - 检查快照：`d09695dde36aeeb8fd826b2ed6a7169964d2ffad`。

这两个项目的 README 声明沿用 UVR 的 MIT 许可。翻译词汇经过精确匹配、术语修订与新增；感谢上述贡献者。未复制或运行它们的 Windows 加载器、模糊匹配逻辑、`.pyc` 或原生库。

## PyInstaller

- https://github.com/pyinstaller/pyinstaller
- 安装器通过依赖调用其官方 Mach-O 修正与 UUID 更新工具，不在仓库内复制实现。
- PyInstaller 的许可及 bootloader 例外由上游提供：https://pyinstaller.org/en/stable/license.html 。本项目不分发新的 bootloader 或 UVR 可执行文件。
