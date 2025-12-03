import React, { useState, useEffect, useRef } from 'react';

const { createElement: e } = React;

// Random utility functions
const random = (min, max) => Math.random() * (max - min) + min;

export default function BalloonNote({ note, category, onClick, containerSize, theme }) {
    // State for position and movement
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    const animationRef = useRef(null);

    // Theme Palettes (Gradients)
    const THEME_PALETTES = {
        default: [
            'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)', // Purple/Pink
            'linear-gradient(135deg, #84fab0 0%, #8fd3f4 100%)', // Green/Blue
            'linear-gradient(135deg, #e0c3fc 0%, #8ec5fc 100%)', // Lavender/Blue
            'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)', // Pink/Red
            'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)', // Blue/Cyan
            'linear-gradient(135deg, #fa709a 0%, #fee140 100%)', // Pink/Yellow
        ],
        douyin: [
            'linear-gradient(135deg, #00f2ea 0%, #00c6fb 100%)', // Cyan/Blue
            'linear-gradient(135deg, #ff0050 0%, #ff4b1f 100%)', // Pink/Red
            'linear-gradient(135deg, #7f00ff 0%, #e100ff 100%)', // Purple/Pink
            'linear-gradient(135deg, #ffffff 0%, #e6e9f0 100%)', // White
        ],
        youtube: [
            'linear-gradient(135deg, #ff0000 0%, #cc0000 100%)', // Red
            'linear-gradient(135deg, #ff416c 0%, #ff4b2b 100%)', // Red/Orange
            'linear-gradient(135deg, #ffffff 0%, #f5f5f5 100%)', // White
            'linear-gradient(135deg, #282828 0%, #434343 100%)', // Dark Grey
        ]
    };

    // Get color based on theme
    const getColor = () => {
        const palette = THEME_PALETTES[theme] || THEME_PALETTES['default'];
        // Use category ID hash to pick consistent color from palette
        const hash = category.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return palette[hash % palette.length];
    };

    const balloonGradient = getColor();

    // Initialize random position
    useEffect(() => {
        if (containerSize.width > 0) {
            setPosition({
                x: random(50, containerSize.width - 150),
                y: random(100, containerSize.height - 200)
            });
        }
    }, [containerSize]);

    // Floating animation effect
    useEffect(() => {
        let time = random(0, 100);
        const speed = random(0.3, 0.6);
        const driftSpeed = random(0.1, 0.3);
        const rangeX = random(20, 50);
        const rangeY = random(30, 60);
        const phase = random(0, Math.PI * 2);
        const driftDirection = Math.random() > 0.5 ? 1 : -1;

        const animate = () => {
            time += 0.01 * speed;

            // Vertical bobbing + Horizontal drift
            const bobX = Math.sin(time + phase) * rangeX;
            const bobY = Math.cos(time * 0.8 + phase) * rangeY;

            // Continuous drift
            const driftX = (time * driftSpeed * 10 * driftDirection) % (rangeX * 2);

            setOffset({
                x: bobX + driftX,
                y: bobY
            });
            animationRef.current = requestAnimationFrame(animate);
        };

        animate();
        return () => cancelAnimationFrame(animationRef.current);
    }, []);

    // Size based on content length (clamped)
    const size = Math.min(Math.max(120, note.title.length * 9), 180);
    // Determine tooltip side (left if on right half of screen)
    const tooltipSide = position.x > containerSize.width / 2 ? 'left' : 'right';

    return e('div', {
        className: 'balloon',
        onClick: () => onClick(note),
        style: {
            left: position.x,
            top: position.y,
            width: size,
            height: size,
            background: balloonGradient, // Use gradient directly
            transform: `translate(${offset.x}px, ${offset.y}px)`,
            zIndex: Math.floor(size),
        }
    },
        e('div', { className: 'balloon-knot', style: { background: balloonGradient } }),
        e('div', { className: 'balloon-content' },
            e('div', { className: 'balloon-icon' }, category.icon),
            e('div', { className: 'balloon-title' }, note.title)
        ),
        e('div', { className: `balloon-tooltip tooltip-${tooltipSide}` }, note.command)
    );
}
