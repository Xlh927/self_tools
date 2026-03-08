import React, { useEffect, useRef } from 'react';
import ProgressBar from './ProgressBar.js';
import useTaskRunner from '../../hooks/useTaskRunner.js';
import { formatError } from '../../utils/error.js';

const { createElement: e } = React;

export default function TaskController({
    taskId,
    onStart,
    onComplete,
    onError,
    onStop,
    canStart = true,
    telemetry,
}) {
    const runner = useTaskRunner({
        startTask: onStart,
        onComplete,
        onError,
        onStop,
        telemetry,
    });

    const { state, actions } = runner;
    const { taskId: localTaskId, status, progress, message, errorCode } = state;
    const attachedTaskRef = useRef(null);

    useEffect(() => {
        if (taskId && attachedTaskRef.current !== taskId) {
            actions.attachTask(taskId, 'running');
            attachedTaskRef.current = taskId;
            return;
        }
        if (!taskId) {
            attachedTaskRef.current = null;
        }
    }, [actions, taskId]);

    const handleStop = async () => {
        if (!localTaskId) return;
        if (confirm('确定要终止任务吗？')) {
            await actions.stop();
        }
    };

    if (status === 'idle' || (status === 'error' && !localTaskId)) {
        return e('div', { className: 'task-controller' },
            e('button',
                {
                    className: 'btn btn-secondary',
                    onClick: actions.start,
                    disabled: !canStart,
                    style: {
                        fontSize: '1.2rem',
                        padding: 'var(--spacing-md) var(--spacing-xl)',
                        width: '100%',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '8px',
                        background: 'var(--gradient-primary)',
                        border: 'none',
                        color: 'white',
                    }
                },
                '▶️ 开始任务'
            ),
            status === 'error' && message && e('p', { style: { color: 'var(--neon-orange)', marginTop: '8px', textAlign: 'center' } }, formatError(message, errorCode))
        );
    }

    if (status === 'completed') {
        return e('div', { className: 'task-controller animate-fade-in' },
            e(ProgressBar, { progress: 100, message: message || 'Completed' }),
            e('div',
                { style: { display: 'flex', gap: '10px', marginTop: '10px' } },
                e('button',
                    {
                        className: 'btn',
                        onClick: actions.reset,
                        style: {
                            flex: 1,
                            background: 'var(--bg-tertiary)',
                            color: 'var(--text-primary)',
                            border: '1px solid var(--glass-border)'
                        }
                    },
                    '🔄 返回 / 新任务'
                )
            )
        );
    }

    if (status === 'stopped' || status === 'cancelled') {
        return e('div', { className: 'task-controller animate-fade-in' },
            e('div', {
                style: {
                    padding: '12px',
                    background: 'var(--color-danger-bg)',
                    border: '1px solid var(--color-danger)',
                    borderRadius: 'var(--radius-md)',
                    textAlign: 'center',
                    marginBottom: '10px',
                    color: 'var(--color-danger)',
                    fontWeight: '600'
                }
            }, '🛑 任务已取消'),
            errorCode && e('div', {
                style: {
                    textAlign: 'center',
                    color: 'var(--text-secondary)',
                    fontSize: '0.85rem',
                    marginBottom: '10px'
                }
            }, `错误码: ${errorCode}`),
            e('button',
                {
                    className: 'btn',
                    onClick: actions.reset,
                    style: {
                        width: '100%',
                        background: 'var(--bg-tertiary)',
                        border: '1px solid var(--glass-border)'
                    }
                },
                '🔄 重置'
            )
        );
    }

    return e('div', { className: 'task-controller animate-fade-in' },
        e(ProgressBar, {
            progress: progress,
            message:
                status === 'paused'
                    ? `⏸️ 已暂停 - ${message}`
                    : status === 'queued'
                        ? `🕒 排队中 - ${message || 'Waiting for worker'}`
                        : status === 'retrying'
                            ? `🔁 重试中 - ${message}`
                            : formatError(message, errorCode),
            color: (status === 'paused' || status === 'queued' || status === 'retrying')
                ? 'var(--color-warning)'
                : 'var(--color-success)'
        }),
        e('div',
            {
                style: {
                    display: 'flex',
                    gap: 'var(--spacing-md)',
                    marginTop: 'var(--spacing-md)',
                    justifyContent: 'center'
                }
            },
            status === 'running' && e('button',
                {
                    className: 'btn',
                    onClick: actions.pause,
                    style: {
                        flex: 1,
                        background: 'var(--color-warning-bg)',
                        color: 'var(--color-warning)',
                        border: '1px solid var(--color-warning)'
                    }
                },
                '⏸️ 暂停'
            ),
            status === 'queued' && e('div',
                {
                    style: {
                        flex: 1,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-secondary)',
                        border: '1px dashed var(--glass-border)',
                        borderRadius: 'var(--radius-md)'
                    }
                },
                '等待可用 worker...'
            ),
            status === 'paused' && e('button',
                {
                    className: 'btn',
                    onClick: actions.resume,
                    style: {
                        flex: 1,
                        background: 'rgba(82, 196, 26, 0.15)',
                        color: 'var(--color-success)',
                        border: '1px solid var(--color-success)'
                    }
                },
                '▶️ 继续'
            ),
            e('button',
                {
                    className: 'btn',
                    onClick: handleStop,
                    style: {
                        flex: 1,
                        background: 'var(--color-danger-bg)',
                        color: 'var(--color-danger)',
                        border: '1px solid var(--color-danger)'
                    }
                },
                '⏹️ 停止'
            )
        )
    );
}
