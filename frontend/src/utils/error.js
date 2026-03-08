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
        if (err.payload && typeof err.payload === 'object') {
            return {
                error: err.payload.error || err.payload.message || err.message || 'Error',
                error_code: err.payload.error_code || err.code
            };
        }
        return {
            error: err.error || err.message || 'Error',
            error_code: err.error_code || err.code
        };
    }
    return { error: String(err), error_code: undefined };
}
