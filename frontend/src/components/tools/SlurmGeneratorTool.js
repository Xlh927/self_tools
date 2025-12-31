import React, { useState, useEffect } from 'react';

const { createElement: e } = React;

export default function SlurmGeneratorTool() {
    const [task, setTask] = useState('detect');
    const [data, setData] = useState('');
    const [model, setModel] = useState('yolo11m.pt');
    const [epochs, setEpochs] = useState(150);
    const [imgsz, setImgsz] = useState(800);
    const [batch, setBatch] = useState(24);
    const [project, setProject] = useState('runs/train');
    const [name, setName] = useState('baseline');
    const [mode, setMode] = useState('train');
    const [exportFormat, setExportFormat] = useState('torchscript');
    const [half, setHalf] = useState(true);
    const [device, setDevice] = useState('0');
    const [command, setCommand] = useState('');
    const [copied, setCopied] = useState(false);
    const [showReference, setShowReference] = useState(false);

    useEffect(() => {
        let cmd = `subyolo ${task}`;

        if (mode === 'train') {
            cmd += ' train';
            if (data) cmd += ` data="${data}"`;
            if (model) cmd += ` model=${model}`;
            if (epochs) cmd += ` epochs=${epochs}`;
            if (imgsz) cmd += ` imgsz=${imgsz}`;
            if (batch) cmd += ` batch=${batch}`;
            if (project) cmd += ` project="${project}"`;
            if (name) cmd += ` name="${name}"`;
        } else {
            cmd += ' export';
            if (model) cmd += ` model=${model}`;
            if (exportFormat) cmd += ` format=${exportFormat}`;
            if (half) cmd += ` half=True`;
            if (device !== undefined && device !== '') cmd += ` device=${device}`;
        }

        setCommand(cmd);
    }, [task, data, model, epochs, imgsz, batch, project, name, mode, exportFormat, half, device]);

    const handleCopy = () => {
        navigator.clipboard.writeText(command);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const inputStyle = {
        padding: '10px 12px',
        borderRadius: '8px',
        border: '1px solid var(--glass-border)',
        background: 'var(--bg-secondary)',
        color: 'var(--text-primary)',
        width: '100%',
        fontSize: '0.9rem',
        outline: 'none',
        transition: 'border-color 0.2s',
        fontFamily: 'inherit'
    };

    const labelStyle = {
        display: 'block',
        marginBottom: '6px',
        color: 'var(--text-secondary)',
        fontSize: '0.85rem',
        fontWeight: '600'
    };

    const groupStyle = {
        display: 'flex',
        flexDirection: 'column',
        gap: '6px'
    };

    return e('div',
        {
            style: {
                display: 'flex',
                flexDirection: 'column',
                gap: 'var(--spacing-lg)',
                height: '100%'
            }
        },

        // Header
        e('div',
            {
                className: 'glass-card',
                style: {
                    padding: 'var(--spacing-md)',
                    borderLeft: '4px solid var(--primary-blue)',
                    background: 'rgba(33, 150, 243, 0.05)'
                }
            },
            e('h3', { style: { margin: '0 0 5px 0', color: 'var(--text-primary)', fontSize: '1.1rem' } }, '🚀 Slurm 训练命令生成器'),
            e('p', { style: { margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' } },
                '快速生成 YOLO 训练任务的 Slurm 提交命令'
            )
        ),

        // Form
        e('div',
            {
                style: {
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                    gap: 'var(--spacing-md)'
                }
            },
            // Operation Mode
            e('div', { style: groupStyle },
                e('label', { style: labelStyle }, '运行模式 (Mode)'),
                e('select',
                    {
                        value: mode,
                        onChange: (e) => setMode(e.target.value),
                        style: { ...inputStyle, cursor: 'pointer', border: '1px solid var(--primary-blue)' }
                    },
                    e('option', { value: 'train' }, 'Train (训练)'),
                    e('option', { value: 'export' }, 'Export (导出)')
                )
            ),
            // Task
            e('div', { style: groupStyle },
                e('label', { style: labelStyle }, '任务类型 (Task)'),
                e('select',
                    {
                        value: task,
                        onChange: (e) => setTask(e.target.value),
                        style: { ...inputStyle, cursor: 'pointer' }
                    },
                    e('option', { value: 'detect' }, 'Detect (目标检测)'),
                    e('option', { value: 'segment' }, 'Segment (实例分割)')
                )
            ),
            // Model / best.pt
            e('div', { style: groupStyle },
                e('label', { style: labelStyle }, mode === 'train' ? '模型 (Model)' : '权重路径 (model: best.pt)'),
                e('input', {
                    type: 'text',
                    value: model,
                    onChange: (e) => setModel(e.target.value),
                    placeholder: mode === 'train' ? 'yolo11m.pt' : 'runs/train/baseline/weights/best.pt',
                    style: inputStyle
                })
            ),
            // Conditionally render fields based on mode
            ...(mode === 'train' ? [
                // Epochs
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '训练轮数 (Epochs)'),
                    e('input', {
                        type: 'number',
                        value: epochs,
                        onChange: (e) => setEpochs(e.target.value),
                        placeholder: '150',
                        style: inputStyle
                    })
                ),
                // Imgsz
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '图像尺寸 (Imgsz)'),
                    e('input', {
                        type: 'number',
                        value: imgsz,
                        onChange: (e) => setImgsz(e.target.value),
                        placeholder: '800',
                        style: inputStyle
                    })
                ),
                // Batch
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '批次大小 (Batch)'),
                    e('input', {
                        type: 'number',
                        value: batch,
                        onChange: (e) => setBatch(e.target.value),
                        placeholder: '24',
                        style: inputStyle
                    })
                ),
                // Name
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '任务名称 (Name)'),
                    e('input', {
                        type: 'text',
                        value: name,
                        onChange: (e) => setName(e.target.value),
                        placeholder: 'baseline',
                        style: inputStyle
                    })
                ),
                // Project
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '项目路径 (Project)'),
                    e('input', {
                        type: 'text',
                        value: project,
                        onChange: (e) => setProject(e.target.value),
                        placeholder: 'runs/train',
                        style: inputStyle
                    })
                )
            ] : [
                // Export Format
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '导出格式 (Format)'),
                    e('select',
                        {
                            value: exportFormat,
                            onChange: (e) => setExportFormat(e.target.value),
                            style: { ...inputStyle, cursor: 'pointer' }
                        },
                        e('option', { value: 'torchscript' }, 'TorchScript'),
                        e('option', { value: 'onnx' }, 'ONNX'),
                        e('option', { value: 'engine' }, 'TensorRT (Engine)')
                    )
                ),
                // Half Precision
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '半精度 (half=True)'),
                    e('select',
                        {
                            value: half.toString(),
                            onChange: (e) => setHalf(e.target.value === 'true'),
                            style: { ...inputStyle, cursor: 'pointer' }
                        },
                        e('option', { value: 'true' }, 'True'),
                        e('option', { value: 'false' }, 'False')
                    )
                ),
                // Device
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '设备 ID (Device)'),
                    e('input', {
                        type: 'text',
                        value: device,
                        onChange: (e) => setDevice(e.target.value),
                        placeholder: '0',
                        style: inputStyle
                    })
                )
            ])
        ),

        // Data Path (Full Width) - Only for Train mode
        mode === 'train' && e('div', { style: groupStyle },
            e('label', { style: labelStyle }, '📂 数据配置文件路径 (Data YAML)'),
            e('div', { style: { position: 'relative' } },
                e('input', {
                    type: 'text',
                    value: data,
                    onChange: (e) => setData(e.target.value),
                    placeholder: '/mnt/usrhome/sk/ndata/TFDS/dataset/baseline.yaml',
                    style: { ...inputStyle, paddingRight: '40px' }
                }),
                e('span', {
                    style: {
                        position: 'absolute',
                        right: '12px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        fontSize: '1.2rem',
                        pointerEvents: 'none',
                        opacity: 0.5
                    }
                }, '📄')
            )
        ),

        // Result Area
        e('div',
            {
                className: 'glass-card',
                style: {
                    marginTop: 'auto',
                    padding: 'var(--spacing-md)',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-lg)'
                }
            },
            e('div',
                {
                    style: {
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '12px'
                    }
                },
                e('span', { style: { fontWeight: 'bold', color: 'var(--text-primary)', fontSize: '0.95rem' } }, '✨ 生成的命令:'),
                e('button',
                    {
                        onClick: handleCopy,
                        className: 'btn',
                        style: {
                            padding: '8px 16px',
                            background: copied ? 'var(--neon-green)' : 'var(--primary-blue)',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px',
                            transition: 'all 0.2s',
                            fontWeight: '600',
                            fontSize: '0.85rem'
                        },
                        onMouseEnter: (e) => {
                            if (!copied) {
                                e.currentTarget.style.transform = 'scale(1.05)';
                                e.currentTarget.style.boxShadow = '0 4px 12px rgba(33, 150, 243, 0.3)';
                            }
                        },
                        onMouseLeave: (e) => {
                            e.currentTarget.style.transform = 'scale(1)';
                            e.currentTarget.style.boxShadow = 'none';
                        }
                    },
                    copied ? '✅ 已复制' : '📋 复制命令'
                )
            ),
            e('div',
                {
                    style: {
                        padding: '16px',
                        background: '#1e1e1e',
                        color: '#a9b7c6',
                        borderRadius: '8px',
                        fontFamily: '"Consolas", "Monaco", "Courier New", monospace',
                        wordBreak: 'break-all',
                        lineHeight: '1.6',
                        border: '1px solid #333',
                        fontSize: '0.9rem',
                        minHeight: '60px',
                        display: 'flex',
                        alignItems: 'center'
                    }
                },
                command || e('span', { style: { opacity: 0.5, fontStyle: 'italic' } }, '请填写参数以生成命令...')
            )
        ),

        // Reference Panel
        e('div',
            {
                className: 'glass-card',
                style: {
                    padding: 'var(--spacing-md)',
                    background: 'var(--bg-tertiary)',
                    border: '1px solid var(--glass-border)',
                    borderRadius: 'var(--radius-lg)'
                }
            },
            // Toggle Header
            e('div',
                {
                    onClick: () => setShowReference(!showReference),
                    style: {
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        cursor: 'pointer',
                        padding: '8px',
                        borderRadius: '6px',
                        transition: 'background 0.2s'
                    },
                    onMouseEnter: (e) => {
                        e.currentTarget.style.background = 'var(--bg-secondary)';
                    },
                    onMouseLeave: (e) => {
                        e.currentTarget.style.background = 'transparent';
                    }
                },
                e('span', { style: { fontWeight: 'bold', color: 'var(--text-primary)', fontSize: '0.95rem' } }, '📚 常用 Slurm 命令参考'),
                e('span', { style: { fontSize: '1.2rem', transition: 'transform 0.2s', transform: showReference ? 'rotate(180deg)' : 'rotate(0deg)' } }, '▼')
            ),

            // Reference Content
            showReference && e('div',
                {
                    style: {
                        marginTop: 'var(--spacing-md)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 'var(--spacing-md)'
                    }
                },

                // squeue command
                e('div',
                    {
                        style: {
                            padding: 'var(--spacing-sm)',
                            background: 'rgba(33, 150, 243, 0.05)',
                            borderRadius: '6px',
                            borderLeft: '3px solid var(--primary-blue)'
                        }
                    },
                    e('div', { style: { fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '6px', fontSize: '0.9rem' } }, '🔍 查看任务队列 (squeue)'),
                    e('div', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' } }, '查看当前用户的所有任务:'),
                    e('code',
                        {
                            style: {
                                display: 'block',
                                padding: '8px 12px',
                                background: '#1e1e1e',
                                color: '#a9b7c6',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                marginBottom: '6px'
                            }
                        },
                        'squeue -u $USER'
                    ),
                    e('div', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' } }, '查看特定用户的任务:'),
                    e('code',
                        {
                            style: {
                                display: 'block',
                                padding: '8px 12px',
                                background: '#1e1e1e',
                                color: '#a9b7c6',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }
                        },
                        'squeue -u username'
                    )
                ),

                // scancel command
                e('div',
                    {
                        style: {
                            padding: 'var(--spacing-sm)',
                            background: 'rgba(255, 107, 107, 0.05)',
                            borderRadius: '6px',
                            borderLeft: '3px solid #ff6b6b'
                        }
                    },
                    e('div', { style: { fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '6px', fontSize: '0.9rem' } }, '❌ 取消任务 (scancel)'),
                    e('div', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' } }, '取消指定任务 ID:'),
                    e('code',
                        {
                            style: {
                                display: 'block',
                                padding: '8px 12px',
                                background: '#1e1e1e',
                                color: '#a9b7c6',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem',
                                marginBottom: '6px'
                            }
                        },
                        'scancel 12345'
                    ),
                    e('div', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' } }, '取消当前用户的所有任务:'),
                    e('code',
                        {
                            style: {
                                display: 'block',
                                padding: '8px 12px',
                                background: '#1e1e1e',
                                color: '#a9b7c6',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }
                        },
                        'scancel -u $USER'
                    )
                ),

                // sinfo command
                e('div',
                    {
                        style: {
                            padding: 'var(--spacing-sm)',
                            background: 'rgba(67, 233, 123, 0.05)',
                            borderRadius: '6px',
                            borderLeft: '3px solid var(--neon-green)'
                        }
                    },
                    e('div', { style: { fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '6px', fontSize: '0.9rem' } }, 'ℹ️ 查看集群信息 (sinfo)'),
                    e('div', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' } }, '查看所有分区状态:'),
                    e('code',
                        {
                            style: {
                                display: 'block',
                                padding: '8px 12px',
                                background: '#1e1e1e',
                                color: '#a9b7c6',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }
                        },
                        'sinfo'
                    )
                ),

                // scontrol command
                e('div',
                    {
                        style: {
                            padding: 'var(--spacing-sm)',
                            background: 'rgba(238, 90, 111, 0.05)',
                            borderRadius: '6px',
                            borderLeft: '3px solid #ee5a6f'
                        }
                    },
                    e('div', { style: { fontWeight: 'bold', color: 'var(--text-primary)', marginBottom: '6px', fontSize: '0.9rem' } }, '🔧 查看任务详情 (scontrol)'),
                    e('div', { style: { fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '8px' } }, '查看指定任务的详细信息:'),
                    e('code',
                        {
                            style: {
                                display: 'block',
                                padding: '8px 12px',
                                background: '#1e1e1e',
                                color: '#a9b7c6',
                                borderRadius: '4px',
                                fontFamily: 'monospace',
                                fontSize: '0.85rem'
                            }
                        },
                        'scontrol show job 12345'
                    )
                )
            )
        )
    );
}
