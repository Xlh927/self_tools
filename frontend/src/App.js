import React, { useState, useEffect, useRef } from 'react';
import ConverterTool from './components/tools/ConverterTool.js';
import CropperTool from './components/tools/CropperTool.js';
import GeneratorTool from './components/tools/GeneratorTool.js';
import SplitterTool from './components/tools/SplitterTool.js';
import DeduplicatorTool from './components/tools/DeduplicatorTool.js';
import MatcherTool from './components/tools/MatcherTool.js';
import VisualizerTool from './components/tools/VisualizerTool.js';
import LabelModifierTool from './components/tools/LabelModifierTool.js';
import AugmentorTool from './components/tools/AugmentorTool.js';
import GridGeneratorTool from './components/tools/GridGeneratorTool.js';
import SlurmGeneratorTool from './components/tools/SlurmGeneratorTool.js';
import CleanerTool from './components/tools/CleanerTool.js';
import Icon from './components/common/Icon.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

// Tool definitions
const TOOLS = [
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
        id: 'slurm-generator',
        name: 'Slurm 命令生成',
        icon: 'rocket',
        description: '生成 YOLO 训练的 Slurm 提交命令',
        gradient: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)',
    },
    {
        id: 'cleaner',
        name: '数据集清洗',
        icon: 'sparkle',
        description: '筛选并移动无标注图像到背景目录',
        gradient: 'linear-gradient(135deg, #7028e4 0%, #e5b2ca 100%)',
    },
];

function App() {
    // State for helper data
    const [activeTools, setActiveTools] = useState([]);
    const [sidebarPosition, setSidebarPosition] = useState('top'); // left, right, top, bottom
    const [currentTheme, setCurrentTheme] = useState(() => localStorage.getItem('app-theme') || 'bilibili');
    const [nextInstanceId, setNextInstanceId] = useState(1);
    const canvasRef = useRef(null);

    // Tools Management State
    const [toolList, setToolList] = useState(() => {
        const savedOrder = localStorage.getItem('tool-order');
        if (savedOrder) {
            const orderIds = JSON.parse(savedOrder);
            const orderedTools = orderIds.map(id => TOOLS.find(t => t.id === id)).filter(Boolean);
            // Append any new tools that aren't in saved order
            const newTools = TOOLS.filter(t => !orderIds.includes(t.id));
            return [...orderedTools, ...newTools];
        }
        return TOOLS;
    });

    const [draggedToolId, setDraggedToolId] = useState(null);

    const isHorizontal = sidebarPosition === 'top' || sidebarPosition === 'bottom';

    // Persist settings
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('app-theme', currentTheme);
    }, [currentTheme]);

    useEffect(() => {
        localStorage.setItem('tool-order', JSON.stringify(toolList.map(t => t.id)));
    }, [toolList]);

    // Handlers
    const addTool = (toolId) => {
        setActiveTools(prev => [...prev, { instanceId: nextInstanceId, toolId, resetKey: 0 }]);
        setNextInstanceId(prev => prev + 1);
        setTimeout(() => {
            if (canvasRef.current) {
                canvasRef.current.scrollTo({
                    left: canvasRef.current.scrollWidth,
                    behavior: 'smooth'
                });
            }
        }, 100);
    };

    const removeTool = (instanceId) => {
        setActiveTools(prev => prev.filter(t => t.instanceId !== instanceId));
    };

    const resetTool = (instanceId) => {
        setActiveTools(prev => prev.map(t =>
            t.instanceId === instanceId
                ? { ...t, resetKey: t.resetKey + 1 }
                : t
        ));
    };

    // Drag and Drop Handlers
    const handleDragStart = (e, toolId) => {
        setDraggedToolId(toolId);
        e.dataTransfer.effectAllowed = 'move';
        // Hide the drag image for cleaner look (optional, but standard for custom DnD)
        // const img = new Image();
        // img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
        // e.dataTransfer.setDragImage(img, 0, 0);
    };

    const handleDragOver = (e, targetToolId) => {
        e.preventDefault();
        e.dataTransfer.dropEffect = 'move';

        if (!draggedToolId || draggedToolId === targetToolId) return;

        const sourceIndex = toolList.findIndex(t => t.id === draggedToolId);
        const targetIndex = toolList.findIndex(t => t.id === targetToolId);

        if (sourceIndex === -1 || targetIndex === -1) return;

        // Reorder list
        const newList = [...toolList];
        const [movedTool] = newList.splice(sourceIndex, 1);
        newList.splice(targetIndex, 0, movedTool);
        setToolList(newList);
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setDraggedToolId(null);
    };

    const handleHorizontalScroll = (e) => {
        const container = e.currentTarget;
        if (e.deltaY !== 0) {
            container.scrollLeft += e.deltaY;
            // Only prevent default if we actually scrolled, to allow page scroll if at ends
            // But usually in a full-screen app we want to block it.
            // e.preventDefault(); 
        }
    };

    // Layout configuration
    const layoutStyle = {
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        flexDirection: sidebarPosition === 'left' ? 'row' :
            sidebarPosition === 'right' ? 'row-reverse' :
                sidebarPosition === 'top' ? 'column' : 'column-reverse',
    };

    return e('div',
        { className: 'app-container', style: layoutStyle },


        // Sidebar
        e('aside',
            {
                className: 'sidebar glass-card',
                style: {
                    margin: 'var(--spacing-sm)',
                    padding: 'var(--spacing-md)',
                    borderRadius: 'var(--radius-lg)',
                    border: '1px solid var(--glass-border)',
                    background: 'var(--glass-bg)',
                    backdropFilter: 'blur(20px)',
                    zIndex: 100,
                    transition: 'all var(--transition-normal)',
                    display: 'flex',
                    gap: 'var(--spacing-md)',

                    // Dynamic positioning styles
                    ...(isHorizontal ? {
                        width: 'calc(100% - var(--spacing-sm) * 2)',
                        height: '85px',
                        flexDirection: 'row',
                        alignItems: 'center',
                        overflowX: 'auto',
                    } : {
                        height: 'calc(100vh - var(--spacing-sm) * 2)',
                        width: '260px',
                        flexDirection: 'column',
                        overflowY: 'auto',
                        overflowX: 'hidden',
                    })
                },
                onWheel: isHorizontal ? handleHorizontalScroll : undefined
            },

            // Header / Controls
            e('div',
                {
                    style: {
                        display: 'flex',
                        flexDirection: isHorizontal ? 'row' : 'column',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: 'var(--spacing-sm)',
                        marginBottom: isHorizontal ? 0 : 'var(--spacing-md)',
                        marginRight: isHorizontal ? 'var(--spacing-md)' : 0,
                        borderBottom: isHorizontal ? 'none' : '1px solid var(--glass-border)',
                        borderRight: isHorizontal ? '1px solid var(--glass-border)' : 'none',
                        paddingBottom: isHorizontal ? 0 : 'var(--spacing-sm)',
                        paddingRight: isHorizontal ? 'var(--spacing-sm)' : 0,
                        flexShrink: 0
                    }
                },
                // Logo / Title
                e('div',
                    {
                        style: {
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px'
                        }
                    },
                    e('a',
                        {
                            href: '/',
                            title: '返回主页',
                            style: {
                                textDecoration: 'none',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                background: 'var(--bg-tertiary)',
                                padding: '8px',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid var(--glass-border)',
                                color: 'var(--primary-blue)',
                                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                boxShadow: 'var(--shadow-sm)'
                            },
                            onMouseEnter: (e) => {
                                e.currentTarget.style.transform = 'translateY(-2px) scale(1.05)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-md)';
                                e.currentTarget.style.background = 'var(--bg-secondary)';
                            },
                            onMouseLeave: (e) => {
                                e.currentTarget.style.transform = 'translateY(0) scale(1)';
                                e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                                e.currentTarget.style.background = 'var(--bg-tertiary)';
                            }
                        },
                        e(Icon, { name: 'home', size: 24 })
                    ),
                    !isHorizontal && e('div',
                        {
                            style: {
                                fontSize: '1.25rem',
                                fontWeight: '800',
                                background: 'var(--gradient-primary)',
                                WebkitBackgroundClip: 'text',
                                WebkitTextFillColor: 'transparent',
                                whiteSpace: 'nowrap',
                                letterSpacing: '-0.5px'
                            }
                        },
                        '工作台'
                    )
                ),
            ),

            // Tools List
            e('nav',
                {
                    style: {
                        display: 'grid',
                        gridTemplateColumns: isHorizontal ? 'repeat(auto-fill, var(--nav-btn-width))' : '1fr',
                        gridAutoFlow: isHorizontal ? 'column' : 'row',
                        gap: 'var(--spacing-md)', // Increased gap
                        flex: 1,
                        overflow: isHorizontal ? 'visible' : 'auto',
                    }
                },
                ...toolList.map(tool => {
                    const isDragging = draggedToolId === tool.id;

                    return e('button',
                        {
                            key: tool.id,
                            draggable: true,
                            onDragStart: (e) => handleDragStart(e, tool.id),
                            onDragOver: (e) => handleDragOver(e, tool.id),
                            onDrop: handleDrop,
                            onClick: () => addTool(tool.id),
                            className: `tool-btn ${isDragging ? 'dragging' : ''}`,
                            title: tool.name,
                            style: {
                                width: '100%',
                                height: 'var(--nav-btn-height)',
                                margin: '0 auto'
                            }
                        },
                        e(Icon, { name: tool.icon, size: 24 }),
                        e('span', {}, tool.name)
                    );
                })
            ),

            e('div',
                {
                    style: {
                        marginTop: isHorizontal ? 0 : 'var(--spacing-md)',
                        marginLeft: isHorizontal ? 'var(--spacing-md)' : 0,
                        display: 'flex',
                        flexDirection: isHorizontal ? 'row' : 'column',
                        gap: 'var(--spacing-sm)',
                        paddingTop: isHorizontal ? 0 : 'var(--spacing-sm)',
                        borderTop: isHorizontal ? 'none' : '1px solid var(--glass-border)',
                        alignItems: 'center',
                        justifyContent: isHorizontal ? 'flex-end' : 'stretch',
                        flexShrink: 0
                    }
                },
                // Task Status & Clear All (Prominent Section)
                activeTools.length > 0 && e('div', {
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        gap: '0.8rem',
                        padding: '0.6rem 0.8rem',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--glass-border)',
                        width: '100%',
                    }
                },
                    e('div', { style: { display: 'flex', alignItems: 'center', gap: '8px' } },
                        e('span', { style: { fontSize: '1.2rem' } }, '🚀'),
                        e('span', { style: { color: 'var(--text-primary)', fontSize: '0.95rem', whiteSpace: 'nowrap', fontWeight: 800 } },
                            `${activeTools.length} 个任务`
                        )
                    ),
                    e('button',
                        {
                            onClick: () => {
                                if (confirm(`确定要清除所有 ${activeTools.length} 个任务吗？`)) {
                                    setActiveTools([]);
                                }
                            },
                            title: '一键清空工作区',
                            style: {
                                background: 'var(--color-danger-bg)',
                                color: 'var(--color-danger)',
                                border: '1px solid var(--color-danger)',
                                cursor: 'pointer',
                                fontSize: '0.9rem',
                                padding: '4px 8px',
                                borderRadius: 'var(--radius-sm)',
                                fontWeight: 'bold',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                            }
                        },
                        e('span', {}, '🗑️'),
                        '清空'
                    )
                ),

                // Theme and Layout Controls (Grouped Section)
                e('div', {
                    style: {
                        display: 'flex',
                        flexDirection: isHorizontal ? 'row' : 'row',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        width: '100%',
                        marginTop: isHorizontal ? 0 : 'var(--spacing-sm)',
                        paddingTop: isHorizontal ? 0 : 'var(--spacing-sm)',
                        borderTop: isHorizontal ? 'none' : '1px solid rgba(255,255,255,0.05)',
                        gap: '12px'
                    }
                },
                    // Theme Icons
                    e('div', {
                        style: {
                            display: 'flex',
                            gap: '6px',
                            background: 'var(--bg-tertiary)',
                            padding: '4px',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                        }
                    },
                        [
                            { id: 'bilibili', icon: '📺' },
                            { id: 'default', icon: '💎' },
                            { id: 'douyin', icon: '🎵' },
                            { id: 'youtube', icon: '🔴' }
                        ].map(theme =>
                            e('button',
                                {
                                    key: theme.id,
                                    onClick: () => setCurrentTheme(theme.id),
                                    style: {
                                        width: '28px',
                                        height: '28px',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        background: currentTheme === theme.id ? 'var(--gradient-primary)' : 'transparent',
                                        color: currentTheme === theme.id ? 'white' : 'var(--text-secondary)',
                                        border: 'none',
                                        borderRadius: 'var(--radius-sm)',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem',
                                        transition: 'all 0.2s'
                                    },
                                },
                                theme.icon
                            )
                        )
                    ),

                    // Layout Control Buttons
                    e('div',
                        {
                            style: {
                                display: 'flex',
                                gap: '4px',
                                alignItems: 'center',
                                background: 'var(--bg-tertiary)',
                                padding: '4px',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid var(--glass-border)',
                            }
                        },
                        ['left', 'right', 'top', 'bottom'].map(pos =>
                            e('button',
                                {
                                    key: pos,
                                    onClick: () => setSidebarPosition(pos),
                                    className: `pos-btn ${sidebarPosition === pos ? 'active' : ''}`,
                                    style: {
                                        width: '24px',
                                        height: '24px',
                                        fontSize: '0.7rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }
                                },
                                pos[0].toUpperCase()
                            )
                        )
                    )
                )
            )
        ),

        // Main content
        e('main',
            {
                className: 'main-content',
                style: {
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    position: 'relative',
                    // Add some margin if we want a gap between sidebar and content
                    // But flex gap handles it if we added gap to container? 
                    // No, we didn't add gap to container.
                    padding: 'var(--spacing-sm)',
                }
            },

            // Canvas area
            e('div',
                {
                    ref: canvasRef,
                    onWheel: handleHorizontalScroll,
                    style: {
                        flex: 1,
                        overflowX: 'auto',
                        overflowY: 'hidden', // Tools scroll internally
                        scrollBehavior: 'smooth',
                        display: 'flex',
                        borderRadius: 'var(--radius-lg)',
                        // background: 'rgba(0,0,0,0.2)', // Optional background for canvas
                    }
                },
                e('div',
                    {
                        style: {
                            display: 'flex',
                            flexDirection: 'row',
                            justifyContent: 'center', // Center content
                            gap: 'var(--spacing-md)', // Reduced gap
                            height: '100%',
                            minWidth: '100%',
                            width: 'fit-content',
                            paddingRight: 'var(--spacing-xl)', // End padding
                        }
                    },
                    activeTools.length > 0
                        ? activeTools.map(toolInstance =>
                            e(ToolWorkspace, {
                                key: toolInstance.instanceId,
                                instanceId: toolInstance.instanceId,
                                toolId: toolInstance.toolId,
                                resetKey: toolInstance.resetKey,
                                onClose: () => removeTool(toolInstance.instanceId),
                                onReset: () => resetTool(toolInstance.instanceId),
                                style: {
                                    flex: '1 0 450px',
                                    maxWidth: '800px',
                                    height: '100%',
                                    display: 'flex',
                                    flexDirection: 'column',
                                }
                            })
                        )
                        : e(WelcomeScreen)
                )
            )
        )
    );
}

// Welcome Screen Component
function WelcomeScreen() {
    return e('div',
        {
            className: 'welcome-screen animate-fade-in-up',
            style: {
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%',
                height: '100%',
                textAlign: 'center',
                opacity: 0.8,
            }
        },
        e('div',
            {
                style: {
                    fontSize: '6rem',
                    marginBottom: 'var(--spacing-xl)',
                    animation: 'pulse 2s ease-in-out infinite',
                }
            },
            '🚀'
        ),
        e('h2',
            {
                style: {
                    fontSize: '2.5rem',
                    marginBottom: 'var(--spacing-lg)',
                    background: 'var(--gradient-primary)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                }
            },
            '点击左侧工具添加到工作台'
        ),
        e('p',
            {
                style: {
                    fontSize: '1.2rem',
                    color: 'var(--text-secondary)',
                    maxWidth: '600px',
                }
            },
            '支持同时运行多个任务，构建您的图像处理工作流'
        )
    );
}

// Tool Workspace Component
function ToolWorkspace({ instanceId, toolId, resetKey, onClose, onReset, style }) {
    const tool = TOOLS.find(t => t.id === toolId);

    return e('div',
        {
            className: 'glass-card animate-fade-in-up',
            style: {
                position: 'relative',
                padding: 0, // Reset padding for header bar
                borderTop: 'none', // Removed borderTop, using tool-header-border
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                ...style
            }
        },
        // Consolidated Header Bar
        e('div', { className: 'tool-workspace-header' },
            e('div', { className: 'tool-header-info' },
                e('span', { className: 'tool-header-icon' }, 
                    e(Icon, { name: tool.icon, size: 24 })
                ),
                e('div', { className: 'tool-header-title' },
                    e('h2', {}, tool.name),
                    e('p', {}, tool.description)
                )
            ),
            e('div', { className: 'tool-header-actions' },
                e('button',
                    {
                        onClick: onReset,
                        title: '重置',
                        className: 'action-btn reset'
                    },
                    e(Icon, { name: 'refresh', size: 16 }),
                    '重置面板'
                ),
                e('button',
                    {
                        onClick: onClose,
                        title: '关闭',
                        className: 'action-btn close'
                    },
                    e(Icon, { name: 'x', size: 16 }),
                    '关闭窗口'
                )
            )
        ),

        // Tool-specific content
        e('div', {
            className: 'tool-content',
            style: {
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--spacing-md)',
                paddingTop: 0,
            }
        },
            toolId === 'converter' && e(ConverterTool, { key: resetKey }),
            toolId === 'cropper' && e(CropperTool, { key: resetKey }),
            toolId === 'generator' && e(GeneratorTool, { key: resetKey }),
            toolId === 'splitter' && e(SplitterTool, { key: resetKey }),
            toolId === 'deduplicator' && e(DeduplicatorTool, { key: resetKey }),
            toolId === 'matcher' && e(MatcherTool, { key: resetKey }),
            toolId === 'visualizer' && e(VisualizerTool, { key: resetKey }),
            toolId === 'label-modifier' && e(LabelModifierTool, { key: resetKey }),
            toolId === 'augmentor' && e(AugmentorTool, { key: resetKey }),
            toolId === 'grid-generator' && e(GridGeneratorTool, { key: resetKey }),
            toolId === 'slurm-generator' && e(SlurmGeneratorTool, { key: resetKey }),
            toolId === 'cleaner' && e(CleanerTool, { key: resetKey })
        )
    );
}

export default App;
