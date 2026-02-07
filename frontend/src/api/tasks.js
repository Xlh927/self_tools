import { get, post } from './http.js';

export function fetchTaskProgress(taskId) {
    return get(`/api/progress/${taskId}`);
}

export function pauseTask(taskId) {
    return post(`/api/task/${taskId}/pause`, {});
}

export function resumeTask(taskId) {
    return post(`/api/task/${taskId}/resume`, {});
}

export function stopTask(taskId) {
    return post(`/api/task/${taskId}/stop`, {});
}

export function retryTask(taskId) {
    return post(`/api/task/${taskId}/retry`, {});
}

export function listTasks({ limit = 100, status } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status) {
        params.set('status', status);
    }
    return get(`/api/tasks?${params.toString()}`);
}

export function getTaskHistory(taskId, { limit = 200 } = {}) {
    return get(`/api/task/${taskId}/history?limit=${encodeURIComponent(String(limit))}`);
}

export function taskProgressStreamUrl(taskId) {
    return `/api/task/${encodeURIComponent(taskId)}/stream`;
}
