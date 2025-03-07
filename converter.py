import os
from pathlib import Path
import fitz  # PyMuPDF
import argparse


def argument_parser():
    # 创建 ArgumentParser 对象
    parser = argparse.ArgumentParser(description="文件格式转换工具")
    # 添加输入文件夹路径参数
    parser.add_argument("input_file_dir", type=str, help="输入文件夹路径或单个文件路径")
    # 添加输出文件夹路径参数（可选）
    parser.add_argument("output_file_dir", type=str, nargs='?', default=None, help="输出文件夹路径（可选）")
    # 添加转换类型参数
    parser.add_argument("convert_type", type=str, choices=conversion_functions.keys(),
                        help="转换类型（pdf2png, svg2pdf 等）")

    # 解析命令行参数
    args = parser.parse_args()
    return args


def converter_proxy(input_path, output_path, conversion_func):
    """
    处理文件或文件夹中的文件，调用转换函数进行转换。

    参数：
    input_path -- 输入文件夹路径或单个文件路径
    output_path -- 输出文件夹路径
    conversion_func -- 具体的转换函数
    """
    # 如果没有指定输出路径，则默认使用输入路径所在的目录
    if output_path is None:
        output_path = os.path.dirname(input_path) if os.path.isfile(input_path) else input_path

    # 确保输出文件夹存在
    os.makedirs(output_path, exist_ok=True)

    # 检查输入路径是文件还是文件夹
    if os.path.isfile(input_path):
        # 单个文件处理
        conversion_func(input_path, output_path)
    elif os.path.isdir(input_path):
        # 文件夹处理
        for file_name in os.listdir(input_path):
            # 构造完整文件路径
            input_file_path = os.path.join(input_path, file_name)

            # 确保当前文件是目标文件类型
            if os.path.isfile(input_file_path) and conversion_func.is_valid_file(input_file_path):
                conversion_func(input_file_path, output_path)
    else:
        print("输入路径无效，请提供有效的文件或文件夹路径。")


def pdf_to_png(file_path: str, output_path: str):
    """
    将指定文件或文件夹下的 PDF 文件转换为 PNG，文件名称保持不变。

    Args:
        file_path: -- PDF 文件路径
        output_path: -- 用于保存 PNG 文件的输出文件夹路径
    """
    # 打开 PDF 文件
    pdf_document = fitz.open(file_path)
    # 获取文件名
    file_name = os.path.basename(file_path)
    output_folder = output_path

    # 遍历 PDF 的每一页
    for page_number in range(len(pdf_document)):
        # 获取 PDF 页面
        page = pdf_document.load_page(page_number)
        # 将页面转换为图像（分辨率可调整为 2 倍、3 倍等）
        pix = page.get_pixmap(dpi=300)
        # 构造输出文件路径：保持原 PDF 文件名，同时加页码后缀
        output_file_name = f"{Path(file_name).stem}_page{page_number + 1}.png"
        output_file_path = os.path.join(output_folder, output_file_name)
        # 保存图像
        pix.save(output_file_path)
    pdf_document.close()
    print(f"转换完成: {file_name}")


def is_valid_pdf_file(file_path):
    """
    检查文件是否为 PDF 文件。

    参数：
    file_path -- 文件路径
    """
    return file_path.lower().endswith(".pdf")


pdf_to_png.is_valid_file = is_valid_pdf_file


def svg_to_pdf(input_path, output_path):
    """
    将指定文件或文件夹下的 SVG 文件转换为 PDF，文件名称保持不变。

    参数：
    input_path -- 包含 SVG 文件的输入文件夹路径或单个 SVG 文件路径
    output_path -- 用于保存 PDF 文件的输出文件夹路径
    """
    # 这里可以添加 SVG 转 PDF 的逻辑
    print(f"SVG to PDF 转换尚未实现: {input_path}")


def is_valid_svg_file(file_path):
    """
    检查文件是否为 SVG 文件。

    参数：
    file_path -- 文件路径
    """
    return file_path.lower().endswith(".svg")


svg_to_pdf.is_valid_file = is_valid_svg_file


# 定义转换函数字典
conversion_functions = {
    'pdf2png': pdf_to_png,
    'svg2pdf': svg_to_pdf
}


if __name__ == '__main__':
    args = argument_parser()

    # 获取转换函数
    convert_func = conversion_functions.get(args.convert_type)

    if convert_func:
        # 执行转换
        converter_proxy(args.input_file_dir, args.output_file_dir, convert_func)
    else:
        print(f"不支持的转换类型: {args.convert_type}")
