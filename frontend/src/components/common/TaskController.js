import React, { useState, useEffect, useRef } from 'react';
import ProgressBar from './ProgressBar.js';
import { formatError } from '../../utils/error.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

/**
 * TaskController Component
 * Handles task progress polling, display, and controls (Start/Pause/Resume/Stop).
 * 
 * Props:
 * - taskId: string | null - The ID of the running task. If provided, polling starts.
 * - onStart: function - Callback when "Start" button is clicked. Should return a promise that resolves to { success: true, task_id: '...' }.
 * - onComplete: function(result) - Callback when task completes successfully.
 * - onError: function({ error, error_code }) - Callback when task fails.
 * - onStop: function - Callback when task is stopped by user.
 * - canStart: boolean - Whether the start button should be enabled.
 */
export default function TaskController({
    taskId, // Managed by parent or self? Ideally parent starts it and passes ID, but here we want to abstract "Start" button too.
    // Let's say parent handles parameters and "onStart" does the fetch.
    onStart,
    onComplete,
    onError,
    onStop,
    canStart = true
}) {
    // Internal state for task status if taskId is provided
    const [status, setStatus] = useState('idle'); // idle, queued, running, paused, retrying, stopped, completed, error
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState('');
    const [errorCode, setErrorCode] = useState('');
    const [localTaskId, setLocalTaskId] = useState(taskId);

    // Sync prop taskId to local
    useEffect(() => {
        if (taskId) {
            setLocalTaskId(taskId);
            setStatus('running'); // Assume running if ID passed
        }
    }, [taskId]);

    const pollTimer = useRef(null);

    // Polling logic
    useEffect(() => {
        if (!localTaskId || !['queued', 'running', 'paused', 'retrying'].includes(status)) {
            if (pollTimer.current) {
                clearInterval(pollTimer.current);
                pollTimer.current = null;
            }
            return;
        }

        pollTimer.current = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${localTaskId}`);
                if (res.status === 404) {
                    // Task lost?
                    setStatus('error');
                    setMessage('Task not found');
                    setErrorCode('ERR_TASK_NOT_FOUND');
                    if (onError) onError({ error: 'Task not found', error_code: 'ERR_TASK_NOT_FOUND' });
                    return;
                }
                const data = await res.json();

                const payload = data.data && typeof data.data === 'object' ? { ...data.data, ...data } : data;

                setProgress(payload.progress || 0);
                setMessage(payload.message || '');
                if (payload.error_code) {
                    setErrorCode(payload.error_code);
                }

                // Allow backend to dictate status, but map correctly
                if (payload.status) {
                    setStatus(payload.status);
                }

                if (payload.status === 'completed') {
                    setLocalTaskId(null);
                    if (onComplete) onComplete(payload.result);
                } else if (payload.status === 'error') {
                    setLocalTaskId(null);
                    setMessage(payload.error || payload.message);
                    if (onError) onError({ error: payload.error, error_code: payload.error_code });
                } else if (payload.status === 'stopped' || payload.status === 'cancelled') {
                    setLocalTaskId(null);
                    if (onStop) onStop();
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 500);

        return () => {
            if (pollTimer.current) clearInterval(pollTimer.current);
        };
    }, [localTaskId, status]);

    const handleStart = async () => {
        if (!onStart) return;
        setStatus('queued');
        setProgress(0);
        setMessage('Starting...');
        setErrorCode('');

        try {
            const result = await onStart();
            if (result && result.success) {
                if (result.task_id) {
                    setLocalTaskId(result.task_id);
                } else {
                    // Synchronous completion
                    setStatus('completed');
                    setProgress(100);
                    setMessage('Completed successfully');
                    if (onComplete) onComplete(result);
                }
            } else {
                setStatus('error');
                setMessage(result?.error || 'Failed to start');
                setErrorCode(result?.error_code || '');
                if (onError) onError({ error: result?.error || 'Failed to start', error_code: result?.error_code });
            }
        } catch (e) {
            setStatus('error');
            setMessage(e.message);
            setErrorCode('');
            if (onError) onError({ error: e.message });
        }
    };

    const handlePause = async () => {
        if (!localTaskId) return;
        try {
            await fetch(`/api/task/${localTaskId}/pause`, { method: 'POST' });
            setStatus('paused'); // Optimistic update
        } catch (e) {
            console.error('Failed to pause', e);
        }
    };

    const handleResume = async () => {
        if (!localTaskId) return;
        try {
            await fetch(`/api/task/${localTaskId}/resume`, { method: 'POST' });
            setStatus('running'); // Optimistic update
        } catch (e) {
            console.error('Failed to resume', e);
        }
    };

    const handleStop = async () => {
        if (!localTaskId) return;
        if (confirm('确定要终止任务吗？')) {
            try {
                await fetch(`/api/task/${localTaskId}/stop`, { method: 'POST' });
                setStatus('stopped'); // Optimistic update
            } catch (e) {
                console.error('Failed to stop', e);
            }
        }
    };

    const handleReset = () => {
        setStatus('idle');
        setProgress(0);
        setMessage('');
        setErrorCode('');
        setLocalTaskId(null);
        if (onStop) onStop(); // Reset parent state if needed
    };

    // Render Logic

    // Idle State: Show Start Button
    if (status === 'idle' || status === 'error' && !localTaskId) {
        return e('div', { className: 'task-controller' },
            e('button',
                {
                    className: 'btn btn-secondary',
                    onClick: handleStart,
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

    // Finished States
    if (status === 'completed') {
        return e('div', { className: 'task-controller animate-fade-in' },
            e(ProgressBar, { progress: 100, message: message || 'Completed' }),
            e('div',
                { style: { display: 'flex', gap: '10px', marginTop: '10px' } },
                e('button',
                    {
                        className: 'btn',
                        onClick: handleReset,
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
                    onClick: handleReset,
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

    // Active States (running, paused)
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
                    onClick: handlePause,
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
                    onClick: handleResume,
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
