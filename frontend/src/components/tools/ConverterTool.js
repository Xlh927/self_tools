import React, { useState, useEffect, useRef } from 'react';
import ProgressBar from '../common/ProgressBar.js';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';

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

    // New state for class scanning
    const [scannedClasses, setScannedClasses] = useState([]);
    const [scanningClasses, setScanningClasses] = useState(false);
    const [showClassEditor, setShowClassEditor] = useState(false);

    // Auto-infer paths from annotationsDir
    useEffect(() => {
        const normalized = normalizePath(annotationsDir);
        if (normalized && !imagesDir && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setImagesDir(joinPaths(parentDir, 'images'));
            const defaultOut = conversionType === 'voc_to_yolo' ? 'labels' : 'xml';
            setOutputDir(joinPaths(parentDir, defaultOut));
        } else if (normalized && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            const defaultOut = conversionType === 'voc_to_yolo' ? 'labels' : 'xml';
            setOutputDir(joinPaths(parentDir, defaultOut));
        }
    }, [annotationsDir, conversionType]);

    // Auto-infer paths from imagesDir
    useEffect(() => {
        const normalized = normalizePath(imagesDir);
        if (normalized && !annotationsDir && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            // Try common annotation folder names
            const possibleNames = ['annotations', 'labels', 'Annotations', 'Labels', 'xml'];
            setAnnotationsDir(joinPaths(parentDir, possibleNames[0]));
            const defaultOut = conversionType === 'voc_to_yolo' ? 'labels' : 'xml';
            setOutputDir(joinPaths(parentDir, defaultOut));
        } else if (normalized && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            const defaultOut = conversionType === 'voc_to_yolo' ? 'labels' : 'xml';
            setOutputDir(joinPaths(parentDir, defaultOut));
        }
    }, [imagesDir, conversionType]);

    // Auto-scan VOC classes when annotationsDir changes for voc_to_yolo
    useEffect(() => {
        if (conversionType === 'voc_to_yolo' && annotationsDir && annotationsDir.trim() !== '') {
            scanVocClasses();
        } else {
            setScannedClasses([]);
            setShowClassEditor(false);
        }
    }, [annotationsDir, conversionType]);

    // Cleanup timer on unmount
    useEffect(() => {
        return () => {
            if (pollTimer.current) clearInterval(pollTimer.current);
        };
    }, []);

    const scanVocClasses = async () => {
        setScanningClasses(true);
        try {
            const response = await fetch('/api/scan-voc-classes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ annotations_dir: annotationsDir }),
            });

            const data = await response.json();

            if (data.success) {
                // Add enabled property to each class (default: true)
                const classesWithSelection = data.classes.map(cls => ({
                    ...cls,
                    enabled: true
                }));
                setScannedClasses(classesWithSelection);
                setShowClassEditor(true);
            } else {
                console.error('Failed to scan classes:', data.error);
                setScannedClasses([]);
                setShowClassEditor(false);
            }
        } catch (error) {
            console.error('Error scanning classes:', error);
            setScannedClasses([]);
            setShowClassEditor(false);
        } finally {
            setScanningClasses(false);
        }
    };

    const updateClassIndex = (className, newIndex) => {
        setScannedClasses(prev => prev.map(cls =>
            cls.name === className ? { ...cls, index: parseInt(newIndex) || 0 } : cls
        ));
    };

    const toggleClassEnabled = (className) => {
        setScannedClasses(prev => prev.map(cls =>
            cls.name === className ? { ...cls, enabled: !cls.enabled } : cls
        ));
    };

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
            const requestBody = {
                conversion_type: conversionType,
                annotations_dir: annotationsDir,
                images_dir: imagesDir,
                output_dir: outputDir,
                classes_file: classesFile || undefined,
            };

            // Add custom class mapping for VOC to YOLO conversion
            if (conversionType === 'voc_to_yolo' && scannedClasses.length > 0) {
                const customClassMapping = {};
                // Only include enabled classes
                scannedClasses.filter(cls => cls.enabled).forEach(cls => {
                    customClassMapping[cls.name] = cls.index;
                });
                requestBody.custom_class_mapping = customClassMapping;
            }

            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestBody),
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
            ),
            scanningClasses && e('p',
                { style: { fontSize: '0.9rem', color: 'var(--neon-green)', marginTop: '0.5rem' } },
                '🔍 正在扫描类别...'
            )
        ),

        // Class Editor - Show when classes are scanned
        showClassEditor && scannedClasses.length > 0 && e('div',
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
                `✅ 检测到 ${scannedClasses.length} 个类别 (已选择: ${scannedClasses.filter(c => c.enabled).length})`
            ),
            e('div',
                { style: { fontSize: '0.9rem', marginBottom: 'var(--spacing-sm)', color: 'var(--text-secondary)' } },
                '💡 提示: 勾选要转换的类别，可修改类别索引'
            ),
            e('div',
                { style: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--spacing-sm)' } },
                ...scannedClasses.map(cls =>
                    e('div',
                        {
                            key: cls.name,
                            style: {
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--spacing-sm)',
                                padding: 'var(--spacing-sm)',
                                background: cls.enabled ? 'rgba(67, 233, 123, 0.08)' : 'rgba(255, 255, 255, 0.02)',
                                borderRadius: 'var(--radius-md)',
                                border: cls.enabled ? '1px solid rgba(67, 233, 123, 0.3)' : '1px solid rgba(255, 255, 255, 0.05)',
                                opacity: cls.enabled ? 1 : 0.5,
                                transition: 'all 0.2s ease',
                            }
                        },
                        e('input',
                            {
                                type: 'checkbox',
                                checked: cls.enabled,
                                onChange: () => toggleClassEnabled(cls.name),
                                style: {
                                    width: '18px',
                                    height: '18px',
                                    cursor: 'pointer',
                                    accentColor: 'var(--neon-green)',
                                }
                            }
                        ),
                        e('input',
                            {
                                type: 'number',
                                value: cls.index,
                                onChange: (e) => updateClassIndex(cls.name, e.target.value),
                                disabled: !cls.enabled,
                                style: {
                                    width: '60px',
                                    padding: '0.4rem',
                                    background: cls.enabled ? 'rgba(0, 0, 0, 0.3)' : 'rgba(0, 0, 0, 0.1)',
                                    border: `1px solid ${cls.enabled ? 'var(--neon-green)' : 'rgba(255, 255, 255, 0.1)'}`,
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'var(--text-primary)',
                                    textAlign: 'center',
                                    fontSize: '0.9rem',
                                    cursor: cls.enabled ? 'text' : 'not-allowed',
                                }
                            }
                        ),
                        e('span',
                            {
                                style: {
                                    flex: 1,
                                    fontWeight: '500',
                                    textDecoration: cls.enabled ? 'none' : 'line-through'
                                }
                            },
                            cls.name
                        ),
                        e('span',
                            {
                                style: {
                                    padding: '0.2rem 0.6rem',
                                    background: cls.enabled ? 'var(--gradient-primary)' : 'rgba(128, 128, 128, 0.3)',
                                    borderRadius: 'var(--radius-sm)',
                                    fontSize: '0.8rem',
                                    fontWeight: '600',
                                }
                            },
                            `${cls.count} 样本`
                        )
                    )
                )
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
