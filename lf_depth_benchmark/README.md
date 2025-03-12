# 光场重建深度图评估工具

本工具用于评估不同光场重建方法在多个数据集上的深度图估计效果。工具提供了以下功能：

1. **计算深度图的评价指标**：包括均方误差（MSE）和坏像素率（Bad Pixel Ratio）。
2. **保存结果为Markdown表格**：将每个方法在每个数据集上的评估结果保存为Markdown格式的表格。
3. **生成视差图和误差图的对比图**：将PFM格式的视差图转换为PNG格式，并生成对比图，展示各方法的视差图及其与真值的误差图。

## 目录结构

有一个目录`ReconLFs`，其包括多个子目录，如`DispEhcASR, ELFR, DistgASR`等（GT目录用于存放真值数据），表示不同的光场重建方法，每个方法里面又包括多个子目录，包括`HCI, HCI_old, Inria_DLFD`，表示各个方法在不同数据集上重建光场的深度估计图（使用其它视差/深度估计算法得到的某光场重建算法重建结果的深度估计图）。

```txt
├─ReconLFs
│  ├─DispEhcASR
│  │  └─HCI
│  │          bedroom.pfm
│  │          bicycle.pfm
│  │          dishes.pfm
│  │          herbs.pfm
│  ├─DistgASR
│  │  └─HCI
│  │          bedroom.pfm
│  │          bicycle.pfm
│  │          dishes.pfm
│  │          herbs.pfm
│  ├─ELFR
│  │  └─HCI
│  │          bedroom.pfm
│  │          bicycle.pfm
│  │          dishes.pfm
│  │          herbs.pfm
│  ├─GC2ASR
│  ├─GT  # 存放GT. 注意，还需存放对应场景的view图像用于可视化对比
│  └─HLFASR
```

## 功能说明

### 1. 计算评价指标

- **MSE (Mean Squared Error)**: 计算预测深度图与真值深度图之间的均方误差。
- **Bad Pixel Ratio**: 计算预测深度图与真值深度图之间的坏像素率（默认阈值为0.07）。

### 2. 保存结果为Markdown表格

- 每个数据集的结果将保存为一个单独的Markdown文件，文件名为`{dataset}_results.md`。
- 表格的第一列为方法名称，后续列为不同场景的MSE和Bad Pixel Ratio指标。

### 3. 生成视差图和误差图的对比图

- 将PFM格式的视差图转换为PNG格式。
- 生成对比图，展示各方法的视差图及其与真值的误差图。对比图分为两行：
  - 第一行展示真值视差图及各方法的预测视差图。
  - 第二行展示各方法预测视差图与真值视差图的误差图。

## 使用方法

1. **安装依赖**：
   ```bash
   pip install numpy matplotlib imageio pandas
   ```

2. **运行脚本**：
   ```bash
   python evaluate_depth.py
   ```

3. **输出结果**：
   - 评价指标结果将保存在`benchmark_depth`目录下的Markdown文件中。
   - 视差图和误差图的对比图将保存在`benchmark_depth/comparison`目录下。

## 函数功能

- **`read_pfm`**: 读取PFM格式文件。
- **`mean_squared_error`**: 计算均方误差。
- **`bad_pixel_ratio`**: 计算坏像素率。
- **`crop_image`**: 裁剪图像四周22像素。
- **`get_methods_and_datasets`**: 获取所有方法及数据集。
- **`calculate_metrics`**: 计算评价指标。
- **`save_results_to_markdown`**: 保存结果为Markdown表格。
- **`convert_pfm_to_png`**: 将PFM格式的视差图转换为PNG格式。
- **`generate_comparison_plots`**: 生成视差图和误差图的对比图。
- **`generate_mock_data`**: 生成模拟数据（仅用于测试）。

## 示例输出

### Markdown表格示例

```markdown
| Method     | Scene   | MSE    | BadPix |
|------------|---------|--------|--------|
| DispEhcASR | bedroom | 0.0123 | 1.2345 |
| DispEhcASR | bicycle | 0.0145 | 1.5678 |
| DistgASR   | bedroom | 0.0112 | 1.1234 |
| DistgASR   | bicycle | 0.0134 | 1.4567 |
```



## 注意事项

- 确保`ReconLFs`目录结构正确，且每个方法目录下包含相应的PFM文件（提供了生成测试数据的函数）。
- 真值目录`GT`下的PFM文件将被裁剪四周22像素后再进行计算（因为光场重建方法生成的图像是经裁剪过的）。

## 未来改进

- 支持更多评价指标。
- 优化图像生成速度。
- 增加对更多数据集的支持。

---

如有任何问题或建议，请联系开发者。