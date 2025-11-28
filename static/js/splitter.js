// Splitter Tool Logic

// We wrap everything in a function that can be called when the tool is loaded
window.initSplitter = function (container) {
    // Helper to find element within this specific tool container
    const getEl = (id) => container.querySelector(`#${id}`);

    // DOM Elements
    const form = getEl('splitterForm');
    const trainRatio = getEl('trainRatio');
    const valRatio = getEl('valRatio');
    const testRatio = getEl('testRatio');
    const trainValue = getEl('trainValue');
    const valValue = getEl('valValue');
    const testValue = getEl('testValue');
    const trainPreview = getEl('trainPreview');
    const valPreview = getEl('valPreview');
    const testPreview = getEl('testPreview');
    const ratioWarning = getEl('ratioWarning');
    const submitBtn = getEl('submitBtn');
    const progressSection = getEl('progressSection');
    const progressFill = getEl('progressFill');
    const progressText = getEl('progressText');
    const resultSection = getEl('resultSection');
    const resultContent = getEl('resultContent');
    // Toast is global, usually appended to body, so we can use document.getElementById or create a local one?
    // The dashboard has a global toast system? Let's check. 
    // The dashboard.html doesn't have a toast container yet, but the original templates did.
    // We should probably use a scoped toast or a global one.
    // For now, let's look for a global toast or create one if missing.
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }

    let isAdjusting = false;

    // Update ratio displays
    function updateRatioDisplays() {
        const train = parseInt(trainRatio.value);
        const val = parseInt(valRatio.value);
        const test = parseInt(testRatio.value);

        trainValue.textContent = `${train}%`;
        valValue.textContent = `${val}%`;
        testValue.textContent = `${test}%`;

        // Check if sum is 100
        const sum = train + val + test;
        if (sum !== 100) {
            ratioWarning.style.display = 'block';
            ratioWarning.textContent = `⚠️ 当前总和: ${sum}% (需要100%)`;
        } else {
            ratioWarning.style.display = 'none';
        }

        // Update preview (placeholder counts)
        trainPreview.textContent = `${train}% 的标注图片`;
        valPreview.textContent = `${val}% 的标注图片`;
        testPreview.textContent = `${test}% 的标注图片`;
    }

    // Auto-adjust ratios to sum to 100
    function autoAdjustRatios(changedSlider) {
        if (isAdjusting) return;
        isAdjusting = true;

        const train = parseInt(trainRatio.value);
        const val = parseInt(valRatio.value);
        const test = parseInt(testRatio.value);
        const sum = train + val + test;

        if (sum !== 100) {
            const diff = sum - 100;

            // Distribute the difference to other sliders
            if (changedSlider === trainRatio) {
                // Adjust val and test proportionally
                const otherSum = val + test;
                if (otherSum > 0) {
                    const newVal = Math.max(0, Math.min(100, Math.round(val - diff * val / otherSum)));
                    const newTest = Math.max(0, 100 - train - newVal);
                    valRatio.value = newVal;
                    testRatio.value = newTest;
                } else {
                    valRatio.value = Math.max(0, 100 - train);
                    testRatio.value = 0;
                }
            } else if (changedSlider === valRatio) {
                // Adjust train and test proportionally
                const otherSum = train + test;
                if (otherSum > 0) {
                    const newTrain = Math.max(0, Math.min(100, Math.round(train - diff * train / otherSum)));
                    const newTest = Math.max(0, 100 - newTrain - val);
                    trainRatio.value = newTrain;
                    testRatio.value = newTest;
                } else {
                    trainRatio.value = Math.max(0, 100 - val);
                    testRatio.value = 0;
                }
            } else if (changedSlider === testRatio) {
                // Adjust train and val proportionally
                const otherSum = train + val;
                if (otherSum > 0) {
                    const newTrain = Math.max(0, Math.min(100, Math.round(train - diff * train / otherSum)));
                    const newVal = Math.max(0, 100 - newTrain - test);
                    trainRatio.value = newTrain;
                    valRatio.value = newVal;
                } else {
                    trainRatio.value = Math.max(0, 100 - test);
                    valRatio.value = 0;
                }
            }
        }

        updateRatioDisplays();
        isAdjusting = false;
    }

    // Event listeners for ratio sliders
    trainRatio.addEventListener('input', () => {
        autoAdjustRatios(trainRatio);
    });

    valRatio.addEventListener('input', () => {
        autoAdjustRatios(valRatio);
    });

    testRatio.addEventListener('input', () => {
        autoAdjustRatios(testRatio);
    });

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Validate ratios
        const train = parseInt(trainRatio.value);
        const val = parseInt(valRatio.value);
        const test = parseInt(testRatio.value);

        if (train + val + test !== 100) {
            showToast('比例总和必须为100%', 'error');
            return;
        }

        // Get form data
        const formData = {
            format: getEl('format').value,
            images_dir: getEl('imagesDir').value.trim(), // Fixed ID mismatch inputDir -> imagesDir
            annotations_dir: getEl('annotationsDir').value.trim(),
            output_dir: getEl('outputDir').value.trim(),
            train_ratio: train,
            val_ratio: val,
            test_ratio: test,
            use_background: getEl('useBackground').checked,
            random_seed: parseInt(getEl('randomSeed').value)
        };

        // Validate
        if (!formData.images_dir || !formData.output_dir) {
            showToast('请填写所有必填字段', 'error');
            return;
        }

        // Disable form
        setFormEnabled(false);

        // Show progress
        showProgress();

        try {
            // Send request
            const response = await fetch('/api/split', {
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
                showToast('数据集划分成功！', 'success');
            } else {
                showErrorResult(result);
                showToast('划分失败：' + result.error, 'error');
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
            submitBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">划分中...</span>';
        } else {
            submitBtn.innerHTML = `
                <span class="btn-text">开始划分</span>
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
        progressText.textContent = '正在划分数据集...';

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
        const outputStructure = [];
        if (result.output_structure.train) outputStructure.push('train/');
        if (result.output_structure.val) outputStructure.push('val/');
        if (result.output_structure.test) outputStructure.push('test/');
        if (result.output_structure.background) outputStructure.push('background/');

        resultContent.innerHTML = `
            <div class="result-success">
                <div class="result-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                        <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    数据集划分成功！
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">总图片数</div>
                        <div class="stat-value">${result.total_images}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">有标注</div>
                        <div class="stat-value">${result.labeled_images}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">无标注</div>
                        <div class="stat-value">${result.unlabeled_images}</div>
                    </div>
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">训练集</div>
                        <div class="stat-value">${result.train_count}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">验证集</div>
                        <div class="stat-value">${result.val_count}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">测试集</div>
                        <div class="stat-value">${result.test_count}</div>
                    </div>
                    ${result.background_count > 0 ? `
                    <div class="stat-item">
                        <div class="stat-label">背景</div>
                        <div class="stat-value">${result.background_count}</div>
                    </div>
                    ` : ''}
                </div>
                <div style="margin-top: 16px; padding: 12px; background: rgba(0, 242, 254, 0.1); border-radius: 8px;">
                    <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 8px;">
                        ✅ 输出目录结构：
                    </p>
                    <div style="font-family: monospace; font-size: 0.85rem; color: var(--text-primary);">
                        ${outputStructure.map(dir => `📁 ${dir}`).join('<br>')}
                    </div>
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
                    划分失败
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

    // Initialize
    updateRatioDisplays();
};

// If loaded directly (legacy mode), auto-init on document body
if (document.getElementById('splitterForm') && !window.dashboardMode) {
    window.initSplitter(document);
}
