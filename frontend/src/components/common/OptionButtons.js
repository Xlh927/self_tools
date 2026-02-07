import React from 'react';

const { createElement: e } = React;

export default function OptionButtons({
    options,
    value,
    onChange,
    ariaLabel,
    disabled = false,
    className = '',
    buttonClassName = '',
}) {
    return e(
        'div',
        {
            className: `option-group ${className}`.trim(),
            role: 'group',
            'aria-label': ariaLabel
        },
        ...options.map(option => {
            const isActive = value === option.value;
            const isDisabled = disabled || option.disabled;

            return e(
                'button',
                {
                    key: String(option.value),
                    type: 'button',
                    className: `option-button ${isActive ? 'is-active' : ''} ${buttonClassName}`.trim(),
                    onClick: () => {
                        if (!isDisabled) {
                            onChange(option.value);
                        }
                    },
                    disabled: isDisabled,
                    'aria-pressed': isActive
                },
                option.label
            );
        })
    );
}
