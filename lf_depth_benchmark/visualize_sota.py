import os
import fnmatch
import numpy as np
import matplotlib.pyplot as plt
import cv2
from glob import glob
from matplotlib.colors import Normalize
from matplotlib import cm
from matplotlib import gridspec
import imageio.v2 as imageio


def load_image(image_path):
    """加载图像并转换为float32格式的numpy数组。"""
    img = imageio.imread(image_path).astype(np.float32) / 255.0
    # 打印path、shape、最大值、最小值
    # print(f"{image_path}: shape={img.shape}, max={np.max(img)}, min={np.min(img)}")
    return img


def plot_colormap(dataset, lf_index, output_dir, cmap="hot"):
    gradient = np.linspace(0, 1, 256)
    gradient = np.vstack([gradient] * 8)
    output_file = os.path.join(output_dir, f"{dataset}_LF{lf_index}_colormap.png")
    plt.imsave(output_file, gradient, cmap=plt.get_cmap(cmap))


def extract_epi(images, h, h_scale:int =2):
    """从多个角度的光场图像提取水平方向EPI。"""
    epi = np.stack([img[h, :, :] for img in images], axis=0)
    if h_scale <= 1:
        return epi
    # 对epi的h进行resize放大两倍, bilinear插值
    epi = (epi * 255).astype(np.uint8)
    h, w, c = epi.shape
    epi = cv2.resize(epi, (w, h * h_scale), interpolation=cv2.INTER_LINEAR)
    # 加上(0, 255, 0)的边框
    cv2.rectangle(epi, (0, 0), (w, h * h_scale), (0, 255, 0), 2)
    epi = epi / 255.0
    return epi


def draw_zoom_boxes(image, zoom_regions, epi_h):
    """在原图上绘制局部放大区域的方框。"""
    # 如果图像是浮点类型（归一化到 [0, 1]），需要转换为 [0, 255] 的 uint8 类型
    if image.dtype != np.uint8:
        image_with_boxes = (image * 255).astype(np.uint8)
    else:
        image_with_boxes = image.copy()

    # 绘制矩形框
    red_blue = [(255, 0, 0), (0, 0, 255)]
    for i, (x, y, h, w) in enumerate(zoom_regions):
        cv2.rectangle(image_with_boxes, (x, y), (x + w, y + h), red_blue[i], 2)
    # 画一条水平线
    cv2.line(image_with_boxes, (0, epi_h), (image_with_boxes.shape[1], epi_h), (0, 255, 0), 2)
    return image_with_boxes / 255.0


def merge_zoomed_areas(zoomed_areas, target_width, gap=4):
    """调整局部放大区域的大小，使其并排显示，总宽度与中心视点图像相同。gap用于添加空隙"""
    # 先转为np.uint8
    zoomed_areas = [(area * 255).astype(np.uint8) for area in zoomed_areas]
    # resize
    zoom_width = (target_width - gap) // 2
    resized_areas = [cv2.resize(area, (zoom_width, zoom_width)) for area in zoomed_areas]
    red_blue = [(255, 0, 0), (0, 0, 255)]
    # 给每个resize_areas添加颜色边框
    h, w, _ = resized_areas[0].shape
    colored_areas = [cv2.rectangle(area, (0, 0), (w, h), red_blue[i], 2) for i, area in enumerate(resized_areas)]
    gap_white = np.ones((h, gap, 3), dtype=np.uint8) * 255  # 白色空隙
    merged_areas = np.concatenate([colored_areas[0], gap_white, colored_areas[1]], axis=1)
    return merged_areas


def plot_gt_images(gt_images, output_path, dpi=300, jpg_quality=85):
    """
    绘制 GT 图像，将 "中心视点"、"局部放大"、"EPI 图" 这三张图像按照垂直排列保存为 PNG 图像。
    确保行间距与其他方法的布局一致。

    参数:
        gt_images (list): 包含 ["中心视点", "局部放大", "EPI 图"] 对应的图像列表。
        output_path (str): 保存输出图像的路径。
    """
    # 检查 GT 图像数量是否正确
    if len(gt_images) != 3:
        raise ValueError(f"GT 图像数量应为 3（['中心视点', '局部放大', 'EPI 图']），但实际为 {len(gt_images)}。")

    # 获取图像宽度和高度信息
    image_width = gt_images[0].shape[1]  # 所有图像宽度相同
    image_heights = [img.shape[0] for img in gt_images]  # 每张图像的高度

    # 计算图像总高度
    total_height = sum(image_heights)

    # 设置图像宽高比例
    fig_width = 5  # 固定每列宽度
    fig_height = (fig_width / image_width) * total_height

    # 创建子图网格，行数为 3，列数为 1
    fig, axes = plt.subplots(3, 1, figsize=(fig_width, fig_height),
                             gridspec_kw={'height_ratios': image_heights})

    # 遍历 GT 图像，绘制到对应的子图中
    for row_idx, image in enumerate(gt_images):
        ax = axes[row_idx]
        ax.imshow(image)  # 显示图像
        ax.axis('off')  # 不显示坐标轴

    # 调整布局并保存图像
    plt.tight_layout()  # 进一步调整整体布局，减少子图边距
    plt.savefig(output_path + "_gt.png", format='png', dpi=dpi, bbox_inches='tight')
    # 保存为 JPEG 格式，设置质量为 85
    plt.savefig(output_path + "_gt.jpg", format='jpg', dpi=dpi, pil_kwargs={"quality": jpg_quality}, bbox_inches='tight')
    plt.savefig(output_path + "_gt.pdf", format='pdf', bbox_inches='tight')
    plt.close(fig)


def plot_sota_visual_comparison(method_images, output_path, cmap="hot", dpi=300, jpg_quality=85):
    """
    绘制视觉对比图，将不同方法的图像按列排列，每列从上到下依次是中心视点、局部放大、EPI 图、误差图。
    确保每个方法的子图宽度一致，高度根据输入图像自适应。

    参数:
        method_images (dict): 字典，key 是方法名，value 是一个包含 ["中心视点", "局部放大", "EPI 图", "误差图"] 对应图像的列表。
        output_path (str): 保存输出图像的路径。
    """
    # 从字典method_images提取key为GTLF的数据, 并从字典中移除, 单独处理
    gt_images = method_images.pop("GTLF")[:-1]  # 最后一个误差图是全0, 扔掉
    plot_gt_images(gt_images, output_path, dpi, jpg_quality)
    # 获取方法数量和每种方法的图像数量
    num_methods = len(method_images)
    num_images_per_method = 4  # 每种方法有4张图片：中心视点、局部放大、EPI 图、误差图

    # 获取第一个方法的第一个图像的宽度作为参考宽度
    sample_image = list(method_images.values())[0][0]
    image_width = sample_image.shape[1]  # 图像的宽度

    # 动态计算图像的总高度，按每列的高度之和计算
    total_height = sum(img.shape[0] for img in list(method_images.values())[0])

    # 设置图像总宽度（每列5个单位宽度）
    fig_width = 5 * num_methods
    # 根据宽高比动态计算图像总高度
    fig_height = (fig_width / (num_methods * image_width)) * total_height

    # 创建子图网格
    fig, axes = plt.subplots(num_images_per_method, num_methods, figsize=(fig_width, fig_height),
                             gridspec_kw={'height_ratios': [img.shape[0] for img in list(method_images.values())[0]]})

    # 如果只有一个方法，axes 是 1D，否则是 2D，统一转换为 2D
    if num_methods == 1:
        axes = axes[:, None]

    # 遍历每种方法及其对应的图像
    for col_idx, (method_name, images) in enumerate(method_images.items()):
        # 检查图像数量是否正确
        if len(images) != num_images_per_method:
            raise ValueError(f"方法 '{method_name}' 的图像数量应为 {num_images_per_method}，但实际为 {len(images)}。")

        # 遍历每张图像并绘制到对应的子图中
        for row_idx, image in enumerate(images):
            ax = axes[row_idx, col_idx]
            cur_cmap = cmap if row_idx == 3 else None
            ax.imshow(image, cmap=cur_cmap)  # 显示图像，保持原比例
            ax.axis('off')  # 不显示坐标轴

            # 如果是第一行，显示方法名作为列标题
            if row_idx == 0:
                pass
                # ax.set_title(method_name, fontsize=16)

    # 保存图像（去除多余白边）
    plt.tight_layout()  # 进一步调整整体布局，减少子图边距
    plt.savefig(output_path + ".png", format='png', dpi=dpi, bbox_inches='tight')
    # 保存为 JPEG 格式，设置质量为 85
    plt.savefig(output_path + ".jpg", format='jpg', dpi=dpi, pil_kwargs={"quality": jpg_quality}, bbox_inches='tight')
    plt.savefig(output_path + ".pdf", format='pdf', bbox_inches='tight')
    plt.close()


def process_light_field(folder, dataset, lf_index, zoom_regions, epi_h:int):
    """处理单个光场，生成视觉对比图。"""
    methods = ["GTLF", "GC2ASR", "DispEhcASR", "ELFR", "FS-GAF", "HLFASR", "DistgASR"]
    gt_folder = os.path.join(folder, "GTLF", dataset)
    gt_path = os.path.join(gt_folder, f"LF{lf_index}_view24_fine.png")
    ground_truth = load_image(gt_path)

    output_dir = "visual_sota"
    os.makedirs(output_dir, exist_ok=True)

    # 计算所有方法的误差，并找出最大误差值
    max_error = 0
    method_images = {}
    error_maps = {}

    for method in methods:
        method_folder = os.path.join(folder, method, dataset)
        img_path = os.path.join(method_folder, f"LF{lf_index}_view24_fine.png")

        if not os.path.exists(img_path):
            print(f"{method} not found for LF{lf_index}")
            continue

        reconstructed = load_image(img_path)
        error_map = np.mean(np.abs(reconstructed - ground_truth), axis=-1)
        max_error = max(max_error, np.max(error_map))
        error_maps[method] = error_map

    # 归一化误差图并生成可视化
    for method in methods:
        if method not in error_maps:
            print(f"{method} not found for LF{lf_index}")
            continue

        method_folder = os.path.join(folder, method, dataset)
        img_path = os.path.join(method_folder, f"LF{lf_index}_view24_fine.png")
        reconstructed = load_image(img_path)
        zoomed_areas = [reconstructed[y:y + h, x:x + w] for (x, y, h, w) in zoom_regions]
        merged_zoomed_areas = merge_zoomed_areas(zoomed_areas, reconstructed.shape[1])  # 第一个zoom用红色、第二个用蓝色
        reconstructed_with_boxes = draw_zoom_boxes(reconstructed, zoom_regions, epi_h)
        normalized_error_map = error_maps[method] / max_error  # 归一化误差图
        epi_images = [load_image(os.path.join(method_folder, f"LF{lf_index}_view{j}_fine.png")) for j in range(21, 28)]
        epi = extract_epi(epi_images, epi_h, h_scale=4)

        method_images[method] = [reconstructed_with_boxes, merged_zoomed_areas, epi, normalized_error_map]

    cmap = "hot"  # "bwr"
    output_path = os.path.join(output_dir, f"{dataset}_LF{lf_index}_epi{epi_h}_comparison")
    plot_sota_visual_comparison(method_images, output_path, cmap)
    plot_colormap(dataset, lf_index, output_dir, cmap)
    print(f"Visual comparison saved to {output_path}.png, max error is {max_error}")


if __name__ == '__main__':
    # 示例调用
    # process_light_field("ReconLFs", "HCI", 3, [(30, 30, 40, 80), (200, 100, 30, 80)], 50)
    selected_lfs = {
        "HCI": [
            [3, [(30, 30, 40, 80), (200, 100, 30, 80)], 50],
            [3, [(30, 30, 40, 80), (200, 100, 30, 80)], 50]
        ],
        "HCI_old": [
            [3, (30, 30, 40, 80), (200, 100, 30, 80), 50],
            [3, (30, 30, 40, 80), (200, 100, 30, 80), 50]
        ],
        "Inria_DLFD": [
            [0, (30, 30, 40, 80), (200, 100, 30, 80), 50],
            [0, (30, 30, 40, 80), (200, 100, 30, 80), 50]
        ],
    }
    for dataset, lfs in selected_lfs.items():
        for lf_index, zoom_regions, epi_h in lfs:
            process_light_field("ReconLFs", dataset, lf_index, zoom_regions, epi_h)
