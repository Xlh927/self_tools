import React, { useState, useEffect, useRef } from 'react';
import TaskController from '../common/TaskController.js';
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

    // Result state
    const [result, setResult] = useState(null);
    const [taskId, setTaskId] = useState(null);

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

    const handleStartTask = async () => {
        setResult(null);

        const response = await fetch('/api/visualize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                images_dir: imagesDir,
                annotations_dir: annotationsDir,
                output_dir: outputDir,
                box_thickness: parseInt(boxThickness),
                text_size: parseInt(textSize),
                rename_mode: renameMode,
                rename_content: renameContent
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
                    disabled: renameMode === 'none'
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
                }
            )
        ),

        // Task Controller
        e(TaskController, {
            taskId: taskId,
            onStart: handleStartTask,
            onComplete: handleComplete,
            onError: handleError,
            onStop: handleStop,
            canStart: !!(imagesDir && annotationsDir && outputDir)
        }),

        // Result
        result && e('div',
            {
                className: `result-box ${result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', { style: { marginTop: 0 } }, result.success ? '✅ 可视化完成！' : '❌ 可视化失败'),
            result.success && e('div', {},
                e('p', { style: { fontWeight: 600, color: 'var(--color-success)' } }, `已处理图像: ${result.processed_count || 0}`),
                result.errors && result.errors.length > 0 && e('div', { style: { marginTop: '10px' } },
                    e('p', { style: { color: 'var(--color-warning)', fontWeight: 600 } }, `⚠️ 发生 ${result.errors.length} 个错误:`),
                    e('ul', { style: { maxHeight: '120px', overflowY: 'auto', fontSize: '0.85rem', background: 'var(--bg-tertiary)', padding: '8px', borderRadius: '4px', border: '1.5px solid var(--form-border)' } },
                        result.errors.slice(0, 10).map((err, i) => e('li', { key: i, style: { marginBottom: '4px' } }, err)),
                        result.errors.length > 10 && e('li', { style: { fontStyle: 'italic' } }, `... 还有 ${result.errors.length - 10} 个错误`)
                    )
                )
            ),
            result.error && e('p', { style: { color: 'var(--color-danger)', fontWeight: 600 } }, result.error)
        )
    );
}
