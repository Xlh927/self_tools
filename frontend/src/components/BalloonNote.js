import React, { useState, useEffect, useRef } from 'react';

const { createElement: e } = React;

// Random utility functions
const random = (min, max) => Math.random() * (max - min) + min;

export default function BalloonNote({ note, category, onClick, containerSize, theme }) {
    // State for position and movement
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    const animationRef = useRef(null);

    // Theme Palettes
    const THEME_PALETTES = {
        default: null, // Use category color
        pornhub: ['#ff9900', '#ffffff', '#e6ac00', '#cccccc', '#ffb84d'], // Orange/White/Yellow
        douyin: ['#00f2ea', '#ff0050', '#ffffff', '#e0e0e0', '#800080'], // Cyan/Pink/White/Purple
        youtube: ['#ff0000', '#ffffff', '#282828', '#cc0000', '#aaaaaa']  // Red/White/Grey
    };

    // Get color based on theme
    const getColor = () => {
        if (!theme || theme === 'default' || !THEME_PALETTES[theme]) {
            return category.color;
        }

        const palette = THEME_PALETTES[theme];
        // Use category ID hash to pick consistent color from palette
        const hash = category.id.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
        return palette[hash % palette.length];
    };

    const baseColor = getColor();

    // Initialize random position
    useEffect(() => {
        if (containerSize.width > 0) {
            setPosition({
                x: random(50, containerSize.width - 100),
                y: random(50, containerSize.height - 100)
            });
        }
    }, [containerSize]);

    // Floating animation effect
    useEffect(() => {
        let time = random(0, 100);
        const speed = random(0.2, 0.5);
        const range = random(10, 30);

        const animate = () => {
            time += 0.01 * speed;
            setOffset({
                x: Math.sin(time) * range,
                y: Math.cos(time * 0.8) * range
            });
            animationRef.current = requestAnimationFrame(animate);
        };

        animate();
        return () => cancelAnimationFrame(animationRef.current);
    }, []);

    // Size based on content length (clamped)
    const size = Math.min(Math.max(100, note.title.length * 8), 160);

    // Color with opacity for glass effect
    const bgColor = baseColor + '40'; // 25% opacity
    const borderColor = baseColor + '80'; // 50% opacity

    return e('div', {
        className: 'balloon glass-card',
        onClick: () => onClick(note),
        style: {
            left: position.x,
            top: position.y,
            width: size,
            height: size,
            backgroundColor: bgColor,
            borderColor: borderColor,
            transform: `translate(${offset.x}px, ${offset.y}px)`,
            zIndex: Math.floor(size), // Larger balloons on top
            display: 'flex',
            flexDirection: 'column',
            padding: '10px',
            textAlign: 'center',
            color: 'var(--text-primary)',
            fontSize: '0.9rem',
            overflow: 'hidden'
        }
    },
        e('div', { style: { fontSize: '1.5rem', marginBottom: '5px' } }, category.icon),
        e('div', {
            style: {
                fontWeight: 600,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 3,
                WebkitBoxOrient: 'vertical'
            }
        }, note.title)
    );
}
