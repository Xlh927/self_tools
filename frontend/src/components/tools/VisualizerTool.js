import React, { useState, useEffect, useRef } from 'react';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

export default function VisualizerTool() {
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');

    // Customization settings
    const [boxThickness, setBoxThickness] = useState(3);
    const [textSize, setTextSize] = useState(5);
    const [renameMode, setRenameMode] = useState('none'); // none, prefix, suffix
    const [renameContent, setRenameContent] = useState('name'); // name, id

    const [loading, setLoading] = useState(false);
    const [taskId, setTaskId] = useState(null);
    const [progress, setProgress] = useState(0);
    const [statusMessage, setStatusMessage] = useState('');
    const [result, setResult] = useState(null);

    // Auto-infer paths from imagesDir
    useEffect(() => {
        const normalized = normalizePath(imagesDir);
        if (normalized && !annotationsDir && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setAnnotationsDir(joinPaths(parentDir, 'annotations'));
            setOutputDir(joinPaths(parentDir, 'visualized'));
        } else if (normalized && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setOutputDir(joinPaths(parentDir, 'visualized'));
        }
    }, [imagesDir]);

    // Auto-infer paths from annotationsDir
    useEffect(() => {
        const normalized = normalizePath(annotationsDir);
        if (normalized && !imagesDir && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setImagesDir(joinPaths(parentDir, 'images'));
            setOutputDir(joinPaths(parentDir, 'visualized'));
        } else if (normalized && !outputDir) {
            const parentDir = getParentDir(normalized) || normalized;
            setOutputDir(joinPaths(parentDir, 'visualized'));
        }
    }, [annotationsDir]);

    // Polling effect
    useEffect(() => {
        let intervalId;
        if (taskId) {
            intervalId = setInterval(async () => {
                try {
                    const res = await fetch(`/api/progress/${taskId}`);
                    const data = await res.json();

                    if (data.success === false) {
                        // Task not found or error
                        clearInterval(intervalId);
                        setLoading(false);
                        setTaskId(null);
                        setResult({ success: false, error: data.error });
                        return;
                    }

                    setProgress(data.progress || 0);
                    setStatusMessage(data.message || '');

                    if (data.status === 'completed' || data.status === 'error' || data.status === 'cancelled') {
                        clearInterval(intervalId);
                        setLoading(false);
                        setTaskId(null);

                        if (data.status === 'completed') {
                            setResult(data.result);
                        } else if (data.status === 'cancelled') {
                            setResult({ success: false, error: '操作已取消' });
                        } else {
                            setResult({ success: false, error: data.error });
                        }
                    }
                } catch (err) {
                    console.error('Polling error:', err);
                }
            }, 1000);
        }
        return () => {
            if (intervalId) clearInterval(intervalId);
        };
    }, [taskId]);

    const handleVisualize = async () => {
        setLoading(true);
        setResult(null);
        setProgress(0);
        setStatusMessage('正在启动...');

        try {
            const response = await fetch('/api/visualize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    images_dir: imagesDir,
                    annotations_dir: annotationsDir,
                    output_dir: outputDir,
                    box_thickness: boxThickness,
                    text_size: textSize,
                    rename_mode: renameMode,
                    rename_content: renameContent
                }),
            });

            const data = await response.json();

            if (data.success && data.task_id) {
                setTaskId(data.task_id);
                // Loading remains true until polling finishes
            } else {
                setLoading(false);
                setResult(data);
            }
        } catch (error) {
            setLoading(false);
            setResult({ success: false, error: error.message });
        }
    };

    const handleStop = async () => {
        if (!taskId) return;
        try {
            await fetch(`/api/stop-task/${taskId}`, { method: 'POST' });
            setStatusMessage('正在取消...');
        } catch (err) {
            console.error('Stop error:', err);
        }
    };

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

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
                    disabled: loading
                }
            )
        ),

        // Images Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '🖼️ 图片文件目录',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: '/path/to/images',
                    value: imagesDir,
                    onChange: (e) => setImagesDir(e.target.value),
                    disabled: loading
                }
            )
        ),

        // Settings Row
        e('div', { style: { display: 'flex', gap: 'var(--spacing-md)' } },
            // Box Thickness
            e('div', { className: 'input-group', style: { flex: 1 } },
                e('label', { className: 'input-label' }, '📏 边框粗细'),
                e('input', {
                    type: 'number',
                    className: 'input-field',
                    value: boxThickness,
                    min: 1,
                    max: 20,
                    onChange: (e) => setBoxThickness(parseInt(e.target.value) || 1),
                    disabled: loading
                })
            ),
            // Text Size
            e('div', { className: 'input-group', style: { flex: 1 } },
                e('label', { className: 'input-label' }, '🔤 文字大小'),
                e('input', {
                    type: 'number',
                    className: 'input-field',
                    value: textSize,
                    min: 1,
                    max: 20,
                    onChange: (e) => setTextSize(parseInt(e.target.value) || 1),
                    disabled: loading
                })
            )
        ),

        // Rename Settings Row
        e('div', { style: { display: 'flex', gap: 'var(--spacing-md)' } },
            // Rename Mode
            e('div', { className: 'input-group', style: { flex: 1.5 } },
                e('label', { className: 'input-label' }, '🏷️ 重命名模式'),
                e('select', {
                    className: 'input-field',
                    value: renameMode,
                    onChange: (e) => setRenameMode(e.target.value),
                    disabled: loading
                },
                    e('option', { value: 'none' }, '不重命名'),
                    e('option', { value: 'prefix' }, '添加前缀'),
                    e('option', { value: 'suffix' }, '添加后缀')
                )
            ),
            // Rename Content
            e('div', { className: 'input-group', style: { flex: 1 } },
                e('label', { className: 'input-label' }, '📝 重命名内容'),
                e('select', {
                    className: 'input-field',
                    value: renameContent,
                    onChange: (e) => setRenameContent(e.target.value),
                    disabled: loading || renameMode === 'none'
                },
                    e('option', { value: 'name' }, '标签名称'),
                    e('option', { value: 'id' }, '标签索引')
                )
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
                    disabled: loading
                }
            )
        ),

        // Progress Bar (Only when running)
        loading && taskId && e('div', { style: { marginTop: 'var(--spacing-sm)' } },
            e('div', {
                style: {
                    display: 'flex',
                    justifyContent: 'space-between',
                    marginBottom: '5px',
                    fontSize: '0.9rem',
                    color: 'var(--text-secondary)'
                }
            },
                e('span', {}, statusMessage || '处理中...'),
                e('span', {}, `${progress}%`)
            ),
            e('div', { className: 'progress-track' },
                e('div', {
                    className: 'progress-fill',
                    style: { width: `${progress}%` }
                })
            )
        ),

        // Buttons
        e('div', { style: { display: 'flex', gap: '10px' } },
            e('button',
                {
                    className: 'btn btn-primary',
                    onClick: handleVisualize,
                    disabled: loading || !imagesDir || !annotationsDir || !outputDir,
                    style: {
                        fontSize: '1.1rem',
                        padding: 'var(--spacing-md) var(--spacing-xl)',
                        flex: 1,
                    }
                },
                loading ? '处理中...' : '👁️ 开始可视化'
            ),
            loading && e('button',
                {
                    className: 'btn btn-danger',
                    onClick: handleStop,
                    style: {
                        fontSize: '1.1rem',
                        padding: 'var(--spacing-md)',
                        width: 'auto',
                    }
                },
                '停止'
            )
        ),

        // Result
        result && !loading && e('div',
            {
                className: 'glass-card',
                style: {
                    marginTop: 'var(--spacing-lg)',
                    background: result.success ? 'rgba(67, 233, 123, 0.1)' : 'rgba(245, 87, 108, 0.1)',
                    border: `2px solid ${result.success ? 'var(--neon-green)' : 'var(--neon-orange)'}`,
                }
            },
            e('h3', {}, result.success ? '✅ 可视化完成！' : '❌ 可视化失败'),
            result.success && e('div', {},
                e('p', {}, `已处理图像: ${result.processed_count || 0}`),
                result.errors && result.errors.length > 0 && e('div', { style: { marginTop: '10px' } },
                    e('p', { style: { color: 'var(--neon-orange)' } }, `⚠️ 发生 ${result.errors.length} 个错误:`),
                    e('ul', { style: { maxHeight: '100px', overflowY: 'auto', fontSize: '0.85rem' } },
                        result.errors.slice(0, 5).map((err, i) => e('li', { key: i }, err)),
                        result.errors.length > 5 && e('li', {}, '...')
                    )
                )
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
