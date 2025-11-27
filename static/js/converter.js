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
const classManagementSection = document.getElementById('classManagementSection');
const classListContainer = document.getElementById('classListContainer');
const scanClassesBtn = document.getElementById('scanClassesBtn');
const loadClassesBtn = document.getElementById('loadClassesBtn');
const annotationsDir = document.getElementById('annotationsDir');
const imagesDir = document.getElementById('imagesDir');
const outputDir = document.getElementById('outputDir');
const classesFile = document.getElementById('classesFile');

// Update UI based on conversion type
conversionType.addEventListener('change', (e) => {
    const isVocToYolo = e.target.value === 'voc_to_yolo';

    // Update hints
    annotationsHint.textContent = isVocToYolo ? '(XML文件)' : '(TXT文件)';
    
    // Classes file is always optional now
    classesOptional.textContent = '(可选)';
    const classesFileInput = document.getElementById('classesFile');
    classesFileInput.removeAttribute('required');
    
    // Show class management section
    if (classManagementSection) {
        classManagementSection.style.display = 'block';
    }
});

// Scan classes button event
scanClassesBtn?.addEventListener('click', async function() {
    const annotationsDirVal = annotationsDir.value.trim();
    const isYoloToVoc = conversionType.value !== 'voc_to_yolo';
    
    if (!annotationsDirVal) {
        showToast('请先填写标注文件目录', 'error');
        annotationsDir.classList.add('error');
        return;
    }
    
    this.disabled = true;
    this.innerHTML = '<svg class="btn-icon" width="16" height="16" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="4" stroke="currentColor" stroke-width="2"><animateTransform attributeName="transform" attributeType="XML" type="rotate" from="0 10 10" to="360 10 10" dur="1s" repeatCount="indefinite"/></circle></svg>扫描中...';
    
    try {
        // Make API request to scan classes
        const response = await fetch('/api/scan-classes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                annotations_dir: annotationsDirVal,
                is_yolo_format: isYoloToVoc
            })
        });
        
        if (!response.ok) {
            throw new Error(`扫描失败: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success && data.classes && data.classes.length > 0) {
            displayClassList(data.classes);
            showToast(`成功扫描到 ${data.classes.length} 个类别`, 'success');
        } else {
            showToast('未找到类别信息，请检查路径', 'error');
        }
    } catch (error) {
        showToast(`扫描失败: ${error.message}`, 'error');
    } finally {
        this.disabled = false;
        this.innerHTML = '<svg width="16" height="16" viewBox="0 0 20 20" fill="none"><circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="2"/><circle cx="10" cy="10" r="3" stroke="currentColor" stroke-width="2"/></svg>扫描类别';
    }
});

// Load classes from file button event
loadClassesBtn?.addEventListener('click', async function() {
    if (!classesFile.value.trim()) {
        showToast('请先填写类别文件路径', 'error');
        classesFile.classList.add('error');
        return;
    }
    
    try {
        // Make API request to load classes from file
        const response = await fetch('/api/load-classes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                classes_file: classesFile.value.trim()
            })
        });
        
        if (!response.ok) {
            throw new Error(`加载失败: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.success && data.classes && data.classes.length > 0) {
            displayClassList(data.classes);
            showToast(`成功加载 ${data.classes.length} 个类别`, 'success');
        } else {
            showToast('加载类别文件失败，请检查路径', 'error');
        }
    } catch (error) {
        showToast(`加载失败: ${error.message}`, 'error');
    }
});

// Display class list
function displayClassList(classes) {
    if (!classListContainer) return;
    
    classListContainer.innerHTML = '';
    
    const classTable = document.createElement('div');
    classTable.className = 'class-table';
    
    // Table header
    const header = document.createElement('div');
    header.className = 'class-row header';
    header.innerHTML = `
        <div class="class-col index">索引</div>
        <div class="class-col name">类别名称</div>
        <div class="class-col count">计数</div>
        <div class="class-col keep">保留</div>
    `;
    classTable.appendChild(header);
    
    // Table rows
    classes.forEach((cls, index) => {
        const row = document.createElement('div');
        row.className = 'class-row';
        row.innerHTML = `
            <div class="class-col index">${index}</div>
            <div class="class-col name">
                <input type="text" class="class-name-input" value="${cls.name || `class_${index}`}" data-index="${index}">
            </div>
            <div class="class-col count">${cls.count || 0}</div>
            <div class="class-col keep">
                <input type="checkbox" class="class-keep-checkbox" checked data-index="${index}">
            </div>
        `;
        classTable.appendChild(row);
    });
    
    classListContainer.appendChild(classTable);
    
    // Add event listeners to inputs
    document.querySelectorAll('.class-name-input').forEach(input => {
        input.addEventListener('input', updateCustomClasses);
    });
    
    document.querySelectorAll('.class-keep-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', updateSelectedClasses);
    });
}

// Update custom classes hidden field
function updateCustomClasses() {
    const customClasses = [];
    document.querySelectorAll('.class-name-input').forEach(input => {
        customClasses[parseInt(input.dataset.index)] = input.value;
    });
    
    // Store in a hidden field
    let hiddenField = document.getElementById('customClasses');
    if (!hiddenField) {
        hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.id = 'customClasses';
        hiddenField.name = 'custom_classes';
        form.appendChild(hiddenField);
    }
    hiddenField.value = JSON.stringify(customClasses);
}

// Update selected classes hidden field
function updateSelectedClasses() {
    const selectedClasses = [];
    document.querySelectorAll('.class-keep-checkbox:checked').forEach(checkbox => {
        selectedClasses.push(parseInt(checkbox.dataset.index));
    });
    
    // Store in a hidden field
    let hiddenField = document.getElementById('selectedClasses');
    if (!hiddenField) {
        hiddenField = document.createElement('input');
        hiddenField.type = 'hidden';
        hiddenField.id = 'selectedClasses';
        hiddenField.name = 'selected_classes';
        form.appendChild(hiddenField);
    }
    hiddenField.value = JSON.stringify(selectedClasses);
}

// Input event handlers for auto-inference
[annotationsDir, imagesDir, outputDir, classesFile].forEach(field => {
    field?.addEventListener('input', function() {
        this.classList.remove('error');
        
        // Try to auto-infer other paths using smart input manager
        if (window.smartInputManager) {
            window.smartInputManager.tryInferPaths(field.id, this.value);
        }
    });
});

// Form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = {
        conversion_type: conversionType.value,
        annotations_dir: annotationsDir.value.trim(),
        images_dir: imagesDir.value.trim(),
        output_dir: outputDir.value.trim(),
        classes_file: classesFile.value.trim()
    };
    
    // Add custom classes and selected classes if available
    const customClassesField = document.getElementById('customClasses');
    const selectedClassesField = document.getElementById('selectedClasses');
    
    if (customClassesField && customClassesField.value) {
        formData.custom_classes = customClassesField.value;
    }
    
    if (selectedClassesField && selectedClassesField.value) {
        formData.selected_classes = selectedClassesField.value;
    }

    // Validate
    if (!formData.annotations_dir || !formData.images_dir || !formData.output_dir) {
        showToast('请填写所有必填字段', 'error');
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
    
    const selectedClassesHtml = result.selected_classes && result.selected_classes.length > 0 ? `
        <div class="result-selected-classes">
            <h4>已保留类别 (${result.selected_classes.length}):</h4>
            <div class="classes-list">
                ${result.selected_classes.map(cls => `<span class="class-tag selected">${cls}</span>`).join('')}
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
            ${selectedClassesHtml}
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

// Initialize smart input manager if available
if (window.smartInputManager) {
    window.smartInputManager.initialize({
        annotationsDir: annotationsDir,
        imagesDir: imagesDir,
        outputDir: outputDir,
        classesFile: classesFile,
        conversionType: conversionType
    });
}

// Auto-fill example paths on development (optional)
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    // Create test button
    const testBtn = document.createElement('button');
    testBtn.textContent = '填充测试路径';
    testBtn.className = 'secondary-btn';
    testBtn.style.marginLeft = '10px';
    testBtn.addEventListener('click', function() {
        const basePath = '/path/to/dataset';
        annotationsDir.value = conversionType.value === 'yolo_to_voc' ? `${basePath}/labels` : `${basePath}/Annotations`;
        imagesDir.value = `${basePath}/images`;
        outputDir.value = `${basePath}/output`;
        classesFile.value = `${basePath}/classes.txt`;
    });
    
    const actionsDiv = document.querySelector('.form-actions');
    if (actionsDiv) {
        actionsDiv.appendChild(testBtn);
    }
}

// Trigger initial state update
conversionType.dispatchEvent(new Event('change'));