import React, { useState, useRef } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import OptionButtons from '../common/OptionButtons.js';
import { visualizeAnnotations } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';
import useDatasetPathInference from '../../hooks/useDatasetPathInference.js';

const { createElement: e, useState: useStateHook, useRef: useRefHook } = React;

export default function VisualizerTool() {
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');

    // Customization settings
    const [boxThickness, setBoxThickness] = useState(3);
    const [textSize, setTextSize] = useState(5);
    const [renameMode, setRenameMode] = useState('none'); // none, prefix, suffix
    const [renameContent, setRenameContent] = useState('name'); // name, id

    useDatasetPathInference({
        imagesDir,
        setImagesDir,
        annotationsDir,
        setAnnotationsDir,
        outputDir,
        setOutputDir,
        outputFolderName: 'visualized',
    });

    const task = useToolTask({
        toolName: 'visualizer',
        startTask: () => visualizeAnnotations({
            images_dir: imagesDir,
            annotations_dir: annotationsDir,
            output_dir: outputDir,
            box_thickness: parseInt(boxThickness),
            text_size: parseInt(textSize),
            rename_mode: renameMode,
            rename_content: renameContent,
        }),
    });

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
                e(OptionButtons, {
                    options: [
                        { value: 'none', label: '不重命名' },
                        { value: 'prefix', label: '添加前缀' },
                        { value: 'suffix', label: '添加后缀' }
                    ],
                    value: renameMode,
                    onChange: setRenameMode,
                    ariaLabel: '重命名模式'
                })
            ),
            // Rename Content
            e('div', { className: 'input-group', style: { flex: 1 } },
                e('label', { className: 'input-label' }, '📝 重命名内容'),
                e(OptionButtons, {
                    options: [
                        { value: 'name', label: '标签名称' },
                        { value: 'id', label: '标签索引' }
                    ],
                    value: renameContent,
                    onChange: setRenameContent,
                    disabled: renameMode === 'none',
                    ariaLabel: '重命名内容'
                })
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
            ...task.taskControllerProps,
            canStart: !!(imagesDir && annotationsDir && outputDir)
        }),

        // Result
        task.result && e('div',
            {
                className: `result-box ${task.result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', { style: { marginTop: 0 } }, task.result.success ? '✅ 可视化完成！' : '❌ 可视化失败'),
            task.result.success && e('div', {},
                e('p', { style: { fontWeight: 600, color: 'var(--color-success)' } }, `已处理图像: ${task.result.processed_count || 0}`),
                task.result.errors && task.result.errors.length > 0 && e('div', { style: { marginTop: '10px' } },
                    e('p', { style: { color: 'var(--color-warning)', fontWeight: 600 } }, `⚠️ 发生 ${task.result.errors.length} 个错误:`),
                    e('ul', { style: { maxHeight: '120px', overflowY: 'auto', fontSize: '0.85rem', background: 'var(--bg-tertiary)', padding: '8px', borderRadius: '4px', border: '1.5px solid var(--form-border)' } },
                        task.result.errors.slice(0, 10).map((err, i) => e('li', { key: i, style: { marginBottom: '4px' } }, err)),
                        task.result.errors.length > 10 && e('li', { style: { fontStyle: 'italic' } }, `... 还有 ${task.result.errors.length - 10} 个错误`)
                    )
                )
            ),
            e(ErrorText, { error: task.result.error, errorCode: task.result.error_code })
        )
    );
}
