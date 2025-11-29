import React, { useState, useEffect, useRef } from 'react';
import ProgressBar from '../common/ProgressBar.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

export default function ConverterTool() {
    const [conversionType, setConversionType] = useState('voc_to_yolo');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [imagesDir, setImagesDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [classesFile, setClassesFile] = useState('');
    const [loading, setLoading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMessage, setProgressMessage] = useState('');
    const [result, setResult] = useState(null);
    const pollTimer = useRef(null);

    // Auto-infer paths from annotationsDir
    useEffect(() => {
        if (annotationsDir && !imagesDir && !outputDir) {
            const parentDir = annotationsDir.split('/').slice(0, -1).join('/');
            setImagesDir(`${parentDir}/images`);
            setOutputDir(`${parentDir}/output_${conversionType}`);
        } else if (annotationsDir && !outputDir) {
            const parentDir = annotationsDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/output_${conversionType}`);
        }
    }, [annotationsDir, conversionType]);

    // Auto-infer paths from imagesDir
    useEffect(() => {
        if (imagesDir && !annotationsDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            // Try common annotation folder names
            const possibleNames = ['annotations', 'labels', 'Annotations', 'Labels'];
            setAnnotationsDir(`${parentDir}/${possibleNames[0]}`);
            setOutputDir(`${parentDir}/output_${conversionType}`);
        } else if (imagesDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/output_${conversionType}`);
        }
    }, [imagesDir, conversionType]);

    // Cleanup timer on unmount
    useEffect(() => {
        return () => {
            if (pollTimer.current) clearInterval(pollTimer.current);
        };
    }, []);

    const startPolling = (taskId) => {
        pollTimer.current = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}`);
                if (res.status === 404) {
                    clearInterval(pollTimer.current);
                    return;
                }
                const data = await res.json();

                setProgress(data.progress);
                setProgressMessage(data.message);

                if (data.status === 'completed') {
                    clearInterval(pollTimer.current);
                    setLoading(false);
                    setResult(data.result);
                } else if (data.status === 'error') {
                    clearInterval(pollTimer.current);
                    setLoading(false);
                    setResult({ success: false, error: data.error });
                }
            } catch (err) {
                console.error('Polling error:', err);
            }
        }, 500);
    };

    const handleConvert = async () => {
        setLoading(true);
        setResult(null);
        setProgress(0);
        setProgressMessage('Starting...');

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    conversion_type: conversionType,
                    annotations_dir: annotationsDir,
                    images_dir: imagesDir,
                    output_dir: outputDir,
                    classes_file: classesFile || undefined,
                }),
            });

            const data = await response.json();

            if (data.success && data.task_id) {
                startPolling(data.task_id);
            } else {
                setLoading(false);
                setResult(data);
            }
        } catch (error) {
            setLoading(false);
            setResult({ success: false, error: error.message });
        }
    };

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Conversion Type
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '转换方向'),
            e('select',
                {
                    className: 'select-field',
                    value: conversionType,
                    onChange: (e) => setConversionType(e.target.value),
                },
                e('option', { value: 'voc_to_yolo' }, 'VOC → YOLO'),
                e('option', { value: 'yolo_to_voc' }, 'YOLO → VOC')
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

        // Images Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🖼️ 图片文件目录',
                e('span', { style: { color: 'var(--neon-green)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(自动推理)')
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

        // Classes File
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🏷️ 类别文件',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } },
                    conversionType === 'yolo_to_voc' ? '(必填)' : '(可选，自动生成)'
                )
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

        // Progress Bar
        loading && e(ProgressBar, { progress, message: progressMessage }),

        // Convert Button
        !loading && e('button',
            {
                className: 'btn btn-primary',
                onClick: handleConvert,
                disabled: !annotationsDir || !imagesDir || !outputDir,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                }
            },
            '🚀 开始转换'
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
            e('h3', {}, result.success ? '✅ 转换成功！' : '❌ 转换失败'),
            result.success && e('div', {},
                e('p', {}, `已转换: ${result.converted} 个文件`),
                result.skipped > 0 && e('p', {}, `跳过: ${result.skipped} 个文件`),
                result.classes && e('div', {},
                    e('p', {}, '检测到的类别:'),
                    e('div',
                        { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--spacing-sm)', marginTop: 'var(--spacing-sm)' } },
                        ...result.classes.map(cls =>
                            e('span',
                                {
                                    key: cls,
                                    style: {
                                        background: 'var(--gradient-primary)',
                                        padding: '0.25rem 0.75rem',
                                        borderRadius: 'var(--radius-md)',
                                        fontSize: '0.9rem',
                                    }
                                },
                                cls
                            )
                        )
                    )
                )
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
