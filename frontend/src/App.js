import React, { useEffect, useRef, useState } from 'react';
import ToolSidebar from './components/shell/ToolSidebar.js';
import ToolWorkspace from './components/shell/ToolWorkspace.js';
import WelcomeScreen from './components/shell/WelcomeScreen.js';
import { TOOLS } from './config/tools.js';

const { createElement: e } = React;

function normalizeToolOrder(tools) {
    const slurmTool = tools.find((tool) => tool.id === 'slurm-generator');
    const otherTools = tools.filter((tool) => tool.id !== 'slurm-generator');
    return slurmTool ? [...otherTools, slurmTool] : otherTools;
}

function loadToolOrder() {
    const savedOrder = localStorage.getItem('tool-order');
    if (!savedOrder) return normalizeToolOrder(TOOLS);
    const orderIds = JSON.parse(savedOrder);
    const orderedTools = orderIds.map((id) => TOOLS.find((tool) => tool.id === id)).filter(Boolean);
    const newTools = TOOLS.filter((tool) => !orderIds.includes(tool.id));
    return normalizeToolOrder([...orderedTools, ...newTools]);
}

export default function App() {
    const [activeTools, setActiveTools] = useState([]);
    const [currentTheme, setCurrentTheme] = useState(() => localStorage.getItem('app-theme') || 'bilibili');
    const [nextInstanceId, setNextInstanceId] = useState(1);
    const [toolList, setToolList] = useState(loadToolOrder);
    const [draggedToolId, setDraggedToolId] = useState(null);

    const canvasRef = useRef(null);
    const isHorizontal = true;

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('app-theme', currentTheme);
    }, [currentTheme]);

    useEffect(() => {
        localStorage.setItem('tool-order', JSON.stringify(toolList.map((tool) => tool.id)));
    }, [toolList]);

    const addTool = (toolId) => {
        setActiveTools((prev) => [...prev, { instanceId: nextInstanceId, toolId, resetKey: 0 }]);
        setNextInstanceId((prev) => prev + 1);
        setTimeout(() => {
            if (canvasRef.current) {
                canvasRef.current.scrollTo({ left: canvasRef.current.scrollWidth, behavior: 'smooth' });
            }
        }, 100);
    };

    const removeTool = (instanceId) => {
        setActiveTools((prev) => prev.filter((tool) => tool.instanceId !== instanceId));
    };

    const resetTool = (instanceId) => {
        setActiveTools((prev) => prev.map((tool) => (
            tool.instanceId === instanceId ? { ...tool, resetKey: tool.resetKey + 1 } : tool
        )));
    };

    const clearAllTools = () => {
        if (activeTools.length === 0) return;
        if (confirm(`确定要清空当前工作台中的 ${activeTools.length} 个工具吗？`)) {
            setActiveTools([]);
        }
    };

    const handleDragStart = (evt, toolId) => {
        setDraggedToolId(toolId);
        evt.dataTransfer.effectAllowed = 'move';
    };

    const handleDragOver = (evt, targetToolId) => {
        evt.preventDefault();
        evt.dataTransfer.dropEffect = 'move';
        if (!draggedToolId || draggedToolId === targetToolId) return;

        const sourceIndex = toolList.findIndex((tool) => tool.id === draggedToolId);
        const targetIndex = toolList.findIndex((tool) => tool.id === targetToolId);
        if (sourceIndex < 0 || targetIndex < 0) return;

        const nextList = [...toolList];
        const [movedTool] = nextList.splice(sourceIndex, 1);
        nextList.splice(targetIndex, 0, movedTool);
        setToolList(nextList);
    };

    const handleDrop = (evt) => {
        evt.preventDefault();
        setDraggedToolId(null);
    };

    const handleHorizontalScroll = (evt) => {
        const container = evt.currentTarget;
        if (evt.deltaY !== 0) {
            container.scrollLeft += evt.deltaY;
        }
    };

    const layoutStyle = {
        display: 'flex',
        height: '100vh',
        overflow: 'hidden',
        flexDirection: 'column',
    };

    return e('div',
        { className: 'app-container', style: layoutStyle },
        e(ToolSidebar, {
            toolList,
            currentTheme,
            activeToolsCount: activeTools.length,
            isHorizontal,
            draggedToolId,
            onDragStart: handleDragStart,
            onDragOver: handleDragOver,
            onDrop: handleDrop,
            onAddTool: addTool,
            onClearAll: clearAllTools,
            onThemeChange: setCurrentTheme,
        }),
        e('main',
            {
                className: 'main-content',
                style: {
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    overflow: 'hidden',
                    position: 'relative',
                    padding: 'var(--spacing-sm)',
                }
            },
            e('div',
                {
                    ref: canvasRef,
                    onWheel: handleHorizontalScroll,
                    style: {
                        flex: 1,
                        overflowX: 'auto',
                        overflowY: 'hidden',
                        scrollBehavior: 'smooth',
                        display: 'flex',
                        borderRadius: 'var(--radius-lg)',
                    }
                },
                e('div',
                    {
                        style: {
                            display: 'flex',
                            flexDirection: 'row',
                            justifyContent: 'center',
                            gap: 'var(--spacing-md)',
                            height: '100%',
                            minWidth: '100%',
                            width: 'fit-content',
                            paddingRight: 'var(--spacing-xl)',
                        }
                    },
                    activeTools.length > 0
                        ? activeTools.map((toolInstance) =>
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
