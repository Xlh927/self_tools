import React, { useState, useRef } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import OptionButtons from '../common/OptionButtons.js';
import { augmentDataset } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';
import useDatasetPathInference from '../../hooks/useDatasetPathInference.js';

const { createElement: e, useState: useStateHook, useRef: useRefHook } = React;

export default function AugmentorTool() {
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [annotationFormat, setAnnotationFormat] = useState('yolo');
    const [classesFile, setClassesFile] = useState('');

    // Augmentation options
    const [selectedAugmentations, setSelectedAugmentations] = useState({
        hflip: true,
        vflip: false,
        rotate90: false,
        rotate180: false,
        rotate270: false,
        brightness_up: true,
        brightness_down: true,
        contrast_up: true,
        contrast_down: true,
        noise: false,
        blur: false,
    });

    useDatasetPathInference({
        imagesDir,
        setImagesDir,
        annotationsDir,
        setAnnotationsDir,
        outputDir,
        setOutputDir,
        outputFolderName: 'augmented',
        outputFromAnnotationsMode: 'when_images_empty',
    });

    const toggleAugmentation = (key) => {
        setSelectedAugmentations(prev => ({
            ...prev,
            [key]: !prev[key]
        }));
    };

    const task = useToolTask({
        toolName: 'augmentor',
        startTask: () => {
            const augmentations = Object.keys(selectedAugmentations)
                .filter(key => selectedAugmentations[key]);

            if (augmentations.length === 0) {
                throw new Error('请至少选择一种增强方法');
            }

            return augmentDataset({
                images_dir: imagesDir,
                annotations_dir: annotationsDir,
                output_dir: outputDir,
                annotation_format: annotationFormat,
                augmentations: augmentations,
                classes_file: classesFile || undefined,
            });
        },
    });

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
            e(OptionButtons, {
                options: [
                    { value: 'voc', label: 'VOC (XML)' },
                    { value: 'yolo', label: 'YOLO (TXT)' }
                ],
                value: annotationFormat,
                onChange: setAnnotationFormat,
                ariaLabel: '标注格式'
            })
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
                className: 'result-box info',
                style: {
                    margin: 'var(--spacing-md) 0',
                    borderColor: 'var(--color-info)'
                }
            },
            e('h3',
                { style: { color: 'var(--color-info)' } },
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
                                padding: 'var(--spacing-md)',
                                background: selectedAugmentations[option.key] ? 'var(--color-info-bg)' : 'var(--bg-tertiary)',
                                border: `1.5px solid ${selectedAugmentations[option.key] ? 'var(--color-info)' : 'var(--glass-border)'}`,
                                borderRadius: 'var(--radius-md)',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                opacity: selectedAugmentations[option.key] ? 1 : 0.7,
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

        // Task Controller
        e(TaskController, {
            ...task.taskControllerProps,
            canStart: !!(imagesDir && annotationsDir && outputDir && selectedCount > 0)
        }),

        // Result
        task.result && e('div',
            {
                className: `result-box ${task.result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', {}, task.result.success ? '✅ 增强成功！' : '❌ 增强失败'),
            task.result.success && e('div', {},
                e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-sm)' } },
                    e('div', {}, `原始图片: ${task.result.processed} 张`),
                    e('div', {}, `增强图片: ${task.result.generated} 张`),
                ),
                e('p', { style: { fontWeight: 'bold', color: 'var(--color-success)', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' } },
                    `总计图片: ${task.result.total_images} 张 (${Math.round((task.result.generated / task.result.processed) * 100)}% 增长)`
                ),
                task.result.errors && task.result.errors.length > 0 && e('div', { style: { marginTop: 'var(--spacing-md)', color: 'var(--color-danger)', fontWeight: 600 } },
                    `⚠️ 警告: ${task.result.errors.length} 个文件处理失败`
                )
            ),
            e(ErrorText, { error: task.result.error, errorCode: task.result.error_code })
        )
    );
}
