import React, { useState, useEffect, useRef } from 'react';

const { createElement: e } = React;

export default function GridGeneratorTool() {
    const [rows, setRows] = useState(2);
    const [cols, setCols] = useState(2);
    const [cells, setCells] = useState([]);
    const [rowLabels, setRowLabels] = useState(Array(2).fill(''));
    const [colLabels, setColLabels] = useState(Array(2).fill(''));
    const [selectedCells, setSelectedCells] = useState([]);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [activeCellId, setActiveCellId] = useState(null);
    const fileInputRef = useRef(null);

    // Default style config (hidden from user in easy mode)
    const padding = 10;
    const margin = 20;
    const fontSize = 24;
    const background = 'white';

    // Initialize cells
    useEffect(() => {
        // Only initialize if empty or dimensions changed significantly
        // But we want to preserve existing cells if possible when resizing
        const newCells = [];
        for (let r = 0; r < rows; r++) {
            for (let c = 0; c < cols; c++) {
                // Check if this position is already covered by an existing cell
                const existing = cells.find(cell =>
                    r >= cell.row && r < cell.row + cell.rowspan &&
                    c >= cell.col && c < cell.col + cell.colspan
                );

                if (existing) {
                    if (!newCells.find(nc => nc.id === existing.id)) {
                        newCells.push(existing);
                    }
                } else {
                    newCells.push({
                        id: `${r}-${c}-${Date.now()}`,
                        row: r,
                        col: c,
                        rowspan: 1,
                        colspan: 1,
                        file: null,
                        preview: null,
                        subtitle: ''
                    });
                }
            }
        }
        setCells(newCells);

        // Update labels
        setRowLabels(prev => {
            const newLabels = [...prev];
            while (newLabels.length < rows) newLabels.push('');
            return newLabels.slice(0, rows);
        });

        setColLabels(prev => {
            const newLabels = [...prev];
            while (newLabels.length < cols) newLabels.push('');
            return newLabels.slice(0, cols);
        });
    }, [rows, cols]);

    const handleFileSelect = (file, cellId) => {
        // Store file object and create preview URL
        setCells(prev => prev.map(c =>
            c.id === cellId ? {
                ...c,
                file: file,  // Store actual File object
                preview: URL.createObjectURL(file)
            } : c
        ));
    };

    const handleCellClick = (id, e) => {
        if (e.ctrlKey || e.metaKey) {
            setSelectedCells(prev => prev.includes(id) ? prev.filter(cid => cid !== id) : [...prev, id]);
        } else {
            setSelectedCells([id]);
            setActiveCellId(id);
            if (fileInputRef.current) {
                fileInputRef.current.click();
            }
        }
    };

    const handleMerge = () => {
        if (selectedCells.length < 2) return;

        // Find bounding box of selected cells
        const selected = cells.filter(c => selectedCells.includes(c.id));
        const minRow = Math.min(...selected.map(c => c.row));
        const maxRow = Math.max(...selected.map(c => c.row + c.rowspan));
        const minCol = Math.min(...selected.map(c => c.col));
        const maxCol = Math.max(...selected.map(c => c.col + c.colspan));

        // Create new merged cell
        const newCell = {
            id: `merged-${Date.now()}`,
            row: minRow,
            col: minCol,
            rowspan: maxRow - minRow,
            colspan: maxCol - minCol,
            path: selected[0].path, // Keep first image
            preview: selected[0].preview
        };

        // Remove old cells and add new one
        setCells(prev => [
            ...prev.filter(c => !selectedCells.includes(c.id)),
            newCell
        ]);
        setSelectedCells([newCell.id]);
    };

    const handleUnmerge = () => {
        if (selectedCells.length !== 1) return;

        const cell = cells.find(c => c.id === selectedCells[0]);
        if (cell.rowspan === 1 && cell.colspan === 1) return;

        // Remove merged cell
        const remaining = cells.filter(c => c.id !== cell.id);

        // Fill the void with 1x1 cells
        const newCells = [];
        for (let r = cell.row; r < cell.row + cell.rowspan; r++) {
            for (let c = cell.col; c < cell.col + cell.colspan; c++) {
                newCells.push({
                    id: `${r}-${c}-${Date.now()}`,
                    row: r,
                    col: c,
                    rowspan: 1,
                    colspan: 1,
                    file: null,
                    preview: null,
                    subtitle: ''
                });
            }
        }

        setCells([...remaining, ...newCells]);
        setSelectedCells([]);
    };

    const handleGenerate = async () => {
        setLoading(true);
        setResult(null);

        const defaultPath = `/home/qzq/Downloads/grid_${Date.now()}.png`;

        try {
            // Create FormData
            const formData = new FormData();

            // Add config as JSON string
            const config = {
                cells: cells.map((c, idx) => ({
                    row: c.row,
                    col: c.col,
                    rowspan: c.rowspan,
                    colspan: c.colspan,
                    subtitle: c.subtitle || '',
                    // Don't include file or preview
                })),
                row_labels: rowLabels,
                col_labels: colLabels,
                output_path: defaultPath,
                padding,
                margin,
                font_size: fontSize,
                background
            };

            formData.append('config', JSON.stringify(config));

            // Add all files with cell_ prefix
            cells.forEach((cell, idx) => {
                if (cell.file) {
                    formData.append(`cell_${idx}`, cell.file);
                }
            });

            const response = await fetch('/api/generate-grid', {
                method: 'POST',
                body: formData
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
        { style: { display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)', height: '100%' } },

        // Header & Toolbar
        e('div',
            {
                className: 'glass-card',
                style: {
                    padding: 'var(--spacing-md)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    background: 'rgba(33, 150, 243, 0.1)',
                    border: '2px solid var(--primary-blue)'
                }
            },
            e('div', {},
                e('h2', { style: { margin: 0, color: 'var(--primary-blue)' } }, '📑 论文宫格 (小白版)'),
                e('p', { style: { margin: '5px 0 0 0', fontSize: '0.9rem', color: 'var(--text-secondary)' } },
                    '点击格子上传图片，按住 Ctrl 多选合并'
                )
            ),
            e('div', { style: { display: 'flex', gap: '20px', alignItems: 'center' } },
                // Row Control
                e('div', { style: { display: 'flex', alignItems: 'center', gap: '10px' } },
                    e('span', { style: { fontWeight: 'bold' } }, '行数:'),
                    e('button', { className: 'btn', onClick: () => setRows(Math.max(1, rows - 1)) }, '-'),
                    e('span', { style: { fontSize: '1.2rem', minWidth: '20px', textAlign: 'center' } }, rows),
                    e('button', { className: 'btn', onClick: () => setRows(rows + 1) }, '+')
                ),
                // Col Control
                e('div', { style: { display: 'flex', alignItems: 'center', gap: '10px' } },
                    e('span', { style: { fontWeight: 'bold' } }, '列数:'),
                    e('button', { className: 'btn', onClick: () => setCols(Math.max(1, cols - 1)) }, '-'),
                    e('span', { style: { fontSize: '1.2rem', minWidth: '20px', textAlign: 'center' } }, cols),
                    e('button', { className: 'btn', onClick: () => setCols(cols + 1) }, '+')
                )
            )
        ),

        // Main Workspace
        e('div', { style: { display: 'flex', gap: '10px', flex: 1, minHeight: '400px' } },

            // Left Labels (Rows)
            e('div', { style: { display: 'flex', flexDirection: 'column', gap: '10px', paddingTop: '40px', width: '100px' } },
                rowLabels.map((label, i) =>
                    e('input', {
                        key: i,
                        className: 'input-field',
                        style: { flex: 1, textAlign: 'right' },
                        placeholder: `Row ${i + 1}`,
                        value: label,
                        onChange: (e) => {
                            const newLabels = [...rowLabels];
                            newLabels[i] = e.target.value;
                            setRowLabels(newLabels);
                        }
                    })
                )
            ),

            // Center Grid Area
            e('div', { style: { flex: 1, display: 'flex', flexDirection: 'column', gap: '10px' } },

                // Top Labels (Cols)
                e('div', { style: { display: 'flex', gap: '10px', paddingLeft: '0' } },
                    colLabels.map((label, i) =>
                        e('input', {
                            key: i,
                            className: 'input-field',
                            style: { flex: 1, textAlign: 'center' },
                            placeholder: `Col ${i + 1}`,
                            value: label,
                            onChange: (e) => {
                                const newLabels = [...colLabels];
                                newLabels[i] = e.target.value;
                                setColLabels(newLabels);
                            }
                        })
                    )
                ),

                // The Grid
                e('div', {
                    style: {
                        display: 'grid',
                        gridTemplateColumns: `repeat(${cols}, 1fr)`,
                        gridTemplateRows: `repeat(${rows}, 1fr)`,
                        gap: '10px',
                        flex: 1,
                        background: '#f5f5f5',
                        padding: '10px',
                        borderRadius: '8px'
                    }
                },
                    cells.map(cell =>
                        e('div', {
                            key: cell.id,
                            onClick: (e) => handleCellClick(cell.id, e),
                            style: {
                                gridColumn: `${cell.col + 1} / span ${cell.colspan}`,
                                gridRow: `${cell.row + 1} / span ${cell.rowspan}`,
                                background: selectedCells.includes(cell.id) ? 'rgba(33, 150, 243, 0.2)' : 'white',
                                border: selectedCells.includes(cell.id) ? '2px solid var(--primary-blue)' : '2px dashed #ccc',
                                borderRadius: '8px',
                                display: 'flex',
                                justifyContent: 'center',
                                alignItems: 'center',
                                cursor: 'pointer',
                                position: 'relative',
                                overflow: 'hidden',
                                transition: 'all 0.2s ease'
                            },
                            onDragOver: (e) => e.preventDefault(),
                            onDrop: (e) => {
                                e.preventDefault();
                                if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                                    handleFileSelect(e.dataTransfer.files[0], cell.id);
                                }
                            }
                        },
                            cell.preview ?
                                e('img', {
                                    src: cell.preview,
                                    style: { width: '100%', height: '100%', objectFit: 'cover' }
                                }) :
                                e('div', { style: { textAlign: 'center', color: '#ccc' } },
                                    e('span', { style: { fontSize: '2rem' } }, '+'),
                                    e('div', { style: { fontSize: '0.8rem' } }, '点击或拖拽')
                                ),
                            // Subtitle Input
                            e('input', {
                                type: 'text',
                                className: 'input-field',
                                style: {
                                    position: 'absolute',
                                    bottom: '5px',
                                    left: '5px',
                                    right: '5px',
                                    height: '24px',
                                    background: 'rgba(255, 255, 255, 0.8)',
                                    color: '#333',
                                    fontSize: '0.8rem',
                                    padding: '0 5px',
                                    border: '1px solid #ccc',
                                    borderRadius: '4px',
                                    zIndex: 10
                                },
                                placeholder: '请输入小标题...',
                                value: cell.subtitle || '',
                                onClick: (e) => e.stopPropagation(), // Prevent triggering cell click
                                onChange: (e) => {
                                    const val = e.target.value;
                                    setCells(prev => prev.map(c =>
                                        c.id === cell.id ? { ...c, subtitle: val } : c
                                    ));
                                }
                            })
                        )
                    )
                )
            )
        ),

        // Floating Action Bar (Merge/Unmerge)
        selectedCells.length > 0 && e('div', {
            className: 'glass-card',
            style: {
                position: 'fixed',
                bottom: '100px',
                left: '50%',
                transform: 'translateX(-50%)',
                padding: '10px 20px',
                display: 'flex',
                gap: '10px',
                zIndex: 1000,
                boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
            }
        },
            selectedCells.length > 1 && e('button', {
                className: 'btn btn-primary',
                onClick: handleMerge
            }, '🔗 合并单元格'),

            selectedCells.length === 1 && cells.find(c => c.id === selectedCells[0] && (c.rowspan > 1 || c.colspan > 1)) && e('button', {
                className: 'btn btn-danger',
                onClick: handleUnmerge
            }, '✂️ 拆分单元格')
        ),

        // Generate Button
        !loading && e('button',
            {
                className: 'btn btn-primary',
                onClick: handleGenerate,
                style: { padding: 'var(--spacing-md)', fontSize: '1.2rem', marginTop: '10px' }
            },
            '✨ 一键生成图片'
        ),

        // Loading
        loading && e('div',
            { style: { textAlign: 'center', padding: 'var(--spacing-lg)', color: 'var(--primary-blue)' } },
            e('div', { className: 'spinner' }),
            e('p', {}, '正在生成...')
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
            e('h3', {}, result.success ? '✅ 生成成功！' : '❌ 生成失败'),
            result.success && e('div', {},
                e('p', {}, `文件已保存至: ${result.output_path}`),
                e('p', { style: { fontSize: '0.9rem', color: '#666' } }, '(请在文件管理器中查看)')
            ),
            result.error && e('p', { style: { color: 'var(--neon-orange)' } }, result.error)
        ),

        // Global hidden file input for grid cells
        e('input', {
            type: 'file',
            ref: fileInputRef,
            accept: 'image/*',
            style: { display: 'none' },
            onChange: (e) => {
                if (e.target.files && e.target.files[0] && activeCellId) {
                    handleFileSelect(e.target.files[0], activeCellId);
                    e.target.value = ''; // Reset to allow same file selection
                }
            }
        })
    );
}
