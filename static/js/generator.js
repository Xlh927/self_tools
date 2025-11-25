// DOM Elements
const form = document.getElementById('generatorForm');
const annotationFormat = document.getElementById('annotationFormat');
const annotationHint = document.getElementById('annotationHint');
const classFilterHint = document.getElementById('classFilterHint');
const classFilterHelp = document.getElementById('classFilterHelp');
const windowWidth = document.getElementById('windowWidth');
const windowHeight = document.getElementById('windowHeight');
const strideX = document.getElementById('strideX');
const strideY = document.getElementById('strideY');
const overlapThreshold = document.getElementById('overlapThreshold');
const thresholdValue = document.getElementById('thresholdValue');
const previewWindow = document.getElementById('previewWindow');
const previewStride = document.getElementById('previewStride');
const previewThreshold = document.getElementById('previewThreshold');
const submitBtn = document.getElementById('submitBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const resultContent = document.getElementById('resultContent');
const toast = document.getElementById('toast');

// Update UI based on annotation format
annotationFormat.addEventListener('change', (e) => {
    const format = e.target.value;

    if (format === 'voc') {
        annotationHint.textContent = '(XML文件)';
        classFilterHint.textContent = '(类别名称，逗号分隔)';
        classFilterHelp.textContent = 'VOC格式: 输入类别名称，如 "person,car,bicycle"';
        document.getElementById('classFilter').placeholder = '例如: person,car,bicycle';
    } else if (format === 'yolo') {
        annotationHint.textContent = '(TXT文件)';
        classFilterHint.textContent = '(类别索引，逗号分隔)';
        classFilterHelp.textContent = 'YOLO格式: 输入类别索引（从0开始），如 "0,1,3"';
        document.getElementById('classFilter').placeholder = '例如: 0,1,3';
    } else if (format === 'json') {
        annotationHint.textContent = '(JSON文件)';
        classFilterHint.textContent = '(类别名称，逗号分隔)';
        classFilterHelp.textContent = 'JSON格式: 输入类别名称，如 "person,car,bicycle"';
        document.getElementById('classFilter').placeholder = '例如: person,car,bicycle';
    }
});

// Update threshold display
overlapThreshold.addEventListener('input', (e) => {
    const value = e.target.value;
    thresholdValue.textContent = `${value}%`;
    updatePreview();
});

// Update preview when parameters change
function updatePreview() {
    const wWidth = parseInt(windowWidth.value) || 640;
    const wHeight = parseInt(windowHeight.value) || 640;
    const sX = parseInt(strideX.value) || 320;
    const sY = parseInt(strideY.value) || 320;
    const threshold = parseInt(overlapThreshold.value) || 100;

    previewWindow.textContent = `${wWidth} × ${wHeight}`;
    previewStride.textContent = `${sX} × ${sY}`;
    previewThreshold.textContent = `${threshold}%`;
}

windowWidth.addEventListener('input', updatePreview);
windowHeight.addEventListener('input', updatePreview);
strideX.addEventListener('input', updatePreview);
strideY.addEventListener('input', updatePreview);

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Parse class filter
    const classFilterValue = document.getElementById('classFilter').value.trim();
    let classes = [];

    if (classFilterValue) {
        const format = annotationFormat.value;
        if (format === 'yolo') {
            // Parse as integers
            classes = classFilterValue.split(',').map(s => parseInt(s.trim())).filter(n => !isNaN(n));
        } else {
            // Parse as strings
            classes = classFilterValue.split(',').map(s => s.trim()).filter(s => s.length > 0);
        }
    }

    if (classes.length === 0) {
        showToast('请输入至少一个类别', 'error');
        return;
    }

    // Get form data
    const formData = {
        annotation_format: annotationFormat.value,
        images_dir: document.getElementById('imagesDir').value.trim(),
        annotations_dir: document.getElementById('annotationsDir').value.trim(),
        output_dir: document.getElementById('outputDir').value.trim(),
        classes: classes,
        window_width: parseInt(windowWidth.value),
        window_height: parseInt(windowHeight.value),
        stride_x: parseInt(strideX.value),
        stride_y: parseInt(strideY.value),
        overlap_threshold: parseInt(overlapThreshold.value)
    };

    // Validate
    if (!formData.images_dir || !formData.annotations_dir || !formData.output_dir) {
        showToast('请填写所有必填字段', 'error');
        return;
    }

    // Disable form
    setFormEnabled(false);

    // Show progress
    showProgress();

    try {
        // Send request
        const response = await fetch('/api/generate', {
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
            showToast('数据集生成成功！', 'success');
        } else {
            showErrorResult(result);
            showToast('生成失败：' + result.error, 'error');
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
        submitBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">生成中...</span>';
    } else {
        submitBtn.innerHTML = `
            <span class="btn-text">开始生成</span>
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
    progressText.textContent = '正在生成数据集...';

    // Simulate progress
    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 90) {
            progress = 90;
            clearInterval(interval);
        }
        progressFill.style.width = progress + '%';
    }, 300);

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
    const classesHtml = result.classes_found && result.classes_found.length > 0 ? `
        <div class="result-classes">
            <h4>检测到的类别 (${result.classes_found.length}):</h4>
            <div class="classes-list">
                ${result.classes_found.map(cls => `<span class="class-tag">${cls}</span>`).join('')}
            </div>
        </div>
    ` : '';

    resultContent.innerHTML = `
        <div class="result-success">
            <div class="result-title">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                    <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                数据集生成成功！
            </div>
            <div class="result-stats">
                <div class="stat-item">
                    <div class="stat-label">处理图片</div>
                    <div class="stat-value">${result.total_images}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">生成切片</div>
                    <div class="stat-value">${result.crops_with_annotations}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">跳过空切片</div>
                    <div class="stat-value">${result.empty_crops_skipped}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">提取标注</div>
                    <div class="stat-value">${result.annotations_extracted}</div>
                </div>
            </div>
            ${classesHtml}
            <div style="margin-top: 16px; padding: 12px; background: rgba(0, 242, 254, 0.1); border-radius: 8px;">
                <p style="color: var(--text-secondary); font-size: 0.9rem;">
                    ✅ 数据集已保存为YOLO格式，包含 images/ 和 labels/ 目录
                </p>
            </div>
        </div>
    `;

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
                生成失败
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
