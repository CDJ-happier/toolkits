目前的科研绘图工作流：

```mermaid
graph LR
	vscode["vscode+drawio"]
	svg
	pdf
	pdf_crop
	vscode -->|"导出"| svg -->|"edge浏览器保存为"| pdf -->|"LaTex提供的裁剪工具"| pdf_crop
```

当文件数量较少时，可能还能接受，但当数量很多时，上面流程比较繁琐，遂尝试将上面的流程自动化。

功能需求：

1. 对某个drawio文件执行上述工作流。`python drawio_automation.py xxxx.drawio [output_dir]`；
2. 对某个文件夹下的所有drawio文件执行上述工作流。`python drawio_automation.py xxx_dir [output_dir]`；
3. 基于git获取指定文件夹下已变更的drawio文件，对这些文件执行上述工作流。`python drawio_automation.py  xxx_dir [output_dir] -g`；

其它要求：

1. 对于每次执行，除了指定输入文件或者文件夹，还可以指定输出文件路径或文件夹路径。如果不指定，则默认与输入文件或文件夹同路径。
2. 当对文件夹及其子目录下的多个drawio文件执行工作流时，还可以指定一个参数，用于决定导出的pdf文件在输出文件夹中是否保持输入文件夹的相对结构。注意，这个功能只有当输出文件夹output_dir不为空时才实现。

---

# Draw.io 自动化工作流工具

## 概述

本工具用于自动化处理 `.drawio` 文件，将其转换为 SVG 和 PDF 格式，并支持将生成的 PDF 文件迁移到 LaTeX 项目目录中。工具支持以下功能：

1. 将单个 `.drawio` 文件转换为 SVG 和 PDF。
2. 批量处理文件夹及其子目录下的所有 `.drawio` 文件。
3. 基于 Git 检测变更的 `.drawio` 文件，仅处理已修改的文件。
4. 将生成的 PDF 文件迁移到 LaTeX 项目的指定目录中（如figures目录），支持保持目录结构。

---

## 文件结构

```
drawio-automation/
├── config.json                # 迁移配置文件，定义 LaTeX 项目目录和文件迁移规则
├── drawio_automation.py       # 主程序文件
├── README.md                  # 项目说明文档
└── requirements.txt           # 依赖文件（可选）
```

---

## 使用方式

### 1. 安装依赖

确保已安装以下工具：

- [draw.io Desktop](https://github.com/jgraph/drawio-desktop/releases)
- Microsoft Edge 浏览器
- LaTeX 的 `pdfcrop` 工具
- Git（如果需要使用 Git 变更检测功能）

并根据你自己的安装路径修改代码中的相关变量：

### 2. 迁移配置文件

在 `config.json` 中定义 LaTeX 项目的目录和文件迁移规则：

```json
{
    "latex_pic_dir": "D:/code/gh_cdj/master-thesis/figures",
    "files_to_copy": {
        "chap01": ["lf_recon_schema.pdf", "methods_by_date_and_result.pdf"],
        "chap02": ["lf_double_plane.pdf", "lf_macpi_schema.pdf", "lf_sai_epi_schema.pdf"],
        "chap03": ["occlusion_analysis.pdf", "occlusion_effect_of_warp.pdf"],
        ".": []
    }
}
```

`"chap01": ["lf_recon_schema.pdf", "methods_by_date_and_result.pdf"]`表示将这两个文件复制到`latex_pic_dir/chap01`目录下。

### 3. 运行工具

通过命令行运行工具，支持以下参数：

```bash
python drawio_automation.py <input_path> [output_path] [options]
```

#### 参数说明

| 参数                   | 说明                                                         |
| ---------------------- | ------------------------------------------------------------ |
| `input_path`           | 输入的 `.drawio` 文件或文件夹路径（必填）                    |
| `output_path`          | 输出的文件或文件夹路径（可选，默认为输入路径）               |
| `-b, --batch`          | 批量处理文件夹及其子目录下的所有 `.drawio` 文件              |
| `-g, --git-changes`    | 仅处理 Git 检测到的已变更的 `.drawio` 文件                   |
| `-k, --keep-structure` | 在输出文件夹中保持输入文件夹的相对目录结构（仅当 `output_path` 为文件夹时生效） |
| `-m, --migration`      | 将生成的 PDF 文件迁移到 LaTeX 项目目录中                     |
| `--debug`              | 启用调试模式，打印详细日志信息                               |

---

## 使用示例

### 示例 1：处理单个文件

将 `example.drawio` 转换为 PDF，并保存到当前目录：

```bash
python drawio_automation.py example.drawio
```

### 示例 2：处理文件夹

批量处理 `examples/` 文件夹下的所有 `.drawio` 文件，并将 PDF 保存到 `output/` 文件夹中：

```bash
python drawio_automation.py examples/ output/ -b
```

### 示例 3：处理 Git 变更文件

仅处理 Git 检测到的已变更的 `.drawio` 文件，并将 PDF 保存到 `output/` 文件夹中：

```bash
python drawio_automation.py examples/ output/ -g
```

### 示例 4：保持目录结构

批量处理 `examples/` 文件夹及其子目录下的 `.drawio` 文件，并在 `output/` 文件夹中保持目录结构：

```bash
python drawio_automation.py examples/ output/ -b -k
```

### 示例 5：迁移到 LaTeX 项目

将生成的 PDF 文件迁移到 LaTeX 项目的图片目录中：

```bash
python drawio_automation.py examples/ output/ -b -m
```

---

## 注意事项

1. **路径配置**：
   - 确保 `config.json` 中的 `latex_pic_dir` 路径正确。
   - 确保 `draw.io`、`Edge` 和 `pdfcrop` 的路径在代码中正确配置。

2. **Git 变更检测**：
   - 使用 `-g` 参数时，确保当前目录是 Git 仓库，并且已安装 Git。

3. **调试模式**：
   - 使用 `--debug` 参数可以查看详细的日志信息，便于排查问题。

---

## 其他说明

- **配置文件动态加载**：`config.json` 中的配置可以动态修改，无需修改代码。
- **日志输出**：建议使用 `logging` 模块替代 `print`，便于控制日志级别和输出格式。
- **错误处理**：工具已增加基本的错误处理逻辑，避免因权限问题或文件锁定导致程序崩溃。

---

## 贡献与反馈

如有任何问题或建议，欢迎提交 Issue 或 Pull Request。

---

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

---

希望这份 `README.md` 文件能满足你的需求！如果有其他问题或需要进一步修改，请随时告诉我。