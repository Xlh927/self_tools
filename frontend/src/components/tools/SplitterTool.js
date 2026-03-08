import React, { useState } from 'react';
import TaskController from '../common/TaskController.js';
import ErrorText from '../common/ErrorText.js';
import OptionButtons from '../common/OptionButtons.js';
import { splitDataset } from '../../api/tools.js';
import useToolTask from '../../hooks/useToolTask.js';
import useDatasetPathInference from '../../hooks/useDatasetPathInference.js';

const { createElement: e, useState: useStateHook } = React;

export default function SplitterTool() {
    const [format, setFormat] = useState('voc');
    const [imagesDir, setImagesDir] = useState('');
    const [annotationsDir, setAnnotationsDir] = useState('');
    const [outputDir, setOutputDir] = useState('');
    const [trainRatio, setTrainRatio] = useState(80);
    const [valRatio, setValRatio] = useState(20);
    const [testRatio, setTestRatio] = useState(0);
    const [useBackground, setUseBackground] = useState(true);
    const [randomSeed, setRandomSeed] = useState(42);

    useDatasetPathInference({
        imagesDir,
        setImagesDir,
        annotationsDir,
        setAnnotationsDir,
        outputDir,
        setOutputDir,
        outputFolderName: 'split_dataset',
    });

    // Normalize ratios to sum to 100
    const handleRatioChange = (type, value) => {
        let newVal = parseInt(value);
        if (isNaN(newVal)) newVal = 0;
        if (newVal < 0) newVal = 0;
        if (newVal > 100) newVal = 100;

        if (type === 'train') {
            setTrainRatio(newVal);
            // Adjust val first, then test if needed
            let remaining = 100 - newVal;
            let newValRatio = remaining - testRatio;
            if (newValRatio < 0) {
                setValRatio(0);
                setTestRatio(remaining);
            } else {
                setValRatio(newValRatio);
            }
        } else if (type === 'val') {
            setValRatio(newVal);
            // Adjust train first, then test if needed
            let remaining = 100 - newVal;
            let newTrainRatio = remaining - testRatio;
            if (newTrainRatio < 0) {
                setTrainRatio(0);
                setTestRatio(remaining);
            } else {
                setTrainRatio(newTrainRatio);
            }
        } else if (type === 'test') {
            setTestRatio(newVal);
            // Adjust train first, then val if needed
            let remaining = 100 - newVal;
            let newTrainRatio = remaining - valRatio;
            if (newTrainRatio < 0) {
                setTrainRatio(0);
                setValRatio(remaining);
            } else {
                setTrainRatio(newTrainRatio);
            }
        }
    };

    const totalRatio = trainRatio + valRatio + testRatio;
    const isRatioValid = totalRatio === 100;

    const task = useToolTask({
        toolName: 'splitter',
        startTask: () => splitDataset({
            format: format,
            images_dir: imagesDir,
            annotations_dir: annotationsDir,
            output_dir: outputDir,
            train_ratio: trainRatio,
            val_ratio: valRatio,
            test_ratio: testRatio,
            use_background: useBackground,
            random_seed: parseInt(randomSeed, 10),
        }),
    });

    return e('div',
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' } },

        // Format Selection
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '数据集格式'),
            e(OptionButtons, {
                options: [
                    { value: 'voc', label: 'VOC (XML)' },
                    { value: 'yolo', label: 'YOLO (TXT)' }
                ],
                value: format,
                onChange: setFormat,
                ariaLabel: '数据集格式'
            })
        ),

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

        // Ratios
        e('div', { className: 'result-box info', style: { padding: 'var(--spacing-md)', borderColor: 'var(--accent-purple)' } },
            e('h4', { style: { marginTop: 0, color: 'var(--accent-purple)' } }, '划分比例 (%)'),
            e('div', { style: { display: 'flex', gap: 'var(--spacing-md)', alignItems: 'flex-end' } },
                e('div', { style: { flex: 1 } },
                    e('label', { className: 'input-label', style: { fontSize: '0.8rem' } }, '训练集 (Train)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: trainRatio,
                        onChange: (e) => handleRatioChange('train', e.target.value)
                    })
                ),
                e('div', { style: { flex: 1 } },
                    e('label', { className: 'input-label', style: { fontSize: '0.8rem' } }, '验证集 (Val)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: valRatio,
                        onChange: (e) => handleRatioChange('val', e.target.value)
                    })
                ),
                e('div', { style: { flex: 1 } },
                    e('label', { className: 'input-label', style: { fontSize: '0.8rem' } }, '测试集 (Test)'),
                    e('input', {
                        type: 'number', className: 'input-field', value: testRatio,
                        onChange: (e) => handleRatioChange('test', e.target.value)
                    })
                )
            ),
            !isRatioValid && e('p', { style: { color: 'var(--color-danger)', marginTop: '0.5rem', fontSize: '0.9rem', fontWeight: 600 } },
                `⚠️ 总和必须为 100% (当前: ${totalRatio}%)`
            ),
            // Visual bar
            e('div', { style: { height: '12px', width: '100%', display: 'flex', marginTop: '1rem', borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--form-border)' } },
                e('div', { style: { width: `${trainRatio}%`, background: 'var(--color-info)' } }),
                e('div', { style: { width: `${valRatio}%`, background: 'var(--color-warning)' } }),
                e('div', { style: { width: `${testRatio}%`, background: 'var(--color-danger)' } })
            )
        ),

        // Options
        e('div', { style: { display: 'flex', gap: 'var(--spacing-md)' } },
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' } },
                e('input', {
                    type: 'checkbox',
                    checked: useBackground,
                    onChange: (e) => setUseBackground(e.target.checked)
                }),
                '包含背景图片 (无标注)'
            ),
            e('label', { style: { display: 'flex', alignItems: 'center', gap: '0.5rem' } },
                '随机种子:',
                e('input', {
                    type: 'number',
                    value: randomSeed,
                    onChange: (e) => setRandomSeed(e.target.value),
                    style: { width: '60px', padding: '0.2rem', background: 'var(--bg-tertiary)', border: '1px solid var(--glass-border)', color: 'white' }
                })
            )
        ),

        // Task Controller
        e(TaskController, {
            ...task.taskControllerProps,
            canStart: !!(imagesDir && annotationsDir && outputDir && isRatioValid)
        }),

        // Result
        task.result && e('div',
            {
                className: `result-box ${task.result.success ? 'success' : 'error'} animate-fade-in-up`,
            },
            e('h3', { style: { marginTop: 0 } }, task.result.success ? '✅ 划分完成！' : '❌ 划分失败'),
            task.result.success && e('div', {},
                e('div', { style: { display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-sm)' } },
                    e('div', {}, `训练集: ${task.result.train_count || 0}`),
                    e('div', {}, `验证集: ${task.result.val_count || 0}`),
                    e('div', {}, `测试集: ${task.result.test_count || 0}`),
                ),
                task.result.output_dir && e('p', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', background: 'var(--bg-tertiary)', padding: '4px 8px', borderRadius: '4px', wordBreak: 'break-all' } }, `输出目录: ${task.result.output_dir}`)
            ),
            e(ErrorText, { error: task.result.error, errorCode: task.result.error_code })
        )
    );
}
