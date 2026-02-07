# Self Tools - CV 数据集工具平台

Self Tools 是一个面向计算机视觉数据集处理的本地化工具平台。  
它将数据集转换、清洗、增强、可视化和浏览归拢到同一套 Web 界面中，适合日常标注集生产与训练前准备。

## 功能定位

- 一个应用，覆盖数据集处理全流程
- 本地运行，不依赖云端服务
- 任务可视化进度，支持暂停/恢复/终止

## 功能清单（CV Tools）

- 数据集格式转换：VOC ↔ YOLO
- 图像滑窗裁剪：大图切片
- 数据集生成器：按标注生成训练样本
- 数据集划分：训练/验证/测试拆分
- 图像去重：哈希与相似度检测
- 图像匹配：按参考集合筛选复制
- 标注可视化：标注渲染检查
- YOLO 标签修改：类别 ID 批量映射
- 数据集增强：翻转/旋转等扩增
- 论文宫格排版：对比图网格输出
- Slurm 命令生成：YOLO 训练命令模板
- 数据集清洗：无标注背景样本分离

## 功能清单（Image Viewer）

- 本地目录快速浏览与缩略图缓存
- 快捷键分类/反分类
- 分类目录联动与统计

## 运行方式

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

前端使用 Vite 构建，需安装 Node.js 18+（含 `npm`）。

### 2. 启动（推荐）

```bash
./scripts/dev_up.sh
```

默认地址：

- 首页：`http://localhost:8080`
- 后端 API：`http://127.0.0.1:5000`

### 3. 停止

在启动终端按 `Ctrl+C`，脚本会自动清理进程。

## 开发测试

### 烟雾测试

```bash
python3 tests/smoke_test.py
```

### 核心 API 测试

```bash
python3 tests/api_core_test.py
```

### 任务队列能力

- SQLite 持久化任务存储（`data/tasks.db`）
- 多 worker 并发执行（`SELF_TOOLS_MAX_WORKERS`）
- 失败自动重试（`max_retries` 请求参数）
- 任务历史追踪（`/api/task/<task_id>/history`）

## 打包发布

推送 `v*` 标签后，GitHub Actions 会自动构建三平台可执行文件并发布到 Releases。

- Windows: `self_tools-windows.exe`
- macOS: `self_tools-macos`
- Linux: `self_tools-linux`

详细流程见 `RELEASE.md`。
