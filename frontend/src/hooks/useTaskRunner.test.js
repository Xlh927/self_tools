import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import useTaskRunner from './useTaskRunner.js';

function createApiMocks() {
    return {
        fetchTaskProgress: vi.fn(),
        pauseTask: vi.fn().mockResolvedValue({ success: true, status: 'paused', message: 'Task paused' }),
        resumeTask: vi.fn().mockResolvedValue({ success: true, status: 'running', message: 'Task resumed' }),
        stopTask: vi.fn().mockResolvedValue({ success: true, status: 'stopped', message: 'Task stopped' }),
    };
}

describe('useTaskRunner', () => {
    it('runs queued task until completion and emits onComplete', async () => {
        const onComplete = vi.fn();
        const api = createApiMocks();
        api.fetchTaskProgress
            .mockResolvedValueOnce({
                success: true,
                status: 'running',
                progress: 50,
                message: 'Running',
            })
            .mockResolvedValueOnce({
                success: true,
                status: 'completed',
                progress: 100,
                message: 'Done',
                result: { success: true, converted: 3 },
            });

        const startTask = vi.fn().mockResolvedValue({
            success: true,
            task_id: 'task-1',
            status: 'queued',
            message: 'Task queued',
        });

        const { result } = renderHook(() =>
            useTaskRunner({
                startTask,
                onComplete,
                pollInterval: 10,
                api,
            })
        );

        await act(async () => {
            await result.current.actions.start();
        });

        await waitFor(() => {
            expect(onComplete).toHaveBeenCalledTimes(1);
        }, { timeout: 1000 });

        expect(api.fetchTaskProgress).toHaveBeenCalled();
        expect(result.current.state.status).toBe('completed');
        expect(result.current.state.progress).toBe(100);
    });

    it('sets error state when start fails', async () => {
        const onError = vi.fn();
        const api = createApiMocks();
        const startTask = vi.fn().mockResolvedValue({
            success: false,
            error: 'bad request',
            error_code: 'ERR_BAD_REQUEST',
        });

        const { result } = renderHook(() =>
            useTaskRunner({
                startTask,
                onError,
                pollInterval: 10,
                api,
            })
        );

        await act(async () => {
            await result.current.actions.start();
        });

        expect(result.current.state.status).toBe('error');
        expect(result.current.state.errorCode).toBe('ERR_BAD_REQUEST');
        expect(onError).toHaveBeenCalled();
    });
});
