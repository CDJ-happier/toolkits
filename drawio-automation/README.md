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

ps: vscode + drawio插件不支持导出为pdf，但drawio桌面版支持，并且还支持crop。因此，仅使用drawio桌面版就可进行自动化。

---

# Draw.io Automation Tool

## 概述

`drawio_automation.py` 是一个用于自动化处理 Draw.io 文件的 Python 脚本。它可以将 `.drawio` 文件批量导出为多种格式（如 PDF、SVG、PNG、JPG 等），并支持根据 Git 检测到的变更文件进行选择性导出。此外，该工具还支持将生成的 PDF 文件迁移到 LaTeX 项目目录中，以便在 LaTeX 文档中直接使用。

目录结构：

```txt
drawio-automation/
├── config_drawio_migration.json                # 迁移配置文件，定义 LaTeX 项目目录和文件迁移规则
├── drawio_automation.py       # 主程序文件
├── README.md                  # 项目说明文档
└── requirements.txt           # 依赖文件（可选）
```

## 功能

- **批量导出**：将指定文件夹下的所有 `.drawio` 文件导出为 PDF、SVG、PNG、JPG 等格式。
- **Git 变更检测** (:heart_eyes:)：支持仅处理 Git 检测到的变更文件，减少不必要的导出操作。
- **目录结构保持**：在导出时可以选择保持输入文件夹的相对目录结构。
- **LaTeX 项目迁移** (:+1:)：将生成的 PDF 文件自动迁移到 LaTeX 项目目录中，方便在 LaTeX 文档中使用。
- **多种导出选项**：支持设置导出比例、边框宽度、JPEG 质量、透明背景等选项。

## 使用说明

### 1. 安装依赖

确保已安装 Python 3.x 和 Draw.io Desktop 应用程序。Draw.io Desktop 的 CLI 路径需要在脚本中配置（默认为 `D:\Program Files\draw.io\draw.io.exe`）。

### 2. 配置文件

ps：如果没有迁移需求，则不需要配置文件。

在运行脚本之前，需要创建一个名为 `config_drawio_migration.json` 的配置文件，用于指定 LaTeX 项目的图片目录和需要复制的文件列表。配置文件格式如下：

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

### 3. 运行脚本

通过命令行运行脚本，支持以下参数：

```bash
python drawio_automation.py <input_path> [output_path] [options]
```

#### 参数说明

- `input_path`：输入的 `.drawio` 文件或包含 `.drawio` 文件的文件夹路径。
- `output_path`：输出的文件或文件夹路径（可选，默认为输入路径）。
- `-x, --export-types`：导出的文件格式（如 `pdf`, `svg`, `png`, `jpg`），默认为 `pdf`。
- `-g, --git-changes`：仅处理 Git 检测到的变更文件。
- `-k, --keep-structure`：保持输入文件夹的相对目录结构。
- `-m, --migration`：将生成的 PDF 文件迁移到 LaTeX 项目目录。
- `-q, --quality-jpg`：JPEG 导出质量（1-100），默认为 85。
- `--debug`：启用调试模式，显示更多执行信息。

### 4. 示例

#### 示例 1：导出单个文件为 PDF 和 SVG

```bash
python drawio_automation.py example.drawio -x pdf svg
```

#### 示例 2：批量导出文件夹中的所有 `.drawio` 文件为 PDF 和 PNG

```bash
python drawio_automation.py ./drawio_files -x pdf png
```

#### 示例 3：仅处理 Git 检测到的变更文件并保持目录结构

```bash
python drawio_automation.py ./drawio_files -g -k
```

#### 示例 4：导出并迁移到 LaTeX 项目目录

```bash
python drawio_automation.py ./drawio_files -m
```

## 其他说明

- **Draw.io CLI 路径**：如果 Draw.io Desktop 的 CLI 路径与默认路径不同，请在脚本中修改 `DRAWIO_EXE_PATH` 变量。
- **Git 路径**：确保 Git 可执行文件已添加到系统的 PATH 环境变量中。
- **调试模式**：启用调试模式可以查看详细的执行信息，帮助排查问题。

## 注意事项

- 该脚本依赖于 Draw.io Desktop 的 CLI 功能，因此需要安装 Draw.io Desktop 应用程序。
- 在迁移到 LaTeX 项目目录时，确保 `config_drawio_migration.json` 文件中的路径配置正确。

## 贡献

欢迎提交 Issue 或 Pull Request 来改进此工具。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

