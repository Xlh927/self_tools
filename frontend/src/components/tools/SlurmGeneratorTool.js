import React, { useState, useEffect } from 'react';

const { createElement: e } = React;

export default function SlurmGeneratorTool() {
    const [task, setTask] = useState('detect');
    const [data, setData] = useState('');
    const [model, setModel] = useState('yolo11m.pt');
    const [epochs, setEpochs] = useState(200);
    const [imgsz, setImgsz] = useState(800);
    const [batch, setBatch] = useState(24);
    const [cache, setCache] = useState(true);  // New cache parameter
    const [project, setProject] = useState('/runs/train');
    const [name, setName] = useState('baseline');
    const [mode, setMode] = useState('train');
    const [exportFormat, setExportFormat] = useState('torchscript');
    const [half, setHalf] = useState(true);
    const [device, setDevice] = useState('0');
    const [source, setSource] = useState('data/images');
    const [saveTxt, setSaveTxt] = useState(false);
    const [command, setCommand] = useState('');
    const [copied, setCopied] = useState(false);
    const [showReference, setShowReference] = useState(false);

    // SubFP Mode States
    const [inputList, setInputList] = useState('imageFolders.txt');
    const [inputBase, setInputBase] = useState('');
    const [handler, setHandler] = useState('tv');
    const [conf, setConf] = useState(0.25);
    const [iou, setIoU] = useState(0.5);
    const [classes, setClasses] = useState('');
    const [view, setView] = useState('L1,L2,L3,L4,L5');
    const [saveDir, setSaveDir] = useState('');
    const [fpTxt, setFpTxt] = useState(false);
    const [fpPlot, setFpPlot] = useState(false);
    const [fpSource, setFpSource] = useState(false);
    const [fpCsv, setFpCsv] = useState(false);

    useEffect(() => {
        let cmd = `subyolo ${task}`;

        if (mode === 'train') {
            cmd += ' train';
            if (data) cmd += ` data="${data}"`;
            if (model) cmd += ` model=${model}`;
            if (epochs) cmd += ` epochs=${epochs}`;
            if (imgsz) cmd += ` imgsz=${imgsz}`;
            if (batch) cmd += ` batch=${batch}`;
            if (cache) cmd += ` cache=True`;
            if (project) cmd += ` project="${project}"`;
            if (name) cmd += ` name="${name}"`;
        } else if (mode === 'val') {
            cmd += ' val';
            if (model) cmd += ` model=${model}`;
            if (data) cmd += ` data="${data}"`;
            if (imgsz) cmd += ` imgsz=${imgsz}`;
            if (batch) cmd += ` batch=${batch}`;
            if (project) cmd += ` project="${project}"`;
            if (name) cmd += ` name="${name}"`;
            if (device !== undefined && device !== '') cmd += ` device=${device}`;
        } else if (mode === 'predict') {
            cmd += ' predict';
            if (model) cmd += ` model=${model}`;
            if (source) cmd += ` source="${source}"`;
            if (imgsz) cmd += ` imgsz=${imgsz}`;
            if (project) cmd += ` project="${project}"`;
            if (name) cmd += ` name="${name}"`;
            if (saveTxt) cmd += ` save_txt=True`;
            if (device !== undefined && device !== '') cmd += ` device=${device}`;
        } else if (mode === 'subfp') {
            cmd = 'subfp';
            if (inputList) cmd += ` --input_list ${inputList}`;
            if (inputBase) cmd += ` --input_base ${inputBase}`;
            if (handler) cmd += ` --handler ${handler}`;
            if (model) cmd += ` --weights ${model}`; // Reusing model state for weights
            if (imgsz) cmd += ` --imgsz ${imgsz}`;
            if (conf !== undefined && conf !== '') cmd += ` --conf ${conf}`;
            if (iou !== undefined && iou !== '') cmd += ` --iou ${iou}`;
            if (classes) cmd += ` --classes ${classes}`;
            if (view) cmd += ` --view ${view}`;
            if (saveDir) cmd += ` --save_dir ${saveDir}`;

            if (fpTxt) cmd += ` --txt True`;
            if (fpPlot) cmd += ` --plot True`;
            if (fpSource) cmd += ` --source True`;
            if (fpCsv) cmd += ` --csv True`;
        } else {
            cmd += ' export';
            if (model) cmd += ` model=${model}`;
            if (exportFormat) cmd += ` format=${exportFormat}`;
            if (half) cmd += ` half=True`;
            if (device !== undefined && device !== '') cmd += ` device=${device}`;
        }

        setCommand(cmd);
    }, [task, data, model, epochs, imgsz, batch, cache, project, name, mode, exportFormat, half, device, source, saveTxt,
        inputList, inputBase, handler, conf, iou, classes, view, saveDir, fpTxt, fpPlot, fpSource, fpCsv]);

    const handleSubfpPreset = (type) => {
        if (type === 'false_alarm') {
            // 压误报: All 4 True
            setFpTxt(true);
            setFpPlot(true);
            setFpSource(true);
            setFpCsv(true);
        } else if (type === 'threshold') {
            // 测阈值: Only CSV True
            setFpTxt(false);
            setFpPlot(false);
            setFpSource(false);
            setFpCsv(true);
        }
    };

    const handleCopy = () => {
        navigator.clipboard.writeText(command);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const handleDataChange = (e) => {
        const val = e.target.value;
        setData(val);

        // Auto-populate Project and Name if path contains '/dataset/'
        if (val && val.includes('/dataset/')) {
            // Extract base path (content before /dataset/)
            const parts = val.split('/dataset/');
            const basePath = parts[0];

            // Determine suffix based on mode
            let suffix = 'runs/train';
            if (mode === 'val') suffix = 'runs/val';
            else if (mode === 'predict') suffix = 'runs/predict';

            setProject(`${basePath}/${suffix}`);

            // Extract filename for Name field (dataset + _ + filename)
            const fileNameWithExt = val.split('/').pop();
            const fileName = fileNameWithExt.replace('.yaml', '').replace('.yml', '');
            setName(fileName);
        }
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
                        onChange: (e) => {
                            setMode(e.target.value);
                            // Auto-adjust project path based on mode
                            if (e.target.value === 'train') {
                                setProject('/runs/train');
                                setModel('yolo11m.pt');
                            }
                            else if (e.target.value === 'val') {
                                setProject('/runs/val');
                                setModel('');
                            }
                            else if (e.target.value === 'predict') {
                                setProject('/runs/predict');
                                setModel('');
                            }
                            else if (e.target.value === 'export') setModel('');
                            else if (e.target.value === 'subfp') setModel('');
                        },
                        style: { ...inputStyle, cursor: 'pointer', border: '1px solid var(--primary-blue)' }
                    },
                    e('option', { value: 'train' }, 'Train (训练)'),
                    e('option', { value: 'val' }, 'Val (验证)'),

                    e('option', { value: 'predict' }, 'Predict (推理)'),
                    e('option', { value: 'export' }, 'Export (导出)'),
                    e('option', { value: 'subfp' }, 'SubFP (压误报/测阈值)')
                )
            ),
            // Task
            mode !== 'subfp' && e('div', { style: groupStyle },
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
            // Model / best.pt / weights
            e('div', { style: ['subfp', 'val', 'predict', 'export'].includes(mode) ? { ...groupStyle, gridColumn: '1 / -1' } : groupStyle },
                e('label', { style: labelStyle }, mode === 'train' ? '模型 (Model)' : (mode === 'subfp' ? '权重 (Weights)' : '权重路径 (model: best.pt)')),
                e('input', {
                    type: 'text',
                    value: model,
                    onChange: (e) => setModel(e.target.value),
                    placeholder: mode === 'train' ? 'yolo11m.pt' : (mode === 'subfp' ? '.torchscript' : 'runs/train/baseline/weights/best.pt'),
                    style: inputStyle
                })
            ),
            // Conditionally render fields based on mode
            ...(mode === 'train' || mode === 'val' ? [
                // Epochs (Train only)
                mode === 'train' && e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '训练轮数 (Epochs)'),
                    e('input', {
                        type: 'number',
                        value: epochs,
                        onChange: (e) => setEpochs(e.target.value),
                        placeholder: '200',
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
                // Cache (Train only)
                mode === 'train' && e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '缓存数据 (Cache)'),
                    e('select',
                        {
                            value: cache.toString(),
                            onChange: (e) => setCache(e.target.value === 'true'),
                            style: { ...inputStyle, cursor: 'pointer' }
                        },
                        e('option', { value: 'true' }, 'True'),
                        e('option', { value: 'false' }, 'False')
                    )
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

                // Device (Val only here, Train uses default but could show it)
                mode === 'val' && e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '设备 ID (Device)'),
                    e('input', {
                        type: 'text',
                        value: device,
                        onChange: (e) => setDevice(e.target.value),
                        placeholder: '0',
                        style: inputStyle
                    })
                )
            ].filter(Boolean) : (mode === 'predict' ? [
                // Source
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '推理来源 (Source)'),
                    e('input', {
                        type: 'text',
                        value: source,
                        onChange: (e) => setSource(e.target.value),
                        placeholder: 'data/images',
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

                // Save Txt
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '保存标签 (save_txt)'),
                    e('select',
                        {
                            value: saveTxt.toString(),
                            onChange: (e) => setSaveTxt(e.target.value === 'true'),
                            style: { ...inputStyle, cursor: 'pointer' }
                        },
                        e('option', { value: 'false' }, 'False'),
                        e('option', { value: 'true' }, 'True')
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
            ] : (mode === 'subfp' ? [
                // Input List
                e('div', { style: { ...groupStyle, gridColumn: '1 / -1' } },
                    e('label', { style: labelStyle }, '输入列表 (Input List)'),
                    e('input', {
                        type: 'text',
                        value: inputList,
                        onChange: (e) => setInputList(e.target.value),
                        placeholder: 'imageFolders.txt',
                        style: inputStyle
                    })
                ),
                // Input Base
                e('div', { style: { ...groupStyle, gridColumn: '1 / -1' } },
                    e('label', { style: labelStyle }, '路径前缀 (Input Base)'),
                    e('input', {
                        type: 'text',
                        value: inputBase,
                        onChange: (e) => setInputBase(e.target.value),
                        placeholder: '/mnt/projects/tv/TV/训练测试/普客/',
                        style: inputStyle
                    })
                ),
                // Save Dir (Moved here)
                e('div', { style: { ...groupStyle, gridColumn: '1 / -1' } },
                    e('label', { style: labelStyle }, '保存目录 (Save Dir)'),
                    e('input', {
                        type: 'text',
                        value: saveDir,
                        onChange: (e) => setSaveDir(e.target.value),
                        placeholder: '结果默认保存在.torchscrit同级目录中',
                        style: inputStyle
                    })
                ),
                // Handler
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '处理类型 (Handler)'),
                    e('select',
                        {
                            value: handler,
                            onChange: (e) => setHandler(e.target.value),
                            style: { ...inputStyle, cursor: 'pointer' }
                        },
                        e('option', { value: 'tv' }, 'tv'),
                        e('option', { value: 'tf' }, 'tf')
                    )
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
                // Conf
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '置信度 (Conf)'),
                    e('input', {
                        type: 'number',
                        value: conf,
                        onChange: (e) => setConf(e.target.value),
                        step: '0.01',
                        placeholder: '0.25',
                        style: inputStyle
                    })
                ),
                // IoU
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, 'IoU 阈值'),
                    e('input', {
                        type: 'number',
                        value: iou,
                        onChange: (e) => setIoU(e.target.value),
                        step: '0.01',
                        placeholder: '0.5',
                        style: inputStyle
                    })
                ),
                // Classes
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '类别 (Classes)'),
                    e('input', {
                        type: 'text',
                        value: classes,
                        onChange: (e) => setClasses(e.target.value),
                        placeholder: 'Leave empty for all',
                        style: inputStyle
                    })
                ),
                // View
                e('div', { style: groupStyle },
                    e('label', { style: labelStyle }, '视图 (View)'),
                    e('input', {
                        type: 'text',
                        value: view,
                        onChange: (e) => setView(e.target.value),
                        placeholder: 'L1,L2,L3,L4,L5',
                        style: inputStyle
                    })
                ),

                // Presets Buttons
                e('div', { style: { ...groupStyle, gridColumn: '1 / -1', marginTop: '10px' } },
                    e('label', { style: labelStyle }, '快速预设 (Presets)'),
                    e('div', { style: { display: 'flex', gap: '10px' } },
                        e('button', {
                            onClick: () => handleSubfpPreset('false_alarm'),
                            style: { ...inputStyle, background: 'var(--primary-blue)', color: 'white', cursor: 'pointer', textAlign: 'center' }
                        }, '🔍 压误报 (False Alarm)'),
                        e('button', {
                            onClick: () => handleSubfpPreset('threshold'),
                            style: { ...inputStyle, background: 'var(--primary-blue)', color: 'white', cursor: 'pointer', textAlign: 'center' }
                        }, '📊 测阈值 (Threshold)')
                    )
                ),
                // Checkboxes
                e('div', { style: { ...groupStyle, gridColumn: '1 / -1', display: 'flex', flexDirection: 'row', gap: '20px', flexWrap: 'wrap' } },
                    e('label', { style: { display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '5px', color: 'var(--text-primary)' } },
                        e('input', { type: 'checkbox', checked: fpTxt, onChange: (e) => setFpTxt(e.target.checked) }), 'txt'
                    ),
                    e('label', { style: { display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '5px', color: 'var(--text-primary)' } },
                        e('input', { type: 'checkbox', checked: fpPlot, onChange: (e) => setFpPlot(e.target.checked) }), 'plot'
                    ),
                    e('label', { style: { display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '5px', color: 'var(--text-primary)' } },
                        e('input', { type: 'checkbox', checked: fpSource, onChange: (e) => setFpSource(e.target.checked) }), 'source'
                    ),
                    e('label', { style: { display: 'flex', alignItems: 'center', cursor: 'pointer', gap: '5px', color: 'var(--text-primary)' } },
                        e('input', { type: 'checkbox', checked: fpCsv, onChange: (e) => setFpCsv(e.target.checked) }), 'csv'
                    )
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
            ])))
        ),

        // Project Path (Full Width) - For Train, Val, Predict
        (mode !== 'export' && mode !== 'subfp') && e('div', { style: groupStyle },
            e('label', { style: labelStyle }, '📂 项目路径 (Project)'),
            e('div', { style: { position: 'relative' } },
                e('input', {
                    type: 'text',
                    value: project,
                    onChange: (e) => setProject(e.target.value),
                    placeholder: '/runs/train',
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
                }, '📂')
            )
        ),

        // Data Path (Full Width) - Only for Train mode
        mode === 'train' && e('div', { style: groupStyle },
            e('label', { style: labelStyle }, '📂 数据配置文件路径 (Data YAML)'),
            e('div', { style: { position: 'relative' } },
                e('input', {
                    type: 'text',
                    value: data,
                    onChange: handleDataChange,
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
