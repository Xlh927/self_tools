export class ApiError extends Error {
    constructor(message, { status, code, payload } = {}) {
        super(message || 'API request failed');
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
        this.payload = payload;
    }
}

function isJsonLikeBody(body) {
    if (body === null || body === undefined) return false;
    if (typeof body !== 'object') return false;
    if (body instanceof FormData) return false;
    if (body instanceof Blob) return false;
    if (body instanceof ArrayBuffer) return false;
    return true;
}

export function unwrapApiPayload(payload) {
    if (!payload || typeof payload !== 'object') return payload;
    if (payload.data && typeof payload.data === 'object') {
        return { ...payload, ...payload.data };
    }
    return payload;
}

export function toApiError(err) {
    if (err instanceof ApiError) return err;
    if (err && typeof err === 'object') {
        return new ApiError(err.message || err.error || 'Request failed', {
            status: err.status,
            code: err.error_code || err.code,
            payload: err,
        });
    }
    return new ApiError(String(err || 'Request failed'));
}

export async function request(url, options = {}) {
    const init = { ...options };
    const headers = { ...(options.headers || {}) };

    if (isJsonLikeBody(options.body)) {
        init.body = JSON.stringify(options.body);
        if (!headers['Content-Type']) {
            headers['Content-Type'] = 'application/json';
        }
    }
    init.headers = headers;

    const response = await fetch(url, init);
    const contentType = response.headers.get('content-type') || '';

    let rawPayload = null;
    if (response.status !== 204) {
        if (contentType.includes('application/json')) {
            rawPayload = await response.json();
        } else {
            const text = await response.text();
            rawPayload = { message: text };
        }
    }

    const payload = unwrapApiPayload(rawPayload || {});

    if (!response.ok || (payload && payload.success === false)) {
        throw new ApiError(
            (payload && (payload.error || payload.message)) || `Request failed (${response.status})`,
            {
                status: response.status,
                code: payload && (payload.error_code || payload.code),
                payload,
            }
        );
    }

    return payload;
}

export function get(url, options = {}) {
    return request(url, { ...options, method: 'GET' });
}

export function post(url, body, options = {}) {
    return request(url, { ...options, method: 'POST', body });
}

export function del(url, options = {}) {
    return request(url, { ...options, method: 'DELETE' });
}
