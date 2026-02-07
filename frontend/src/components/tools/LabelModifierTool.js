import React, { useState, useEffect } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';
import { normalizeError } from '../../utils/error.js';
import { modifyLabels, scanYoloClasses } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function LabelModifierTool() {
    const [labelDir, setLabelDir] = useState('');
    const [overwrite, setOverwrite] = useState(true);
    const [outputDir, setOutputDir] = useState('');
    const [scanning, setScanning] = useState(false);

    const [foundClasses, setFoundClasses] = useState([]);
    const [classMapping, setClassMapping] = useState({});

    // Auto-infer output path
    useEffect(() => {
        if (labelDir && !outputDir && !overwrite) {
            const normalized = normalizePath(labelDir);
            const parentDir = getParentDir(normalized);
            setOutputDir(parentDir ? joinPaths(parentDir, 'labels_modified') : 'labels_modified');
        }
    }, [labelDir, overwrite]);

    const task = useToolTask({
        toolName: 'label_modifier',
        startTask: () => modifyLabels({
            label_dir: labelDir,
            class_mapping: classMapping,
            overwrite: overwrite,
            output_dir: overwrite ? null : outputDir,
        }),
    });

    // Auto-scan when directory is entered (debounce or on blur could be better, but button is safer)
    const handleScan = async () => {
        if (!labelDir) return;
        setScanning(true);
        setFoundClasses([]);
        setClassMapping({});
        task.setResult(null);

        try {
            const data = await scanYoloClasses({ label_dir: labelDir });
            if (data.success) {
                setFoundClasses(data.classes); // Now array of {id, count}
                // Initialize mapping with identity (no change)
                const initialMapping = {};
                data.classes.forEach(cls => {
                    initialMapping[cls.id] = cls.id;
                });
                setClassMapping(initialMapping);
            } else {
                const normalized = normalizeError(data);
                task.setResult({ success: false, ...normalized });
            }
        } catch (error) {
            const normalized = normalizeError(error);
            task.setResult({ success: false, ...normalized });
        } finally {
            setScanning(false);
        }
    };

    const handleMappingChange = (oldClass, newClass) => {
        setClassMapping(prev => ({
            ...prev,
            [oldClass]: parseInt(newClass) || 0
        }));
    };

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Label Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📁 YOLO 标签目录',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('div', { style: { display: 'flex', gap: '0.5rem' } },
                e('input',
                    {
                        type: 'text',
                        className: 'input-field',
                        placeholder: '/path/to/labels',
                        value: labelDir,
                        onChange: (e) => setLabelDir(e.target.value),
                        style: { flex: 1 }
                    }
                ),
                e('button',
                    {
                        className: 'btn btn-secondary',
                        onClick: handleScan,
                        disabled: scanning || !labelDir,
                        style: { whiteSpace: 'nowrap' }
                    },
                    scanning ? '扫描中...' : '🔍 扫描类别'
                )
            )
        ),

        // Class Mapping Table
        foundClasses.length > 0 && e('div', { className: 'result-box info', style: { padding: 'var(--spacing-md)', borderColor: 'var(--color-info)' } },
            e('h3', { style: { marginTop: 0, marginBottom: 'var(--spacing-md)', fontSize: '1rem', color: 'var(--color-info)' } }, '🏷️ 类别映射配置'),
            e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 'var(--spacing-sm)', alignItems: 'center', fontWeight: 'bold', marginBottom: '0.5rem', color: 'var(--text-secondary)', textAlign: 'center' } },
                e('span', {}, '原 ID'),
                e('span', {}, '样本数'),
                e('span', {}, ''),
                e('span', {}, '新 ID')
            ),
            e('div', { style: { maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem', paddingRight: '4px' } },
                foundClasses.map(cls =>
                    e('div', { key: cls.id, style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 'var(--spacing-sm)', alignItems: 'center' } },
                        e('div', { className: 'input-field', style: { background: 'var(--bg-tertiary)', textAlign: 'center', height: '40px', display: 'flex', alignItems: 'center', justifyContent: 'center' } }, cls.id),
                        e('div', { style: { textAlign: 'center', fontWeight: 600, color: 'var(--text-secondary)' } }, cls.count),
                        e('div', { style: { textAlign: 'center', color: 'var(--text-tertiary)', fontSize: '1.2rem' } }, '➡'),
                        e('input', {
                            type: 'number',
                            className: 'input-field',
                            value: classMapping[cls.id],
                            onChange: (e) => handleMappingChange(cls.id, e.target.value),
                            style: { textAlign: 'center', height: '40px', borderColor: classMapping[cls.id] !== cls.id ? 'var(--primary-blue)' : '' }
                        })
                    )
                )
            )
        ),

        // Overwrite Option
        e('div', { className: 'input-group', style: { flexDirection: 'row', alignItems: 'center', gap: '0.5rem' } },
            e('input',
                {
                    type: 'checkbox',
                    id: 'overwrite-checkbox',
                    checked: overwrite,
                    onChange: (e) => setOverwrite(e.target.checked),
                    style: { width: 'auto' }
                }
            ),
            e('label', { htmlFor: 'overwrite-checkbox', style: { cursor: 'pointer', userSelect: 'none' } }, '覆盖原文件')
        ),

        // Output Directory (only if not overwriting)
        !overwrite && e('div', { className: 'input-group' },
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

        // Task Controller
        e(TaskController, {
            ...task.taskControllerProps,
            canStart: !!(labelDir && foundClasses.length > 0 && (overwrite || outputDir))
        }),

        // Result
        task.result && e('div',
            {
                className: `result-box ${task.result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', { style: { marginTop: 0 } }, task.result.success ? '✅ 修改完成！' : '❌ 修改失败'),
            task.result.success && e('div', {},
                e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-sm)' } },
                    e('div', { style: { color: 'var(--color-info)' } }, `已处理: ${task.result.processed}`),
                    e('div', { style: { color: 'var(--color-success)' } }, `已修改: ${task.result.modified}`),
                ),
                task.result.errors > 0 && e('p', { style: { color: 'var(--color-danger)', fontWeight: 600 } }, `⚠️ 错误: ${task.result.errors} 个文件`)
            ),
            e(ErrorText, { error: task.result.error, errorCode: task.result.error_code })
        )
    );
}
