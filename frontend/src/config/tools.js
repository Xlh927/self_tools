export const TOOLS = [
    {
        id: 'converter',
        name: '数据集格式转换',
        icon: 'arrow-path',
        description: 'VOC ↔ YOLO 格式互转',
        gradient: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
    },
    {
        id: 'cropper',
        name: '图像滑窗裁剪',
        icon: 'scissors',
        description: '滑窗方式裁剪大图',
        gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    },
    {
        id: 'generator',
        name: '数据集生成器',
        icon: 'target',
        description: '从大图标注生成小型数据集',
        gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    },
    {
        id: 'splitter',
        name: '数据集划分',
        icon: 'chart-bar',
        description: '智能划分训练集、验证集和测试集',
        gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    },
    {
        id: 'deduplicator',
        name: '图像去重',
        icon: 'trash-2',
        description: '智能检测并删除重复图像',
        gradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    },
    {
        id: 'matcher',
        name: '图像匹配',
        icon: 'search',
        description: '根据参考文件夹筛选并复制图像',
        gradient: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    },
    {
        id: 'visualizer',
        name: '标注可视化',
        icon: 'eye',
        description: '自动检测标注格式并可视化',
        gradient: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
    },
    {
        id: 'label-modifier',
        name: 'YOLO 标签修改',
        icon: 'tag',
        description: '批量修改 YOLO 标签类别 ID',
        gradient: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
    },
    {
        id: 'augmentor',
        name: '数据集增强',
        icon: 'sparkles',
        description: '通过图像变换扩充数据集',
        gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    },
    {
        id: 'grid-generator',
        name: '论文宫格排版',
        icon: 'layout-grid',
        description: '生成学术论文风格的图片对比网格',
        gradient: 'linear-gradient(135deg, #2196f3 0%, #00bcd4 100%)',
    },
    {
        id: 'cleaner',
        name: '数据集清洗',
        icon: 'sparkle',
        description: '筛选并移动无标注图像到背景目录',
        gradient: 'linear-gradient(135deg, #7028e4 0%, #e5b2ca 100%)',
    },
    {
        id: 'slurm-generator',
        name: 'Slurm 命令生成',
        icon: 'rocket',
        description: '生成 YOLO 训练的 Slurm 提交命令',
        gradient: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)',
    },
];

export function getToolById(toolId) {
    return TOOLS.find((tool) => tool.id === toolId);
}
