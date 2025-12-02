import React, { useState, useEffect } from 'react';

const { createElement: e } = React;

export default function AugmentorTool() {
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [annotationFormat, setAnnotationFormat] = useState('voc');
    const [classesFile, setClassesFile] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    // Augmentation options
    const [selectedAugmentations, setSelectedAugmentations] = useState({
        hflip: true,
        vflip: false,
        rotate90: false,
        rotate180: false,
        rotate270: false,
        brightness_up: false,
        brightness_down: false,
        contrast_up: false,
        contrast_down: false,
        noise: false,
        blur: false,
    });

    // Auto-infer paths
    useEffect(() => {
        if (imagesDir && !annotationsDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            setAnnotationsDir(`${parentDir}/annotations`);
            setOutputDir(`${parentDir}/augmented`);
        } else if (imagesDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/augmented`);
        }
    }, [imagesDir]);

    const toggleAugmentation = (key) => {
        setSelectedAugmentations(prev => ({
            ...prev,
            [key]: !prev[key]
        }));
    };

    const handleAugment = async () => {
        setLoading(true);
        setResult(null);

        try {
            // Get selected augmentations
            const augmentations = Object.keys(selectedAugmentations)
                .filter(key => selectedAugmentations[key]);

            if (augmentations.length === 0) {
                setResult({ success: false, error: '请至少选择一种增强方法' });
                setLoading(false);
                return;
            }

            const response = await fetch('/api/augment', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    images_dir: imagesDir,
                    annotations_dir: annotationsDir,
                    output_dir: outputDir,
                    annotation_format: annotationFormat,
                    augmentations: augmentations,
                    classes_file: classesFile || undefined,
                }),
            });

            const data = await response.json();
            setResult(data);
            setLoading(false);
        } catch (error) {
            setResult({ success: false, error: error.message });
            setLoading(false);
        }
    };

    const augmentationOptions = [
        { key: 'hflip', label: '水平翻转', icon: '↔️', category: 'geometric' },
        { key: 'vflip', label: '垂直翻转', icon: '↕️', category: 'geometric' },
        { key: 'rotate90', label: '旋转90°', icon: '↻', category: 'geometric' },
        { key: 'rotate180', label: '旋转180°', icon: '↺', category: 'geometric' },
        { key: 'rotate270', label: '旋转270°', icon: '↶', category: 'geometric' },
        { key: 'brightness_up', label: '提高亮度', icon: '☀️', category: 'color' },
        { key: 'brightness_down', label: '降低亮度', icon: '🌙', category: 'color' },
        { key: 'contrast_up', label: '提高对比度', icon: '🔆', category: 'color' },
        { key: 'contrast_down', label: '降低对比度', icon: '🔅', category: 'color' },
        { key: 'noise', label: '添加噪声', icon: '🌫️', category: 'effect' },
        { key: 'blur', label: '高斯模糊', icon: '💧', category: 'effect' },
    ];

    const selectedCount = Object.values(selectedAugmentations).filter(Boolean).length;

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Header
        e('div',
            { className: 'glass-card', style: { padding: 'var(--spacing-md)', background: 'rgba(138, 43, 226, 0.1)', border: '2px solid var(--neon-purple)' } },
            e('h2', { style: { margin: 0, color: 'var(--neon-purple)' } }, '📊 数据集增强'),
            e('p', { style: { margin: '0.5rem 0 0 0', color: 'var(--text-secondary)' } },
                '通过图像变换扩充数据集，自动处理标注文件'
            )
        ),

        // Images Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🖼️ 图片目录',
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
                '📁 标注目录',
                e('span', { style: { color: 'var(--neon-green)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(自动推理)')
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

        // Annotation Format
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '🏷️ 标注格式'),
            e('select',
                {
                    className: 'select-field',
                    value: annotationFormat,
                    onChange: (e) => setAnnotationFormat(e.target.value),
                },
                e('option', { value: 'voc' }, 'VOC (XML)'),
                e('option', { value: 'yolo' }, 'YOLO (TXT)')
            )
        ),

        // Classes File (for YOLO)
        annotationFormat === 'yolo' && e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📋 类别文件',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(可选)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/classes.txt',
                    value: classesFile,
                    onChange: (e) => setClassesFile(e.target.value),
                }
            )
        ),

        // Augmentation Options
        e('div',
            {
                className: 'glass-card',
                style: {
                    padding: 'var(--spacing-md)',
                    background: 'rgba(67, 233, 123, 0.05)',
                    border: '2px solid var(--neon-green)',
                }
            },
            e('h3',
                { style: { marginBottom: 'var(--spacing-md)', color: 'var(--neon-green)' } },
                `增强方法 (已选择: ${selectedCount})`
            ),
            e('div',
                { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 'var(--spacing-sm)' } },
                ...augmentationOptions.map(option =>
                    e('div',
                        {
                            key: option.key,
                            onClick: () => toggleAugmentation(option.key),
                            style: {
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--spacing-sm)',
                                padding: 'var(--spacing-sm)',
                                background: selectedAugmentations[option.key] ? 'rgba(67, 233, 123, 0.15)' : 'rgba(255, 255, 255, 0.03)',
                                border: `2px solid ${selectedAugmentations[option.key] ? 'var(--neon-green)' : 'rgba(255, 255, 255, 0.1)'}`,
                                borderRadius: 'var(--radius-md)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                opacity: selectedAugmentations[option.key] ? 1 : 0.6,
                            }
                        },
                        e('input',
                            {
                                type: 'checkbox',
                                checked: selectedAugmentations[option.key],
                                onChange: () => { },
                                style: {
                                    width: '18px',
                                    height: '18px',
                                    accentColor: 'var(--neon-green)',
                                    cursor: 'pointer',
                                }
                            }
                        ),
                        e('span', { style: { fontSize: '1.2rem' } }, option.icon),
                        e('span', { style: { flex: 1, fontWeight: '500', fontSize: '0.9rem' } }, option.label)
                    )
                )
            )
        ),

        // Augment Button
        !loading && e('button',
            {
                className: 'btn btn-primary',
                onClick: handleAugment,
                disabled: !imagesDir || !annotationsDir || !outputDir || selectedCount === 0,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                }
            },
            '🚀 开始增强'
        ),

        // Loading
        loading && e('div',
            { style: { textAlign: 'center', padding: 'var(--spacing-lg)', color: 'var(--neon-green)' } },
            e('div', { className: 'spinner' }),
            e('p', {}, '正在处理数据增强...')
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
            e('h3', {}, result.success ? '✅ 增强成功！' : '❌ 增强失败'),
            result.success && e('div', {},
                e('p', {}, `原始图片: ${result.processed} 张`),
                e('p', {}, `增强图片: ${result.generated} 张`),
                e('p', { style: { fontWeight: 'bold', color: 'var(--neon-green)' } },
                    `总计图片: ${result.total_images} 张 (${Math.round((result.generated / result.processed) * 100)}% 增长)`
                ),
                result.errors && result.errors.length > 0 && e('div', {},
                    e('p', { style: { marginTop: 'var(--spacing-md)', color: 'var(--neon-orange)' } },
                        `⚠️ 警告: ${result.errors.length} 个文件处理失败`
                    )
                )
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
