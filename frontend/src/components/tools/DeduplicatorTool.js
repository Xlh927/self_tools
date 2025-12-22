import React, { useState } from 'react';

const { createElement: e, useState: useStateHook } = React;

export default function DeduplicatorTool() {
    const [folderPath, setFolderPath] = useState('');
    const [hashAlgorithm, setHashAlgorithm] = useState('average');
    const [similarityThreshold, setSimilarityThreshold] = useState(5);
    const [useMd5, setUseMd5] = useState(false);

    const [keepStrategy, setKeepStrategy] = useState('first');
    const [dryRun, setDryRun] = useState(true);

    const [loading, setLoading] = useState(false);
    const [report, setReport] = useState(null);
    const [removeResult, setRemoveResult] = useState(null);

    const handleFindDuplicates = async () => {
        setLoading(true);
        setReport(null);
        setRemoveResult(null);

        try {
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
            if (data.success) {
                setReport(data.report);
            } else {
                setReport({ error: data.error });
            }
        } catch (error) {
            setReport({ error: error.message });
        } finally {
            setLoading(false);
        }
    };

    const handleRemoveDuplicates = async () => {
        if (!confirm('确定要删除重复图片吗？此操作不可撤销！')) return;

        setLoading(true);
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
            setRemoveResult({ success: false, error: error.message });
        } finally {
            setLoading(false);
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

        // Find Button
        e('button',
            {
                className: 'btn btn-primary',
                onClick: handleFindDuplicates,
                disabled: loading || !folderPath,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                }
            },
            loading ? '扫描中...' : '🔍 扫描重复图片'
        ),

        // Report
        report && !report.error && e('div',
            {
                className: 'glass-card',
                style: {
                    marginTop: 'var(--spacing-lg)',
                    border: '2px solid var(--neon-blue)',
                }
            },
            e('h3', {}, '📊 扫描报告'),
            e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-lg)' } },
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '扫描文件: '),
                    e('span', { style: { fontWeight: 'bold' } }, report.total_files)
                ),
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '重复组数: '),
                    e('span', { style: { fontWeight: 'bold', color: 'var(--neon-orange)' } }, report.duplicate_groups)
                ),
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '重复文件: '),
                    e('span', { style: { fontWeight: 'bold', color: 'var(--neon-orange)' } }, report.total_duplicates)
                ),
                e('div', {},
                    e('span', { style: { color: 'var(--text-secondary)' } }, '可节省空间: '),
                    e('span', { style: { fontWeight: 'bold', color: 'var(--neon-green)' } }, report.wasted_size)
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
                        disabled: loading,
                        style: { width: '100%' }
                    },
                    loading ? '处理中...' : (dryRun ? '🧪 测试删除' : '🗑️ 确认删除')
                )
            )
        ),

        // Remove Result
        removeResult && e('div',
            {
                className: 'glass-card',
                style: {
                    marginTop: 'var(--spacing-md)',
                    background: removeResult.success ? 'rgba(67, 233, 123, 0.1)' : 'rgba(245, 87, 108, 0.1)',
                    border: `1px solid ${removeResult.success ? 'var(--neon-green)' : 'var(--neon-orange)'}`,
                }
            },
            e('h4', {}, removeResult.success ? (dryRun ? '✅ 测试完成' : '✅ 删除完成') : '❌ 操作失败'),
            removeResult.success && e('div', {},
                e('p', {}, `已删除: ${removeResult.removed_count} 个文件`),
                e('p', {}, `释放空间: ${removeResult.saved_space}`),
                dryRun && e('p', { style: { color: 'var(--neon-yellow)', fontSize: '0.9rem' } }, '注意：这是测试运行，没有实际删除文件')
            ),
            removeResult.error && e('p', { style: { color: 'var(--neon-orange)' } }, removeResult.error)
        )
    );
}
