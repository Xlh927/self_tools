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
        stretch_width: false,
        stretch_height: false,
        brightness: true,
        contrast: true,
        noise: false,
        blur: false,
    });
    const [augmentationParams, setAugmentationParams] = useState({
        stretch_width: { min: 0.8, max: 1.2 },
        stretch_height: { min: 0.9, max: 1.1 },
        brightness: { min: 0.7, max: 1.3 },
        contrast: { min: 0.7, max: 1.3 },
        noise: { var_min: 0, var_max: 15 },
        blur: { kernel: 3 },
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

    const updateAugmentationParam = (key, param, value) => {
        setAugmentationParams(prev => ({
            ...prev,
            [key]: {
                ...prev[key],
                [param]: value
            }
        }));
    };

    const buildAugmentationPayload = (key) => {
        const params = augmentationParams[key];
        if (!params) {
            return { name: key };
        }
        return { name: key, ...params };
    };

    const task = useToolTask({
        toolName: 'augmentor',
        startTask: () => {
            const augmentations = Object.keys(selectedAugmentations)
                .filter(key => selectedAugmentations[key])
                .map(buildAugmentationPayload);

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
        { key: 'stretch_width', label: '宽度拉伸', icon: '⇔', category: 'geometric', params: [
            { name: 'min', label: '最小', type: 'number', min: 0.5, max: 2.0, step: 0.05 },
            { name: 'max', label: '最大', type: 'number', min: 0.5, max: 2.0, step: 0.05 },
        ] },
        { key: 'stretch_height', label: '高度拉伸', icon: '⇕', category: 'geometric', params: [
            { name: 'min', label: '最小', type: 'number', min: 0.5, max: 2.0, step: 0.05 },
            { name: 'max', label: '最大', type: 'number', min: 0.5, max: 2.0, step: 0.05 },
        ] },
        { key: 'brightness', label: '亮度调整', icon: '☀️', category: 'color', params: [
            { name: 'min', label: '最小系数', type: 'number', min: 0.1, max: 3.0, step: 0.05 },
            { name: 'max', label: '最大系数', type: 'number', min: 0.1, max: 3.0, step: 0.05 },
        ] },
        { key: 'contrast', label: '对比度调整', icon: '🔆', category: 'color', params: [
            { name: 'min', label: '最小系数', type: 'number', min: 0.1, max: 3.0, step: 0.05 },
            { name: 'max', label: '最大系数', type: 'number', min: 0.1, max: 3.0, step: 0.05 },
        ] },
        { key: 'noise', label: '添加噪声', icon: '🌫️', category: 'effect', params: [
            { name: 'var_min', label: '最小方差', type: 'number', min: 0, max: 100, step: 1 },
            { name: 'var_max', label: '最大方差', type: 'number', min: 0, max: 100, step: 1 },
        ] },
        { key: 'blur', label: '高斯模糊', icon: '💧', category: 'effect', params: [
            { name: 'kernel', label: '核大小', type: 'select', options: [3, 5, 7] },
        ] },
    ];

    const selectedCount = Object.values(selectedAugmentations).filter(Boolean).length;

    const renderParamControls = (option) => {
        if (!selectedAugmentations[option.key] || !option.params) {
            return null;
        }

        return e('div',
            {
                onClick: (event) => event.stopPropagation(),
                style: {
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(86px, 1fr))',
                    gap: 'var(--spacing-xs)',
                    width: '100%',
                    marginTop: 'var(--spacing-sm)',
                    paddingTop: 'var(--spacing-sm)',
                    borderTop: '1px solid var(--glass-border)',
                }
            },
            ...option.params.map(param =>
                e('label',
                    {
                        key: param.name,
                        style: {
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '4px',
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            fontWeight: 600,
                        }
                    },
                    param.label,
                    param.type === 'select'
                        ? e('select', {
                            className: 'input-field',
                            value: augmentationParams[option.key][param.name],
                            onChange: (event) => updateAugmentationParam(option.key, param.name, Number(event.target.value)),
                            style: { padding: '6px 8px', fontSize: '0.8rem' },
                        },
                            ...param.options.map(value =>
                                e('option', { key: value, value }, value)
                            )
                        )
                        : e('input', {
                            type: 'number',
                            className: 'input-field',
                            value: augmentationParams[option.key][param.name],
                            min: param.min,
                            max: param.max,
                            step: param.step,
                            onChange: (event) => updateAugmentationParam(option.key, param.name, Number(event.target.value)),
                            style: { padding: '6px 8px', fontSize: '0.8rem' },
                        })
                )
            )
        );
    };

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
                { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--spacing-sm)' } },
                ...augmentationOptions.map(option =>
                    e('div',
                        {
                            key: option.key,
                            onClick: () => toggleAugmentation(option.key),
                            style: {
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'stretch',
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
                        e('div',
                            { style: { display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' } },
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
                        ),
                        renderParamControls(option)
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
