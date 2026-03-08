import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    fetchTaskProgress as defaultFetchTaskProgress,
    pauseTask as defaultPauseTask,
    resumeTask as defaultResumeTask,
    stopTask as defaultStopTask,
    taskProgressStreamUrl as defaultTaskProgressStreamUrl,
} from '../api/tasks.js';
import { normalizeError } from '../utils/error.js';
import { reportTaskTelemetry as defaultReportTaskTelemetry } from '../utils/taskTelemetry.js';

const ACTIVE_STATUSES = ['queued', 'running', 'paused', 'retrying'];
const TERMINAL_STATUSES = ['completed', 'error', 'stopped', 'cancelled'];
const MIN_SYNC_INTERVAL_MS = 500;
const STREAM_RECONCILE_INTERVAL_MS = 1000;
const MAX_POLL_ERRORS_WITH_STREAM = 6;
const MAX_POLL_ERRORS_WITHOUT_STREAM = 3;

export default function useTaskRunner({
    startTask,
    onComplete,
    onError,
    onStop,
    pollInterval = 500,
    api = {},
    telemetry = {},
}) {
    const fetchProgress = api.fetchTaskProgress || defaultFetchTaskProgress;
    const pauseApi = api.pauseTask || defaultPauseTask;
    const resumeApi = api.resumeTask || defaultResumeTask;
    const stopApi = api.stopTask || defaultStopTask;
    const taskStreamUrl = api.taskProgressStreamUrl || defaultTaskProgressStreamUrl;
    const enableTaskStream = api.enableTaskStream !== false;
    const telemetryEnabled = telemetry.enabled !== false;
    const telemetryToolName = telemetry.toolName || 'unknown_tool';
    const telemetryExtra = useMemo(() => {
        if (telemetry.extra && typeof telemetry.extra === 'object') {
            return telemetry.extra;
        }
        return null;
    }, [telemetry.extra]);
    const telemetryReporter = typeof telemetry.reporter === 'function'
        ? telemetry.reporter
        : defaultReportTaskTelemetry;

    const [taskId, setTaskId] = useState(null);
    const [status, setStatus] = useState('idle');
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState('');
    const [errorCode, setErrorCode] = useState('');
    const runRef = useRef({
        startedAtMs: 0,
        taskId: null,
        source: null,
    });

    const mountedRef = useRef(true);
    useEffect(() => {
        return () => {
            mountedRef.current = false;
        };
    }, []);

    const emitTelemetry = useCallback((eventName, payload = {}) => {
        if (!telemetryEnabled) return;
        telemetryReporter(eventName, {
            tool_name: telemetryToolName,
            ...(telemetryExtra || {}),
            ...payload,
        });
    }, [telemetryEnabled, telemetryExtra, telemetryReporter, telemetryToolName]);

    const beginRun = useCallback((source = 'start', nextTaskId = null) => {
        runRef.current = {
            startedAtMs: Date.now(),
            taskId: nextTaskId || null,
            source,
        };
        emitTelemetry('tool_task_started', {
            task_id: nextTaskId || null,
            source,
        });
    }, [emitTelemetry]);

    const endRun = useCallback((eventName, payload = {}) => {
        const run = runRef.current;
        const startedAtMs = run.startedAtMs || 0;
        const durationMs = startedAtMs > 0 ? Math.max(0, Date.now() - startedAtMs) : null;
        emitTelemetry(eventName, {
            task_id: payload.task_id || run.taskId || null,
            source: run.source || null,
            duration_ms: durationMs,
            ...payload,
        });
        runRef.current = {
            startedAtMs: 0,
            taskId: null,
            source: null,
        };
    }, [emitTelemetry]);

    const applyTaskPayload = useCallback((payload) => {
        if (!mountedRef.current || !payload || typeof payload !== 'object') return;
        if (payload.status) setStatus(payload.status);
        if (typeof payload.progress === 'number') setProgress(payload.progress);
        if (payload.message) setMessage(payload.message);
        if (payload.error_code) setErrorCode(payload.error_code);
    }, []);

    const attachTask = useCallback((nextTaskId, nextStatus = 'running') => {
        if (!nextTaskId) return;
        setTaskId(nextTaskId);
        setStatus(nextStatus);
        const current = runRef.current;
        if (!current.startedAtMs || current.taskId !== nextTaskId) {
            beginRun('attach', nextTaskId);
            return;
        }
        runRef.current = { ...current, taskId: nextTaskId };
    }, [beginRun]);

    const reset = useCallback(() => {
        setTaskId(null);
        setStatus('idle');
        setProgress(0);
        setMessage('');
        setErrorCode('');
        runRef.current = {
            startedAtMs: 0,
            taskId: null,
            source: null,
        };
    }, []);

    const start = useCallback(async () => {
        if (!startTask) return null;
        beginRun('start');
        setStatus('queued');
        setProgress(0);
        setMessage('Starting...');
        setErrorCode('');

        try {
            const result = await startTask();
            if (result && result.success === false) {
                throw result;
            }
            if (result && result.task_id) {
                setTaskId(result.task_id);
                setStatus(result.status || 'queued');
                if (result.message) setMessage(result.message);
                runRef.current = { ...runRef.current, taskId: result.task_id };
                return result;
            }

            setStatus('completed');
            setProgress(100);
            setMessage((result && result.message) || 'Completed successfully');
            endRun('tool_task_completed', {
                status: 'completed',
            });
            if (onComplete) onComplete(result);
            return result;
        } catch (err) {
            const normalized = normalizeError(err);
            setStatus('error');
            setMessage(normalized.error || 'Failed to start task');
            setErrorCode(normalized.error_code || '');
            endRun('tool_task_failed', {
                status: 'error',
                phase: 'start',
                error: normalized.error || 'Failed to start task',
                error_code: normalized.error_code || '',
            });
            if (onError) onError(normalized);
            return { success: false, ...normalized };
        }
    }, [beginRun, endRun, onComplete, onError, startTask]);

    const pause = useCallback(async () => {
        if (!taskId) return;
        try {
            const payload = await pauseApi(taskId);
            applyTaskPayload(payload);
            setStatus(payload.status || 'paused');
        } catch (err) {
            const normalized = normalizeError(err);
            setMessage(normalized.error || 'Pause failed');
            setErrorCode(normalized.error_code || '');
        }
    }, [applyTaskPayload, pauseApi, taskId]);

    const resume = useCallback(async () => {
        if (!taskId) return;
        try {
            const payload = await resumeApi(taskId);
            applyTaskPayload(payload);
            setStatus(payload.status || 'running');
        } catch (err) {
            const normalized = normalizeError(err);
            setMessage(normalized.error || 'Resume failed');
            setErrorCode(normalized.error_code || '');
        }
    }, [applyTaskPayload, resumeApi, taskId]);

    const stop = useCallback(async () => {
        if (!taskId) return;
        try {
            const payload = await stopApi(taskId);
            applyTaskPayload(payload);
            setStatus(payload.status || 'stopped');
        } catch (err) {
            const normalized = normalizeError(err);
            setMessage(normalized.error || 'Stop failed');
            setErrorCode(normalized.error_code || '');
        }
    }, [applyTaskPayload, stopApi, taskId]);

    useEffect(() => {
        if (!taskId || TERMINAL_STATUSES.includes(status)) {
            return;
        }

        let cancelled = false;
        let isFinished = false;
        let pollingTimer = null;
        let stream = null;
        let pollErrorCount = 0;

        const failSync = (phase, err) => {
            if (cancelled || isFinished) return;
            const normalized = normalizeError(err);
            isFinished = true;
            setStatus('error');
            setMessage(normalized.error || 'Task sync error');
            setErrorCode(normalized.error_code || '');
            setTaskId(null);
            endRun('tool_task_failed', {
                status: 'error',
                phase,
                error: normalized.error || 'Task sync error',
                error_code: normalized.error_code || '',
            });
            if (onError) onError(normalized);
        };

        const completeTerminalTask = (payload) => {
            if (isFinished) return;
            isFinished = true;
            setTaskId(null);

            if (payload.status === 'completed') {
                endRun('tool_task_completed', {
                    status: 'completed',
                });
                if (onComplete) onComplete(payload.result);
                return;
            }

            if (payload.status === 'error') {
                endRun('tool_task_failed', {
                    status: 'error',
                    phase: 'runtime',
                    error: payload.error || payload.message || 'Task failed',
                    error_code: payload.error_code || '',
                });
                if (onError) {
                    onError({
                        error: payload.error || payload.message || 'Task failed',
                        error_code: payload.error_code,
                    });
                }
                return;
            }

            if (payload.status === 'stopped' || payload.status === 'cancelled') {
                endRun('tool_task_stopped', {
                    status: payload.status,
                    error_code: payload.error_code || '',
                });
                if (onStop) onStop();
            }
        };

        const handleTaskPayload = (payload) => {
            if (cancelled || !payload || typeof payload !== 'object') return;
            applyTaskPayload(payload);
            if (TERMINAL_STATUSES.includes(payload.status)) {
                completeTerminalTask(payload);
            }
        };

        const fetchAndHandleProgress = async () => {
            const payload = await fetchProgress(taskId);
            if (cancelled || isFinished) return;
            handleTaskPayload(payload);
        };

        const startPolling = () => {
            if (pollingTimer) return;
            const intervalMs = stream
                ? Math.max(MIN_SYNC_INTERVAL_MS, Math.max(pollInterval, STREAM_RECONCILE_INTERVAL_MS))
                : Math.max(MIN_SYNC_INTERVAL_MS, pollInterval);
            pollingTimer = setInterval(async () => {
                if (cancelled || isFinished) return;
                try {
                    await fetchAndHandleProgress();
                    pollErrorCount = 0;
                } catch (err) {
                    pollErrorCount += 1;
                    const threshold = stream ? MAX_POLL_ERRORS_WITH_STREAM : MAX_POLL_ERRORS_WITHOUT_STREAM;
                    if (pollErrorCount >= threshold) {
                        failSync('polling', err);
                    }
                }
            }, intervalMs);

            // Immediate first sync to avoid waiting for the first timer tick.
            fetchAndHandleProgress()
                .then(() => {
                    pollErrorCount = 0;
                })
                .catch((err) => {
                    pollErrorCount += 1;
                    const threshold = stream ? MAX_POLL_ERRORS_WITH_STREAM : MAX_POLL_ERRORS_WITHOUT_STREAM;
                    if (pollErrorCount >= threshold) {
                        failSync('polling', err);
                    }
                });
        };

        const disableStream = () => {
            if (stream) {
                stream.close();
                stream = null;
            }
        };

        startPolling();

        if (enableTaskStream && typeof EventSource !== 'undefined') {
            try {
                const streamUrl = taskStreamUrl(taskId);
                if (streamUrl) {
                    stream = new EventSource(streamUrl);
                    stream.onmessage = (event) => {
                        if (cancelled || isFinished || !event || !event.data) return;
                        try {
                            const payload = JSON.parse(event.data);
                            handleTaskPayload(payload);
                        } catch (_err) {
                            // Malformed stream payload should not block state convergence.
                            disableStream();
                        }
                    };
                    stream.onerror = () => {
                        if (cancelled || isFinished) return;
                        disableStream();
                    };
                }
            } catch (_err) {
                disableStream();
            }
        }

        return () => {
            cancelled = true;
            if (stream) {
                stream.close();
            }
            if (pollingTimer) {
                clearInterval(pollingTimer);
            }
        };
    }, [
        applyTaskPayload,
        endRun,
        enableTaskStream,
        fetchProgress,
        onComplete,
        onError,
        onStop,
        pollInterval,
        status,
        taskId,
        taskStreamUrl,
    ]);

    const actions = useMemo(() => ({
        attachTask,
        start,
        pause,
        resume,
        stop,
        reset,
    }), [attachTask, pause, reset, resume, start, stop]);

    return {
        state: {
            taskId,
            status,
            progress,
            message,
            errorCode,
            isActive: ACTIVE_STATUSES.includes(status),
        },
        actions,
    };
}
