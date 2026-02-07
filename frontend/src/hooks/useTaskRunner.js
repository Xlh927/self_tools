import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    fetchTaskProgress as defaultFetchTaskProgress,
    pauseTask as defaultPauseTask,
    resumeTask as defaultResumeTask,
    stopTask as defaultStopTask,
} from '../api/tasks.js';
import { normalizeError } from '../utils/error.js';

const ACTIVE_STATUSES = ['queued', 'running', 'paused', 'retrying'];
const TERMINAL_STATUSES = ['completed', 'error', 'stopped', 'cancelled'];

export default function useTaskRunner({
    startTask,
    onComplete,
    onError,
    onStop,
    pollInterval = 500,
    api = {},
}) {
    const fetchProgress = api.fetchTaskProgress || defaultFetchTaskProgress;
    const pauseApi = api.pauseTask || defaultPauseTask;
    const resumeApi = api.resumeTask || defaultResumeTask;
    const stopApi = api.stopTask || defaultStopTask;

    const [taskId, setTaskId] = useState(null);
    const [status, setStatus] = useState('idle');
    const [progress, setProgress] = useState(0);
    const [message, setMessage] = useState('');
    const [errorCode, setErrorCode] = useState('');

    const mountedRef = useRef(true);
    useEffect(() => {
        return () => {
            mountedRef.current = false;
        };
    }, []);

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
    }, []);

    const reset = useCallback(() => {
        setTaskId(null);
        setStatus('idle');
        setProgress(0);
        setMessage('');
        setErrorCode('');
    }, []);

    const start = useCallback(async () => {
        if (!startTask) return null;
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
                return result;
            }

            setStatus('completed');
            setProgress(100);
            setMessage((result && result.message) || 'Completed successfully');
            if (onComplete) onComplete(result);
            return result;
        } catch (err) {
            const normalized = normalizeError(err);
            setStatus('error');
            setMessage(normalized.error || 'Failed to start task');
            setErrorCode(normalized.error_code || '');
            if (onError) onError(normalized);
            return { success: false, ...normalized };
        }
    }, [onComplete, onError, startTask]);

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
        if (!taskId || !ACTIVE_STATUSES.includes(status)) {
            return;
        }

        let cancelled = false;
        const timer = setInterval(async () => {
            if (cancelled) return;
            try {
                const payload = await fetchProgress(taskId);
                if (cancelled) return;
                applyTaskPayload(payload);

                if (TERMINAL_STATUSES.includes(payload.status)) {
                    setTaskId(null);
                    if (payload.status === 'completed') {
                        if (onComplete) onComplete(payload.result);
                    } else if (payload.status === 'error') {
                        if (onError) {
                            onError({
                                error: payload.error || payload.message || 'Task failed',
                                error_code: payload.error_code,
                            });
                        }
                    } else if (payload.status === 'stopped' || payload.status === 'cancelled') {
                        if (onStop) onStop();
                    }
                }
            } catch (err) {
                if (cancelled) return;
                const normalized = normalizeError(err);
                setStatus('error');
                setMessage(normalized.error || 'Polling error');
                setErrorCode(normalized.error_code || '');
                setTaskId(null);
                if (onError) onError(normalized);
            }
        }, pollInterval);

        return () => {
            cancelled = true;
            clearInterval(timer);
        };
    }, [applyTaskPayload, fetchProgress, onComplete, onError, onStop, pollInterval, status, taskId]);

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
