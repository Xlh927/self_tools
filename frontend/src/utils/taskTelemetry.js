const TELEMETRY_EVENT_NAME = 'self-tools:task-telemetry';
const TELEMETRY_BUFFER_KEY = '__SELF_TOOLS_TASK_TELEMETRY__';
const TELEMETRY_BUFFER_LIMIT = 200;

function safeWindow() {
    if (typeof window === 'undefined') return null;
    return window;
}

function appendToBuffer(win, entry) {
    if (!win) return;
    const current = Array.isArray(win[TELEMETRY_BUFFER_KEY]) ? win[TELEMETRY_BUFFER_KEY] : [];
    current.push(entry);
    if (current.length > TELEMETRY_BUFFER_LIMIT) {
        current.splice(0, current.length - TELEMETRY_BUFFER_LIMIT);
    }
    win[TELEMETRY_BUFFER_KEY] = current;
}

function dispatchTelemetryEvent(win, entry) {
    if (!win || typeof win.dispatchEvent !== 'function' || typeof CustomEvent === 'undefined') return;
    win.dispatchEvent(new CustomEvent(TELEMETRY_EVENT_NAME, { detail: entry }));
}

export function reportTaskTelemetry(eventName, payload = {}) {
    const entry = {
        event: eventName,
        timestamp_ms: Date.now(),
        ...payload,
    };

    const win = safeWindow();
    appendToBuffer(win, entry);
    dispatchTelemetryEvent(win, entry);

    try {
        if (eventName === 'tool_task_failed') {
            console.error('[task-telemetry]', entry);
        } else {
            console.info('[task-telemetry]', entry);
        }
    } catch (_err) {
        // Ignore console failures in restricted environments.
    }

    return entry;
}

export function getTaskTelemetryEventName() {
    return TELEMETRY_EVENT_NAME;
}

