# appimage-shortcut

> 一键为 `.AppImage` 文件创建桌面快捷方式，集成到 Linux 系统应用菜单中。

--- AppImage 是 Linux 下便捷的「零安装」软件包格式，但它不会自动出现在开始菜单或程序启动器里。本工具自动化了整个集成流程：将 AppImage 移动到标准位置、赋予可执行权限、提取图标、生成 `.desktop` 条目、刷新桌面数据库——一步到位。

---

## 功能特性

- ✅ **自动安装** — 将 AppImage 移至 `~/Applications/` 并创建快捷方式
- ✅ **图标提取** — `--extract-icon` 自动从 AppImage 中抽取图标（支持 PNG/SVG）
- ✅ **自定义图标** — `--icon` 手动指定任意图标文件
- ✅ **分类管理** — `--category` 指定应用分类（Network / Office / Development / Game 等）
- ✅ **系统安装** — `--system` 安装到 `/usr/share/`（所有用户可见，需 sudo）
- ✅ **预览模式** — `--dry-run` 仅显示 `.desktop` 内容，不实际安装
- ✅ **保留原文件** — 复制而非移动（`--no-move` 可完全跳过移动步骤）

## 快速开始

### 下载

```bash
wget -O appimage-shortcut.py https://raw.githubusercontent.com/your-repo/appimage-shortcut/main/appimage-shortcut.py
# 或直接克隆仓库
git clone https://github.com/your-repo/appimage-shortcut.git
```

### 基本用法

```bash
chmod +x appimage-shortcut.py

# 为一个 AppImage 创建快捷方式
./appimage-shortcut.py Obsidian-1.8.9.AppImage

# 完成后在应用程序菜单中搜索「Obsidian」即可启动
```

### 常用示例

```bash
# 指定显示名称、分类、自动提取图标
./appimage-shortcut.py Slack-4.33.90.AppImage \
    --name Slack \
    --category Network; \
    --extract-icon

# 保留 AppImage 在原位置，不移动
./appimage-shortcut.py ~/Downloads/MyApp.AppImage --no-move

# 带终端窗口运行
./appimage-shortcut.py CLI-Tool.AppImage --terminal

# 安装到系统目录（所有用户可见）
sudo ./appimage-shortcut.py TeamViewer.AppImage --system

# 仅预览，不执行任何操作
./appimage-shortcut.py MyApp.AppImage --dry-run
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `appimage` | **（必填）** | AppImage 文件路径 |
| `--name` | 文件名（去后缀） | 应用程序菜单中显示的名称 |
| `--icon` | 自动/默认图标 | 图标文件路径（.png / .svg） |
| `--category` | `Utility;` | 桌面分类，参考 [Desktop Menu Specification](https://specifications.freedesktop.org/menu-spec/latest/) |
| `--comment` | 空 | 菜单中的描述文字 |
| `--extract-icon` | 关闭 | 从 AppImage 中自动提取图标 |
| `--no-move` | 关闭 | 不把 AppImage 移动到 `~/Applications/` |
| `--terminal` | 关闭 | 启动时显示终端窗口 |
| `--system` | 关闭 | 安装到系统目录（需 sudo） |
| `--dry-run` | 关闭 | 仅预览 `.desktop` 内容，不安装 |

### 常用 Category 值

| 值 | 适用场景 |
|----|----------|
| `Utility;` | 工具类应用（默认） |
| `Network;` | 网络通讯类（Slack、Telegram） |
| `Office;` | 办公类（OnlyOffice、LibreOffice） |
| `Development;` | 开发工具（VS Code、IntelliJ） |
| `Graphics;` | 图像处理（GIMP、Inkscape） |
| `AudioVideo;` | 音视频（VLC、OBS） |
| `Game;` | 游戏 |

## 工作流程

```
AppImage 文件
     │
     ├─ ① 复制到 ~/Applications/（除非 --no-move）
     ├─ ② 赋予可执行权限（chmod +x）
     ├─ ③ 提取图标（--extract-icon 时）
     ├─ ④ 生成 .desktop 文件 → ~/.local/share/applications/
     ├─ ⑤ 安装图标 → ~/.local/share/icons/hicolor/
     └─ ⑥ 更新桌面数据库 → 应用菜单立即可见 ✓
```

## 目录结构

```
~/.local/share/
├── applications/
│   └── {Name}.desktop         ← 快捷方式文件
└── icons/hicolor/
    └── apps/
        └── {icon-name}.png    ← 应用图标

~/Applications/
    └── {AppName}.AppImage     ← 集中管理的 AppImage 文件
```

## 常见问题

### 快捷方式没有出现在菜单中？

```bash
# 手动刷新桌面数据库
update-desktop-database ~/.local/share/applications/
# 或重启桌面环境
```

### 如何删除快捷方式？

```bash
rm ~/.local/share/applications/{Name}.desktop
update-desktop-database ~/.local/share/applications/
```

### AppImage 打不开？

```bash
# 安装 FUSE 依赖（Ubuntu/Debian）
sudo apt install libfuse2

# 或使用 --no-move 配合 --dry-run 先测试
```

## 依赖

- **Python 3.6+**（标准库，无需额外安装）
- **FUSE 库** — AppImage 运行时需要（`libfuse2`）
- **`update-desktop-database`** — 可选，用于刷新菜单（通常在 `desktop-file-utils` 包中）

## 许可证

MIT License
