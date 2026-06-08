#!/usr/bin/env python3
"""
============================================================================
  appimage-shortcut — 为 .AppImage 文件创建桌面快捷方式
  (基于 Linux 下 AppImage 桌面集成的通用实践)

  用法:
    ./appimage-shortcut.py <AppImage 文件> [选项]

  选项:
    --name <名称>         自定义菜单中显示的名称（默认取自文件名）
    --icon <图标文件>     手动指定图标路径（.png / .svg）
    --category <类别>     桌面分类，如 Network;Office;Development;Game;
                         默认 Utility; （参考 "Desktop Menu Specification"）
    --no-move             不把 AppImage 移动到 ~/Applications/
    --terminal            启动时显示终端窗口
    --comment <描述>      菜单提示文字
    --system              安装到 /usr/share/ （需要 sudo），而非 ~/.local/share/
    --extract-icon        从 AppImage 中提取图标（自动）
    --dry-run             仅预览 .desktop 文件内容，不执行安装
    --remove              删除已安装的快捷方式（可配合 --name 指定名称，或传入 AppImage 自动推断）

  删除快捷方式:
    ./appimage-shortcut.py --remove --name Obsidian
    ./appimage-shortcut.py --remove Obsidian-1.8.9.AppImage
    ./appimage-shortcut.py --remove Slack --system   # 删除系统级快捷方式

  示例:
    ./appimage-shortcut.py Obsidian-1.8.9.AppImage
    ./appimage-shortcut.py Slack-4.33.90.AppImage --name Slack --category Network; --extract-icon
    ./appimage-shortcut.py ./downloads/MyApp.AppImage --no-move --dry-run
============================================================================
"""

import os
import sys
import shutil
import stat
import subprocess
import argparse
import tempfile
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="[%(levelname)s] %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("appimage-shortcut")

# ---------------------------------------------------------------------------
# 标准路径
# ---------------------------------------------------------------------------
XDG_DATA_HOME = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
APPLICATIONS_DIR = XDG_DATA_HOME / "applications"
ICONS_DIR = XDG_DATA_HOME / "icons" / "hicolor"
APPS_DIR = Path.home() / "Applications"

SYSTEM_APPLICATIONS_DIR = Path("/usr/share/applications")
SYSTEM_ICONS_DIR = Path("/usr/share/icons/hicolor")


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
def ensure_dir(path: Path) -> Path:
    """确保目录存在，返回该路径"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_executable(path: Path) -> None:
    """给文件添加可执行权限"""
    st = path.stat()
    if not (st.st_mode & stat.S_IXUSR):
        path.chmod(st.st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        log.info(f"已赋予可执行权限: {path}")


def sanitize_name(name: str) -> str:
    """清理名称，移除非法字符"""
    # 去掉 .AppImage 后缀
    for suffix in [".appimage", ".AppImage", ".appimg", ".AppImg"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    # 保留字母、数字、空格、中划线、下划线
    safe = "".join(c if c.isalnum() or c in " -_.+" else "_" for c in name)
    return safe.strip()


def extract_appimage_icon(appimage_path: Path, dest_dir: Path) -> Path | None:
    """
    使用 --appimage-extract 从 AppImage 中提取图标。
    返回找到的最佳图标路径，或 None。
    """
    log.info("正在从 AppImage 提取图标 ...")
    with tempfile.TemporaryDirectory(prefix="appimage-extract-") as tmpdir:
        extract_dir = Path(tmpdir) / "squashfs-root"
        try:
            subprocess.run(
                [str(appimage_path), "--appimage-extract"],
                cwd=tmpdir,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
            log.warning(f"提取失败: {e}")
            return None

        if not extract_dir.is_dir():
            # 尝试找任意子目录
            items = list(Path(tmpdir).iterdir())
            if items:
                extract_dir = items[0] if items[0].is_dir() else None
            if not extract_dir:
                log.warning("提取后未找到目录结构")
                return None

        # 常见的图标文件名
        icon_candidates = [
            "*.png",
            "*.svg",
            "*.xpm",
        ]
        found_icons: list[Path] = []
        for pattern in icon_candidates:
            found_icons.extend(extract_dir.rglob(pattern))

        # 按分辨率排序（优先高分辨率），或优先名为 .DirIcon 的文件
        dir_icon = extract_dir / ".DirIcon"
        if dir_icon.is_file():
            found_icons.insert(0, dir_icon)

        if not found_icons:
            log.warning("提取后未发现图标文件")
            return None

        # 选择最佳图标（优先 256x256 或更大，若为 PNG）
        best = found_icons[0]
        best_size = 0
        for icon_path in found_icons:
            if icon_path.suffix == ".png":
                # 尝试从文件名中猜测尺寸，如 "icon_128.png"、"256.png"
                name = icon_path.stem
                for part in name.replace("_", " ").replace("-", " ").split():
                    if part.isdigit():
                        size = int(part)
                        if 16 <= size <= 512 and size > best_size:
                            best_size = size
                            best = icon_path
                            break
                # 也可以用 `file` 命令或 `identify`，但这里简化处理
            elif icon_path.suffix == ".svg":
                # SVG 矢量图视为最佳
                if best.suffix != ".svg":
                    best = icon_path

        # 复制到目标目录
        ext = best.suffix.lower()
        if ext == ".png":
            icon_dest = dest_dir / "apps" / "256" / f"{best.stem}.png"
        elif ext == ".svg":
            icon_dest = dest_dir / "scalable" / "apps" / f"{best.stem}.svg"
        else:
            icon_dest = dest_dir / "apps" / "256" / best.name

        ensure_dir(icon_dest.parent)
        shutil.copy2(best, icon_dest)
        log.info(f"图标已提取并安装: {icon_dest}")
        return icon_dest

    return None


def create_desktop_content(
    exec_path: str,
    name: str,
    icon_path: str = "",
    comment: str = "",
    categories: str = "Utility;",
    terminal: bool = False,
) -> str:
    """生成 .desktop 文件内容"""
    lines = [
        "[Desktop Entry]",
        "Type=Application",
        f"Name={name}",
        f"Exec={exec_path}",
        f"Icon={icon_path}" if icon_path else "Icon=application-x-executable",
        f"Comment={comment}" if comment else "",
        "Terminal=true" if terminal else "Terminal=false",
        f"Categories={categories}",
        "X-AppImage-Version=1.0",
        "",
    ]
    return "\n".join(line for line in lines if line)


def _parse_desktop_icon(desktop_path: Path) -> str | None:
    """从 .desktop 文件中提取 Icon= 的值"""
    try:
        for line in desktop_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("Icon="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def _guess_icon_files(icon_name: str, icons_base: Path) -> list[Path]:
    """
    根据图标名称（无扩展名）猜测可能安装的图标文件路径。
    搜索 apps/ 下各子目录中的匹配文件。
    """
    found: list[Path] = []
    apps_dir = icons_base / "apps"
    if not apps_dir.is_dir():
        return found
    for size_dir in apps_dir.iterdir():
        if size_dir.is_dir():
            for f in size_dir.iterdir():
                if f.stem == icon_name:
                    found.append(f)
    # 也搜索 scalable/apps/
    scalable = icons_base / "scalable" / "apps"
    if scalable.is_dir():
        for f in scalable.iterdir():
            if f.stem == icon_name:
                found.append(f)
    return found


def _cleanup_empty_dirs(path: Path) -> None:
    """递归删除空目录（不会删除根级目录）"""
    try:
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()
            log.debug(f"已删除空目录: {path}")
            # 继续向上清理
            _cleanup_empty_dirs(path.parent)
    except (PermissionError, OSError):
        pass


def remove_shortcut(
    name: str,
    *,
    system: bool = False,
    dry_run: bool = False,
) -> int:
    """
    删除指定名称的 .desktop 快捷方式及其关联图标。
    返回 0 表示成功，1 表示未找到。
    """
    if system:
        apps_dir = SYSTEM_APPLICATIONS_DIR
        icons_base = SYSTEM_ICONS_DIR
        prefix = "系统"
    else:
        apps_dir = APPLICATIONS_DIR
        icons_base = ICONS_DIR
        prefix = "用户"

    # 查找 .desktop 文件（精确匹配或带编号的后备匹配）
    desktop_files: list[Path] = []
    # 精确匹配
    exact = apps_dir / f"{name}.desktop"
    if exact.is_file():
        desktop_files.append(exact)
    else:
        # 模糊匹配：{name}-数字.desktop
        for f in apps_dir.glob(f"{name}-*.desktop"):
            desktop_files.append(f)

    if not desktop_files:
        log.error(f"未找到 {prefix}快捷方式「{name}」(.desktop 文件)")
        return 1

    desktop_file = desktop_files[0]
    if len(desktop_files) > 1:
        log.info(f"找到多个匹配，将删除第一个: {desktop_file}")

    # 读取图标信息
    icon_name = _parse_desktop_icon(desktop_file)
    icon_files: list[Path] = []
    if icon_name and not icon_name.startswith("/") and icon_name != "application-x-executable":
        icon_files = _guess_icon_files(icon_name, icons_base)

    # ---- 执行删除 ----
    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"  [DRY RUN] 将删除以下文件")
        print(f"{'=' * 60}")
        print(f"  📄 {desktop_file}")
        for ic in icon_files:
            print(f"  🖼  {ic}")
        print(f"{'=' * 60}\n")
        return 0

    # 删除 .desktop 文件
    desktop_file.unlink()
    log.info(f"已删除快捷方式: {desktop_file}")

    # 删除关联图标
    for ic in icon_files:
        try:
            ic.unlink()
            log.info(f"已删除图标: {ic}")
            # 尝试删除空父目录
            _cleanup_empty_dirs(ic.parent)
        except FileNotFoundError:
            pass

    # 更新桌面数据库
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            capture_output=True,
            timeout=30,
        )
    except FileNotFoundError:
        log.warning("未找到 update-desktop-database 命令（不影响功能）")
    except subprocess.TimeoutExpired:
        pass

    print()
    print(f"  ✔ 快捷方式「{name}」已删除！")
    print(f"  📄 删除: {desktop_file}")
    if icon_files:
        print(f"  🖼  删除: {len(icon_files)} 个图标文件")
    print()

    return 0


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(
        description="为 .AppImage 文件创建桌面快捷方式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("appimage", type=str, nargs="?", default=None,
                        help="AppImage 文件路径（--remove 模式可选）")
    parser.add_argument("--name", type=str, default=None, help="菜单显示名称")
    parser.add_argument("--icon", type=str, default=None, help="图标文件路径")
    parser.add_argument("--category", type=str, default="Utility;", help="桌面分类")
    parser.add_argument("--no-move", action="store_true", help="不要将 AppImage 移动到 ~/Applications/")
    parser.add_argument("--terminal", action="store_true", help="运行时显示终端")
    parser.add_argument("--comment", type=str, default="", help="备注描述")
    parser.add_argument("--system", action="store_true", help="安装到系统目录（需 sudo）")
    parser.add_argument("--extract-icon", action="store_true", help="从 AppImage 自动提取图标")
    parser.add_argument("--dry-run", action="store_true", help="仅预览 .desktop 内容")
    parser.add_argument("--remove", action="store_true", help="删除已安装的快捷方式")

    args = parser.parse_args()

    # ---- 删除模式 ----
    if args.remove:
        if not args.name and not args.appimage:
            log.error("使用 --remove 时需要指定 --name 或 AppImage 文件路径")
            return 1
        display_name = args.name or sanitize_name(Path(args.appimage).stem)
        return remove_shortcut(display_name, system=args.system, dry_run=args.dry_run)

    # ---- 校验 AppImage 文件 ----
    appimage = Path(args.appimage).resolve()
    if not appimage.is_file():
        log.error(f"文件不存在: {appimage}")
        return 1

    # 检查是否为 ELF / AppImage（通过 magic bytes 简单判断）
    with open(appimage, "rb") as f:
        magic = f.read(4)
    if magic[:4] != b"\x7fELF":
        log.warning("文件头部不是 ELF 格式，可能不是有效的 AppImage")

    # ---- 确定目标路径 ----
    if args.system:
        apps_dir = SYSTEM_APPLICATIONS_DIR
        icons_base = SYSTEM_ICONS_DIR
        prefix = "系统"
    else:
        apps_dir = APPLICATIONS_DIR
        icons_base = ICONS_DIR
        prefix = "用户"

    # ---- 处理 AppImage 文件位置 ----
    if not args.no_move and not args.system:
        # 将 AppImage 移动到 ~/Applications/
        ensure_dir(APPS_DIR)
        target_appimage = APPS_DIR / appimage.name

        if target_appimage.exists():
            log.warning(f"目标位置已存在: {target_appimage}，跳过移动")
        elif appimage.parent == APPS_DIR:
            target_appimage = appimage
            log.info("AppImage 已在 ~/Applications/ 中")
        else:
            log.info(f"移动 AppImage 到 {target_appimage} ...")
            shutil.copy2(appimage, target_appimage)
            log.info(f"已复制（原始文件保留）: {target_appimage}")
            # 如果用户想删除原文件，可以提示
            log.info("提示: 原始文件仍保留，可手动删除。")

        make_executable(target_appimage)
        exec_path = str(target_appimage)
    else:
        make_executable(appimage)
        exec_path = str(appimage)

    # ---- 确定显示名称 ----
    display_name = args.name or sanitize_name(appimage.stem)

    # ---- 提取 / 解析图标 ----
    icon_path_str = ""

    if args.icon:
        # 用户手动指定图标
        icon_file = Path(args.icon)
        if icon_file.is_file():
            if args.system:
                icon_dest = icons_base / "scalable" / "apps" / icon_file.name
            else:
                icon_dest = icons_base / "scalable" / "apps" / icon_file.name
            ensure_dir(icon_dest.parent)
            shutil.copy2(icon_file, icon_dest)
            icon_path_str = str(icon_dest)
            log.info(f"自定义图标已安装: {icon_dest}")
        else:
            log.warning(f"指定的图标文件不存在: {icon_file}")

    elif args.extract_icon and not args.dry_run:
        icon_extracted = extract_appimage_icon(appimage, icons_base)
        if icon_extracted:
            # .desktop 的 Icon= 字段使用不带扩展名的名称
            icon_path_str = icon_extracted.stem
            log.info(f"图标提取完成: {icon_extracted}")

    # ---- 生成 .desktop 文件 ----
    desktop_content = create_desktop_content(
        exec_path=exec_path,
        name=display_name,
        icon_path=icon_path_str,
        comment=args.comment,
        categories=args.category,
        terminal=args.terminal,
    )

    if args.dry_run:
        print("\n" + "=" * 60)
        print(f"  [DRY RUN] 预览 .desktop 文件内容")
        print("=" * 60)
        print(desktop_content)
        print("=" * 60)
        return 0

    # ---- 写入 .desktop 文件 ----
    ensure_dir(apps_dir)
    desktop_file = apps_dir / f"{display_name}.desktop"

    # 防止重名冲突
    counter = 1
    while desktop_file.exists():
        desktop_file = apps_dir / f"{display_name}-{counter}.desktop"
        counter += 1

    desktop_file.write_text(desktop_content, encoding="utf-8")
    desktop_file.chmod(0o755)
    log.info(f"{prefix}快捷方式已创建: {desktop_file}")

    # ---- 更新桌面数据库 ----
    try:
        subprocess.run(
            ["update-desktop-database", str(apps_dir)],
            capture_output=True,
            timeout=30,
        )
    except FileNotFoundError:
        log.warning("未找到 update-desktop-database 命令（不影响功能）")
    except subprocess.TimeoutExpired:
        pass

    print()
    print(f"  ✔ 完成！在应用程序菜单中搜索「{display_name}」即可启动。")
    print(f"  📄 .desktop 文件: {desktop_file}")
    if icon_path_str:
        print(f"  🖼  图标: {icon_path_str}")
    print(f"  🚀 可执行文件: {exec_path}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
