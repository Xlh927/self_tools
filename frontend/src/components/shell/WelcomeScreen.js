import React from 'react';

const { createElement: e } = React;

export default function WelcomeScreen() {
    return e('div',
        {
            className: 'welcome-screen animate-fade-in-up',
            style: {
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                width: '100%',
                height: '100%',
                textAlign: 'center',
                opacity: 0.8,
            }
        },
        e('div',
            {
                style: {
                    fontSize: '6rem',
                    marginBottom: 'var(--spacing-xl)',
                    animation: 'pulse 2s ease-in-out infinite',
                }
            },
            '🚀'
        ),
        e('h2',
            {
                style: {
                    fontSize: '2.5rem',
                    marginBottom: 'var(--spacing-lg)',
                    background: 'var(--gradient-primary)',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    backgroundClip: 'text',
                }
            },
            '点击工具添加到工作台'
        ),
        e('p',
            {
                style: {
                    fontSize: '1.2rem',
                    color: 'var(--text-secondary)',
                    maxWidth: '600px',
                }
            },
            '工作流模式,开发中...'
        )
    );
}
