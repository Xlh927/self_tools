import React, { useState, useEffect, useRef } from 'react';
import ConverterTool from './components/tools/ConverterTool.js';
import CropperTool from './components/tools/CropperTool.js';
import GeneratorTool from './components/tools/GeneratorTool.js';
import SplitterTool from './components/tools/SplitterTool.js';
import DeduplicatorTool from './components/tools/DeduplicatorTool.js';
import MatcherTool from './components/tools/MatcherTool.js';
import VisualizerTool from './components/tools/VisualizerTool.js';

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
];

function App() {
    // State for active tools on the canvas
    const [activeTools, setActiveTools] = useState([]);
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
    const [sidebarPosition, setSidebarPosition] = useState('left'); // left, right, top, bottom
    const [nextInstanceId, setNextInstanceId] = useState(1);
    const canvasRef = useRef(null);

    const isHorizontal = sidebarPosition === 'top' || sidebarPosition === 'bottom';

    const addTool = (toolId) => {
        setActiveTools(prev => [...prev, { instanceId: nextInstanceId, toolId }]);
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
                            fontSize: '1.2rem',
                            fontWeight: 'bold',
                            background: 'var(--gradient-primary)',
                            WebkitBackgroundClip: 'text',
                            WebkitTextFillColor: 'transparent',
                            whiteSpace: 'nowrap',
                            writingMode: isHorizontal ? 'horizontal-tb' : 'horizontal-tb',
                        }
                    },
                    isHorizontal ? 'AI Toolkit' : 'AI Toolkit'
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
                                padding: 'var(--spacing-sm)',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: isHorizontal ? 'column' : 'row',
                                alignItems: 'center',
                                gap: 'var(--spacing-sm)',
                                transition: 'all 0.2s',
                                minWidth: isHorizontal ? '80px' : 'auto',
                                justifyContent: isHorizontal || sidebarCollapsed ? 'center' : 'flex-start',
                                position: 'relative',
                                overflow: 'hidden',
                            },
                            onMouseEnter: (e) => {
                                e.currentTarget.style.borderColor = 'var(--neon-blue)';
                                e.currentTarget.style.background = 'var(--bg-secondary)';
                                e.currentTarget.style.transform = 'scale(1.05)';
                            },
                            onMouseLeave: (e) => {
                                e.currentTarget.style.borderColor = 'var(--glass-border)';
                                e.currentTarget.style.background = 'var(--bg-tertiary)';
                                e.currentTarget.style.transform = 'scale(1)';
                            }
                        },
                        e('span', { style: { fontSize: '1.5rem' } }, tool.icon),
                        (!sidebarCollapsed && !isHorizontal) && e('span',
                            { style: { fontSize: '0.9rem', whiteSpace: 'nowrap' } },
                            tool.name
                        ),
                        (isHorizontal) && e('span',
                            { style: { fontSize: '0.7rem', whiteSpace: 'nowrap' } },
                            tool.name
                        )
                    )
                )
            ),

            // Layout Controls (Bottom/End of sidebar)
            !sidebarCollapsed && e('div',
                {
                    style: {
                        display: 'flex',
                        flexDirection: isHorizontal ? 'row' : 'column',
                        gap: '5px',
                        marginTop: isHorizontal ? 0 : 'auto',
                        marginLeft: isHorizontal ? 'auto' : 0,
                        paddingTop: isHorizontal ? 0 : 'var(--spacing-sm)',
                        paddingLeft: isHorizontal ? 'var(--spacing-sm)' : 0,
                        borderTop: isHorizontal ? 'none' : '1px solid var(--glass-border)',
                        borderLeft: isHorizontal ? '1px solid var(--glass-border)' : 'none',
                    }
                },
                e('div', { style: { fontSize: '0.7rem', color: 'var(--text-tertiary)', textAlign: 'center' } }, '布局'),
                e('div', { style: { display: 'flex', gap: '2px', flexDirection: isHorizontal ? 'row' : 'row', flexWrap: 'wrap', justifyContent: 'center' } },
                    ['left', 'right', 'top', 'bottom'].map(pos =>
                        e('button',
                            {
                                key: pos,
                                onClick: () => setSidebarPosition(pos),
                                title: `Dock ${pos}`,
                                style: {
                                    background: sidebarPosition === pos ? 'var(--neon-blue)' : 'var(--bg-tertiary)',
                                    color: sidebarPosition === pos ? 'black' : 'var(--text-secondary)',
                                    border: 'none',
                                    borderRadius: '4px',
                                    width: '20px',
                                    height: '20px',
                                    cursor: 'pointer',
                                    fontSize: '10px',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                }
                            },
                            pos[0].toUpperCase()
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
            // Header
            e('header',
                {
                    style: {
                        background: 'var(--glass-bg)',
                        backdropFilter: 'blur(20px)',
                        borderRadius: 'var(--radius-lg)',
                        border: '1px solid var(--glass-border)',
                        padding: 'var(--spacing-md)',
                        marginBottom: 'var(--spacing-md)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                    }
                },
                e('div', {},
                    e('h1',
                        {
                            style: {
                                fontSize: '1.5rem',
                                margin: 0,
                                background: 'var(--gradient-primary)',
                                WebkitBackgroundClip: 'text',
                                WebkitTextFillColor: 'transparent',
                                backgroundClip: 'text',
                            }
                        },
                        '图像处理工作台'
                    )
                ),
                e('div', { style: { display: 'flex', gap: 'var(--spacing-md)' } },
                    e('span', { style: { color: 'var(--text-secondary)', fontSize: '0.9rem' } },
                        activeTools.length > 0 ? `当前运行: ${activeTools.length} 个任务` : '空闲'
                    )
                )
            ),

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
                                onClose: () => removeTool(toolInstance.instanceId),
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
function ToolWorkspace({ instanceId, toolId, onClose, style }) {
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
            toolId === 'converter' && e(ConverterTool),
            toolId === 'cropper' && e(CropperTool),
            toolId === 'generator' && e(GeneratorTool),
            toolId === 'splitter' && e(SplitterTool),
            toolId === 'deduplicator' && e(DeduplicatorTool),
            toolId === 'matcher' && e(MatcherTool),
            toolId === 'visualizer' && e(VisualizerTool)
        )
    );
}

export default App;
