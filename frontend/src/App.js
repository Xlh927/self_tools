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

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

// Tool definitions
const TOOLS = [
    {
        id: 'converter',
        name: '数据集格式转换',
        icon: '🔄',
        description: 'VOC ↔ YOLO 格式互转',
        gradient: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
    },
    {
        id: 'cropper',
        name: '图像滑窗裁剪',
        icon: '✂️',
        description: '滑窗方式裁剪大图',
        gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
    },
    {
        id: 'generator',
        name: '数据集生成器',
        icon: '🎯',
        description: '从大图标注生成小型数据集',
        gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
    },
    {
        id: 'splitter',
        name: '数据集划分',
        icon: '📊',
        description: '智能划分训练集、验证集和测试集',
        gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
    },
    {
        id: 'deduplicator',
        name: '图像去重',
        icon: '🗑️',
        description: '智能检测并删除重复图像',
        gradient: 'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',
    },
    {
        id: 'matcher',
        name: '图像匹配',
        icon: '🔍',
        description: '根据参考文件夹筛选并复制图像',
        gradient: 'linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)',
    },
    {
        id: 'visualizer',
        name: '标注可视化',
        icon: '👁️',
        description: '自动检测标注格式并可视化',
        gradient: 'linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%)',
    },
    {
        id: 'label-modifier',
        name: 'YOLO 标签修改',
        icon: '🏷️',
        description: '批量修改 YOLO 标签类别 ID',
        gradient: 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
    },
    {
        id: 'augmentor',
        name: '数据集增强',
        icon: '📊',
        description: '通过图像变换扩充数据集',
        gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    },
    {
        id: 'grid-generator',
        name: '论文宫格排版',
        icon: '📑',
        description: '生成学术论文风格的图片对比网格',
        gradient: 'linear-gradient(135deg, #2196f3 0%, #00bcd4 100%)',
    },
    {
        id: 'slurm-generator',
        name: 'Slurm 命令生成',
        icon: '🚀',
        description: '生成 YOLO 训练的 Slurm 提交命令',
        gradient: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a6f 100%)',
    },
];

function App() {
    // State for active tools on the canvas
    const [activeTools, setActiveTools] = useState([]);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [sidebarPosition, setSidebarPosition] = useState('top'); // left, right, top, bottom
    const [currentTheme, setCurrentTheme] = useState(() => {
        return localStorage.getItem('app-theme') || 'default';
    });
    const [nextInstanceId, setNextInstanceId] = useState(1);
    const canvasRef = useRef(null);

    const isHorizontal = sidebarPosition === 'top' || sidebarPosition === 'bottom';

    // Apply theme to document root
    useEffect(() => {
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('app-theme', currentTheme);
    }, [currentTheme]);

    const addTool = (toolId) => {
        setActiveTools(prev => [...prev, { instanceId: nextInstanceId, toolId, resetKey: 0 }]);
        setNextInstanceId(prev => prev + 1);
        setTimeout(() => {
            if (canvasRef.current) {
                canvasRef.current.scrollTo({
                    left: canvasRef.current.scrollWidth, // Scroll horizontal
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
                        width: 'calc(100% - var(--spacing-md) * 2)',
                        height: sidebarCollapsed ? '80px' : 'auto',
                        flexDirection: 'row',
                        alignItems: 'center',
                        overflowX: 'auto',
                        overflowY: 'hidden',
                    } : {
                        height: 'calc(100vh - var(--spacing-md) * 2)',
                        width: sidebarCollapsed ? '90px' : '280px',
                        flexDirection: 'column',
                        overflowY: 'auto',
                        overflowX: 'hidden',
                    })
                }
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
                    }
                },
                // Logo / Title
                !sidebarCollapsed && e('div',
                    {
                        style: {
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px'
                        }
                    },
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
                                    fontSize: '1.2rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    background: 'var(--bg-tertiary)',
                                    padding: '4px',
                                    borderRadius: ' var(--radius-sm)',
                                    border: '1px solid var(--glass-border)',
                                    color: 'var(--text-primary)',
                                    transition: 'all 0.2s'
                                },
                                onMouseEnter: (e) => {
                                    e.currentTarget.style.background = 'var(--bg-secondary)';
                                    e.currentTarget.style.transform = 'scale(1.1)';
                                },
                                onMouseLeave: (e) => {
                                    e.currentTarget.style.background = 'var(--bg-tertiary)';
                                    e.currentTarget.style.transform = 'scale(1)';
                                }
                            },
                            '🏠'
                        ),
                        e('div',
                            {
                                style: {
                                    fontSize: '1.2rem',
                                    fontWeight: 'bold',
                                    background: 'var(--gradient-primary)',
                                    WebkitBackgroundClip: 'text',
                                    WebkitTextFillColor: 'transparent',
                                    whiteSpace: 'nowrap',
                                }
                            },
                            '图像处理工作台'
                        )
                    )
                ),

                // Collapse Button
                e('button',
                    {
                        onClick: () => setSidebarCollapsed(!sidebarCollapsed),
                        className: 'btn-ghost',
                        style: {
                            padding: '5px',
                            borderRadius: '50%',
                            width: '32px',
                            height: '32px',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                        }
                    },
                    isHorizontal
                        ? (sidebarCollapsed ? '↕️' : '↕️')
                        : (sidebarCollapsed ? '↔️' : '↔️')
                )
            ),

            // Tools List
            e('nav',
                {
                    style: {
                        display: 'flex',
                        flexDirection: isHorizontal ? 'row' : 'column',
                        gap: 'var(--spacing-sm)',
                        flex: 1,
                        overflow: 'auto',
                    }
                },
                ...TOOLS.map(tool =>
                    e('button',
                        {
                            key: tool.id,
                            onClick: () => addTool(tool.id),
                            className: 'tool-btn',
                            title: tool.name,
                            style: {
                                background: 'var(--bg-tertiary)',
                                border: '1px solid var(--glass-border)',
                                borderRadius: 'var(--radius-md)',
                                padding: '0.4rem',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: isHorizontal ? 'column' : 'row',
                                alignItems: 'center',
                                gap: '0.35rem',
                                transition: 'all 0.2s',
                                minWidth: isHorizontal ? '60px' : 'auto',
                                justifyContent: isHorizontal || sidebarCollapsed ? 'center' : 'flex-start',
                                position: 'relative',
                                overflow: 'hidden',
                            },
                            onMouseEnter: (e) => {
                                e.currentTarget.style.borderColor = 'var(--primary-blue)';
                                e.currentTarget.style.background = 'var(--bg-secondary)';
                                e.currentTarget.style.transform = 'scale(1.03)';
                            },
                            onMouseLeave: (e) => {
                                e.currentTarget.style.borderColor = 'var(--glass-border)';
                                e.currentTarget.style.background = 'var(--bg-tertiary)';
                                e.currentTarget.style.transform = 'scale(1)';
                            }
                        },
                        e('span', { style: { fontSize: '1.2rem' } }, tool.icon),
                        (!sidebarCollapsed && !isHorizontal) && e('span',
                            { style: { fontSize: '0.8rem', whiteSpace: 'nowrap', color: 'var(--text-primary)' } },
                            tool.name
                        ),
                        (isHorizontal) && e('span',
                            { style: { fontSize: '0.65rem', whiteSpace: 'nowrap', color: 'var(--text-primary)' } },
                            tool.name
                        )
                    )
                )
            ),

            !sidebarCollapsed && e('div',
                {
                    style: {
                        marginTop: isHorizontal ? 0 : 'auto',
                        marginLeft: isHorizontal ? 'auto' : 0,
                        display: 'flex',
                        flexDirection: isHorizontal ? 'row' : 'column',
                        gap: 'var(--spacing-md)',
                        paddingTop: isHorizontal ? 0 : 'var(--spacing-md)',
                        borderTop: isHorizontal ? 'none' : '1px solid var(--glass-border)',
                        alignItems: 'center', // Always center vertically
                        justifyContent: isHorizontal ? 'flex-end' : 'stretch',
                    }
                },
                // Task Status & Clear All - Shared container with Theme Switcher for better alignment
                e('div', {
                    style: {
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.6rem',
                        padding: '0.2rem 0.6rem',
                        background: 'var(--bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--glass-border)',
                        height: '36px', // Fixed height for alignment
                    }
                },
                    e('span', { style: { color: 'var(--text-secondary)', fontSize: '0.75rem', whiteSpace: 'nowrap', fontWeight: 600 } },
                        `${activeTools.length} 任务`
                    ),
                    activeTools.length > 0 && e('button',
                        {
                            onClick: () => {
                                if (confirm(`确定要清除所有 ${activeTools.length} 个任务吗？`)) {
                                    setActiveTools([]);
                                }
                            },
                            title: '清除所有',
                            style: {
                                background: 'transparent',
                                border: 'none',
                                cursor: 'pointer',
                                fontSize: '0.9rem',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                padding: '2px',
                                borderRadius: '4px',
                                transition: 'all 0.2s'
                            },
                            onMouseEnter: (e) => e.currentTarget.style.background = 'rgba(255,100,100,0.1)',
                            onMouseLeave: (e) => e.currentTarget.style.background = 'transparent',
                        },
                        '🗑️'
                    ),
                    // Vertical Divider
                    e('div', { style: { width: '1px', height: '16px', background: 'var(--glass-border)', margin: '0 2px' } }),
                    // Theme Switcher Integrated
                    ...[
                        { id: 'default', icon: '💎' },
                        { id: 'douyin', icon: '🎵' },
                        { id: 'youtube', icon: '📺' }
                    ].map(theme =>
                        e('button',
                            {
                                key: theme.id,
                                onClick: () => setCurrentTheme(theme.id),
                                style: {
                                    padding: '0.3rem 0.6rem',
                                    background: currentTheme === theme.id ? 'var(--gradient-primary)' : 'transparent',
                                    color: currentTheme === theme.id ? 'white' : 'var(--text-secondary)',
                                    border: 'none',
                                    borderRadius: 'var(--radius-sm)',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem',
                                    transition: 'all 0.2s',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                },
                            },
                            theme.icon
                        )
                    )
                ),
                // Layout Control
                e('div',
                    {
                        style: {
                            display: 'flex',
                            flexDirection: isHorizontal ? 'row' : 'column',
                            gap: '8px',
                            alignItems: 'center',
                            background: 'var(--bg-tertiary)',
                            padding: '0.2rem 0.6rem',
                            borderRadius: 'var(--radius-md)',
                            border: '1px solid var(--glass-border)',
                            height: '36px', // Match height
                        }
                    },
                    e('div', { style: { fontSize: '0.65rem', color: 'var(--text-tertiary)', whiteSpace: 'nowrap' } }, '固定位置'),
                    e('div', { style: { display: 'flex', gap: '4px' } },
                        ['left', 'right', 'top', 'bottom'].map(pos =>
                            e('button',
                                {
                                    key: pos,
                                    onClick: () => setSidebarPosition(pos),
                                    style: {
                                        background: sidebarPosition === pos ? 'var(--primary-blue)' : 'transparent',
                                        color: sidebarPosition === pos ? 'white' : 'var(--text-secondary)',
                                        border: '1px solid var(--glass-border)',
                                        borderRadius: '4px',
                                        width: '22px',
                                        height: '22px',
                                        cursor: 'pointer',
                                        fontSize: '0.65rem',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        transition: 'all 0.2s',
                                    },
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
                borderTop: `4px solid transparent`,
                backgroundImage: `linear-gradient(var(--bg-tertiary), var(--bg-tertiary)), ${tool.gradient}`,
                backgroundOrigin: 'border-box',
                backgroundClip: 'padding-box, border-box',
                ...style // Apply passed styles
            }
        },
        // Close button
        e('button',
            {
                onClick: onClose,
                style: {
                    position: 'absolute',
                    top: 'var(--spacing-md)',
                    right: 'var(--spacing-md)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-tertiary)',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    padding: '5px',
                    borderRadius: '50%',
                    transition: 'all 0.2s',
                    zIndex: 10,
                },
                onMouseEnter: (e) => {
                    e.currentTarget.style.background = 'rgba(255, 0, 0, 0.2)';
                    e.currentTarget.style.color = '#ff5252';
                },
                onMouseLeave: (e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-tertiary)';
                }
            },
            '✕'
        ),

        // Reset button
        e('button',
            {
                onClick: onReset,
                title: '重置为初始状态',
                style: {
                    position: 'absolute',
                    top: 'var(--spacing-md)',
                    right: 'calc(var(--spacing-md) + 40px)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--text-tertiary)',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    padding: '5px',
                    borderRadius: '50%',
                    transition: 'all 0.2s',
                    zIndex: 10,
                },
                onMouseEnter: (e) => {
                    e.currentTarget.style.background = 'rgba(33, 150, 243, 0.2)';
                    e.currentTarget.style.color = 'var(--primary-blue)';
                    e.currentTarget.style.transform = 'rotate(180deg)';
                },
                onMouseLeave: (e) => {
                    e.currentTarget.style.background = 'transparent';
                    e.currentTarget.style.color = 'var(--text-tertiary)';
                    e.currentTarget.style.transform = 'rotate(0deg)';
                }
            },
            '🔄'
        ),

        e('div',
            {
                style: {
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--spacing-md)',
                    marginBottom: 'var(--spacing-xl)',
                    paddingBottom: 'var(--spacing-lg)',
                    borderBottom: '2px solid var(--glass-border)',
                    flexShrink: 0, // Header shouldn't shrink
                }
            },
            e('span', { style: { fontSize: '2.5rem' } }, tool.icon),
            e('div',
                {},
                e('h2',
                    {
                        style: {
                            margin: 0,
                            marginBottom: '0.2rem',
                            fontSize: '1.5rem',
                        }
                    },
                    tool.name
                ),
                e('p',
                    {
                        style: {
                            margin: 0,
                            color: 'var(--text-secondary)',
                            fontSize: '0.9rem',
                        }
                    },
                    tool.description
                )
            )
        ),

        // Tool-specific content
        e('div', {
            className: 'tool-content',
            style: {
                flex: 1,
                overflowY: 'auto', // Internal scroll
                paddingRight: '5px', // Space for scrollbar
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
            toolId === 'slurm-generator' && e(SlurmGeneratorTool, { key: resetKey })
        )
    );
}

export default App;
