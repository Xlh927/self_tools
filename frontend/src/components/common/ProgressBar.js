import React from 'react';

const { createElement: e } = React;

export default function ProgressBar({ progress, message, status }) {
    return e('div',
        {
            className: 'progress-container',
            style: {
                width: '100%',
                marginTop: 'var(--spacing-md)',
                marginBottom: 'var(--spacing-md)',
            }
        },
        e('div',
            {
                style: {
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: '5px',
                    fontSize: '0.9rem',
                    color: 'var(--text-secondary)',
                }
            },
            e('span', {}, message || 'Processing...'),
            e('span', {}, `${progress}%`)
        ),
        e('div',
            {
                style: {
                    width: '100%',
                    height: '8px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '4px',
                    overflow: 'hidden',
                }
            },
            e('div',
                {
                    style: {
                        width: `${progress}%`,
                        height: '100%',
                        background: status === 'error' ? 'var(--neon-orange)' : 'var(--gradient-primary)',
                        transition: 'width 0.3s ease-out',
                        borderRadius: '4px',
                    }
                }
            )
        )
    );
}
