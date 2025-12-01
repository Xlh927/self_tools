import React, { useState, useEffect } from 'react';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function LabelModifierTool() {
    const [labelDir, setLabelDir] = useState('');
    const [overwrite, setOverwrite] = useState(true);
    const [outputDir, setOutputDir] = useState('');
    const [loading, setLoading] = useState(false);
    const [scanning, setScanning] = useState(false);
    const [result, setResult] = useState(null);
    const [foundClasses, setFoundClasses] = useState([]);
    const [classMapping, setClassMapping] = useState({});

    // Auto-infer output path
    useEffect(() => {
        if (labelDir && !outputDir && !overwrite) {
            const parentDir = labelDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/labels_modified`);
        }
    }, [labelDir, overwrite]);

    // Auto-scan when directory is entered (debounce or on blur could be better, but button is safer)

    const handleScan = async () => {
        if (!labelDir) return;
        setScanning(true);
        setFoundClasses([]);
        setClassMapping({});
        setResult(null);

        try {
            const response = await fetch('/api/scan-yolo-classes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label_dir: labelDir }),
            });

            const data = await response.json();
            if (data.success) {
                setFoundClasses(data.classes); // Now array of {id, count}
                // Initialize mapping with identity (no change)
                const initialMapping = {};
                data.classes.forEach(cls => {
                    initialMapping[cls.id] = cls.id;
                });
                setClassMapping(initialMapping);
            } else {
                setResult({ success: false, error: data.error });
            }
        } catch (error) {
            setResult({ success: false, error: error.message });
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

    const handleModify = async () => {
        setLoading(true);
        setResult(null);

        try {
            const response = await fetch('/api/modify-labels', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    label_dir: labelDir,
                    class_mapping: classMapping,
                    overwrite: overwrite,
                    output_dir: overwrite ? null : outputDir
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
        foundClasses.length > 0 && e('div', { className: 'glass-card', style: { padding: 'var(--spacing-md)' } },
            e('h3', { style: { marginTop: 0, marginBottom: 'var(--spacing-md)', fontSize: '1rem' } }, '🏷️ 类别映射配置'),
            e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 'var(--spacing-sm)', alignItems: 'center', fontWeight: 'bold', marginBottom: '0.5rem', color: 'var(--text-secondary)' } },
                e('span', {}, '原类别 ID'),
                e('span', {}, '样本数量'),
                e('span', { style: { textAlign: 'center' } }, '➡'),
                e('span', {}, '新类别 ID')
            ),
            e('div', { style: { maxHeight: '300px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' } },
                foundClasses.map(cls =>
                    e('div', { key: cls.id, style: { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 'var(--spacing-sm)', alignItems: 'center' } },
                        e('div', { className: 'input-field', style: { background: 'var(--bg-tertiary)', textAlign: 'center' } }, cls.id),
                        e('div', { style: { textAlign: 'center', color: 'var(--text-secondary)', fontSize: '0.9rem' } }, cls.count),
                        e('div', { style: { textAlign: 'center', color: 'var(--text-tertiary)' } }, '➡'),
                        e('input', {
                            type: 'number',
                            className: 'input-field',
                            value: classMapping[cls.id],
                            onChange: (e) => handleMappingChange(cls.id, e.target.value),
                            style: { textAlign: 'center', borderColor: classMapping[cls.id] !== cls.id ? 'var(--neon-blue)' : '' }
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

        // Modify Button
        e('button',
            {
                className: 'btn btn-primary',
                onClick: handleModify,
                disabled: loading || !labelDir || (!overwrite && !outputDir) || foundClasses.length === 0,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                    marginTop: 'var(--spacing-sm)'
                }
            },
            loading ? '处理中...' : '🚀 开始修改'
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
            e('h3', {}, result.success ? '✅ 修改完成！' : '❌ 修改失败'),
            result.success && e('div', {},
                e('p', {}, `已处理: ${result.processed} 个文件`),
                e('p', {}, `已修改: ${result.modified} 个文件`),
                result.errors > 0 && e('p', { style: { color: 'var(--neon-orange)' } }, `错误: ${result.errors} 个文件`)
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
