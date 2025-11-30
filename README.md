# 数据集格式转换工具 / Dataset Format Converter

一个简单易用的Web应用，支持VOC和YOLO数据集格式的双向转换。专为新手设计，只需输入几个路径即可完成转换。

## ✨ 特性

- 🔄 **双向转换**：支持 VOC ↔ YOLO 格式互转
- 🎨 **现代界面**：美观的深色主题UI，操作简单直观
- 🚀 **批量处理**：自动处理整个目录的标注文件
- 📊 **实时反馈**：显示转换进度和详细结果
- 🏷️ **自动检测**：VOC转YOLO时自动检测类别
- ⚡ **快速高效**：基于Python的高性能转换

## 📋 系统要求

- Python 3.7+
- Flask
- Pillow (PIL)

## 📦 下载使用

### 方式一：下载可执行文件（推荐）

从 [Releases](https://github.com/GGbao8848/self_tools/releases) 页面下载对应平台的可执行文件：

- **Windows**: `self_tools-windows.exe`
- **macOS**: `self_tools-macos`
- **Linux**: `self_tools-linux`

下载后直接双击运行，浏览器会自动打开应用界面。

### 方式二：从源码运行


### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务器

```bash
python dev_server.py
```

### 3. 打开浏览器

访问：http://localhost:5000

## 📖 使用说明

### VOC → YOLO 转换

1. 选择转换方向：**VOC → YOLO**
2. 填写以下路径：
   - **标注文件目录**：包含 `.xml` 文件的目录
   - **图片文件目录**：包含对应图片的目录
   - **输出目录**：转换后的文件保存位置
   - **类别文件**（可选）：`classes.txt` 文件路径，如不提供将自动生成
3. 点击"开始转换"

**输出文件：**
- 每个XML文件对应一个 `.txt` 标注文件
- 自动生成 `classes.txt` 类别文件

### YOLO → VOC 转换

1. 选择转换方向：**YOLO → VOC**
2. 填写以下路径：
   - **标注文件目录**：包含 `.txt` 文件的目录
   - **图片文件目录**：包含对应图片的目录
   - **输出目录**：转换后的文件保存位置
   - **类别文件**（必需）：`classes.txt` 文件路径
3. 点击"开始转换"

**输出文件：**
- 每个TXT文件对应一个 `.xml` 标注文件

## 📁 目录结构示例

```
dataset/
├── images/              # 图片目录
│   ├── img001.jpg
│   ├── img002.jpg
│   └── ...
├── annotations/         # 标注目录
│   ├── img001.xml      # VOC格式
│   └── img002.xml
└── classes.txt         # 类别文件（每行一个类别）
```

## 📝 格式说明

### VOC 格式 (XML)

```xml
<annotation>
  <size>
    <width>640</width>
    <height>480</height>
  </size>
  <object>
    <name>cat</name>
    <bndbox>
      <xmin>100</xmin>
      <ymin>150</ymin>
      <xmax>300</xmax>
      <ymax>350</ymax>
    </bndbox>
  </object>
</annotation>
```

### YOLO 格式 (TXT)

```
0 0.3125 0.5208 0.3125 0.4167
```

格式：`class_id x_center y_center width height`（所有坐标已归一化）

### Classes 文件

```
cat
dog
person
car
```

每行一个类别名称，行号对应类别ID（从0开始）

## 🔧 API 接口

### POST /api/convert

**请求体：**

```json
{
  "conversion_type": "voc_to_yolo",
  "annotations_dir": "/path/to/annotations",
  "images_dir": "/path/to/images",
  "output_dir": "/path/to/output",
  "classes_file": "/path/to/classes.txt"
}
```

**响应：**

```json
{
  "success": true,
  "converted": 100,
  "skipped": 2,
  "total": 102,
  "classes": ["cat", "dog", "person"],
  "errors": []
}
```

## ⚠️ 注意事项

1. **路径要求**：请使用绝对路径，确保路径存在且有读写权限
2. **文件命名**：标注文件名应与图片文件名一致（扩展名除外）
3. **类别文件**：
   - VOC→YOLO：可选，不提供时自动生成
   - YOLO→VOC：必需，确保类别顺序正确
4. **图片格式**：支持 `.jpg`, `.jpeg`, `.png`, `.bmp`
5. **输出目录**：如不存在会自动创建

## 🐛 故障排除

### 转换失败

- 检查路径是否正确
- 确认文件权限
- 查看错误提示信息

### 找不到图片

- 确保图片文件名与标注文件名匹配
- 检查图片格式是否支持

### 类别ID错误

- 确认 `classes.txt` 文件格式正确
- 检查类别顺序是否与训练时一致

## 📄 许可证

MIT License

## 🔧 开发者

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/GGbao8848/self_tools.git
cd self_tools

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器
python dev_server.py
```

### 发布新版本

详细的发布流程请参考 [RELEASE.md](RELEASE.md)

简要步骤：
```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions 会自动构建并发布到 Releases。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**提示**：首次使用建议先用少量文件测试，确认转换结果正确后再批量处理。
