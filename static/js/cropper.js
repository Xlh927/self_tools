// DOM Elements
const form = document.getElementById('cropperForm');
const processingMode = document.getElementById('processingMode');
const inputPathLabel = document.getElementById('inputPathLabel');
const inputPath = document.getElementById('inputPath');
const windowWidth = document.getElementById('windowWidth');
const windowHeight = document.getElementById('windowHeight');
const overlapX = document.getElementById('overlapX');
const overlapY = document.getElementById('overlapY');
const previewWindow = document.getElementById('previewWindow');
const previewOverlap = document.getElementById('previewOverlap');
const previewStride = document.getElementById('previewStride');
const submitBtn = document.getElementById('submitBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const resultContent = document.getElementById('resultContent');
const toast = document.getElementById('toast');

// Update UI based on processing mode
processingMode.addEventListener('change', (e) => {
    const isSingle = e.target.value === 'single';
    inputPathLabel.textContent = isSingle ? '图片路径' : '文件夹路径';
    inputPath.placeholder = isSingle ? '例如: /path/to/image.jpg' : '例如: /path/to/images';
});

// Update preview when parameters change
function updatePreview() {
    const wWidth = parseInt(windowWidth.value) || 1024;
    const wHeight = parseInt(windowHeight.value) || 1024;
    const oX = parseInt(overlapX.value) || 0;
    const oY = parseInt(overlapY.value) || 0;

    previewWindow.textContent = `${wWidth} × ${wHeight}`;
    previewOverlap.textContent = `${oX} × ${oY}`;

    const strideX = wWidth - oX;
    const strideY = wHeight - oY;
    previewStride.textContent = `${strideX} × ${strideY}`;

    // Validate overlap
    if (oX >= wWidth || oY >= wHeight) {
        previewStride.style.color = '#f5576c';
        previewStride.textContent = '⚠️ 重叠度过大';
    } else if (strideX <= 0 || strideY <= 0) {
        previewStride.style.color = '#f5576c';
        previewStride.textContent = '⚠️ 无效步长';
    } else {
        previewStride.style.color = '';
    }
}

windowWidth.addEventListener('input', updatePreview);
windowHeight.addEventListener('input', updatePreview);
overlapX.addEventListener('input', updatePreview);
overlapY.addEventListener('input', updatePreview);

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = {
        mode: processingMode.value,
        input_path: inputPath.value.trim(),
        output_dir: document.getElementById('outputDir').value.trim(),
        window_width: parseInt(windowWidth.value),
        window_height: parseInt(windowHeight.value),
        overlap_x: parseInt(overlapX.value),
        overlap_y: parseInt(overlapY.value)
    };

    // Validate
    if (!formData.input_path || !formData.output_dir) {
        showToast('请填写所有必填字段', 'error');
        return;
    }

    if (formData.window_width <= 0 || formData.window_height <= 0) {
        showToast('窗口大小必须为正数', 'error');
        return;
    }

    if (formData.overlap_x < 0 || formData.overlap_y < 0) {
        showToast('重叠度不能为负数', 'error');
        return;
    }

    if (formData.overlap_x >= formData.window_width || formData.overlap_y >= formData.window_height) {
        showToast('重叠度必须小于窗口大小', 'error');
        return;
    }

    // Disable form
    setFormEnabled(false);

    // Show progress
    showProgress();

    try {
        // Send request
        const response = await fetch('/api/crop', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const result = await response.json();

        // Hide progress
        hideProgress();

        // Show result
        if (result.success) {
            showSuccessResult(result);
            showToast('裁剪成功完成！', 'success');
        } else {
            showErrorResult(result);
            showToast('裁剪失败：' + result.error, 'error');
        }

    } catch (error) {
        hideProgress();
        showErrorResult({ error: error.message });
        showToast('请求失败：' + error.message, 'error');
    } finally {
        setFormEnabled(true);
    }
});

// Enable/disable form
function setFormEnabled(enabled) {
    const inputs = form.querySelectorAll('input, select, button');
    inputs.forEach(input => {
        input.disabled = !enabled;
    });

    if (!enabled) {
        submitBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">裁剪中...</span>';
    } else {
        submitBtn.innerHTML = `
            <span class="btn-text">开始裁剪</span>
            <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M5 10h10M11 6l4 4-4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
        `;
    }
}

// Show progress
function showProgress() {
    resultSection.style.display = 'none';
    progressSection.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = '正在裁剪...';

    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) {
            progress = 90;
            clearInterval(interval);
        }
        progressFill.style.width = progress + '%';
    }, 200);

    // Store interval ID for cleanup
    progressSection.dataset.intervalId = interval;
}

// Hide progress
function hideProgress() {
    const intervalId = progressSection.dataset.intervalId;
    if (intervalId) {
        clearInterval(parseInt(intervalId));
    }

    progressFill.style.width = '100%';
    setTimeout(() => {
        progressSection.style.display = 'none';
    }, 500);
}

// Show success result
function showSuccessResult(result) {
    let html = '';

    if (result.mode === 'single' || result.image) {
        // Single image result
        html = `
            <div class="result-success">
                <div class="result-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                        <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    裁剪成功完成！
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">原始尺寸</div>
                        <div class="stat-value">${result.original_size.width} × ${result.original_size.height}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">窗口大小</div>
                        <div class="stat-value">${result.window_size.width} × ${result.window_size.height}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">生成切片</div>
                        <div class="stat-value">${result.crops_count}</div>
                    </div>
                </div>
            </div>
        `;
    } else {
        // Folder batch result
        html = `
            <div class="result-success">
                <div class="result-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                        <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    批量裁剪完成！
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">处理图片</div>
                        <div class="stat-value">${result.processed}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">失败图片</div>
                        <div class="stat-value">${result.failed}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">总切片数</div>
                        <div class="stat-value">${result.total_crops}</div>
                    </div>
                </div>
        `;

        if (result.errors && result.errors.length > 0) {
            html += `
                <div class="error-list">
                    <h4 style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px;">
                        警告 (${result.errors.length}):
                    </h4>
                    ${result.errors.slice(0, 10).map(err => `<div class="error-item">${err}</div>`).join('')}
                    ${result.errors.length > 10 ? `<div class="error-item">...还有 ${result.errors.length - 10} 个警告</div>` : ''}
                </div>
            `;
        }

        html += '</div>';
    }

    resultContent.innerHTML = html;
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Show error result
function showErrorResult(result) {
    resultContent.innerHTML = `
        <div class="result-error">
            <div class="result-title">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="#f5576c" stroke-width="2"/>
                    <path d="M12 8v4M12 16h.01" stroke="#f5576c" stroke-width="2" stroke-linecap="round"/>
                </svg>
                裁剪失败
            </div>
            <p style="color: var(--text-secondary); margin-top: 12px;">
                ${result.error || '未知错误'}
            </p>
        </div>
    `;

    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// Show toast notification
function showToast(message, type = 'success') {
    toast.textContent = message;
    toast.className = `toast ${type} show`;

    setTimeout(() => {
        toast.classList.remove('show');
    }, 4000);
}

// Initialize preview
updatePreview();
