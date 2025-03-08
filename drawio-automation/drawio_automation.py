import os
import subprocess
import shutil
import argparse
import json
from pathlib import Path
from typing import Optional, List, Union

try:
    with open("config_drawio_migration.json", "r", encoding="utf-8") as f:
        config = json.load(f)
    LATEX_PIC_DIR = config["latex_pic_dir"]
    files_to_copy = config["files_to_copy"]
    # print("Reading config_drawio_migration.json for migration function ...")
    # print("Target Migration Dir: ", LATEX_PIC_DIR)
    # print("Migration Files and Target SubDir:")
    # print(files_to_copy)
except FileNotFoundError:
    LATEX_PIC_DIR = ""
    files_to_copy = []
    print("config_drawio_migration.json not found, which effect migration function.")

# 以下为默认路径，可根据实际情况修改, 或者将其添加到环境变量中(如PDFCROP_PATH)
DRAWIO_EXE_PATH = r"D:\Program Files\draw.io\draw.io.exe"  # draw.io-desktop 的 CLI 路径
GIT_EXE_PATH = "git"  # git 可执行文件路径, 已添加到 PATH 环境变量中
DEBUG = False
EXPORT_JPG_QUALITY = 85  # JPEG 图片质量，范围从 1 到 100


def validate_quality(value):
    ivalue = int(value)
    if ivalue < 1 or ivalue > 100:
        raise argparse.ArgumentTypeError(f"JPEG quality must be between 1 and 100, got {ivalue}")
    return ivalue


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automate Draw.io files workflow: Export .drawio to multiple types. "
                    "Supports batch processing and Git-detected changes.")

    # 输入文件或文件夹
    parser.add_argument("input_path", type=str, help="Input file (.drawio) or folder containing .drawio files")

    # 输出文件或文件夹
    parser.add_argument("output_path", type=str, nargs="?", default="",
                        help="Output file or folder path (default: same as input path)")

    # 导出格式
    parser.add_argument("-x", "--export-types", nargs="+", default=["pdf"],
                        help="Export format (e.g., 'pdf', 'svg', 'png', 'jpg')")

    # Git变更文件处理
    parser.add_argument("-g", "--git-changes", action="store_true",
                        help="Only process .drawio files detected as changed by Git")

    # 是否保持目录结构
    parser.add_argument("-k", "--keep-structure", action="store_true",
                        help="Keep the input folder's relative directory structure in the output folder (only applicable when -b/-g)")

    # 是否迁移到latex工程目录
    parser.add_argument("-m", "--migration", action="store_true",
                        help="Move the generated PDF files to the latex project directory according to config_drawio_migration.json")

    # 导出JPEG质量
    parser.add_argument("-q", "--quality-jpg", type=validate_quality, default=85, help="Export JPEG quality (1-100)")

    # 调试模式（可选）
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode to display additional information during execution")

    return parser.parse_args()


def export_drawio(
    input_file: str,       # 输入的 .drawio 文件路径
    output_file: str,      # 输出的文件路径（支持 PDF、SVG、PNG 等）
    format: Optional[str] = None,  # 导出格式（如 "pdf", "svg", "png" 等）
    scale: Optional[float] = None,  # 导出比例
    border: Optional[int] = None,  # 边框宽度
    quality: Optional[int] = None,  # JPEG 质量（1-100）
    transparent: bool = False,  # 是否设置透明背景（仅 PNG）
    embed_diagram: bool = False,  # 是否嵌入图表副本（仅 PNG、SVG、PDF）
    embed_svg_images: bool = False,  # 是否在 SVG 中嵌入图像（仅 SVG）
    embed_svg_fonts: bool = True,  # 是否在 SVG 中嵌入字体（仅 SVG）
    width: Optional[int] = None,  # 输出宽度（保持宽高比）
    height: Optional[int] = None,  # 输出高度（保持宽高比）
    crop: bool = False,  # 是否裁剪 PDF 到图表大小（仅 PDF）
    all_pages: bool = False,  # 是否导出所有页面（仅 PDF）
    page_index: Optional[int] = None,  # 导出特定页面（默认第一页）
    layers: Optional[List[int]] = None,  # 导出特定图层（逗号分隔的索引）
    page_range: Optional[str] = None,  # 导出页面范围（如 "1..3"，仅 PDF）
    svg_theme: Optional[str] = None,  # SVG 主题（"dark", "light", "auto"）
    svg_links_target: Optional[str] = None,  # SVG 链接目标（"auto", "new-win", "same-win"）
):
    """
    将 .drawio 文件导出为指定格式（PDF、SVG、PNG 等），支持多种导出选项。

    :param drawio_exe_path: draw.io CLI 路径
    :param input_file: 输入的 .drawio 文件路径
    :param output_file: 输出的文件路径
    :param format: 导出格式（如 "pdf", "svg", "png" 等）
    :param scale: 导出比例
    :param border: 边框宽度
    :param quality: JPEG 质量（1-100）
    :param transparent: 是否设置透明背景（仅 PNG）
    :param embed_diagram: 是否嵌入图表副本（仅 PNG、SVG、PDF）
    :param embed_svg_images: 是否在 SVG 中嵌入图像（仅 SVG）
    :param embed_svg_fonts: 是否在 SVG 中嵌入字体（仅 SVG）
    :param width: 输出宽度（保持宽高比）
    :param height: 输出高度（保持宽高比）
    :param crop: 是否裁剪 PDF 到图表大小（仅 PDF）
    :param all_pages: 是否导出所有页面（仅 PDF）
    :param page_index: 导出特定页面（默认第一页）
    :param layers: 导出特定图层（逗号分隔的索引）
    :param page_range: 导出页面范围（如 "1..3"，仅 PDF）
    :param svg_theme: SVG 主题（"dark", "light", "auto"）
    :param svg_links_target: SVG 链接目标（"auto", "new-win", "same-win"）
    """
    # 检查输入文件是否存在
    if not Path(input_file).exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")

    # 构建命令行参数
    command = [DRAWIO_EXE_PATH, "--export", input_file, "--output", output_file]

    # 添加可选参数
    if format:
        command.extend(["--format", format])
    if scale is not None:
        command.extend(["--scale", str(scale)])
    if border is not None:
        command.extend(["--border", str(border)])
    if quality is not None:
        command.extend(["--quality", str(quality)])
    if transparent:
        command.append("--transparent")
    if embed_diagram:
        command.append("--embed-diagram")
    if embed_svg_images:
        command.append("--embed-svg-images")
    if not embed_svg_fonts:
        command.extend(["--embed-svg-fonts", "false"])
    if width is not None:
        command.extend(["--width", str(width)])
    if height is not None:
        command.extend(["--height", str(height)])
    if crop:
        command.append("--crop")
    if all_pages:
        command.append("--all-pages")
    if page_index is not None:
        command.extend(["--page-index", str(page_index)])
    if layers:
        command.extend(["--layers", ",".join(map(str, layers))])
    if page_range:
        command.extend(["--page-range", page_range])
    if svg_theme:
        command.extend(["--svg-theme", svg_theme])
    if svg_links_target:
        command.extend(["--svg-links-target", svg_links_target])

    # 执行导出命令
    try:
        subprocess.run(command, check=True)
        if DEBUG:
            print(f"导出成功: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"导出失败: {e}")
    except FileNotFoundError:
        print(f"未找到 draw.io CLI: {drawio_exe_path}")


def drawio_to_svg(drawio_file, svg_file=""):
    """
    Args:
        drawio_file: Draw.io 文件路径
        svg_file: SVG 文件保存路径, 默认为空. 若为空则保存路径和文件名同 drawio_file
    Description:
        使用 draw.io-desktop 的 CLI 将 .drawio 文件导出为 .svg 文件
    """
    # 转换为绝对路径
    drawio_file = os.path.abspath(drawio_file)
    # 如果svg_file为空，则保存路径和文件名同drawio_file
    if svg_file == "":
        svg_file = os.path.splitext(drawio_file)[0] + ".svg"
    svg_file = os.path.abspath(svg_file)

    svg_dir = os.path.dirname(svg_file)
    if not os.path.exists(svg_dir):
        os.makedirs(svg_dir)

    export_drawio(
        input_file=drawio_file,
        output_file=svg_file,
        format="svg",
        embed_svg_images=True,  # 嵌入图像
        embed_svg_fonts=True,  # 嵌入字体
        svg_theme="light",  # 使用暗色主题
    )


def drawio_to_pdf(drawio_file, pdf_file="", crop=False):
    """
    Args:
        drawio_file: SVG 文件路径
        pdf_file: PDF 文件保存路径, 默认为空. 若为空则保存路径和文件名同 svg_file
        crop: 是否裁剪 PDF
    Description:
        使用 draw.io-desktop 的 CLI 将 .drawio 文件导出为 .pdf 文件
    """
    # 转换为绝对路径
    drawio_file = os.path.abspath(drawio_file)
    # 如果pdf_file为空，则保存路径和文件名同svg_file
    if pdf_file == "":
        pdf_file = os.path.splitext(drawio_file)[0] + ".pdf"
    pdf_file = os.path.abspath(pdf_file)

    # 确保目标文件夹存在
    pdf_dir = os.path.dirname(pdf_file)
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    export_drawio(
        input_file=drawio_file,
        output_file=pdf_file,
        format="pdf",
        crop=crop,  # 裁剪空白区域
    )


def drawio_to_png(drawio_file, png_file=""):
    """
    Args:
        drawio_file: Draw.io 文件路径
        png_file: PNG 文件保存路径, 默认为空. 若为空则保存路径和文件名同 drawio_file
    Description:
        使用 draw.io-desktop 的 CLI 将 .drawio 文件导出为 .png 文件. PNG是无损压缩.
    """
    # 转换为绝对路径
    drawio_file = os.path.abspath(drawio_file)
    # 如果png_file为空，则保存路径和文件名同drawio_file
    if png_file == "":
        png_file = os.path.splitext(drawio_file)[0] + ".png"
    png_file = os.path.abspath(png_file)
    png_dir = os.path.dirname(png_file)
    if not os.path.exists(png_dir):
        os.makedirs(png_dir)

    export_drawio(
        input_file=drawio_file,
        output_file=png_file,
        format="png",
        all_pages=True,  # 导出所有页面
        scale=2,  # 放大两倍
        transparent=True,  # 透明背景
    )


def drawio_to_jpg(drawio_file, jpg_file="", quality=85):
    """
    Args:
        drawio_file: Draw.io 文件路径
        jpg_file: JPG 文件保存路径, 默认为空. 若为空则保存路径和文件名同 drawio_file
        quality: JPG 导出质量, 1-100. JPG 是有损压缩
    Description:
        使用 draw.io-desktop 的 CLI 将 .drawio 文件导出为 .jpg 文件.
    """
    # 转换为绝对路径
    drawio_file = os.path.abspath(drawio_file)
    # 如果jpg_file为空，则保存路径和文件名同drawio_file
    if jpg_file == "":
        jpg_file = os.path.splitext(drawio_file)[0] + ".jpg"
    jpg_file = os.path.abspath(jpg_file)
    jpg_dir = os.path.dirname(jpg_file)
    if not os.path.exists(jpg_dir):
        os.makedirs(jpg_dir)

    export_drawio(
        input_file=drawio_file,
        output_file=jpg_file,
        format="jpg",
        all_pages=True,  # 导出所有页面
        scale=2,  # 放大两倍
        transparent=True,  # 透明背景
        quality=quality,  # JPG 导出质量, 1-100. JPG 是有损压缩
    )


def process_file(drawio_file, output_dir="", keep_structure=False, input_dir="", export_types=None):
    """
    Args:
        drawio_file: 文件全路径
        output_dir: 输出路径
        keep_structure: 是否保持文件结构
        input_dir: 输入路径, drawio_file 的祖先目录
        export_types: 要导出的类型, 支持 svg, pdf, png, jpg
    Description:
        处理单个 .drawio 文件，生成 SVG 和 PDF 文件。
    """
    # 计算输出路径
    if export_types is None:
        export_types = ["pdf", "jpg"]
    if output_dir:
        if keep_structure and input_dir:
            # 保持相对目录结构
            rel_path = os.path.relpath(drawio_file, input_dir)
            base_name = os.path.splitext(os.path.basename(rel_path))[0]
            file_basename = os.path.join(output_dir, os.path.dirname(rel_path), f"{base_name}")
        else:
            # 不保持目录结构
            base_name = os.path.splitext(os.path.basename(drawio_file))[0]
            file_basename = os.path.join(output_dir, f"{base_name}")
    else:
        # 输出路径为空，使用输入文件所在目录
        file_basename = os.path.splitext(drawio_file)[0]

    # 执行转换
    for export_type in export_types:
        if export_type == "svg":
            drawio_to_svg(drawio_file, f"{file_basename}.svg")
        elif export_type == "pdf":
            drawio_to_pdf(drawio_file, f"{file_basename}.pdf", crop=True)
        elif export_type == "png":
            drawio_to_png(drawio_file, f"{file_basename}.png")
        elif export_type == "jpg":
            drawio_to_jpg(drawio_file, f"{file_basename}.jpg", quality=EXPORT_JPG_QUALITY)
        else:
            print(f"Unsupported export type: {export_type}")

    return file_basename  # 文件路径及名称, 但不包括后缀名


def process_folder(input_dir, output_dir="", keep_structure=False, git_changes=False, export_types=None):
    """
    Args:
        input_dir: 输入文件夹
        output_dir: 输出文件夹, 默认为空. 为空则同 input_dir.
        keep_structure: 是否保持文件夹相对结构
        git_changes: 是否只对git检测到变化的 drawio 文件执行导出功能
        export_types: 要导出的类型, 支持 svg, pdf, png, jpg
    Description:
        处理文件夹下的所有 .drawio 文件。
    """
    if DEBUG:
        print(f"\n\033[32mExporting drawio file under {input_dir} to {output_dir} with keep_structure={keep_structure}, export_types={export_types} using git={git_changes}...\033[0m")  # 绿色文本
    if git_changes:
        # 只处理 Git 检测到的变更文件
        modified_files = get_modified_files(input_dir, ["drawio"])
        if len(modified_files) == 0:
            print("No modified drawio files found.")
            return
        for file in modified_files:
            drawio_file = os.path.join(input_dir, file)
            process_file(drawio_file, output_dir, keep_structure, input_dir, export_types)
    else:
        # 处理所有 .drawio 文件
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith(".drawio"):
                    drawio_file = os.path.join(root, file)
                    process_file(drawio_file, output_dir, keep_structure, input_dir, export_types)


def get_modified_files(directory, file_extension=None):
    """
    获取 Git 检测到的变更文件列表。
    """
    if file_extension is None:
        file_extension = ["drawio"]

    original_dir = os.getcwd()
    try:
        # 切换到目标目录
        os.chdir(directory)

        # 调用 git status --porcelain 获取文件状态
        result = subprocess.run(
            [GIT_EXE_PATH, "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 检查命令是否成功执行
        if result.returncode != 0:
            print(f"Error: {result.stderr.strip()}")
            return []

        # 解析结果，提取被修改的文件
        modified_files = []
        for line in result.stdout.splitlines():
            status, file_path = line[:2].strip(), line[3:].strip()
            file_ext = file_path.split(".")[-1] if "." in file_path else ""
            if status in {"M", "A"} and file_ext in file_extension:
                modified_files.append(file_path)

        return modified_files

    finally:
        # 切换回原始目录
        os.chdir(original_dir)


def migrate_folder_to_latex_project(src_folder, latex_folder, file_extensions):
    """
    将 files_to_copy 中指定的文件复制到 latex_folder 目录下。
    """
    if not os.path.exists(latex_folder):
        print(f"Error: Source folder '{latex_folder}' not found.")
        return

    # 构建文件名到文件路径的映射字典
    file_path_map = dict()
    for root, dirs, files in os.walk(src_folder):
        # 跳过隐藏文件夹
        dirs[:] = [d for d in dirs if not d.startswith('.')]

        for file_name in files:
            # 跳过隐藏文件
            if file_name.startswith('.'):
                continue

            # 获取文件的扩展名
            file_ext = os.path.splitext(file_name)[1]  # 获取文件的扩展名
            file_ext = file_ext[1:] if file_ext else ""  # 去掉点号

            # 只记录指定扩展名的文件
            if file_ext in file_extensions:
                if file_name in file_path_map:
                    continue
                file_path_map[file_name] = os.path.join(root, file_name)

    files_missing = []
    # 遍历文件字典并复制文件
    for sub_directory, file_list in files_to_copy.items():
        sub_directory_path = os.path.join(latex_folder, sub_directory)
        if not os.path.exists(sub_directory_path):
            os.makedirs(sub_directory_path)

        for file_name in file_list:
            if file_name in file_path_map:
                source_file_path = file_path_map[file_name]
                target_file_path = os.path.join(sub_directory_path, file_name)
                try:
                    shutil.copy2(source_file_path, target_file_path)
                    if DEBUG:
                        print(f"Copied {source_file_path} to {target_file_path}")
                except Exception as e:
                    print(f"Error copying {source_file_path}: {e}")
            else:
                files_missing.append(file_name)
    if len(files_missing):
        for file_name in files_missing:
            print(f"{file_name} not found in files_to_copy. Migration failed!")
        print(f"Warning: {len(files_missing)} files not found in files_to_copy. Migration failed!")


def migrate_file_to_latex_project(file_path, latex_folder):
    """
    根据 files_to_copy 将 file_path 迁移到 latex_folder 中去。
    """
    filename = os.path.basename(file_path)
    for sub_directory, file_list in files_to_copy.items():
        if filename in file_list:
            sub_directory_path = os.path.join(latex_folder, sub_directory)
            if not os.path.exists(sub_directory_path):
                os.makedirs(sub_directory_path)

            try:
                shutil.copy2(file_path, sub_directory_path)
                if DEBUG:
                    print(f"Copied {file_path} to {sub_directory_path}")
            except Exception as e:
                print(f"Error copying {file_path}: {e}")
            return
    print(f"Warning: File '{filename}' not found in files_to_copy. Migration failed!")


def migrate_to_latex_project(src_dir, latex_folder, migration_mode="single", file_path=None):
    """
    根据迁移模式将文件迁移到 LaTeX 项目目录。
    """
    if DEBUG:
        print("\n\033[32mMigrating files to LaTeX project...\033[0m")  # 绿色文本
    if migration_mode == "single" and file_path:
        migrate_file_to_latex_project(file_path, latex_folder)
    elif migration_mode == "batch":
        migrate_folder_to_latex_project(src_dir, latex_folder, file_extensions=["pdf", "png", "jpg"])
    else:
        print("Error: Invalid migration mode or file path.")


def main():
    args = parse_args()
    global DEBUG, EXPORT_JPG_QUALITY
    if args.debug:
        DEBUG = True
    EXPORT_JPG_QUALITY = args.quality_jpg

    # 确定输出路径
    output_dir = args.output_path if args.output_path else os.path.dirname(os.path.abspath(args.input_path))

    # 处理单个文件
    if os.path.isfile(args.input_path) and args.input_path.endswith(".drawio"):
        file_basename = process_file(args.input_path, output_dir, args.keep_structure,
                                     os.path.dirname(args.input_path), args.export_types)
        if args.migration:
            pdf_file_path = file_basename + ".pdf"
            migrate_to_latex_project("", LATEX_PIC_DIR, migration_mode="single", file_path=pdf_file_path)
    # 处理文件夹
    elif os.path.isdir(args.input_path):
        process_folder(args.input_path, output_dir, args.keep_structure, args.git_changes, args.export_types)
        if args.migration:
            migrate_to_latex_project(output_dir, LATEX_PIC_DIR, migration_mode="batch")
    else:
        print(f"Error: Invalid input path: {args.input_path}")


if __name__ == "__main__":
    main()




