// Deduplicator Tool Logic

window.initDeduplicator = function (container) {
    const getEl = (id) => container.querySelector(`#${id}`);

    // DOM Elements
    const form = getEl('deduplicatorForm');
    const detectionMode = getEl('detectionMode');
    const hashAlgorithm = getEl('hashAlgorithm');
    const similarityThreshold = getEl('similarityThreshold');
    const thresholdValue = getEl('thresholdValue');
    const hashAlgorithmGroup = getEl('hashAlgorithmGroup');
    const thresholdGroup = getEl('thresholdGroup');
    const scanBtn = getEl('scanBtn');
    const removeBtn = getEl('removeBtn');
    const progressSection = getEl('progressSection');
    const progressFill = getEl('progressFill');
    const progressText = getEl('progressText');
    const resultSection = getEl('resultSection');
    const resultContent = getEl('resultContent');
    const duplicatesPreview = getEl('duplicatesPreview');
    const duplicatesContainer = getEl('duplicatesContainer');

    // Global toast fallback
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }

    let currentDuplicates = null;

    // Update threshold display
    similarityThreshold.addEventListener('input', () => {
        thresholdValue.textContent = similarityThreshold.value;
    });

    // Toggle algorithm selection based on detection mode
    detectionMode.addEventListener('change', () => {
        const isPerceptual = detectionMode.value === 'perceptual';
        hashAlgorithmGroup.style.display = isPerceptual ? 'block' : 'none';
        thresholdGroup.style.display = isPerceptual ? 'block' : 'none';
    });

    // Scan for duplicates
    scanBtn.addEventListener('click', async () => {
        const folderPath = getEl('folderPath').value.trim();

        if (!folderPath) {
            showToast('请输入图像文件夹路径', 'error');
            return;
        }

        // Disable buttons
        setButtonsEnabled(false);

        // Show progress
        showProgress('正在扫描重复图像...');

        const requestData = {
            folder_path: folderPath,
            hash_algorithm: hashAlgorithm.value,
            use_md5: detectionMode.value === 'exact',
            similarity_threshold: parseInt(similarityThreshold.value)
        };

        try {
            const response = await fetch('/api/find-duplicates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            // Hide progress
            hideProgress();

            if (result.success) {
                currentDuplicates = result.report;
                showScanResult(result.report);

                if (result.report.duplicate_groups > 0) {
                    removeBtn.disabled = false;
                    showToast(`发现 ${result.report.duplicate_groups} 组重复图像`, 'success');
                } else {
                    removeBtn.disabled = true;
                    showToast('未发现重复图像', 'info');
                }
            } else {
                showErrorResult(result.error);
                showToast('扫描失败：' + result.error, 'error');
                removeBtn.disabled = true;
            }

        } catch (error) {
            hideProgress();
            showErrorResult(error.message);
            showToast('请求失败：' + error.message, 'error');
            removeBtn.disabled = true;
        } finally {
            setButtonsEnabled(true);
        }
    });

    // Remove duplicates
    removeBtn.addEventListener('click', async () => {
        if (!currentDuplicates || currentDuplicates.duplicate_groups === 0) {
            showToast('没有可删除的重复项', 'error');
            return;
        }

        const confirmMsg = `确定要删除 ${currentDuplicates.total_duplicate_files} 个重复文件吗？\n` +
            `将释放约 ${currentDuplicates.potential_space_saved_mb} MB 空间`;

        if (!confirm(confirmMsg)) {
            return;
        }

        const folderPath = getEl('folderPath').value.trim();

        // Disable buttons
        setButtonsEnabled(false);

        // Show progress
        showProgress('正在删除重复图像...');

        const requestData = {
            folder_path: folderPath,
            hash_algorithm: hashAlgorithm.value,
            use_md5: detectionMode.value === 'exact',
            similarity_threshold: parseInt(similarityThreshold.value),
            keep_strategy: getEl('keepStrategy').value,
            dry_run: false
        };

        try {
            const response = await fetch('/api/remove-duplicates', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            const result = await response.json();

            // Hide progress
            hideProgress();

            if (result.success) {
                showRemoveResult(result);
                showToast(`成功删除 ${result.removed_count} 个文件，释放 ${result.space_saved_mb} MB`, 'success');

                // Reset state
                currentDuplicates = null;
                removeBtn.disabled = true;
                duplicatesPreview.style.display = 'none';
            } else {
                showErrorResult(result.error);
                showToast('删除失败：' + result.error, 'error');
            }

        } catch (error) {
            hideProgress();
            showErrorResult(error.message);
            showToast('请求失败：' + error.message, 'error');
        } finally {
            setButtonsEnabled(true);
        }
    });

    // Enable/disable buttons
    function setButtonsEnabled(enabled) {
        scanBtn.disabled = !enabled;
        if (!enabled || !currentDuplicates || currentDuplicates.duplicate_groups === 0) {
            removeBtn.disabled = true;
        } else {
            removeBtn.disabled = !enabled;
        }

        const inputs = form.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.disabled = !enabled;
        });

        if (!enabled) {
            scanBtn.innerHTML = '<div class="spinner"></div><span class="btn-text">扫描中...</span>';
        } else {
            scanBtn.innerHTML = `
                <span class="btn-text">扫描重复项</span>
                <svg class="btn-icon" width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <circle cx="9" cy="9" r="6" stroke="currentColor" stroke-width="2" />
                    <path d="M14 14l4 4" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
                </svg>
            `;
        }
    }

    // Show progress
    function showProgress(message) {
        resultSection.style.display = 'none';
        duplicatesPreview.style.display = 'none';
        progressSection.style.display = 'block';
        progressFill.style.width = '0%';
        progressText.textContent = message;

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

    // Show scan result
    function showScanResult(report) {
        if (report.duplicate_groups === 0) {
            resultContent.innerHTML = `
                <div class="result-success">
                    <div class="result-title">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                            <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                            <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                        未发现重复图像
                    </div>
                    <p style="color: var(--text-secondary); margin-top: 12px;">
                        该文件夹中没有重复的图像文件 ✨
                    </p>
                </div>
            `;
            resultSection.style.display = 'block';
            duplicatesPreview.style.display = 'none';
            return;
        }

        resultContent.innerHTML = `
            <div class="result-success">
                <div class="result-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                        <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    扫描完成
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">重复组数</div>
                        <div class="stat-value">${report.duplicate_groups}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">重复文件</div>
                        <div class="stat-value">${report.total_duplicate_files}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">可释放空间</div>
                        <div class="stat-value">${report.potential_space_saved_mb} MB</div>
                    </div>
                </div>
                <div style="margin-top: 16px; padding: 12px; background: rgba(255, 152, 0, 0.1); border-radius: 8px;">
                    <p style="color: var(--text-secondary); font-size: 0.9rem;">
                        ⚠️ 建议：查看下方重复组预览，确认无误后再点击"删除重复项"按钮
                    </p>
                </div>
            </div>
        `;

        resultSection.style.display = 'block';

        // Show duplicates preview
        showDuplicatesPreview(report.groups);
    }

    // Show duplicates preview
    function showDuplicatesPreview(groups) {
        if (!groups || groups.length === 0) {
            duplicatesPreview.style.display = 'none';
            return;
        }

        // Show up to 10 groups
        const displayGroups = groups.slice(0, 10);
        const hasMore = groups.length > 10;

        duplicatesContainer.innerHTML = displayGroups.map((group, index) => {
            const files = group.files.map(file => {
                const filename = file.path.split('/').pop();
                return `
                    <div class="duplicate-file">
                        <span class="file-name" title="${file.path}">${filename}</span>
                        <span class="file-size">${file.size_mb} MB</span>
                    </div>
                `;
            }).join('');

            return `
                <div class="duplicate-group">
                    <div class="group-header">
                        <span class="group-title">🔗 重复组 ${index + 1}</span>
                        <span class="group-count">${group.count} 个文件</span>
                    </div>
                    <div class="group-files">
                        ${files}
                    </div>
                </div>
            `;
        }).join('');

        if (hasMore) {
            duplicatesContainer.innerHTML += `
                <div style="text-align: center; padding: 16px; color: var(--text-secondary);">
                    ... 还有 ${groups.length - 10} 组未显示
                </div>
            `;
        }

        duplicatesPreview.style.display = 'block';
    }

    // Show remove result
    function showRemoveResult(result) {
        resultContent.innerHTML = `
            <div class="result-success">
                <div class="result-title">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                        <circle cx="12" cy="12" r="10" stroke="#00f2fe" stroke-width="2"/>
                        <path d="M8 12l2 2 4-4" stroke="#00f2fe" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    删除完成
                </div>
                <div class="result-stats">
                    <div class="stat-item">
                        <div class="stat-label">已删除</div>
                        <div class="stat-value">${result.removed_count}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">已保留</div>
                        <div class="stat-value">${result.kept_count}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">释放空间</div>
                        <div class="stat-value">${result.space_saved_mb} MB</div>
                    </div>
                </div>
                <div style="margin-top: 16px; padding: 12px; background: rgba(0, 242, 254, 0.1); border-radius: 8px;">
                    <p style="color: var(--text-secondary); font-size: 0.9rem;">
                        ✅ 成功释放 ${result.space_saved_mb} MB 存储空间
                    </p>
                </div>
            </div>
        `;

        resultSection.style.display = 'block';
    }

    // Show error result
    function showErrorResult(errorMsg) {
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
                    ${errorMsg || '未知错误'}
                </p>
            </div>
        `;

        resultSection.style.display = 'block';
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
    thresholdValue.textContent = similarityThreshold.value;
    hashAlgorithmGroup.style.display = 'block';
    thresholdGroup.style.display = 'block';
};

// If loaded directly (legacy mode), auto-init on document body
if (document.getElementById('deduplicatorForm') && !window.dashboardMode) {
    window.initDeduplicator(document);
}
