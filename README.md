# Minecraft 存档打包与导入工具

<!-- AUTO-README:START -->

[![release](https://img.shields.io/github/v/release/dcajusteno-ops/minecraft-world-archive-save-tool?sort=semver&label=release)](https://github.com/dcajusteno-ops/minecraft-world-archive-save-tool/releases) [![last commit](https://img.shields.io/github/last-commit/dcajusteno-ops/minecraft-world-archive-save-tool)](https://github.com/dcajusteno-ops/minecraft-world-archive-save-tool/commits)

带图形界面的 Minecraft 存档辅助工具：一键打包导出存档、批量导入，并在不同游戏版本之间迁移 mods、配置与存档。

> 当前版本：v0.2

## 技术栈

- 语言：Python（100.0%）

## 目录结构

```text
.gitignore
mc_archiver.py
mc_archiver.spec
README.md
```

## License

尚未声明许可证。

<!-- AUTO-README:END -->

## 核心功能

- **扫描与打包**：自动扫描 `.minecraft` 目录下的所有存档（同时支持全局 `saves` 与多版本隔离目录），把选中的存档打包成 ZIP。
- **一键导入**：把打包好的 ZIP 解压到指定的 `.minecraft` 目录，或某个版本的隔离目录。
- **版本数据迁移**：从旧版本目录把 `mods` / `config` / `saves` / `resourcepacks` / `shaderpacks` 迁移到新版本目录，省去手动复制粘贴，迁移过程带进度条。

## 界面说明

工具基于 Python 标准库自带的 Tkinter 开发，**不需要安装任何第三方依赖**，共三个标签页：

| 标签页 | 作用 |
| --- | --- |
| 打包导出 | 扫描 `.minecraft` 下的存档并打包成 ZIP |
| 一键导入 | 把 ZIP 导入到全局存档或指定版本目录 |
| 版本数据迁移 | 跨版本搬运 mods、配置、存档、资源包、光影 |

## 使用方式

### 直接运行（推荐）

到 [Releases](../../releases) 下载最新的 `mc_archiver.exe`，双击即可运行，无需安装 Python。

> exe 未做代码签名，首次运行时 Windows SmartScreen 可能提示「已保护你的电脑」，点「更多信息 → 仍要运行」即可。

### 从源码运行

需要 Python 3.8 及以上：

```bash
python mc_archiver.py
```

Windows / macOS 的官方安装包已自带 Tkinter，无需额外安装；部分 Linux 发行版需要单独装：

```bash
sudo apt install python3-tk
```

### 打包为 exe

```bash
pip install pyinstaller
python -m PyInstaller mc_archiver.spec --noconfirm
```

产物为 `dist/mc_archiver.exe`（单文件、无控制台窗口）。仓库内的 `dist/mc_archiver.exe` 就是按这种方式打出来的，**修改 `mc_archiver.py` 后记得重新执行上面的命令**，否则源码与二进制会不一致。

## 版本历史

### v0.2

- 修复版本名过长时无法完整显示的问题：
  - 「版本数据迁移」页的版本下拉框改为自适应窗口宽度，不再写死 20 字符；
  - 下拉列表按最长版本名自动撑宽；
  - 下拉框下方新增「完整版本名」回显行，超长版本名会自动换行完整显示；
- 「一键导入」的目标下拉列表同样按最长版本名撑宽。
- 「打包导出」的存档列表新增水平滚动条，长版本名 + 长存档名可横向查看。
- 窗口默认尺寸调整为 760×560，并支持自由缩放。
- `.gitignore` 不再忽略 `mc_archiver.spec`，保证打包过程可复现。

### v0.1

- 首个版本：存档打包导出、一键导入、版本数据迁移。
