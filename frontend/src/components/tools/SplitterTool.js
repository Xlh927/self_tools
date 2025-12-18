import React, { useState, useEffect } from 'react';

const { createElement: e, useState: useStateHook, useEffect: useEffectHook } = React;

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

    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);

    // Auto-infer paths from imagesDir
    useEffect(() => {
        if (imagesDir && !annotationsDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            setAnnotationsDir(`${parentDir}/annotations`);
            setOutputDir(`${parentDir}/split_dataset`);
        } else if (imagesDir && !outputDir) {
            const parentDir = imagesDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/split_dataset`);
        }
    }, [imagesDir]);

    // Auto-infer paths from annotationsDir
    useEffect(() => {
        if (annotationsDir && !imagesDir && !outputDir) {
            const parentDir = annotationsDir.split('/').slice(0, -1).join('/');
            setImagesDir(`${parentDir}/images`);
            setOutputDir(`${parentDir}/split_dataset`);
        } else if (annotationsDir && !outputDir) {
            const parentDir = annotationsDir.split('/').slice(0, -1).join('/');
            setOutputDir(`${parentDir}/split_dataset`);
        }
    }, [annotationsDir]);

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

    const handleSplit = async () => {
        setLoading(true);
        setResult(null);

        try {
            const response = await fetch('/api/split', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    format: format,
                    images_dir: imagesDir,
                    annotations_dir: annotationsDir,
                    output_dir: outputDir,
                    train_ratio: trainRatio,
                    val_ratio: valRatio,
                    test_ratio: testRatio,
                    use_background: useBackground,
                    random_seed: parseInt(randomSeed),
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

        // Format Selection
        e('div', { className: 'input-group' },
            e('label', { className: 'input-label' }, '数据集格式'),
            e('select',
                {
                    className: 'select-field',
                    value: format,
                    onChange: (e) => setFormat(e.target.value),
                },
                e('option', { value: 'voc' }, 'VOC (XML)'),
                e('option', { value: 'yolo' }, 'YOLO (TXT)')
            )
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
        e('div', { className: 'glass-card', style: { padding: 'var(--spacing-md)' } },
            e('h4', { style: { marginTop: 0, color: 'var(--neon-pink)' } }, '划分比例 (%)'),
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
            !isRatioValid && e('p', { style: { color: 'var(--neon-orange)', marginTop: '0.5rem', fontSize: '0.9rem' } },
                `⚠️ 总和必须为 100% (当前: ${totalRatio}%)`
            ),
            // Visual bar
            e('div', { style: { height: '10px', width: '100%', display: 'flex', marginTop: '1rem', borderRadius: '5px', overflow: 'hidden' } },
                e('div', { style: { width: `${trainRatio}%`, background: 'var(--neon-blue)' } }),
                e('div', { style: { width: `${valRatio}%`, background: 'var(--neon-purple)' } }),
                e('div', { style: { width: `${testRatio}%`, background: 'var(--neon-pink)' } })
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

        // Submit Button
        e('button',
            {
                className: 'btn btn-secondary',
                onClick: handleSplit,
                disabled: loading || !imagesDir || !annotationsDir || !outputDir || !isRatioValid,
                style: {
                    fontSize: '1.1rem',
                    padding: 'var(--spacing-md) var(--spacing-xl)',
                    width: '100%',
                    marginTop: 'var(--spacing-md)',
                }
            },
            loading ? '划分中...' : '📊 开始划分'
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
            e('h3', {}, result.success ? '✅ 划分完成！' : '❌ 划分失败'),
            result.success && e('div', {},
                e('p', {}, `训练集: ${result.train_count || 0}`),
                e('p', {}, `验证集: ${result.val_count || 0}`),
                e('p', {}, `测试集: ${result.test_count || 0}`),
                result.output_dir && e('p', { style: { fontSize: '0.9rem', opacity: 0.8 } }, `输出目录: ${result.output_dir}`)
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        )
    );
}
