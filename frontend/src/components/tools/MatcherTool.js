import React, { useState, useEffect } from 'react';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function MatcherTool() {
    const [sourceDir, setSourceDir] = useState('');
    const [referenceDir, setReferenceDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [dryRun, setDryRun] = useState(false);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    // Auto-infer output path
    useEffect(() => {
        if (sourceDir && !outputDir) {
            const parentDir = sourceDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/matched_images`);
        }
    }, [sourceDir]);

    const handleMatch = async () => {
        setLoading(true);
        setResult(null);

        try {
            const response = await fetch('/api/match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_dir: sourceDir,
                    reference_dir: referenceDir,
                    output_dir: outputDir,
                    dry_run: dryRun,
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

        // Source Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📁 源图片目录 (Source)',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/source_images',
                    value: sourceDir,
                    onChange: (e) => setSourceDir(e.target.value),
                }
            )
        ),

        // Reference Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📁 参考目录 (Reference)',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填，提供文件名的目录)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/reference_files',
                    value: referenceDir,
                    onChange: (e) => setReferenceDir(e.target.value),
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

        // Options
        e('div', { style: { marginBottom: 'var(--spacing-md)' } },
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' } },
                e('input', {
                    type: 'checkbox',
                    checked: dryRun,
                    onChange: (e) => setDryRun(e.target.checked)
                }),
                '空跑测试 (Dry Run) - 仅统计不复制'
            )
        ),

        // Match Button
        e('button',
            {
                className: 'btn btn-primary',
                onClick: handleMatch,
                disabled: loading || !sourceDir || !referenceDir || !outputDir,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                }
            },
            loading ? '匹配中...' : '🔍 开始匹配并复制'
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
            e('h3', {}, result.success ? '✅ 匹配完成！' : '❌ 匹配失败'),
            result.success && e('div', {},
                e('p', {}, `匹配成功: ${result.matched_count} 个文件`),
                e('p', {}, `未找到: ${result.missing_count} 个文件`),
                result.output_dir && e('p', { style: { fontSize: '0.9rem', opacity: 0.8 } }, `输出目录: ${result.output_dir}`),
                dryRun && e('p', { style: { color: 'var(--neon-yellow)', fontSize: '0.9rem' } }, '注意：这是测试运行，没有实际复制文件')
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
