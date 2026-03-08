import React, { useEffect, useRef, useState } from 'react';
import Icon from '../common/Icon.js';

const { createElement: e } = React;

const THEME_OPTIONS = [
    { id: 'bilibili', shortLabel: 'B', label: 'Bilibili' },
    { id: 'default', shortLabel: 'D', label: 'Default' },
    { id: 'douyin', shortLabel: 'T', label: 'Douyin' },
    { id: 'youtube', shortLabel: 'Y', label: 'YouTube' },
];

function getSidebarStyle(isHorizontal) {
    if (isHorizontal) {
        return {
            width: 'calc(100% - var(--spacing-sm) * 2)',
            minHeight: 'auto',
            flexDirection: 'row',
            alignItems: 'flex-start',
            flexWrap: 'nowrap',
            overflow: 'hidden',
        };
    }

    return {
        height: 'calc(100vh - var(--spacing-sm) * 2)',
        width: '280px',
        flexDirection: 'column',
        overflowY: 'auto',
        overflowX: 'hidden',
    };
}

export default function ToolSidebar({
    toolList,
    currentTheme,
    activeToolsCount,
    isHorizontal,
    draggedToolId,
    onDragStart,
    onDragOver,
    onDrop,
    onAddTool,
    onClearAll,
    onThemeChange,
}) {
    const sidebarRef = useRef(null);
    const toolNavRef = useRef(null);
    const themeSwitcherRef = useRef(null);
    const controlsRef = useRef(null);
    const [shouldCompactThemeSwitcher, setShouldCompactThemeSwitcher] = useState(false);

    const sidebarStyle = getSidebarStyle(isHorizontal);

    useEffect(() => {
        if (!isHorizontal) {
            setShouldCompactThemeSwitcher(false);
            return undefined;
        }

        const measure = () => {
            const sidebar = sidebarRef.current;
            const toolNav = toolNavRef.current;
            const themeSwitcher = themeSwitcherRef.current;
            const controls = controlsRef.current;
            if (!sidebar || !toolNav || !themeSwitcher || !controls) return;

            const toolButtons = Array.from(toolNav.querySelectorAll('.tool-btn-horizontal'));
            const themeButtons = Array.from(themeSwitcher.querySelectorAll('.toolbar-segment-btn'));
            if (!toolButtons.length || !themeButtons.length) {
                setShouldCompactThemeSwitcher(false);
                return;
            }

            const sidebarStyle = window.getComputedStyle(sidebar);
            const toolNavStyle = window.getComputedStyle(toolNav);
            const themeStyle = window.getComputedStyle(themeSwitcher);
            const controlsStyle = window.getComputedStyle(controls);

            const sidebarGap = parseFloat(sidebarStyle.columnGap || sidebarStyle.gap || '0');
            const toolGap = parseFloat(toolNavStyle.columnGap || toolNavStyle.gap || '0');
            const themeGap = parseFloat(themeStyle.columnGap || themeStyle.gap || '0');
            const controlsGap = parseFloat(controlsStyle.columnGap || controlsStyle.gap || '0');

            const toolWidth = toolButtons.reduce((sum, button) => sum + button.offsetWidth, 0)
                + toolGap * Math.max(toolButtons.length - 1, 0);

            const themeButtonsWidth = themeButtons.reduce((sum, button) => sum + button.offsetWidth, 0);
            const themeSingleRowWidth = themeButtonsWidth
                + themeGap * Math.max(themeButtons.length - 1, 0)
                + parseFloat(themeStyle.paddingLeft || '0')
                + parseFloat(themeStyle.paddingRight || '0')
                + parseFloat(themeStyle.borderLeftWidth || '0')
                + parseFloat(themeStyle.borderRightWidth || '0');

            const themeCompactWidth = (28 * 2) + themeGap
                + parseFloat(themeStyle.paddingLeft || '0')
                + parseFloat(themeStyle.paddingRight || '0')
                + parseFloat(themeStyle.borderLeftWidth || '0')
                + parseFloat(themeStyle.borderRightWidth || '0');

            const controlsWidth = controls.offsetWidth;
            const clearButtonWidth = Math.max(0, controlsWidth - themeSwitcher.offsetWidth - controlsGap);
            const singleControlsWidth = clearButtonWidth + themeSingleRowWidth + (clearButtonWidth > 0 ? controlsGap : 0);
            const compactControlsWidth = clearButtonWidth + themeCompactWidth + (clearButtonWidth > 0 ? controlsGap : 0);

            const requiredSingle = toolWidth + singleControlsWidth + sidebarGap;
            const requiredCompact = toolWidth + compactControlsWidth + sidebarGap;

            if (shouldCompactThemeSwitcher) {
                setShouldCompactThemeSwitcher(requiredCompact > sidebar.clientWidth + 1 || requiredSingle > sidebar.clientWidth + 1);
            } else {
                setShouldCompactThemeSwitcher(requiredSingle > sidebar.clientWidth + 1);
            }
        };

        measure();

        const resizeObserver = new ResizeObserver(() => {
            window.requestAnimationFrame(measure);
        });

        if (sidebarRef.current) resizeObserver.observe(sidebarRef.current);
        if (toolNavRef.current) resizeObserver.observe(toolNavRef.current);
        if (themeSwitcherRef.current) resizeObserver.observe(themeSwitcherRef.current);
        if (controlsRef.current) resizeObserver.observe(controlsRef.current);

        window.addEventListener('resize', measure);
        return () => {
            resizeObserver.disconnect();
            window.removeEventListener('resize', measure);
        };
    }, [isHorizontal, toolList.length, shouldCompactThemeSwitcher]);

    const themeSwitcher = e('div',
        {
            ref: themeSwitcherRef,
            className: `toolbar-segment ${shouldCompactThemeSwitcher ? 'is-compact-grid' : ''}`,
            role: 'group',
            'aria-label': '选择主题',
        },
        ...THEME_OPTIONS.map((theme) =>
            e('button',
                {
                    key: theme.id,
                    onClick: () => onThemeChange(theme.id),
                    className: `toolbar-segment-btn ${currentTheme === theme.id ? 'active' : ''}`,
                    title: theme.label,
                    'aria-label': `切换到 ${theme.label} 主题`,
                },
                theme.shortLabel
            )
        )
    );

    const clearButton = e('button',
        {
            type: 'button',
            className: 'toolbar-clear-btn',
            onClick: onClearAll,
            disabled: activeToolsCount === 0,
            title: activeToolsCount === 0 ? '当前没有打开的工作台' : '清空工作台',
            'aria-label': '清空工作台',
        },
        e(Icon, { name: 'trash', size: 16 }),
        e('span', {}, '清空工作台')
    );

    const controlsBlock = e('div',
        {
            ref: controlsRef,
            className: `sidebar-controls ${isHorizontal ? 'is-horizontal' : 'is-vertical'} ${shouldCompactThemeSwitcher ? 'is-compact' : ''}`,
        },
        clearButton,
        themeSwitcher
    );

    const toolButtons = toolList.map((tool) => {
        const isDragging = draggedToolId === tool.id;
        return e('button',
            {
                key: tool.id,
                draggable: true,
                onDragStart: (evt) => onDragStart(evt, tool.id),
                onDragOver: (evt) => onDragOver(evt, tool.id),
                onDrop: onDrop,
                onClick: () => onAddTool(tool.id),
                className: `tool-btn ${isHorizontal ? 'tool-btn-horizontal' : 'tool-btn-vertical'} ${isDragging ? 'dragging' : ''}`,
                title: tool.name,
            },
            e('span', { className: 'tool-btn-icon' },
                e(Icon, { name: tool.icon, size: isHorizontal ? 18 : 24 })
            ),
            e('span', { className: 'tool-btn-label' }, tool.name)
        );
    });

    return e('aside',
        {
            className: `sidebar glass-card ${isHorizontal ? 'sidebar-horizontal' : 'sidebar-vertical'}`,
            ref: sidebarRef,
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
                gap: '10px',
                ...sidebarStyle,
            },
        },
        e('nav',
            {
                ref: toolNavRef,
                className: `tool-nav ${isHorizontal ? 'tool-nav-horizontal' : 'tool-nav-vertical'}`,
            },
            ...toolButtons
        ),
        controlsBlock
    );
}
