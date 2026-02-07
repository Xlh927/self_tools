import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import useToolTask from './useToolTask.js';

describe('useToolTask', () => {
    it('resets result on start and maps completion payload', async () => {
        const startTask = vi.fn().mockResolvedValue({ success: true, task_id: 'task-1' });
        const { result } = renderHook(() =>
            useToolTask({
                startTask,
                mapComplete: (payload) => ({ ...payload, mapped: true }),
            })
        );

        act(() => {
            result.current.setResult({ success: true, stale: true });
        });

        await act(async () => {
            await result.current.taskControllerProps.onStart();
        });

        expect(startTask).toHaveBeenCalledTimes(1);
        expect(result.current.result).toBe(null);

        act(() => {
            result.current.taskControllerProps.onComplete({ success: true, value: 1 });
        });

        expect(result.current.result).toEqual({ success: true, value: 1, mapped: true });
        expect(result.current.taskId).toBe(null);
    });

    it('normalizes and maps errors', () => {
        const { result } = renderHook(() =>
            useToolTask({
                mapError: (normalized) => ({ ok: false, ...normalized }),
            })
        );

        act(() => {
            result.current.taskControllerProps.onError({ error: 'bad', error_code: 'ERR_BAD' });
        });

        expect(result.current.result).toEqual({ ok: false, error: 'bad', error_code: 'ERR_BAD' });
    });

    it('exposes telemetry toolName to TaskController props', () => {
        const { result } = renderHook(() =>
            useToolTask({
                toolName: 'splitter',
            })
        );

        expect(result.current.taskControllerProps.telemetry).toEqual({ toolName: 'splitter' });
    });
});
