import React from 'react';
import Icon from '../common/Icon.js';

const { createElement: e } = React;

export default function ToolSidebar({
    toolList,
    activeToolsCount,
    currentTheme,
    sidebarPosition,
    isHorizontal,
    draggedToolId,
    onHorizontalScroll,
    onDragStart,
    onDragOver,
    onDrop,
    onAddTool,
    onClearAll,
    onThemeChange,
    onSidebarPositionChange,
}) {
    return e('aside',
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
            onWheel: isHorizontal ? onHorizontalScroll : undefined
        },
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
                        onMouseEnter: (evt) => {
                            evt.currentTarget.style.transform = 'translateY(-2px) scale(1.05)';
                            evt.currentTarget.style.boxShadow = 'var(--shadow-md)';
                            evt.currentTarget.style.background = 'var(--bg-secondary)';
                        },
                        onMouseLeave: (evt) => {
                            evt.currentTarget.style.transform = 'translateY(0) scale(1)';
                            evt.currentTarget.style.boxShadow = 'var(--shadow-sm)';
                            evt.currentTarget.style.background = 'var(--bg-tertiary)';
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
        e('nav',
            {
                style: {
                    display: 'grid',
                    gridTemplateColumns: isHorizontal ? 'repeat(auto-fill, var(--nav-btn-width))' : '1fr',
                    gridAutoFlow: isHorizontal ? 'column' : 'row',
                    gap: 'var(--spacing-md)',
                    flex: 1,
                    overflow: isHorizontal ? 'visible' : 'auto',
                }
            },
            ...toolList.map((tool) => {
                const isDragging = draggedToolId === tool.id;
                return e('button',
                    {
                        key: tool.id,
                        draggable: true,
                        onDragStart: (evt) => onDragStart(evt, tool.id),
                        onDragOver: (evt) => onDragOver(evt, tool.id),
                        onDrop: onDrop,
                        onClick: () => onAddTool(tool.id),
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
            activeToolsCount > 0 && e('div', {
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
                        `${activeToolsCount} 个任务`
                    )
                ),
                e('button',
                    {
                        onClick: onClearAll,
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
                    ].map((theme) =>
                        e('button',
                            {
                                key: theme.id,
                                onClick: () => onThemeChange(theme.id),
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
                    ['left', 'right', 'top', 'bottom'].map((pos) =>
                        e('button',
                            {
                                key: pos,
                                onClick: () => onSidebarPositionChange(pos),
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
    );
}
