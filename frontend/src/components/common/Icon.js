// Icon Component - Using Heroicons style SVG icons
// All icons use 24x24 viewBox for consistency

import React from 'react';

const { createElement: e } = React;

// Icon mapping - Heroicons style SVG paths
const ICONS = {
    // Navigation & Actions
    'home': {
        path: [
            { d: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z' },
            { d: 'M9 22V12h6v10' }
        ]
    },
    'refresh': {
        path: [
            { d: 'M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8' },
            { d: 'M21 3v5h-5' },
            { d: 'M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16' },
            { d: 'M3 21v-5h5' }
        ]
    },
    'x': {
        path: [
            { d: 'M18 6L6 18' },
            { d: 'M6 6l12 12' }
        ]
    },
    'settings': {
        path: [
            { d: 'M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z' },
            { d: 'M9 12a3 3 0 1 0 6 0 3 3 0 1 0-6 0' }
        ]
    },
    'trash': {
        path: [
            { d: 'M3 6h18' },
            { d: 'M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6' },
            { d: 'M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2' },
            { d: 'M10 11v6' },
            { d: 'M14 11v6' }
        ]
    },
    
    // Tool Icons
    'arrow-path': { // Converter
        path: [
            { d: 'M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2' }
        ]
    },
    'scissors': { // Cropper
        path: [
            { d: 'M6 9H4.5a2.5 2.5 0 0 1 0-5H6' },
            { d: 'M18 9h1.5a2.5 2.5 0 0 0 0-5H18' },
            { d: 'M4 22h16' },
            { d: 'M10 14.66V19c0 .55-.47.98-.97 1.21C7.85 20.75 7 20 7 19' },
            { d: 'M14 14.66V19c0 .55.47.98.97 1.21C16.15 20.75 17 20 17 19' }
        ]
    },
    'target': { // Generator
        path: [
            { d: 'M12 2v4' },
            { d: 'M12 18v4' },
            { d: 'M4.93 4.93l2.83 2.83' },
            { d: 'M16.24 16.24l2.83 2.83' },
            { d: 'M2 12h4' },
            { d: 'M18 12h4' },
            { d: 'M4.93 19.07l2.83-2.83' },
            { d: 'M16.24 7.76l2.83-2.83' },
            { d: 'M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0-6 0' }
        ]
    },
    'chart-bar': { // Splitter
        path: [
            { d: 'M3 3v18h18' },
            { d: 'M7 16h.01' },
            { d: 'M11 12h.01' },
            { d: 'M15 8h.01' },
            { d: 'M19 4h.01' }
        ]
    },
    'trash-2': { // Deduplicator
        path: [
            { d: 'M3 6h18' },
            { d: 'M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6' },
            { d: 'M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2' }
        ]
    },
    'search': { // Matcher
        path: [
            { d: 'M21 21l-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607z' }
        ]
    },
    'eye': { // Visualizer
        path: [
            { d: 'M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7' },
            { d: 'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2' }
        ]
    },
    'tag': { // Label Modifier
        path: [
            { d: 'M12 2H2v10l9.29 9.29a2 2 0 0 0 2.82 0l6.58-6.58a2 2 0 0 0 0-2.82L12 2' },
            { d: 'M7 7h.01' }
        ]
    },
    'sparkles': { // Augmentor
        path: [
            { d: 'M12 2v4' },
            { d: 'M12 18v4' },
            { d: 'M4.93 4.93l2.83 2.83' },
            { d: 'M16.24 16.24l2.83 2.83' },
            { d: 'M2 12h4' },
            { d: 'M18 12h4' },
            { d: 'M4.93 19.07l2.83-2.83' },
            { d: 'M16.24 7.76l2.83-2.83' },
            { d: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8' }
        ]
    },
    'layout-grid': { // Grid Generator
        path: [
            { d: 'M3 3h8v8H3z' },
            { d: 'M14 3h7v7h-7z' },
            { d: 'M14 14h7v7h-7z' },
            { d: 'M3 14h8v8H3z' }
        ]
    },
    'rocket': { // Slurm Generator
        path: [
            { d: 'M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z' },
            { d: 'M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z' },
            { d: 'M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0' },
            { d: 'M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5' }
        ],
        fill: true
    },
    'sparkle': { // Cleaner
        path: [
            { d: 'M12 2v4' },
            { d: 'M12 18v4' },
            { d: 'M4.93 4.93l2.83 2.83' },
            { d: 'M16.24 16.24l2.83 2.83' },
            { d: 'M2 12h4' },
            { d: 'M18 12h4' },
            { d: 'M4.93 19.07l2.83-2.83' },
            { d: 'M16.24 7.76l2.83-2.83' }
        ]
    },
    
    // Navigation
    'chevron-left': {
        path: [
            { d: 'M15 18l-6-6 6-6' }
        ]
    },
    'chevron-right': {
        path: [
            { d: 'M9 18l6-6-6-6' }
        ]
    }
};

export default function Icon({ name, size = 24, className = '', style = {}, strokeWidth = 2 }) {
    const icon = ICONS[name];
    
    if (!icon) {
        console.warn(`Icon "${name}" not found`);
        return null;
    }
    
    const svgProps = {
        viewBox: '0 0 24 24',
        width: size,
        height: size,
        stroke: 'currentColor',
        strokeWidth: strokeWidth,
        strokeLinecap: 'round',
        strokeLinejoin: 'round',
        className: className,
        style: style,
        'aria-hidden': 'true'
    };
    
    if (icon.fill) {
        svgProps.fill = 'currentColor';
    } else {
        svgProps.fill = 'none';
    }
    
    return e('svg', svgProps,
        ...icon.path.map((pathData, idx) => 
            e('path', { key: idx, ...pathData })
        )
    );
}
