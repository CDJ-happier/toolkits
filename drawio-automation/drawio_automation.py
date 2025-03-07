import os
import subprocess
import shutil
import argparse

import json
with open("config_drawio_migration.json", "r", encoding="utf-8") as f:
    config = json.load(f)
LATEX_PIC_DIR = config["latex_pic_dir"]
files_to_copy = config["files_to_copy"]

# 以下为默认路径，可根据实际情况修改, 或者将其添加到环境变量中(如PDFCROP_PATH)
DRAWIO_EXE_PATH = r"D:\Program Files\draw.io\draw.io.exe"  # draw.io-desktop 的 CLI 路径
EDGE_EXE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"  # Edge 可执行文件路径
PDFCROP_EXE_PATH = "pdfcrop"  # latex 提供的 pdfcrop 工具, 已添加到 PATH 环境变量中
GIT_EXE_PATH = "git"  # git 可执行文件路径, 已添加到 PATH 环境变量中
DEBUG = False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Automate Draw.io files workflow: Export SVG(drawio) -> Convert to PDF(edge) -> Crop PDF(latex). "
                    "Supports batch processing and Git-detected changes.")

    # 输入文件或文件夹
    parser.add_argument("input_path", type=str, help="Input file (.drawio) or folder containing .drawio files")

    # 输出文件或文件夹
    parser.add_argument("output_path", type=str, nargs="?", default="",
                        help="Output file or folder path (default: same as input path)")

    # 批量处理模式
    parser.add_argument("-b", "--batch", action="store_true",
                        help="Batch process all .drawio files in the folder (including subdirectories)")

    # Git变更文件处理
    parser.add_argument("-g", "--git-changes", action="store_true",
                        help="Only process .drawio files detected as changed by Git")

    # 是否保持目录结构
    parser.add_argument("-k", "--keep-structure", action="store_true",
                        help="Keep the input folder's relative directory structure in the output folder (only applicable when -b/-g)")

    # 是否迁移到latex工程目录
    parser.add_argument("-m", "--migration", action="store_true",
                        help="Move the generated PDF files to the latex project directory according to config_drawio_migration.json")

    # 调试模式（可选）
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode to display additional information during execution")

    return parser.parse_args()


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

    try:
        subprocess.run([
            DRAWIO_EXE_PATH,  # "draw.io-desktop" 的 CLI 路径
            "--export",
            drawio_file,
            "--output",
            svg_file,
            "--scale",
            "2",  # 可选，导出比例
            "--border",
            "0"
        ], check=True)
        if DEBUG:
            print(f"Converted: {drawio_file} -> {svg_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {drawio_file} to {svg_file}: {e}")
        return


def svg_to_pdf(svg_file, pdf_file="", crop=False):
    """
    Args:
        svg_file: SVG 文件路径
        pdf_file: PDF 文件保存路径, 默认为空. 若为空则保存路径和文件名同svg_file
        crop: 是否裁剪 PDF
    Description:
        使用 Edge 将 SVG 文件转换为 PDF 文件, 可选是否使用latex提供的pdfcrop工具裁剪 PDF 文件
    """
    # 转换为绝对路径
    svg_file = os.path.abspath(svg_file)
    # 如果pdf_file为空，则保存路径和文件名同svg_file
    if pdf_file == "":
        pdf_file = os.path.splitext(svg_file)[0] + ".pdf"
    pdf_file = os.path.abspath(pdf_file)

    # 确保目标文件夹存在
    pdf_dir = os.path.dirname(pdf_file)
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    # 使用 Edge 转换 SVG 到 PDF
    try:
        subprocess.run([
            EDGE_EXE_PATH,  # Edge 可执行文件路径
            "--headless",
            "--disable-gpu",
            "--no-pdf-header-footer",  # 可选，去掉页眉页脚
            f"--print-to-pdf={pdf_file}",
            svg_file
        ], check=True)
        if DEBUG:
            print(f"Converted: {svg_file} -> {pdf_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error converting {svg_file} to {pdf_file}: {e}")
        return

    # 如果需要裁剪 PDF
    if crop:
        try:
            subprocess.run([
                PDFCROP_EXE_PATH,  # pdfcrop 可执行文件路径 或加入到 PATH 环境变量
                pdf_file,
                pdf_file
            ], check=True)
            if DEBUG:
                print(f"Cropped: {pdf_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error cropping {pdf_file}: {e}")


def process_file(drawio_file, output_dir="", keep_structure=False, input_dir=""):
    """
    Args:
        drawio_file: 文件全路径
        output_dir: 输出路径
        keep_structure: 是否保持文件结构
        input_dir: 输入路径, drawio_file 的祖先目录
    Description:
        处理单个 .drawio 文件，生成 SVG 和 PDF 文件。
    """
    # 计算输出路径
    if output_dir:
        if keep_structure and input_dir:
            # 保持相对目录结构
            rel_path = os.path.relpath(drawio_file, input_dir)
            base_name = os.path.splitext(os.path.basename(rel_path))[0]
            svg_file = os.path.join(output_dir, os.path.dirname(rel_path), f"{base_name}.svg")
            pdf_file = os.path.join(output_dir, os.path.dirname(rel_path), f"{base_name}.pdf")
        else:
            # 不保持目录结构
            base_name = os.path.splitext(os.path.basename(drawio_file))[0]
            svg_file = os.path.join(output_dir, f"{base_name}.svg")
            pdf_file = os.path.join(output_dir, f"{base_name}.pdf")
    else:
        # 输出路径为空，使用输入文件所在目录
        svg_file = os.path.splitext(drawio_file)[0] + ".svg"
        pdf_file = os.path.splitext(drawio_file)[0] + ".pdf"

    # 执行转换
    drawio_to_svg(drawio_file, svg_file)
    svg_to_pdf(svg_file, pdf_file, crop=True)
    return svg_file, pdf_file


def process_folder(input_dir, output_dir="", keep_structure=False, git_changes=False):
    """
    Args:
        input_dir: 输入文件夹
        output_dir: 输出文件夹, 默认为空. 为空则同 input_dir.
        keep_structure: 是否保持文件夹相对结构
        git_changes: 是否只对git检测到变化的文件执行工作流
    Description:
        处理文件夹下的所有 .drawio 文件。
    """
    if git_changes:
        # 只处理 Git 检测到的变更文件
        modified_files = get_modified_files(input_dir, ["drawio"])
        for file in modified_files:
            drawio_file = os.path.join(input_dir, file)
            process_file(drawio_file, output_dir, keep_structure, input_dir)
    else:
        # 处理所有 .drawio 文件
        for root, dirs, files in os.walk(input_dir):
            for file in files:
                if file.endswith(".drawio"):
                    drawio_file = os.path.join(root, file)
                    process_file(drawio_file, output_dir, keep_structure, input_dir)


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


def migrate_folder_to_latex_project(src_folder, latex_folder):
    """
    将 files_to_copy 中指定的文件复制到 latex_folder 目录下。
    """
    if not os.path.exists(latex_folder):
        print(f"Error: Source folder '{latex_folder}' not found.")
        return

    # 构建文件名到文件路径的映射字典
    file_path_map = {}
    for root, _, files in os.walk(src_folder):
        for file_name in files:
            if file_name in file_path_map:
                continue
            file_path_map[file_name] = os.path.join(root, file_name)

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
                print(f"Warning: File '{file_name}' not found.")

    print("All specified files have been processed.")


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


def migrate_to_latex_project(output_dir, latex_folder, migration_mode="single", file_path=None):
    """
    根据迁移模式将文件迁移到 LaTeX 项目目录。
    """
    if migration_mode == "single" and file_path:
        migrate_file_to_latex_project(file_path, latex_folder)
    elif migration_mode == "batch":
        migrate_folder_to_latex_project(output_dir, latex_folder)
    else:
        print("Error: Invalid migration mode or file path.")


def main():
    args = parse_args()
    if args.debug:
        DEBUG = True

    # 确定输出路径
    output_dir = args.output_path if args.output_path else os.path.dirname(args.input_path)

    # 处理单个文件
    if os.path.isfile(args.input_path) and args.input_path.endswith(".drawio"):
        _, pdf_file_path = process_file(args.input_path, output_dir, args.keep_structure, os.path.dirname(args.input_path))
        if args.migration:
            migrate_to_latex_project(output_dir, LATEX_PIC_DIR, migration_mode="single", file_path=pdf_file_path)
    # 处理文件夹
    elif os.path.isdir(args.input_path):
        process_folder(args.input_path, output_dir, args.keep_structure, args.git_changes)
        if args.migration:
            migrate_to_latex_project(output_dir, LATEX_PIC_DIR, migration_mode="batch")
    else:
        print(f"Error: Invalid input path: {args.input_path}")


if __name__ == "__main__":
    main()




