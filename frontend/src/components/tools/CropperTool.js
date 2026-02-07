import React, { useState, useEffect, useRef } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import OptionButtons from '../common/OptionButtons.js';
import { getParentDir, joinPaths, normalizePath } from '../../utils/path.js';
import { cropImages } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook, useRef: useRefHook } = React;

export default function CropperTool() {
    const [processingMode, setProcessingMode] = useState('folder');
    const [cropMode, setCropMode] = useState('adaptive'); // 'adaptive' or 'fixed'
    const [inputPath, setInputPath] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [windowWidth, setWindowWidth] = useState(1024);
    const [windowHeight, setWindowHeight] = useState(1024);
    const [overlapX, setOverlapX] = useState(512);
    const [overlapY, setOverlapY] = useState(512);
    const [overlapRatio, setOverlapRatio] = useState(0.3); // For adaptive mode

    // Auto-infer output path
    useEffect(() => {
        if (inputPath && !outputDir) {
            const normalized = normalizePath(inputPath);
            const parentDir = getParentDir(normalized) || normalized;
            setOutputDir(joinPaths(parentDir, 'crops'));
        }
    }, [inputPath]);

    // Auto-infer annotations path if input is folder
    useEffect(() => {
        if (inputPath && !annotationsDir && processingMode === 'folder') {
            // Try to guess annotations dir
            // This is just a guess, user can change it
            // setAnnotationsDir(`${parentDir}/annotations`); 
        }
    }, [inputPath, processingMode]);

    const task = useToolTask({
        toolName: 'cropper',
        startTask: () => cropImages({
            mode: processingMode,
            crop_mode: cropMode,
            input_path: inputPath,
            annotations_dir: annotationsDir || undefined,
            output_dir: outputDir,
            window_width: parseInt(windowWidth, 10),
            window_height: parseInt(windowHeight, 10),
            overlap_x: parseInt(overlapX, 10),
            overlap_y: parseInt(overlapY, 10),
            overlap_ratio: parseFloat(overlapRatio),
        }),
    });

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Processing Mode
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '处理模式'),
            e(OptionButtons, {
                options: [
                    { value: 'folder', label: '📁 文件夹批量' },
                    { value: 'single', label: '📄 单张图片' }
                ],
                value: processingMode,
                onChange: setProcessingMode,
                ariaLabel: '处理模式'
            })
        ),

        // Crop Mode
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '裁剪模式'),
            e(OptionButtons, {
                options: [
                    { value: 'adaptive', label: '🎯 自适应模式（横向长条图像优化）' },
                    { value: 'fixed', label: '📐 固定窗口模式' }
                ],
                value: cropMode,
                onChange: setCropMode,
                ariaLabel: '裁剪模式'
            }),
            cropMode === 'adaptive' && e('div', {
                className: 'info-box',
                style: {
                    marginTop: 'var(--spacing-xs)',
                    fontSize: '0.85rem',
                    color: 'var(--text-tertiary)',
                    background: 'var(--color-success-bg)',
                    borderColor: 'var(--color-success)',
                    padding: 'var(--spacing-sm)',
                    borderWidth: '1px'
                }
            }, '💡 使用图像高度作为正方形裁剪边长，默认重叠度30%，适合横向长条图像')
        ),

        // Input Path
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                processingMode === 'folder' ? '📁 图片文件夹路径' : '📄 图片文件路径',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(必填)')
            ),
            e('input',
                {
                    type: 'text',
                    className: 'input-field',
                    placeholder: processingMode === 'folder' ? '/path/to/images' : '/path/to/image.jpg',
                    value: inputPath,
                    onChange: (e) => setInputPath(e.target.value),
                }
            )
        ),

        // Annotations Directory
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' },
                '📁 标注文件目录',
                e('span', { style: { color: 'var(--text-tertiary)', marginLeft: '0.5rem', fontSize: '0.8rem' } }, '(可选，用于裁剪标注)')
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

        // Adaptive Mode Parameters
        cropMode === 'adaptive' && e('div', { className: 'glass-card', style: { padding: 'var(--spacing-md)' } },
            e('h4', { style: { marginTop: 0, color: 'var(--neon-green)' } }, '🎯 自适应参数'),
            e('div', { className: 'input-group', style: { marginBottom: 0 } },
                e('label', { className: 'input-label' }, '重叠比例'),
                e('div', { style: { display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' } },
                    e('input', {
                        type: 'range',
                        min: 0.1,
                        max: 0.5,
                        step: 0.05,
                        value: overlapRatio,
                        onChange: (ev) => setOverlapRatio(ev.target.value),
                        style: { flex: 1 }
                    }),
                    e('span', { style: { minWidth: '50px', textAlign: 'right', fontWeight: 'bold', color: 'var(--neon-green)' } },
                        `${Math.round(overlapRatio * 100)}%`
                    )
                )
            ),
            e('div', { style: { marginTop: 'var(--spacing-sm)', fontSize: '0.85rem', color: 'var(--text-tertiary)' } },
                '边长 = 图像高度，重叠 = 边长 × 重叠比例'
            )
        ),

        // Fixed Mode Parameters Grid
        cropMode === 'fixed' && e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)' } },
            // Window Size
            e('div', { className: 'glass-card', style: { padding: 'var(--spacing-md)' } },
                e('h4', { style: { marginTop: 0, color: 'var(--neon-blue)' } }, '窗口大小'),
                e('div', { className: 'input-group', style: { marginBottom: 'var(--spacing-sm)' } },
                    e('label', { className: 'input-label' }, '宽度 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: windowWidth,
                        onChange: (ev) => setWindowWidth(ev.target.value)
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '高度 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: windowHeight,
                        onChange: (ev) => setWindowHeight(ev.target.value)
                    })
                )
            ),
            // Overlap
            e('div', { className: 'glass-card', style: { padding: 'var(--spacing-md)' } },
                e('h4', { style: { marginTop: 0, color: 'var(--neon-pink)' } }, '重叠度'),
                e('div', { className: 'input-group', style: { marginBottom: 'var(--spacing-sm)' } },
                    e('label', { className: 'input-label' }, '横向 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: overlapX,
                        onChange: (ev) => setOverlapX(ev.target.value)
                    })
                ),
                e('div', { className: 'input-group', style: { marginBottom: 0 } },
                    e('label', { className: 'input-label' }, '纵向 (px)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: overlapY,
                        onChange: (ev) => setOverlapY(ev.target.value)
                    })
                )
            )
        ),

        // Visual Preview
        cropMode === 'fixed' && e('div', { className: 'glass-card', style: { background: 'rgba(0,0,0,0.2)', padding: 'var(--spacing-sm)' } },
            e('div', { style: { display: 'flex', justifyContent: 'space-around', fontSize: '0.9rem' } },
                e('span', {}, `步长: ${windowWidth - overlapX} × ${windowHeight - overlapY} px`),
                e('span', {}, `有效区域: ${(windowWidth - overlapX) * (windowHeight - overlapY)} px²`)
            )
        ),

        // Task Controller (replaces Progress Bar and Submit Button)
        e(TaskController, {
            ...task.taskControllerProps,
            canStart: !!(inputPath && outputDir)
        }),

        // Result
        task.result && e('div',
            {
                className: `result-box ${task.result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', {}, task.result.success ? '✅ 裁剪完成！' : '❌ 裁剪失败'),
            task.result.success && e('div', {},
                e('div', { style: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-sm)' } },
                    e('div', { style: { color: 'var(--color-info)' } }, `处理文件数: ${task.result.total_files || task.result.total_images || 1}`),
                    e('div', { style: { color: 'var(--color-success)' } }, `生成图片数: ${task.result.total_crops || task.result.crops_generated || 0}`),
                ),
                task.result.output_dir && e('p', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px' } }, `输出目录: ${task.result.output_dir}`)
            ),
            e(ErrorText, { error: task.result.error, errorCode: task.result.error_code })
        )
    );
}
