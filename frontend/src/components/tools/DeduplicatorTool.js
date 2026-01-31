import React, { useState, useEffect, useRef } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import { basename } from '../../utils/path.js';
import { normalizeError } from '../../utils/error.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

export default function DeduplicatorTool() {
    const [folderPath, setFolderPath] = useState('');
    const [hashAlgorithm, setHashAlgorithm] = useState('average');
    const [similarityThreshold, setSimilarityThreshold] = useState(5);
    const [useMd5, setUseMd5] = useState(false);

    const [keepStrategy, setKeepStrategy] = useState('first');
    const [dryRun, setDryRun] = useState(true);

    // Result state
    const [taskId, setTaskId] = useState(null);
    const [report, setReport] = useState(null);
    const [removeResult, setRemoveResult] = useState(null);
    const [removing, setRemoving] = useState(false);

    const handleStartTask = async () => {
        setReport(null);
        setRemoveResult(null);

        const response = await fetch('/api/find-duplicates', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                folder_path: folderPath,
                hash_algorithm: hashAlgorithm,
                use_md5: useMd5,
                similarity_threshold: parseInt(similarityThreshold),
            }),
        });

        const data = await response.json();
        return data;
    };

    const handleComplete = (res) => {
        if (res && res.report) {
            setReport(res.report);
        }
        setTaskId(null);
    };

    const handleError = (err) => {
        const normalized = normalizeError(err);
        setReport({ ...normalized });
        setTaskId(null);
    };

    const handleStop = () => {
        setTaskId(null);
    };

    const handleRemoveDuplicates = async () => {
        if (!confirm('确定要删除重复图片吗？此操作不可撤销！')) return;

        setRemoving(true);
        setRemoveResult(null);

        // Construct duplicates map from report to avoid re-scanning
        let duplicates = null;
        if (report && report.groups) {
            duplicates = {};
            report.groups.forEach(group => {
                duplicates[group.id] = group.files.map(f => f.path);
            });
        }

        try {
            const response = await fetch('/api/remove-duplicates', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    folder_path: folderPath,
                    hash_algorithm: hashAlgorithm,
                    use_md5: useMd5,
                    similarity_threshold: parseInt(similarityThreshold),
                    keep_strategy: keepStrategy,
                    dry_run: dryRun,
                    duplicates: duplicates,
                }),
            });

            const data = await response.json();
            setRemoveResult(data);

            // Clear report if actual deletion occurred (no need to re-scan)
            if (!dryRun && data.success) {
                setReport(null);
            }
        } catch (error) {
            const normalized = normalizeError(error);
            setRemoveResult({ success: false, ...normalized });
        } finally {
            setRemoving(false);
        }
    };

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Folder Path
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📁 图片文件夹路径',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/images',
                    value: folderPath,
                    onChange: (e) => setFolderPath(e.target.value),
                }
            )
        ),

        // Algorithm Settings
        e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' } },
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, '哈希算法'),
                e('select',
                    {
                        className: 'select-field',
                        value: hashAlgorithm,
                        onChange: (e) => setHashAlgorithm(e.target.value),
                    },
                    e('option', { value: 'average' }, 'Average Hash (快速)'),
                    e('option', { value: 'perceptual' }, 'Perceptual Hash (准确)'),
                    e('option', { value: 'difference' }, 'Difference Hash'),
                    e('option', { value: 'wavelet' }, 'Wavelet Hash')
                )
            ),
            e('div', { className: 'input-group' },
                e('label', { className: 'input-label' }, '相似度阈值 (0-10)'),
                e('input', {
                    type: 'number',
                    className: 'input-field',
                    value: similarityThreshold,
                    min: 0,
                    max: 20,
                    onChange: (e) => setSimilarityThreshold(e.target.value),
                })
            )
        ),

        // Options
        e('div', { style: { marginBottom: 'var(--spacing-md)' } },
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' } },
                e('input', {
                    type: 'checkbox',
                    checked: useMd5,
                    onChange: (e) => setUseMd5(e.target.checked)
                }),
                '使用 MD5 精确匹配 (仅检测完全相同的文件)'
            )
        ),

        // Task Controller
        e(TaskController, {
            taskId: taskId,
            onStart: handleStartTask,
            onComplete: handleComplete,
            onError: handleError,
            onStop: handleStop,
            canStart: !!folderPath
        }),

        // Report
        report && report.error && e('div',
            {
                className: 'result-box error animate-fade-in-up',
            },
            e('h3', {}, '❌ 扫描失败'),
            e(ErrorText, { error: report.error, errorCode: report.error_code })
        ),

        report && !report.error && e('div',
            {
                className: 'result-box info animate-fade-in-up',
                style: {
                    borderColor: 'var(--color-info)',
                    borderWidth: '2px'
                }
            },
            e('h3', { style: { color: 'var(--color-info)' } }, '📊 扫描报告'),
            e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' } },
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '扫描文件: '),
                    e('span', { style: { fontWeight: 'bold' } }, report.total_files)
                ),
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '重复组数: '),
                    e('span', { style: { fontWeight: 'bold', color: 'var(--color-danger)' } }, report.duplicate_groups)
                ),
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '重复文件: '),
                    e('span', { style: { fontWeight: 'bold', color: 'var(--color-danger)' } }, report.total_duplicates)
                ),
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '节省空间: '),
                    e('span', { style: { fontWeight: 'bold', color: 'var(--color-success)' } }, report.wasted_size)
                )
            ),

            // Duplicate Groups List
            report.groups && report.groups.length > 0 && e('div',
                {
                    style: {
                        marginBottom: 'var(--spacing-lg)',
                        maxHeight: '300px',
                        overflowY: 'auto',
                        padding: 'var(--spacing-sm)',
                        background: 'rgba(0, 0, 0, 0.2)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--glass-border)',
                    }
                },
                e('h4', { style: { marginTop: 0, marginBottom: 'var(--spacing-sm)', fontSize: '0.9rem', color: 'var(--text-secondary)' } }, '📄 重复文件列表'),
                report.groups.map((group, gIdx) =>
                    e('div', { key: group.id || gIdx, style: { marginBottom: 'var(--spacing-md)', padding: 'var(--spacing-sm)', background: 'var(--bg-secondary)', borderRadius: 'var(--radius-sm)', border: '1.5px solid var(--glass-border)' } },
                        e('div', { style: { fontSize: '0.8rem', fontWeight: 'bold', marginBottom: '4px', color: 'var(--color-info)' } }, `组 ${gIdx + 1} (${group.count} 文件)`),
                        e('div', { style: { display: 'flex', flexDirection: 'column', gap: '2px' } },
                            group.files.map((file, fIdx) =>
                                e('div', { key: fIdx, style: { display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', opacity: 0.8 } },
                                    e('span', { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: '10px' }, title: file.path }, basename(file.path)),
                                    e('span', { style: { color: 'var(--text-tertiary)', flexShrink: 0 } }, file.size_mb + ' MB')
                                )
                            )
                        )
                    )
                )
            ),

            // Removal Options (only if duplicates found)
            report.duplicate_groups > 0 && e('div',
                {
                    style: {
                        padding: 'var(--spacing-md)',
                        background: 'rgba(255, 255, 255, 0.05)',
                        borderRadius: 'var(--radius-md)',
                    }
                },
                e('h4', { style: { marginTop: 0 } }, '🗑️ 删除选项'),
                e('div', { style: { display: 'flex', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-md)' } },
                    e('div', { style: { flex: 1 } },
                        e('label', { className: 'input-label', style: { fontSize: '0.8rem' } }, '保留策略'),
                        e('select',
                            {
                                className: 'select-field',
                                value: keepStrategy,
                                onChange: (e) => setKeepStrategy(e.target.value),
                            },
                            e('option', { value: 'first' }, '保留第一个 (First)'),
                            e('option', { value: 'last' }, '保留最后一个 (Last)'),
                            e('option', { value: 'smallest' }, '保留最小文件 (Smallest)'),
                            e('option', { value: 'largest' }, '保留最大文件 (Largest)')
                        )
                    ),
                    e('div', { style: { flex: 1, display: 'flex', alignItems: 'flex-end', paddingBottom: '10px' } },
                        e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' } },
                            e('input', {
                                type: 'checkbox',
                                checked: dryRun,
                                onChange: (e) => setDryRun(e.target.checked)
                            }),
                            '空跑测试 (Dry Run)'
                        )
                    )
                ),
                e('button',
                    {
                        className: 'btn btn-secondary',
                        onClick: handleRemoveDuplicates,
                        disabled: removing,
                        style: { width: '100%', borderColor: dryRun ? 'var(--color-info)' : 'var(--color-danger)' }
                    },
                    removing ? '处理中...' : (dryRun ? '🧪 测试删除' : '🗑️ 确认物理删除')
                )
            )
        ),

        // Remove Result
        removeResult && e('div',
            {
                className: `result-box ${removeResult.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', {}, removeResult.success ? (dryRun ? '✅ 测试完成' : '✅ 处理完成') : '❌ 操作失败'),
            removeResult.success && e('div', {},
                e('div', { style: { display: 'flex', gap: '20px' } },
                    e('div', {}, `已处理: ${removeResult.removed_count} 个文件`),
                    e('div', { style: { color: 'var(--color-success)', fontWeight: 700 } }, `释放空间: ${removeResult.saved_space}`),
                ),
                dryRun && e('p', { style: { color: 'var(--color-warning)', fontSize: '0.9rem', fontWeight: 600, marginTop: '8px' } }, '💡 这是测试运行，没有实际物理删除')
            ),
            e(ErrorText, { error: removeResult.error, errorCode: removeResult.error_code })
        )
    );
}
