export function normalizePath(path) {
    if (!path) return '';
    return path.replace(/\\/g, '/');
}

function removeTrailingSlashes(path) {
    if (!path) return '';
    // Preserve root indicators while trimming extras from the end
    if (path === '/') return '/';
    return path.replace(/\/+$/, '');
}

export function getParentDir(path) {
    const normalized = normalizePath(path);
    if (!normalized) return '';

    const trimmed = removeTrailingSlashes(normalized);
    if (!trimmed) return normalized.startsWith('/') ? '/' : '';

    const parts = trimmed.split('/');
    if (parts.length <= 1) {
        return parts[0] || (normalized.startsWith('/') ? '/' : '');
    }

    parts.pop();
    const parent = parts.join('/');
    return parent || (normalized.startsWith('/') ? '/' : '');
}

export function joinPaths(...parts) {
    const cleaned = parts
        .filter(Boolean)
        .map((part, index) => {
            let normalized = normalizePath(part);
            if (index > 0) {
                normalized = normalized.replace(/^\/+/, '');
            }
            normalized = removeTrailingSlashes(normalized);
            return normalized;
        });

    if (cleaned.length === 0) return '';
    return cleaned.join('/');
}

export function basename(path) {
    const normalized = normalizePath(path);
    if (!normalized) return '';
    const trimmed = removeTrailingSlashes(normalized);
    const parts = trimmed.split('/');
    return parts.pop() || '';
}
