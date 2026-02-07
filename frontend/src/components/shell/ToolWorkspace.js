import React from 'react';
import Icon from '../common/Icon.js';
import { getToolById } from '../../config/tools.js';
import { getToolComponentById } from '../../config/toolComponents.js';

const { createElement: e } = React;

export default function ToolWorkspace({ instanceId, toolId, resetKey, onClose, onReset, style }) {
    const tool = getToolById(toolId);
    const ToolComponent = getToolComponentById(toolId);

    if (!tool || !ToolComponent) {
        return e('div', { className: 'glass-card', style: { ...style, padding: 'var(--spacing-md)' } }, `Unknown tool: ${toolId}`);
    }

    return e('div',
        {
            className: 'glass-card animate-fade-in-up',
            style: {
                position: 'relative',
                padding: 0,
                borderTop: 'none',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                ...style
            }
        },
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
        e('div', {
            className: 'tool-content',
            style: {
                flex: 1,
                overflowY: 'auto',
                padding: 'var(--spacing-md)',
                paddingTop: 0,
            }
        }, e(ToolComponent, { key: resetKey }))
    );
}
