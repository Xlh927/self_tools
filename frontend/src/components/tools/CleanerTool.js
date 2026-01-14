import React, { useState, useEffect } from 'react';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function CleanerTool() {
    const [imagesDir, setImagesDir] = useState('');
    const [labelsDir, setLabelsDir] = useState('');
    const [backgroundsDir, setBackgroundsDir] = useState('');
    const [dryRun, setDryRun] = useState(false);

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    // Auto-infer labels and backgrounds paths
    useEffect(() => {
        if (imagesDir) {
            const normalized = normalizePath(imagesDir);
            const parentDir = getParentDir(normalized) || normalized;

            // If imagesDir ends with 'images', try to replace it with 'labels'
            if (normalized.endsWith('/images') || normalized === 'images') {
                const baseDir = normalized.substring(0, normalized.lastIndexOf('/images'));
                if (!labelsDir) setLabelsDir(joinPaths(baseDir, 'labels'));
                if (!backgroundsDir) setBackgroundsDir(joinPaths(baseDir, 'backgrounds'));
            } else {
                if (!labelsDir) setLabelsDir(joinPaths(parentDir, 'labels'));
                if (!backgroundsDir) setBackgroundsDir(joinPaths(parentDir, 'backgrounds'));
            }
        }
    }, [imagesDir]);

    const handleClean = async () => {
        setLoading(true);
        setResult(null);

        try {
            const response = await fetch('/api/clean-dataset', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    images_dir: imagesDir,
                    labels_dir: labelsDir,
                    output_dir: backgroundsDir,
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

        // Images Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🖼️ 图片目录 (Images)',
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

        // Labels Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🏷️ 标签目录 (Labels)',
                e('span', { style: { color: 'var(--neon-green)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(自动推理)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/labels',
                    value: labelsDir,
                    onChange: (e) => setLabelsDir(e.target.value),
                }
            )
        ),

        // Backgrounds Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📂 背景图输出目录 (Backgrounds)',
                e('span', { style: { color: 'var(--neon-green)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(自动推理)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/backgrounds',
                    value: backgroundsDir,
                    onChange: (e) => setBackgroundsDir(e.target.value),
                }
            )
        ),

        // Options
        e('div', { style: { marginBottom: 'var(--spacing-md)', display: 'flex', flexDirection: 'column', gap: '0.5rem' } },
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginTop: '0.5rem' } },
                e('input', {
                    type: 'checkbox',
                    checked: dryRun,
                    onChange: (e) => setDryRun(e.target.checked)
                }),
                '空跑测试 (Dry Run) - 仅统计不移动文件'
            ),
            e('div', {
                style: {
                    fontSize: '0.8rem',
                    color: 'var(--neon-orange)',
                    background: 'rgba(255, 152, 0, 0.1)',
                    padding: '8px',
                    borderRadius: '4px',
                    marginTop: '4px'
                }
            }, '⚠️ 注意：该工具会将无标注的图片从原目录移动到背景图目录。')
        ),

        // Clean Button
        e('button',
            {
                className: 'btn btn-primary',
                onClick: handleClean,
                disabled: loading || !imagesDir || !labelsDir || !backgroundsDir,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                }
            },
            loading ? '任务运行中...' : '🧹 开始清洗数据集'
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
            e('h3', {}, result.success ? '✅ 清洗完成！' : '❌ 清洗失败'),
            result.success && e('div', {},
                e('p', {}, `图片总数: ${result.total_count}`),
                e('p', {}, `有标注图片: ${result.labeled_count}`),
                e('p', {}, `无标注图片: ${result.unlabeled_count}`),
                e('p', { style: { fontWeight: 'bold' } }, `已移动图片: ${result.moved_count}`),
                result.output_dir && e('p', { style: { fontSize: '0.9rem', opacity: 0.8 } }, `输出目录: ${result.output_dir}`),
                dryRun && e('p', { style: { color: 'var(--neon-yellow)', fontSize: '0.9rem' } }, '注意：这是测试运行，没有实际移动文件')
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
