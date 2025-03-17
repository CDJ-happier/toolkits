"""
本文件用于计算光场估计的深度图和真值之间的mse和badpix指标
"""

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib import cm
import imageio.v2 as imageio
import pandas as pd

import fnmatch


def mean_squared_error(gt, pred, scale=100):
    """
    计算均方误差 (MSE)

    参数:
        gt: 真实值 (Ground Truth)，类型为列表或 NumPy 数组
        pred: 预测值 (Prediction)，类型为列表或 NumPy 数组

    返回:
        mse: 均方误差
    """
    gt = np.array(gt)
    pred = np.array(pred)
    mse = np.mean((gt - pred) ** 2)
    return mse * scale


def bad_pixel_ratio(gt, pred, eta=0.07):
    """
    计算逐像素相对误差超过阈值的百分比 (Bad Pixel Ratio)

    参数:
        gt: 真实值 (Ground Truth)，NumPy 数组
        pred: 预测值 (Prediction)，NumPy 数组
        eta: 误差阈值

    返回:
        bad_pixel_ratio: Bad Pixel Ratio，单位为百分比
    """
    # 将输入转换为 NumPy 数组
    gt = np.array(gt)
    pred = np.array(pred)

    bad_pix = np.sum(np.abs(gt - pred) > eta) / gt.size

    return bad_pix * 100


def write_pfm(data, fpath, scale=1, file_identifier=b'Pf', dtype="float32"):
    # PFM format definition: http://netpbm.sourceforge.net/doc/pfm.html

    data = np.flipud(data)
    height, width = np.shape(data)[:2]
    values = np.ndarray.flatten(np.asarray(data, dtype=dtype))
    endianess = data.dtype.byteorder
    print(endianess)

    if endianess == '<' or (endianess == '=' and sys.byteorder == 'little'):
        scale *= -1

    with open(fpath, 'wb') as file:
        file.write((file_identifier))
        file.write(('\n%d %d\n' % (width, height)).encode())
        file.write(('%d\n' % scale).encode())

        file.write(values)


# PFM 读取函数
def read_pfm(fpath, expected_identifier="Pf"):
    # PFM format definition: http://netpbm.sourceforge.net/doc/pfm.html

    def _get_next_line(f):
        next_line = f.readline().decode('utf-8').rstrip()
        # ignore comments
        while next_line.startswith('#'):
            next_line = f.readline().rstrip()
        return next_line

    with open(fpath, 'rb') as f:
        #  header
        identifier = _get_next_line(f)
        if identifier != expected_identifier:
            raise Exception('Unknown identifier. Expected: "%s", got: "%s".' % (expected_identifier, identifier))

        try:
            line_dimensions = _get_next_line(f)
            dimensions = line_dimensions.split(' ')
            width = int(dimensions[0].strip())
            height = int(dimensions[1].strip())
        except:
            raise Exception('Could not parse dimensions: "%s". '
                            'Expected "width height", e.g. "512 512".' % line_dimensions)

        try:
            line_scale = _get_next_line(f)
            scale = float(line_scale)
            assert scale != 0
            if scale < 0:
                endianness = "<"
            else:
                endianness = ">"
        except:
            raise Exception('Could not parse max value / endianess information: "%s". '
                            'Should be a non-zero number.' % line_scale)

        try:
            data = np.fromfile(f, "%sf" % endianness)
            data = np.reshape(data, (height, width))
            data = np.flipud(data)
            with np.errstate(invalid="ignore"):
                data *= abs(scale)
        except:
            raise Exception('Invalid binary values. Could not create %dx%d array from input.' % (height, width))

        return data


# 裁剪图像四周22像素
def crop_image(img, crop_size=22):
    return img[crop_size:-crop_size, crop_size:-crop_size, ...]


# 读取目录结构并获取所有方法及数据集
def get_methods_and_datasets(base_dir):
    methods = [method for method in os.listdir(base_dir) if
               os.path.isdir(os.path.join(base_dir, method)) and method != "GT"]
    datasets = []
    for method in methods:
        method_dir = os.path.join(base_dir, method)
        datasets.extend([ds for ds in os.listdir(method_dir) if os.path.isdir(os.path.join(method_dir, ds))])
    return methods, list(set(datasets))


def calculate_metrics(base_dir, methods, datasets, etas, DLFD_scenes=None):
    results = {}
    if DLFD_scenes is None:
        DLFD_scenes = [f"LF{idx}" for idx in [1, 9, 10, 16, 20, 22, 31, 32]]
    for method in methods:
        results[method] = {}
        for dataset in datasets:
            method_dataset_dir = os.path.join(base_dir, method, dataset)
            gt_dir = os.path.join(base_dir, "GT", dataset)
            if not os.path.exists(method_dataset_dir) or not os.path.exists(gt_dir):
                print(f"{method} or GT of {dataset} not found, skipping ...")
                continue

            dataset_results = {}  # 保存每个场景的指标
            mse_list = []  # MSE 结果列表
            badpix_dict = {eta: [] for eta in etas}  # 每个 eta 的 BadPix 结果列表

            for file in os.listdir(method_dataset_dir):
                if not fnmatch.fnmatch(file, "LF*.pfm"):  # 视差文件命名格式为LF{idx}.pfm
                    continue
                # 跳过一些DLFD光场
                filename_no_ext = os.path.splitext(file)[0]  # 去掉扩展 -> LF{idx}
                if dataset == "Inria_DLFD" and filename_no_ext not in DLFD_scenes:
                    continue
                # skip over
                print(f"{method} {dataset} {file} found")
                pred_path = os.path.join(method_dataset_dir, file)
                gt_path = os.path.join(gt_dir, file)
                if not os.path.exists(gt_path):
                    print(f"{gt_path} not found, skipping ...")
                    continue

                pred = read_pfm(pred_path)
                gt = read_pfm(gt_path)
                gt = crop_image(gt, crop_size=22)  # 裁剪 GT 图像四周 22 像素

                mse = mean_squared_error(gt, pred)
                mse_list.append(mse)

                badpix_results = {}
                for eta in etas:
                    badpix = bad_pixel_ratio(gt, pred, eta=eta)
                    badpix_results[f"badpix_eta_{eta}"] = badpix
                    badpix_dict[eta].append(badpix)

                # 保存当前场景的结果
                dataset_results[file] = {"mse": mse, **badpix_results}
                print(f"{method} {dataset} {file}: MSE={mse:.4f}, " +
                      ", ".join([f"BadPix@{eta}={badpix:.2f}%" for eta, badpix in badpix_results.items()]))

            # 计算每个数据集的平均值
            if mse_list:
                average_results = {"mse": np.mean(mse_list)}
                for eta in etas:
                    average_results[f"badpix_eta_{eta}"] = np.mean(badpix_dict[eta])
                dataset_results["average"] = average_results

            results[method][dataset] = dataset_results
    return results


def save_results_to_markdown(results, output_path, etas):
    methods = list(results.keys())
    datasets = {ds for method_results in results.values() for ds in method_results.keys()}
    datasets = sorted(datasets)

    for dataset in datasets:
        data = []
        scenes = set()

        # 收集所有场景
        for method in methods:
            if dataset not in results[method]:
                continue
            dataset_results = results[method][dataset]
            scenes.update(dataset_results.keys())

        scenes = sorted(scenes)
        for scene in scenes:
            for method in methods:
                if dataset not in results[method]:
                    continue
                dataset_results = results[method][dataset]
                if scene in dataset_results:
                    mse = dataset_results[scene].get("mse", "-")
                    row = [scene, method, f"{mse:.2f}" if mse != "-" else "-"]
                    for eta in etas:
                        badpix_key = f"badpix_eta_{eta}"
                        badpix = dataset_results[scene].get(badpix_key, "-")
                        row.append(f"{badpix:.2f}" if badpix != "-" else "-")
                else:
                    row = [scene, method, "-"] + ["-"] * len(etas)
                data.append(row)

        # 将场景和指标保存为 DataFrame
        columns = ["Scene", "Method", "MSE"] + [f"BadPix@{eta}" for eta in etas]
        df = pd.DataFrame(data, columns=columns)

        # 保存为 Markdown 文件
        dataset_output_path = os.path.join(output_path, f"{dataset}_results.md")
        with open(dataset_output_path, "w") as f:
            f.write(df.to_markdown(index=False))

        print(f"Results for dataset {dataset} saved to {dataset_output_path}")


# 将 PFM 转为 PNG
def convert_pfm_to_png(base_dir, methods, datasets, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for method in methods:
        for dataset in datasets:
            method_dataset_dir = os.path.join(base_dir, method, dataset)
            if not os.path.exists(method_dataset_dir):
                continue
            output_dataset_dir = os.path.join(output_dir, method, dataset)
            os.makedirs(output_dataset_dir, exist_ok=True)
            for file in os.listdir(method_dataset_dir):
                if file.endswith(".pfm"):
                    pfm_path = os.path.join(method_dataset_dir, file)
                    png_path = os.path.join(output_dataset_dir, file.replace(".pfm", ".png"))
                    depth_map = read_pfm(pfm_path)
                    normalized_depth = (depth_map - np.min(depth_map)) / (np.max(depth_map) - np.min(depth_map))
                    imageio.imwrite(png_path, (normalized_depth * 255).astype(np.uint8))
                    # plt.imsave(png_path, normalized_depth, cmap="viridis", vmin=0, vmax=1)
                    # plt.close()


# 生成对比图（视差图和误差图）
def generate_comparison_plots(base_dir, methods, datasets, output_dir, DLFD_scenes=None):
    if DLFD_scenes is None:
        DLFD_scenes = [f"LF{idx}" for idx in [1, 9, 10, 16, 20, 22, 31, 32]]
    os.makedirs(output_dir, exist_ok=True)
    # fix methods position manually
    methods = ["GTLF", "GC2ASR", "DispEhcASR", "ELFR", "FS-GAF", "HLFASR", "DistgASR"]
    methods_with_gt = ["GT"] + methods
    for dataset in datasets:
        gt_dir = os.path.join(base_dir, "GT", dataset)
        if not os.path.exists(gt_dir):
            continue
        for file in os.listdir(gt_dir):
            if not fnmatch.fnmatch(file, "LF*.pfm"):
                continue
            # 跳过一些DLFD光场
            filename_no_ext = os.path.splitext(file)[0]
            if dataset == "Inria_DLFD" and filename_no_ext not in DLFD_scenes:
                print(f"Skipping {file} in {dataset} controlled by variable <DLFD_scenes>")
                continue
            # skip over
            disp_gt_path = os.path.join(gt_dir, file)
            disp_gt = read_pfm(disp_gt_path)
            disp_gt = crop_image(disp_gt, crop_size=22)
            view_gt_path = os.path.join(gt_dir, file.replace(".pfm", "_view24_fine.png"))
            try:
                view_gt = imageio.imread(view_gt_path)
                view_gt = crop_image(view_gt, crop_size=22)
            except FileNotFoundError:
                print(f"Warning: File {view_gt_path} not found. Using dummy data for passing")
                view_gt = np.zeros_like(disp_gt)
            fig, axes = plt.subplots(2, len(methods_with_gt), figsize=(4 * len(methods_with_gt), 9))

            # 第一行：视差图
            for i, method in enumerate(methods_with_gt):
                if method == "GT":
                    pred = disp_gt
                else:
                    pred_path = os.path.join(base_dir, method, dataset, file)
                    if not os.path.exists(pred_path):
                        continue
                    pred = crop_image(read_pfm(pred_path))
                normalized_pred = (pred - np.min(pred)) / (np.max(pred) - np.min(pred))
                axes[0, i].imshow(normalized_pred, cmap="viridis", norm=Normalize(vmin=0, vmax=1))
                # axes[0, i].set_title(f"{method}", y=-0.15)  # y=-0.15将title调整到图像下方
                axes[0, i].text(0.5, -0.05, f"{method}", transform=axes[0, i].transAxes,
                                ha="center", va="center", fontsize=14)
                axes[0, i].axis("off")

            # 计算所有方法的误差图并找到全局最大误差
            error_maps = []
            for i, method in enumerate(methods_with_gt):
                if method == "GT":
                    continue
                else:
                    pred_path = os.path.join(base_dir, method, dataset, file)
                    if not os.path.exists(pred_path):
                        print(f"Warning: File {pred_path} not found. Skipping...")
                        continue
                    pred = read_pfm(pred_path)
                    error_map = np.abs(disp_gt - pred)
                error_maps.append(error_map)

            # 找到全局最大误差
            global_max_error = max(np.max(error_map) for error_map in error_maps if error_map is not None)

            # 第二行：误差图
            for i, method in enumerate(methods_with_gt):
                if method == "GT":
                    error_map = view_gt  # 显示view
                else:
                    pred_path = os.path.join(base_dir, method, dataset, file)
                    if not os.path.exists(pred_path):
                        continue
                    pred = read_pfm(pred_path)
                    error_map = np.abs(disp_gt - pred)
                normalized_error = error_map / global_max_error if method != "GT" else error_map
                axes[1, i].imshow(normalized_error, cmap="hot", norm=Normalize(vmin=0, vmax=1))
                title = f"{method} Error" if method != "GT" else "View"
                # axes[1, i].set_title(title, y=-0.15)  # y=-0.15将title调整到图像下方
                # 在子图底部添加注释性文字
                axes[1, i].text(0.5, -0.05, title, transform=axes[1, i].transAxes,
                                ha="center", va="center", fontsize=14)
                axes[1, i].axis("off")

            # 保存对比图
            output_path = os.path.join(output_dir, f"{dataset}_{file.replace('.pfm', '.png')}")
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()


# 生成模拟数据（测试用）
def generate_mock_data(base_dir):
    os.makedirs(base_dir, exist_ok=True)
    methods = ["GC2ASR", "DispEhcASR", "ELFR", "FS-GAF", "DistgASR", "HLFASR"]
    datasets = ["HCI", "HCI_old", "Inria_DLFD"]
    scenes = ["scene1.pfm", "scene2.pfm"]
    h, w = 468, 468
    for method in methods + ["GT"]:
        for dataset in datasets:
            method_dataset_dir = os.path.join(base_dir, method, dataset)
            os.makedirs(method_dataset_dir, exist_ok=True)
            for scene in scenes:
                dummy_data = np.random.rand(h, w).astype(np.float32)
                # dummy_data.tofile(os.path.join(method_dataset_dir, scene))
                write_pfm(dummy_data, os.path.join(method_dataset_dir, scene))
                if method == "GT":
                    view_path = os.path.join(method_dataset_dir, scene.replace(".pfm", ".png"))
                    dummy_data = np.random.randint(0, 256, size=(h, w, 3), dtype=np.uint8)
                    imageio.imwrite(view_path, dummy_data)


# 主函数
def main():
    base_dir = "ReconLFs"
    output_dir = "benchmark_depth_GT"
    png_output_dir = os.path.join(output_dir, "png")
    comparison_output_dir = os.path.join(output_dir, "comparison")

    # 生成模拟数据（仅测试时启用）
    # generate_mock_data(base_dir)
    etas = [0.07, 0.03, 0.01]
    methods, datasets = get_methods_and_datasets(base_dir)
    results = calculate_metrics(base_dir, methods, datasets, etas)
    os.makedirs(output_dir, exist_ok=True)
    save_results_to_markdown(results, output_dir, etas)
    convert_pfm_to_png(base_dir, methods, datasets, png_output_dir)
    generate_comparison_plots(base_dir, methods, datasets, comparison_output_dir)
    print("Processing complete.")


if __name__ == "__main__":
    main()
