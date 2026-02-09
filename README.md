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
Python 建议使用 3.9 - 3.12（当前依赖组合未对 3.13 做兼容保证）。

### 2. 一次性 Bootstrap（首次/依赖更新后）

```bash
./scripts/bootstrap_dev.sh
```

### 3. 纯启动（不重复安装依赖/不重复构建）

```bash
./start.sh
```

说明：若首次启动且 `.venv` 不存在，`start.sh` 会自动执行一次 bootstrap；后续启动不会重复安装依赖。
对于 `build_runtime_bundle.sh` 产出的运行包，`start.sh` 在自动 bootstrap 时会跳过前端 npm 安装与构建（直接使用已打包的 `frontend/dist`）。

默认地址：

- 首页：`http://localhost:8080`
- 后端 API：`http://127.0.0.1:5000`

端口冲突处理（默认自动避让）：

```bash
# 默认 ./start.sh 也会自动寻找可用端口
./start.sh --auto-port

# 也可手动指定端口
./start.sh --backend-port 5001 --frontend-port 8081

# 如需冲突即失败（不自动改端口）
./start.sh --no-auto-port
```

需要时可手动重新 bootstrap：

```bash
./start.sh --bootstrap
```

### 4. 无 Node.js 运行包（部署机器可不安装 Node）

在构建机执行：

```bash
./scripts/build_runtime_bundle.sh
# 或
python3 scripts/build_runtime_bundle.py
```

生成物位于：

- 目录：`release/self_tools_runtime_<timestamp>/`
- 压缩包：`release/self_tools_runtime_<timestamp>.tar.gz`
- 压缩包：`release/self_tools_runtime_<timestamp>.zip`

运行机解压后直接执行：

```bash
./start.sh
```

说明：

- 运行包已包含 `frontend/dist`，运行时不依赖 Node.js。
- 运行包已包含 `wheelhouse/`，首次启动可离线安装 Python 依赖。
- 启动时会检测 `frontend/dist/cv-tools.html` 是否存在；若缺失会给出友好提示。
- 若系统默认是 Python 3.13，可指定解释器启动：
  `SELF_TOOLS_PYTHON=/usr/bin/python3 ./start.sh`

### 5. 停止

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
- 多 worker 并发执行（`SELF_TOOLS_MAX_WORKERS`，默认自动按硬件设置）
- 失败自动重试（`max_retries` 请求参数）
- 任务历史追踪（`/api/task/<task_id>/history`）
- 进度写入节流（默认启用）：
  `SELF_TOOLS_PROGRESS_MIN_INTERVAL_MS`（默认 `300`）、
  `SELF_TOOLS_PROGRESS_MIN_DELTA`（默认 `1`）

### 统一并发策略（自动按硬件）

后端工具并发由 `backend/parallelism_config.py` 统一管理，默认会根据 CPU 核心数和任务规模自动选择串行/线程池/进程池，避免小批量任务被过度并行拖慢。
已覆盖主要长任务工具：`converter/cropper/generator/splitter/deduplicator/matcher/visualizer/augmentor/label_modifier/cleaner/paper_grid_generator`。

- `SELF_TOOLS_RESERVED_CPUS`：预留 CPU 核心数（默认 4 核及以上机器预留 1 核）
- `SELF_TOOLS_MIN_PARALLEL_ITEMS`：小于该任务量时强制串行（默认 `4`）
- `SELF_TOOLS_PROCESS_MIN_ITEMS`：达到该任务量后 CPU 型任务优先进程池（默认 `24`）
- `SELF_TOOLS_MAX_POOL_WORKERS`：线程池/进程池统一上限（默认不限）
- `SELF_TOOLS_MAX_PROCESS_WORKERS`：进程池上限（默认不限）
- `SELF_TOOLS_MAX_THREAD_WORKERS`：线程池上限（默认不限）
- `SELF_TOOLS_FORCE_EXECUTOR`：强制执行器类型（`auto`/`serial`/`thread`/`process`）
- `SELF_TOOLS_FORCE_WORKERS`：强制线程/进程数量（默认不强制）

### 新功能接入模板（后端）

新增异步工具接口时，建议复用 `backend/routes/utils.py` 中的两个抽象：

- `queue_json_task(...)`：统一参数解析、任务入队、进度回调、完成态收敛
- `run_with_error_handling(...)`：统一 `ValidationError` 与内部异常响应

可参考 `backend/routes/split.py`、`backend/routes/match.py`、`backend/routes/visualize.py` 的写法。

### 新功能接入模板（前端）

新增工具组件时，建议优先复用以下抽象：

- `useToolTask(...)`：统一任务启动/完成/失败/停止结果收敛
- `useDatasetPathInference(...)`：统一 `images/annotations/output` 路径自动推断
- `TaskController`：统一任务进度、暂停/恢复/终止与状态展示

### 工具执行链埋点（前端）

前端统一在 `useTaskRunner` 里上报任务埋点事件：

- `tool_task_started`
- `tool_task_completed`
- `tool_task_failed`
- `tool_task_stopped`

每条事件默认包含 `tool_name`、`task_id`、`duration_ms`（终态事件）等字段。  
事件会被推入 `window.__SELF_TOOLS_TASK_TELEMETRY__`（最多 200 条），并通过浏览器事件 `self-tools:task-telemetry` 分发，便于外部监控接入。

## 打包发布

推送 `v*` 标签后，GitHub Actions 会自动构建三平台可执行文件并发布到 Releases。

- Windows: `self_tools-windows.exe`
- macOS: `self_tools-macos`
- Linux: `self_tools-linux`

详细流程见 `RELEASE.md`。
