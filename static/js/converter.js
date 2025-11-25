// DOM Elements
const form = document.getElementById('conversionForm');
const conversionType = document.getElementById('conversionType');
const annotationsHint = document.getElementById('annotationsHint');
const classesOptional = document.getElementById('classesOptional');
const submitBtn = document.getElementById('submitBtn');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const resultSection = document.getElementById('resultSection');
const resultContent = document.getElementById('resultContent');
const toast = document.getElementById('toast');

// Update UI based on conversion type
conversionType.addEventListener('change', (e) => {
    const isVocToYolo = e.target.value === 'voc_to_yolo';

    // Update hints
    annotationsHint.textContent = isVocToYolo ? '(XML文件)' : '(TXT文件)';
    classesOptional.textContent = isVocToYolo ? '(可选)' : '(必需)';

    // Update required attribute
    const classesFileInput = document.getElementById('classesFile');
    if (isVocToYolo) {
        classesFileInput.removeAttribute('required');
    } else {
        classesFileInput.setAttribute('required', 'required');
    }
});

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = {
        conversion_type: document.getElementById('conversionType').value,
        annotations_dir: document.getElementById('annotationsDir').value.trim(),
        images_dir: document.getElementById('imagesDir').value.trim(),
        output_dir: document.getElementById('outputDir').value.trim(),
        classes_file: document.getElementById('classesFile').value.trim()
    };

    // Validate
    if (!formData.annotations_dir || !formData.images_dir || !formData.output_dir) {
        showToast('请填写所有必填字段', 'error');
        return;
    }

    if (formData.conversion_type === 'yolo_to_voc' && !formData.classes_file) {
        showToast('YOLO转VOC需要提供classes.txt文件', 'error');
        return;
    }

    // Disable form
    setFormEnabled(false);

    // Show progress
    showProgress();

    try {
        // Send request
        const response = await fetch('/api/convert', {
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
            showToast('转换成功完成！', 'success');
        } else {
            showErrorResult(result);
            showToast('转换失败：' + result.error, 'error');
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
        submitBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">转换中...</span>';
    } else {
        submitBtn.innerHTML = `
            <span class="btn-text">开始转换</span>
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
    progressText.textContent = '正在转换...';

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
    const classesHtml = result.classes && result.classes.length > 0 ? `
        <div class="result-classes">
            <h4>检测到的类别 (${result.classes.length}):</h4>
            <div class="classes-list">
                ${result.classes.map(cls => `<span class="class-tag">${cls}</span>`).join('')}
            </div>
        </div>
    ` : '';

    const errorsHtml = result.errors && result.errors.length > 0 ? `
        <div class="error-list">
            <h4 style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 8px;">
                警告 (${result.errors.length}):
            </h4>
            ${result.errors.slice(0, 10).map(err => `<div class="error-item">${err}</div>`).join('')}
            ${result.errors.length > 10 ? `<div class="error-item">...还有 ${result.errors.length - 10} 个警告</div>` : ''}
        </div>
    ` : '';

    resultContent.innerHTML = `
        <div class="result-success">
            <div class="result-title">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                    <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                转换成功完成！
            </div>
            <div class="result-stats">
                <div class="stat-item">
                    <div class="stat-label">成功转换</div>
                    <div class="stat-value">${result.converted}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">跳过文件</div>
                    <div class="stat-value">${result.skipped}</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">总文件数</div>
                    <div class="stat-value">${result.total}</div>
                </div>
            </div>
            ${classesHtml}
            ${errorsHtml}
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
                转换失败
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

// Auto-fill example paths on development (optional)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // You can uncomment these for testing
    // document.getElementById('annotationsDir').value = '/path/to/annotations';
    // document.getElementById('imagesDir').value = '/path/to/images';
    // document.getElementById('outputDir').value = '/path/to/output';
}
