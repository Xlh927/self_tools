import React, { useState, useEffect, useRef } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import OptionButtons from '../common/OptionButtons.js';
import { convertDataset, scanVocClasses as scanVocClassesApi } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';
import useDatasetPathInference from '../../hooks/useDatasetPathInference.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

export default function ConverterTool() {
    const [conversionType, setConversionType] = useState('voc_to_yolo');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [imagesDir, setImagesDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [classesFile, setClassesFile] = useState('');

    // New state for class scanning
    const [scannedClasses, setScannedClasses] = useState([]);
    const [scanningClasses, setScanningClasses] = useState(false);
    const [showClassEditor, setShowClassEditor] = useState(false);
    const [classFilter, setClassFilter] = useState({
        view: '',
        part: '',
        fault: '',
        targetIndex: 0,
    });
    const defaultOutputFolder = conversionType === 'voc_to_yolo' ? 'labels' : 'xml';

    const parseKeywords = (value) => value
        .split(/[\s,，;；、]+/)
        .map(keyword => keyword.trim().toLowerCase())
        .filter(Boolean);

    const getMatchedClasses = () => {
        const groups = [
            parseKeywords(classFilter.view),
            parseKeywords(classFilter.part),
            parseKeywords(classFilter.fault),
        ].filter(group => group.length > 0);

        if (groups.length === 0) {
            return [];
        }

        return scannedClasses.filter(cls => {
            const name = cls.name.toLowerCase();
            return groups.every(group => group.some(keyword => name.includes(keyword)));
        });
    };

    const matchedClasses = getMatchedClasses();
    const matchedClassNames = new Set(matchedClasses.map(cls => cls.name));
    const hasActiveFilter = [
        classFilter.view,
        classFilter.part,
        classFilter.fault,
    ].some(value => value.trim());

    useDatasetPathInference({
        imagesDir,
        setImagesDir,
        annotationsDir,
        setAnnotationsDir,
        outputDir,
        setOutputDir,
        outputFolderName: defaultOutputFolder,
    });

    // Auto-scan VOC classes when annotationsDir changes for voc_to_yolo
    useEffect(() => {
        if (conversionType === 'voc_to_yolo' && annotationsDir && annotationsDir.trim() !== '') {
            scanVocClasses();
        } else {
            setScannedClasses([]);
            setShowClassEditor(false);
        }
    }, [annotationsDir, conversionType]);

    const scanVocClasses = async () => {
        setScanningClasses(true);
        try {
            const data = await scanVocClassesApi({ annotations_dir: annotationsDir });

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

    const updateClassFilter = (field, value) => {
        setClassFilter(prev => ({ ...prev, [field]: value }));
    };

    const applyFilterToClasses = ({ keepOnlyMatched = false } = {}) => {
        const targetIndex = parseInt(classFilter.targetIndex, 10) || 0;
        const names = new Set(matchedClasses.map(cls => cls.name));

        setScannedClasses(prev => prev.map(cls => {
            if (names.has(cls.name)) {
                return { ...cls, enabled: true, index: targetIndex };
            }
            if (keepOnlyMatched) {
                return { ...cls, enabled: false };
            }
            return cls;
        }));
    };

    const clearClassFilter = () => {
        setClassFilter(prev => ({
            ...prev,
            view: '',
            part: '',
            fault: '',
        }));
    };

    const task = useToolTask({
        toolName: 'converter',
        startTask: () => {
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

        return convertDataset(requestBody);
        },
    });

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Conversion Type
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '转换方向'),
            e(OptionButtons, {
                options: [
                    { value: 'voc_to_yolo', label: 'VOC → YOLO' },
                    { value: 'yolo_to_voc', label: 'YOLO → VOC' }
                ],
                value: conversionType,
                onChange: setConversionType,
                ariaLabel: '转换方向'
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
                className: 'result-box success',
                style: {
                    margin: 'var(--spacing-md) 0',
                    borderWidth: '2px'
                }
            },
            e('h3',
                { style: { color: 'var(--color-success)' } },
                `✅ 检测到 ${scannedClasses.length} 个类别 (已选择: ${scannedClasses.filter(c => c.enabled).length})`
            ),
            e('div',
                { style: { fontSize: '0.9rem', marginBottom: 'var(--spacing-sm)', color: 'var(--text-secondary)' } },
                '💡 提示: 勾选要转换的类别，可修改类别索引'
            ),
            e('div',
                {
                    style: {
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
                        gap: 'var(--spacing-sm)',
                        padding: 'var(--spacing-sm)',
                        marginBottom: 'var(--spacing-sm)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid rgba(24, 144, 255, 0.22)',
                        background: 'var(--color-info-bg)',
                    }
                },
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '视角关键词'),
                    e('input', {
                        type: 'text',
                        className: 'input-field',
                        placeholder: 'zxj, cebu, dibu',
                        value: classFilter.view,
                        onChange: (event) => updateClassFilter('view', event.target.value),
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '部件关键词'),
                    e('input', {
                        type: 'text',
                        className: 'input-field',
                        placeholder: 'luoshuan',
                        value: classFilter.part,
                        onChange: (event) => updateClassFilter('part', event.target.value),
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '故障型态关键词'),
                    e('input', {
                        type: 'text',
                        className: 'input-field',
                        placeholder: 'songtuo, diushi, yiwu',
                        value: classFilter.fault,
                        onChange: (event) => updateClassFilter('fault', event.target.value),
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '目标类别 ID'),
                    e('input', {
                        type: 'number',
                        min: 0,
                        className: 'input-field',
                        value: classFilter.targetIndex,
                        onChange: (event) => updateClassFilter('targetIndex', event.target.value),
                    })
                ),
                e('div',
                    {
                        style: {
                            display: 'flex',
                            flexWrap: 'wrap',
                            alignItems: 'end',
                            gap: 'var(--spacing-sm)',
                            gridColumn: '1 / -1',
                        }
                    },
                    e('button', {
                        type: 'button',
                        className: 'btn btn-primary',
                        disabled: !hasActiveFilter || matchedClasses.length === 0,
                        onClick: () => applyFilterToClasses(),
                    }, `应用到匹配类别 (${matchedClasses.length})`),
                    e('button', {
                        type: 'button',
                        className: 'btn btn-secondary',
                        disabled: !hasActiveFilter || matchedClasses.length === 0,
                        onClick: () => applyFilterToClasses({ keepOnlyMatched: true }),
                    }, '仅保留匹配类别'),
                    e('button', {
                        type: 'button',
                        className: 'btn btn-ghost',
                        disabled: !hasActiveFilter,
                        onClick: clearClassFilter,
                    }, '清空筛选'),
                    e('span',
                        {
                            style: {
                                color: 'var(--text-secondary)',
                                fontSize: '0.85rem',
                                fontWeight: 600,
                            }
                        },
                        hasActiveFilter
                            ? `当前命中 ${matchedClasses.length} / ${scannedClasses.length} 个类别`
                            : '输入任意关键词后可批量指定类别 ID'
                    )
                )
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
                                border: matchedClassNames.has(cls.name)
                                    ? '2px solid var(--color-info)'
                                    : (cls.enabled ? '1px solid rgba(67, 233, 123, 0.3)' : '1px solid rgba(255, 255, 255, 0.05)'),
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
                                className: 'input-field',
                                value: cls.index,
                                onChange: (e) => updateClassIndex(cls.name, e.target.value),
                                disabled: !cls.enabled,
                                style: {
                                    width: '70px',
                                    padding: '0.4rem',
                                    textAlign: 'center',
                                    borderColor: cls.enabled ? 'var(--color-success)' : 'var(--glass-border)',
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
                    conversionType === 'yolo_to_voc' ? '(可选，留空使用索引)' : '(可选，自动生成)'
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

        // Task Controller
        e(TaskController, {
            ...task.taskControllerProps,
            canStart: !!(annotationsDir && imagesDir && outputDir)
        }),

        // Result
        task.result && e('div',
            {
                className: `result-box ${task.result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', {}, task.result.success ? '✅ 转换成功！' : '❌ 转换失败'),
            task.result.success && e('div', {},
                e('p', { style: { fontWeight: 600 } }, `统计信息:`),
                e('div', { style: { display: 'flex', gap: 'var(--spacing-lg)', marginBottom: 'var(--spacing-md)' } },
                    e('div', { style: { color: 'var(--color-success)' } }, `已转换: ${task.result.converted}`),
                    task.result.skipped > 0 && e('div', { style: { color: 'var(--color-warning)' } }, `跳过: ${task.result.skipped}`),
                ),
                task.result.classes && e('div', {},
                    e('p', { style: { fontSize: '0.85rem', marginBottom: '0.4rem' } }, '检测到的类别:'),
                    e('div',
                        { style: { display: 'flex', flexWrap: 'wrap', gap: 'var(--spacing-xs)' } },
                        ...task.result.classes.map(cls =>
                            e('span',
                                {
                                    key: cls,
                                    style: {
                                        background: 'var(--gradient-primary)',
                                        color: 'white',
                                        padding: '0.15rem 0.6rem',
                                        borderRadius: 'var(--radius-sm)',
                                        fontSize: '0.8rem',
                                        fontWeight: 600
                                    }
                                },
                                cls
                            )
                        )
                    )
                )
            ),
            e(ErrorText, { error: task.result.error, errorCode: task.result.error_code })
        )
    );
}
