import React, { useState, useEffect, useRef } from 'react';

const { createElement: e } = React;

// Random utility functions
const random = (min, max) => Math.random() * (max - min) + min;

export default function BalloonNote({ note, category, onClick, containerSize }) {
    // State for position and movement
    const [position, setPosition] = useState({ x: 0, y: 0 });
    const [offset, setOffset] = useState({ x: 0, y: 0 });
    const animationRef = useRef(null);

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
    const bgColor = category.color + '40'; // 25% opacity
    const borderColor = category.color + '80'; // 50% opacity

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
