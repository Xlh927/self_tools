import React, { useState, useEffect } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import OptionButtons from '../common/OptionButtons.js';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';
import { normalizeError } from '../../utils/error.js';
import { generateDataset, scanClasses as scanClassesApi } from '../../api/tools.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function GeneratorTool() {
    const [annotationFormat, setAnnotationFormat] = useState('voc');
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [windowWidth, setWindowWidth] = useState(640);
    const [windowHeight, setWindowHeight] = useState(640);
    const [strideX, setStrideX] = useState(320);
    const [strideY, setStrideY] = useState(320);
    const [overlapThreshold, setOverlapThreshold] = useState(100);

    const [availableClasses, setAvailableClasses] = useState([]);
    const [selectedClasses, setSelectedClasses] = useState([]);
    const [scanningClasses, setScanningClasses] = useState(false);

    // Result state
    const [result, setResult] = useState(null);

    // Auto-infer paths from imagesDir
    useEffect(() => {
        const normalized = normalizePath(imagesDir);
        if (normalized && !annotationsDir && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setAnnotationsDir(joinPaths(parentDir, 'annotations'));
            setOutputDir(joinPaths(parentDir, 'generated_dataset'));
        } else if (normalized && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setOutputDir(joinPaths(parentDir, 'generated_dataset'));
        }
    }, [imagesDir]);

    // Auto-infer paths from annotationsDir
    useEffect(() => {
        const normalized = normalizePath(annotationsDir);
        if (normalized && !imagesDir && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setImagesDir(joinPaths(parentDir, 'images'));
            setOutputDir(joinPaths(parentDir, 'generated_dataset'));
        } else if (normalized && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setOutputDir(joinPaths(parentDir, 'generated_dataset'));
        }
    }, [annotationsDir]);

    // Auto-detect classes when annotations dir changes
    useEffect(() => {
        if (annotationsDir) {
            scanAnnotationClasses();
        }
    }, [annotationsDir, annotationFormat]);

    const scanAnnotationClasses = async () => {
        if (!annotationsDir) return;
        setScanningClasses(true);
        try {
            const data = await scanClassesApi({
                annotations_dir: annotationsDir,
                is_yolo_format: annotationFormat === 'yolo'
            });
            if (data.success) {
                setAvailableClasses(data.classes.map(c => c.name));
                // Default select all
                setSelectedClasses(data.classes.map(c => c.name));
            }
        } catch (error) {
            console.error('Failed to scan classes:', error);
        } finally {
            setScanningClasses(false);
        }
    };

    const toggleClass = (cls) => {
        if (selectedClasses.includes(cls)) {
            setSelectedClasses(selectedClasses.filter(c => c !== cls));
        } else {
            setSelectedClasses([...selectedClasses, cls]);
        }
    };

    const handleStartTask = async () => {
        setResult(null);

        return generateDataset({
            annotation_format: annotationFormat,
            images_dir: imagesDir,
            annotations_dir: annotationsDir,
            output_dir: outputDir,
            classes: selectedClasses,
            window_width: parseInt(windowWidth, 10),
            window_height: parseInt(windowHeight, 10),
            stride_x: parseInt(strideX, 10),
            stride_y: parseInt(strideY, 10),
            overlap_threshold: parseInt(overlapThreshold, 10),
        });
    };

    const handleComplete = (res) => {
        setResult(res);
    };

    const handleError = (err) => {
        const normalized = normalizeError(err);
        setResult({ success: false, ...normalized });
    };

    const handleStop = () => {
        return undefined;
    };

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Format Selection
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '标注格式'),
            e(OptionButtons, {
                options: [
                    { value: 'voc', label: 'VOC (XML)' },
                    { value: 'yolo', label: 'YOLO (TXT)' },
                    { value: 'json', label: 'COCO (JSON)' }
                ],
                value: annotationFormat,
                onChange: setAnnotationFormat,
                ariaLabel: '标注格式'
            })
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
                    onBlur: scanAnnotationClasses,
                }
            )
        ),

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

        // Class Selection
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🏷️ 筛选类别',
                scanningClasses && e('span', { className: 'animate-pulse', style: { marginLeft: '10px', color: 'var(--neon-blue)' } }, '扫描中...')
            ),
            e('div',
                {
                    style: {
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 'var(--spacing-sm)',
                        padding: 'var(--spacing-md)',
                        background: 'var(--form-bg)',
                        borderRadius: 'var(--radius-md)',
                        border: '1.5px solid var(--form-border)',
                        minHeight: '60px',
                    }
                },
                availableClasses.length > 0
                    ? availableClasses.map(cls =>
                        e('button',
                            {
                                key: cls,
                                onClick: () => toggleClass(cls),
                                style: {
                                    padding: '0.25rem 0.75rem',
                                    borderRadius: 'var(--radius-md)',
                                    border: 'none',
                                    background: selectedClasses.includes(cls) ? 'var(--gradient-primary)' : 'rgba(255,255,255,0.1)',
                                    color: 'white',
                                    cursor: 'pointer',
                                    fontSize: '0.9rem',
                                    transition: 'all 0.2s',
                                }
                            },
                            cls
                        )
                    )
                    : e('span', { style: { color: 'var(--text-tertiary)' } }, '输入标注目录后自动加载类别...')
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

        // Parameters Grid
        e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' } },
            // Window Size
            e('div', { className: 'result-box info', style: { padding: 'var(--spacing-md)', borderColor: 'var(--color-info)' } },
                e('h4', { style: { marginTop: 0, color: 'var(--color-info)' } }, '窗口大小'),
                e('div', { className: 'input-group', style: { marginBottom: 'var(--spacing-sm)' } },
                    e('label', { className: 'input-label' }, '宽度 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: windowWidth,
                        onChange: (e) => setWindowWidth(e.target.value)
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '高度 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: windowHeight,
                        onChange: (e) => setWindowHeight(e.target.value)
                    })
                )
            ),
            // Stride
            e('div', { className: 'result-box success', style: { padding: 'var(--spacing-md)', borderColor: 'var(--color-success)' } },
                e('h4', { style: { marginTop: 0, color: 'var(--color-success)' } }, '步长 (Stride)'),
                e('div', { className: 'input-group', style: { marginBottom: 'var(--spacing-sm)' } },
                    e('label', { className: 'input-label' }, '横向 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: strideX,
                        onChange: (e) => setStrideX(e.target.value)
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '纵向 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: strideY,
                        onChange: (e) => setStrideY(e.target.value)
                    })
                )
            )
        ),

        // Task Controller
        e(TaskController, {
            onStart: handleStartTask,
            onComplete: handleComplete,
            onError: handleError,
            onStop: handleStop,
            canStart: !!(imagesDir && annotationsDir && outputDir)
        }),

        // Result
        result && e('div',
            {
                className: `result-box ${result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', {}, result.success ? '✅ 生成完成！' : '❌ 生成失败'),
            result.success && e('div', {},
                e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-sm)' } },
                    e('div', {}, `生成图片数: ${result.total_images || 0}`),
                    e('div', {}, `生成标注数: ${result.total_annotations || 0}`),
                ),
                result.output_dir && e('p', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px', display: 'inline-block' } }, `输出目录: ${result.output_dir}`)
            ),
            e(ErrorText, { error: result.error, errorCode: result.error_code })
        )
    );
}
