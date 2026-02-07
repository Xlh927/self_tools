export function formatError(error, errorCode) {
    if (!error && !errorCode) return '';
    if (error && errorCode) return `${error} (${errorCode})`;
    return error || errorCode || '';
}

export function normalizeError(err) {
    if (!err) {
        return { error: 'Unknown error', error_code: undefined };
    }
    if (typeof err === 'string') {
        return { error: err, error_code: undefined };
    }
    if (typeof err === 'object') {
        return {
            error: err.error || err.message || 'Error',
            error_code: err.error_code || err.code
        };
    }
    return { error: String(err), error_code: undefined };
}
