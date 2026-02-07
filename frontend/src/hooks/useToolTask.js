import { useCallback, useMemo, useState } from 'react';
import { normalizeError } from '../utils/error.js';

export default function useToolTask({
    startTask,
    mapComplete,
    mapError,
    onStop,
    toolName,
    clearResultOnStart = true,
} = {}) {
    const [result, setResult] = useState(null);
    const [taskId, setTaskId] = useState(null);

    const handleStart = useCallback(async () => {
        if (clearResultOnStart) {
            setResult(null);
        }
        if (!startTask) return null;
        return startTask();
    }, [clearResultOnStart, startTask]);

    const handleComplete = useCallback((payload) => {
        const mapped = typeof mapComplete === 'function' ? mapComplete(payload) : payload;
        setResult(mapped);
        setTaskId(null);
    }, [mapComplete]);

    const handleError = useCallback((err) => {
        const normalized = normalizeError(err);
        const mapped = typeof mapError === 'function'
            ? mapError(normalized, err)
            : { success: false, ...normalized };
        setResult(mapped);
        setTaskId(null);
    }, [mapError]);

    const handleStop = useCallback(() => {
        setTaskId(null);
        if (typeof onStop === 'function') {
            return onStop();
        }
        return undefined;
    }, [onStop]);

    const taskControllerProps = useMemo(() => ({
        taskId,
        onStart: handleStart,
        onComplete: handleComplete,
        onError: handleError,
        onStop: handleStop,
        telemetry: toolName ? { toolName } : undefined,
    }), [handleComplete, handleError, handleStart, handleStop, taskId, toolName]);

    return {
        result,
        setResult,
        taskId,
        setTaskId,
        taskControllerProps,
    };
}
