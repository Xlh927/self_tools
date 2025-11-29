import React, { useState, useEffect } from 'react';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function VisualizerTool() {
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    // Auto-infer output path
    useEffect(() => {
        if (imagesDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/visualized`);
        }
    }, [imagesDir]);

    // Auto-infer annotations path
    useEffect(() => {
        if (imagesDir && !annotationsDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            // Guess
            // setAnnotationsDir(`${parentDir}/annotations`);
        }
    }, [imagesDir]);

    const handleVisualize = async () => {
        setLoading(true);
        setResult(null);

        try {
            const response = await fetch('/api/visualize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    images_dir: imagesDir,
                    annotations_dir: annotationsDir,
                    output_dir: outputDir,
                }),
            });

            const data = await response.json();
            setResult(data);
        } catch (error) {
            setResult({ success: false, error: error.message });
        } finally {
            setLoading(false);
        }
    };

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Images Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🖼️ 图片文件目录',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/images',
                    value: imagesDir,
                    onChange: (e) => setImagesDir(e.target.value),
                }
            )
        ),

        // Annotations Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📁 标注文件目录',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/annotations',
                    value: annotationsDir,
                    onChange: (e) => setAnnotationsDir(e.target.value),
                }
            )
        ),

        // Output Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📤 输出目录',
                e('span', { style: { color: 'var(--neon-green)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(自动推理)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/output',
                    value: outputDir,
                    onChange: (e) => setOutputDir(e.target.value),
                }
            )
        ),

        // Visualize Button
        e('button',
            {
                className: 'btn btn-primary',
                onClick: handleVisualize,
                disabled: loading || !imagesDir || !annotationsDir || !outputDir,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                }
            },
            loading ? '可视化生成中...' : '👁️ 开始可视化'
        ),

        // Result
        result && e('div',
            {
                className: 'glass-card',
                style: {
                    marginTop: 'var(--spacing-lg)',
                    background: result.success ? 'rgba(67, 233, 123, 0.1)' : 'rgba(245, 87, 108, 0.1)',
                    border: `2px solid ${result.success ? 'var(--neon-green)' : 'var(--neon-orange)'}`,
                }
            },
            e('h3', {}, result.success ? '✅ 可视化完成！' : '❌ 可视化失败'),
            result.success && e('div', {},
                e('p', {}, `处理图片: ${result.total_images || 0}`),
                e('p', {}, `生成可视化: ${result.visualized_count || 0}`),
                result.output_dir && e('p', { style: { fontSize: '0.9rem', opacity: 0.8 } }, `输出目录: ${result.output_dir}`)
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
