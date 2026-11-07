# UVR 5.6 macOS 简体中文补丁

为官方 **Ultimate Vocal Remover 5.6 Apple Silicon 桌面版**生成独立的简体中文副本，保留英文原版。

这是非官方的界面本地化项目，不提供分离算法、模型训练、音色克隆或 UVR 原应用下载镜像。

## 做了什么

- 翻译主界面、设置、下载中心、高级选项和常用提示中的显示文本。
- 动态按钮使用单向显示代理：界面显示中文，原始变量仍保留英文。
- 保留全部原始 PyInstaller 归档成员的字节，只在主脚本前增加显示层 hook。
- 不翻译模型文件名、下拉框内部值、数值参数、输入输出路径及配置标识。
- 检查官方可执行文件的 SHA-256，仅处理已经验证的构建。
- 生成不同名称、bundle ID 和 Mach-O UUID 的中文副本，并进行本地 ad-hoc 签名。

## 兼容范围

| 项目 | 当前范围 |
|---|---|
| 系统 | Apple Silicon macOS；当前实测 macOS 27.2 |
| 应用 | 官方 UVR v5.6 的 `Ultimate_Vocal_Remover_v5_6_MacOS_arm64.dmg` |
| 原可执行文件 SHA-256 | `aaf8f36737d698af6d536a88d9072682d51b4099c267ea72373958768adfbb16` |
| 补丁安装环境 | Python 3.11；PyInstaller 6.22.3 |
| 英文原版 | 保留，不覆盖 |
| Intel / Windows / 新 Beta / 其他打包版本 | 本版本不声明支持；校验不匹配会停止 |

文件名相同也可能被上游更新；以 SHA-256 校验为准。补丁不取消这个保护。

## 安装

1. 从 [UVR 官方发布页](https://github.com/Anjok07/ultimatevocalremovergui/releases/tag/v5.6)下载安装 arm64 正式版，放到“应用程序”。
2. 安装 Python 3.11 和 [uv](https://docs.astral.sh/uv/getting-started/installation/)，或使用已有的 Python 3.11 虚拟环境。
3. 克隆本仓库并运行：

```sh
git clone https://github.com/w93139/uvr-macos-zh.git
cd uvr-macos-zh
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python .
.venv/bin/uvr-macos-zh --check
.venv/bin/uvr-macos-zh
```

之后在“应用程序”中双击 **Ultimate Vocal Remover 中文版**。

也可以指定原版和新副本的位置：

```sh
.venv/bin/uvr-macos-zh \
  --source '/Applications/Ultimate Vocal Remover.app' \
  --destination '/Applications/Ultimate Vocal Remover 中文版.app'
```

目标已存在时不会覆盖。安装器先检查兼容性，在临时目录中复制和签名，通过检查后才放到目标位置。

本项目没有 Apple Developer ID 签名或公证。仅为你本机的副本做 ad-hoc 签名；不要求关闭 Gatekeeper，也不会更改系统安全设置。

## 使用与恢复

| 界面 | 用途 |
|---|---|
| 选择音频 | 选择要分离的本地歌曲 |
| 输出文件夹 | 设置保存位置 |
| 选择 MDX-Net 模型 | 选择已安装的模型 |
| 开始分离 | 开始处理并显示进度 |

`MDX-Net`、`Demucs`、模型名称以及下拉选项中的一些英文保持原样，以保证参数和配置兼容。无法精确匹配的动态长提示会回退英文。

恢复英文界面只需退出中文版并打开原版。卸载中文副本前，请先把其应用包内新下载的模型或设置备份到自己的文件夹；本项目不会自动删除它们。

## 验证与开发

```sh
uv pip install --python .venv/bin/python '.[test]'
.venv/bin/python -m pytest -q
```

测试覆盖归档完整性、未知版本拒绝、目标不覆盖、显示代理更新与清理，以及真实 Tk 控件的变量、模型名、路径和回调保持。实际应用的签名、显示与音频处理结果另见 [验证记录](VALIDATION.md)。

本仓库不包含官方 App、可执行文件、模型权重、个人音频、`data.pkl` 或任何登录凭据。

## 为什么不直接安装旧汉化

检查过的社区汉化基于 5.5.1，其中一套依赖 Windows 专用模块，另一套附带 Intel TkDND 组件；旧 `separate.py` 也没有当前 5.6 的 MDX23C 实现。直接替换源码既不能覆盖 Mac 冻结包，又可能回退功能。

本项目参考它们的中文词汇，重新维护精确显示文本映射，不执行旧汉化代码、不打包旧二进制。来源与许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 许可

本项目新增代码按 MIT 许可发布。UVR、PyInstaller 和模型各自的版权与许可保持不变；本项目与上游没有隶属或官方背书关系。
