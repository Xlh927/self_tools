import React from 'react';
import { formatError } from '../../utils/error.js';

const { createElement: e } = React;

export default function ErrorText({ error, errorCode, style }) {
    if (!error && !errorCode) return null;
    return e('p', {
        style: {
            color: 'var(--color-danger)',
            fontWeight: 600,
            ...style
        }
    }, formatError(error, errorCode));
}
