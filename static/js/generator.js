// Generator Tool Logic

window.initGenerator = function (container) {
    const getEl = (id) => container.querySelector(`#${id}`);

    // DOM Elements
    const form = getEl('generatorForm');
    const detectBtn = getEl('detectBtn');
    const submitBtn = getEl('submitBtn');
    const classSelectionGroup = getEl('classSelectionGroup');
    const outputFormatGroup = getEl('outputFormatGroup');
    const classCheckboxes = getEl('classCheckboxes');
    const annotationFormatSelect = getEl('annotationFormat');
    const progressSection = getEl('progressSection');
    const progressFill = getEl('progressFill');
    const progressText = getEl('progressText');
    const resultSection = getEl('resultSection');
    const resultContent = getEl('resultContent');

    // Preview elements
    const windowWidthInput = getEl('windowWidth');
    const windowHeightInput = getEl('windowHeight');
    const strideXInput = getEl('strideX');
    const strideYInput = getEl('strideY');
    const overlapThresholdInput = getEl('overlapThreshold');
    const thresholdValue = getEl('thresholdValue');
    const previewWindow = getEl('previewWindow');
    const previewStride = getEl('previewStride');
    const previewThreshold = getEl('previewThreshold');

    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }

    let detectedClasses = [];

    // Update preview info
    function updatePreview() {
        const windowW = windowWidthInput.value;
        const windowH = windowHeightInput.value;
        const sx = strideXInput.value;
        const sy = strideYInput.value;
        const threshold = overlapThresholdInput.value;

        previewWindow.textContent = `${windowW} × ${windowH}`;
        previewStride.textContent = `${sx} × ${sy}`;
        previewThreshold.textContent = `${threshold}%`;
        thresholdValue.textContent = `${threshold}%`;
    }

    // Event listeners for preview updates
    [windowWidthInput, windowHeightInput, strideXInput, strideYInput, overlapThresholdInput].forEach(input => {
        input.addEventListener('input', updatePreview);
    });

    // Detect classes
    detectBtn.addEventListener('click', async () => {
        const annotationsDir = getEl('annotationsDir').value.trim();

        if (!annotationsDir) {
            showToast('请先输入标注目录', 'error');
            return;
        }

        detectBtn.disabled = true;
        detectBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">检测中...</span>';

        try {
            const response = await fetch('/api/detect-classes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ annotations_dir: annotationsDir })
            });

            const result = await response.json();

            if (result.success) {
                detectedClasses = result.classes;
                annotationFormatSelect.value = result.format;
                annotationFormatSelect.disabled = true; // Lock format after detection

                populateClassCheckboxes(result.classes);
                classSelectionGroup.style.display = 'block';
                outputFormatGroup.style.display = 'block';
                submitBtn.style.display = 'block';
                showToast(`检测到 ${result.classes.length} 个类别 (格式: ${result.format.toUpperCase()})`, 'success');
            } else {
                showToast('检测失败: ' + result.error, 'error');
            }
        } catch (error) {
            showToast('请求失败: ' + error.message, 'error');
        } finally {
            detectBtn.disabled = false;
            detectBtn.innerHTML = '<span class="btn-text">检测类别</span>';
        }
    });

    // Populate class checkboxes
    function populateClassCheckboxes(classes) {
        classCheckboxes.innerHTML = '';

        // Add "Select All" checkbox
        const selectAllDiv = document.createElement('div');
        selectAllDiv.innerHTML = `
            <label class="checkbox-label">
                <input type="checkbox" id="selectAll" checked>
                <span style="font-weight: 600;">全选</span>
            </label>
        `;
        classCheckboxes.appendChild(selectAllDiv);

        const selectAllCheckbox = selectAllDiv.querySelector('#selectAll');
        selectAllCheckbox.addEventListener('change', (e) => {
            const checkboxes = classCheckboxes.querySelectorAll('input[type="checkbox"]:not(#selectAll)');
            checkboxes.forEach(cb => cb.checked = e.target.checked);
        });

        // Add individual class checkboxes
        classes.forEach((cls, index) => {
            const div = document.createElement('div');
            div.innerHTML = `
                <label class="checkbox-label">
                    <input type="checkbox" class="class-checkbox" value="${cls}" checked>
                    <span>${cls}</span>
                </label>
            `;
            classCheckboxes.appendChild(div);
        });
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const selectedClasses = Array.from(
            classCheckboxes.querySelectorAll('.class-checkbox:checked')
        ).map(cb => cb.value);

        if (selectedClasses.length === 0) {
            showToast('请至少选择一个类别', 'error');
            return;
        }

        const outputFormat = container.querySelector('input[name="outputFormat"]:checked').value;
        const annotationFormat = annotationFormatSelect.value;

        const formData = {
            annotation_format: annotationFormat,
            images_dir: getEl('imagesDir').value.trim(),
            annotations_dir: getEl('annotationsDir').value.trim(),
            output_dir: getEl('outputDir').value.trim(),
            selected_classes: selectedClasses,
            output_format: outputFormat,
            window_width: parseInt(windowWidthInput.value),
            window_height: parseInt(windowHeightInput.value),
            stride_x: parseInt(strideXInput.value),
            stride_y: parseInt(strideYInput.value),
            overlap_threshold: parseInt(overlapThresholdInput.value)
        };

        if (!formData.images_dir || !formData.annotations_dir || !formData.output_dir) {
            showToast('请填写所有必填字段', 'error');
            return;
        }

        setFormEnabled(false);
        showProgress();

        try {
            const response = await fetch('/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            hideProgress();

            if (result.success) {
                showSuccessResult(result);
                showToast('数据集生成成功！', 'success');
            } else {
                showErrorResult(result);
                showToast('生成失败: ' + result.error, 'error');
            }
        } catch (error) {
            hideProgress();
            showErrorResult({ error: error.message });
            showToast('请求失败: ' + error.message, 'error');
        } finally {
            setFormEnabled(true);
        }
    });

    function setFormEnabled(enabled) {
        const inputs = form.querySelectorAll('input, button, select');
        inputs.forEach(input => input.disabled = !enabled);

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

    function showProgress() {
        resultSection.style.display = 'none';
        progressSection.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = '正在生成数据集...';

        let progress = 0;
        const interval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 90) {
                progress = 90;
                clearInterval(interval);
            }
            progressFill.style.width = progress + '%';
        }, 200);

        progressSection.dataset.intervalId = interval;
    }

    function hideProgress() {
        const intervalId = progressSection.dataset.intervalId;
        if (intervalId) clearInterval(parseInt(intervalId));

        progressFill.style.width = '100%';
        setTimeout(() => {
            progressSection.style.display = 'none';
        }, 500);
    }

    function showSuccessResult(result) {
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
                        <div class="stat-value">${result.images_processed}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">生成窗口</div>
                        <div class="stat-value">${result.windows_generated}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">有效标注</div>
                        <div class="stat-value">${result.annotations_kept}</div>
                    </div>
                </div>
                ${result.errors && result.errors.length > 0 ? `
                <div style="margin-top: 16px; padding: 12px; background: rgba(245, 87, 108, 0.1); border-radius: 8px;">
                    <p style="color: #f5576c; font-size: 0.9rem; margin-bottom: 8px;">
                        ⚠️ 部分文件处理失败：
                    </p>
                    <div style="font-family: monospace; font-size: 0.85rem; color: var(--text-primary); max-height: 100px; overflow-y: auto;">
                        ${result.errors.slice(0, 5).join('<br>')}
                        ${result.errors.length > 5 ? '<br>...' : ''}
                    </div>
                </div>
                ` : ''}
            </div>
        `;

        resultSection.style.display = 'block';
        resultSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

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

    function showToast(message, type = 'success') {
        toast.textContent = message;
        toast.className = `toast ${type} show`;
        setTimeout(() => toast.classList.remove('show'), 4000);
    }

    // Smart inputs
    const imagesInput = getEl('imagesDir');
    const annotationsInput = getEl('annotationsDir');
    const outputInput = getEl('outputDir');

    imagesInput.addEventListener('change', () => {
        const path = imagesInput.value.trim();
        if (path && !annotationsInput.value) {
            if (path.endsWith('/images') || path.endsWith('\\images')) {
                const parent = path.substring(0, path.length - 7);
                annotationsInput.value = parent + '/labels';
                outputInput.value = parent + '/generated_dataset';
            }
        }
    });

    // Initialize preview
    updatePreview();
};

// If loaded directly (legacy mode), auto-init on document body
if (document.getElementById('generatorForm') && !window.dashboardMode) {
    window.initGenerator(document);
}
