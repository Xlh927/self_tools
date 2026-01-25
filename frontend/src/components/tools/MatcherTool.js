import React, { useState, useEffect } from 'react';
import TaskController from '../common/TaskController.js';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

export default function MatcherTool() {
    const [sourceDir, setSourceDir] = useState('');
    const [referenceDir, setReferenceDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [copyIntersection, setCopyIntersection] = useState(true);
    const [copyDifference, setCopyDifference] = useState(false);
    const [dryRun, setDryRun] = useState(false);

    // Result state
    const [result, setResult] = useState(null);
    const [taskId, setTaskId] = useState(null);

    // Auto-infer output path
    useEffect(() => {
        if (sourceDir && !outputDir) {
            const normalized = normalizePath(sourceDir);
            const parentDir = getParentDir(normalized) || normalized;
            setOutputDir(joinPaths(parentDir, 'matched_images'));
        }
    }, [sourceDir]);

    const handleStartTask = async () => {
        setResult(null);

        const response = await fetch('/api/match', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_dir: sourceDir,
                reference_dir: referenceDir,
                output_dir: outputDir,
                copy_intersection: copyIntersection,
                copy_difference: copyDifference,
                dry_run: dryRun,
            }),
        });

        const data = await response.json();
        return data;
    };

    const handleComplete = (res) => {
        setResult(res);
        setTaskId(null);
    };

    const handleError = (err) => {
        setResult({ success: false, error: err });
        setTaskId(null);
    };

    const handleStop = () => {
        setTaskId(null);
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
        e('div', { style: { marginBottom: 'var(--spacing-md)', display: 'flex', flexDirection: 'column', gap: '0.5rem' } },
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' } },
                e('input', {
                    type: 'checkbox',
                    checked: copyIntersection,
                    onChange: (e) => setCopyIntersection(e.target.checked)
                }),
                '复制交集 (Intersection) - 两个文件夹都有的图片'
            ),
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' } },
                e('input', {
                    type: 'checkbox',
                    checked: copyDifference,
                    onChange: (e) => setCopyDifference(e.target.checked)
                }),
                '复制差集 (Difference) - 仅在源文件夹有的图片'
            ),
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer', marginTop: '0.5rem' } },
                e('input', {
                    type: 'checkbox',
                    checked: dryRun,
                    onChange: (e) => setDryRun(e.target.checked)
                }),
                '空跑测试 (Dry Run) - 仅统计不复制'
            )
        ),

        // Task Controller
        e(TaskController, {
            taskId: taskId,
            onStart: handleStartTask,
            onComplete: handleComplete,
            onError: handleError,
            onStop: handleStop,
            canStart: !!(sourceDir && referenceDir && outputDir)
        }),

        // Result
        result && e('div',
            {
                className: `result-box ${result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', { style: { marginTop: 0 } }, result.success ? '✅ 匹配完成！' : '❌ 匹配失败'),
            result.success && e('div', {},
                e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-sm)' } },
                    e('div', {}, `扫描总数: ${result.total_scanned}`),
                    e('div', { style: { color: 'var(--color-info)', fontWeight: 600 } }, `交集匹配: ${result.matched_count}`),
                    e('div', { style: { color: 'var(--color-warning)', fontWeight: 600 } }, `差集数量: ${result.unmatched_count}`),
                ),
                result.output_dir && e('p', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px' } }, `输出目录: ${result.output_dir}`),
                dryRun && e('p', { style: { color: 'var(--color-warning)', fontSize: '0.9rem', fontWeight: 600, marginTop: '8px' } }, '💡 这是测试运行，没有实际复制文件')
            ),
            result.error && e('p', { style: { color: 'var(--color-danger)', fontWeight: 600 } }, result.error)
        )
    );
}
