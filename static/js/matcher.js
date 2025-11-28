// Matcher Tool Logic

window.initMatcher = function (container) {
    // Helper to find element within this specific tool container
    const getEl = (id) => container.querySelector(`#${id}`);

    // DOM Elements
    const form = getEl('matcherForm');
    const submitBtn = getEl('submitBtn');
    const progressSection = getEl('progressSection');
    const progressFill = getEl('progressFill');
    const progressText = getEl('progressText');
    const resultSection = getEl('resultSection');
    const resultContent = getEl('resultContent');

    // Toast
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }

    // Form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get form data
        const formData = {
            source_dir: getEl('sourceDir').value.trim(),
            reference_dir: getEl('referenceDir').value.trim(),
            output_dir: getEl('outputDir').value.trim(),
            dry_run: getEl('dryRun').checked
        };

        // Validate
        if (!formData.source_dir || !formData.reference_dir || !formData.output_dir) {
            showToast('请填写所有必填字段', 'error');
            return;
        }

        // Disable form
        setFormEnabled(false);

        // Show progress
        showProgress();

        try {
            // Send request
            const response = await fetch('/api/match', {
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
                showToast(formData.dry_run ? '模拟运行完成' : '匹配复制成功！', 'success');
            } else {
                showErrorResult(result);
                showToast('操作失败：' + result.error, 'error');
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
        const inputs = form.querySelectorAll('input, button');
        inputs.forEach(input => {
            input.disabled = !enabled;
        });

        if (!enabled) {
            submitBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">处理中...</span>';
        } else {
            submitBtn.innerHTML = `
                <span class="btn-text">开始匹配</span>
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
        progressText.textContent = '正在扫描匹配...';

        // Simulate progress
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
        resultContent.innerHTML = `
            <div class="result-success">
                <div class="result-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                        <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    ${result.dry_run ? '模拟运行完成' : '匹配复制成功！'}
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">源文件总数</div>
                        <div class="stat-value">${result.total_scanned}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">参考文件数</div>
                        <div class="stat-value">${result.reference_count}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">匹配成功</div>
                        <div class="stat-value">${result.matched_count}</div>
                    </div>
                </div>
                ${result.errors.length > 0 ? `
                <div style="margin-top: 16px; padding: 12px; background: rgba(245, 87, 108, 0.1); border-radius: 8px;">
                    <p style="color: #f5576c; font-size: 0.9rem; margin-bottom: 8px;">
                        ⚠️ 部分文件复制失败：
                    </p>
                    <div style="font-family: monospace; font-size: 0.85rem; color: var(--text-primary); max-height: 100px; overflow-y: auto;">
                        ${result.errors.join('<br>')}
                    </div>
                </div>
                ` : ''}
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
                    操作失败
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

    // Auto-inference logic (Smart Inputs)
    // We can hook into the inputs to provide smart suggestions
    const sourceInput = getEl('sourceDir');
    const referenceInput = getEl('referenceDir');
    const outputInput = getEl('outputDir');

    // If user pastes a path into source, try to guess reference and output
    sourceInput.addEventListener('change', () => {
        const path = sourceInput.value.trim();
        if (path && !referenceInput.value) {
            // Simple heuristic: if path ends with 'images', suggest 'labels'
            if (path.endsWith('/images') || path.endsWith('\\images')) {
                const parent = path.substring(0, path.length - 7);
                referenceInput.value = parent + '/labels';
                outputInput.value = parent + '/matched_images';
            }
        }
    });
};

// If loaded directly (legacy mode), auto-init on document body
if (document.getElementById('matcherForm') && !window.dashboardMode) {
    window.initMatcher(document);
}
