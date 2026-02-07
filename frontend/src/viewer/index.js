const pathInput = document.getElementById('path-input');
const loadBtn = document.getElementById('load-btn');
const settingsBtn = document.getElementById('settings-btn');
const clearCacheBtn = document.getElementById('clear-cache-btn');
const gridView = document.getElementById('grid-view');
const singleView = document.getElementById('single-view');
const singleImage = document.getElementById('single-image');
const closeBtn = document.getElementById('close-btn');
const prevBtn = document.getElementById('prev-btn');
const nextBtn = document.getElementById('next-btn');
const imageInfo = document.getElementById('image-info');
const settingsModal = document.getElementById('settings-modal');
const saveSettingsBtn = document.getElementById('save-settings-btn');
const cancelSettingsBtn = document.getElementById('cancel-settings-btn');
const addClassBtn = document.getElementById('add-class-btn');
const classList = document.getElementById('class-list');
const gridSizeSlider = document.getElementById('grid-size-slider');
const gridSizeValue = document.getElementById('grid-size-value');
const gridGapSlider = document.getElementById('grid-gap-slider');
const gridGapValue = document.getElementById('grid-gap-value');
const themeSelect = document.getElementById('theme-select');
const brightnessSlider = document.getElementById('brightness-slider');
const brightnessValue = document.getElementById('brightness-value');
const resetBrightnessBtn = document.getElementById('reset-brightness-btn');

let currentImages = [];
let currentPath = '';
let currentIndex = -1;
let selectedGridIndex = -1; // Track selected image in grid mode
let useThumbnails = false; // Default to original images
let currentSortMode = 'name_desc'; // Default sort mode
let scrollMode = 'center'; // 'smart' or 'center'
let scrollTopBeforeSingleView = 0; // Restore grid scroll when closing single view

// Zoom state variables
let zoomScale = 1.0;           // Current zoom level
const MIN_ZOOM = 0.01;         // Minimum zoom (1%)
const MAX_ZOOM = 20.0;         // Maximum zoom (2000%)
const ZOOM_STEP = 0.3;         // Zoom increment per wheel tick (faster)

// Pan state variables
let panX = 0;                  // Horizontal pan offset
let panY = 0;                  // Vertical pan offset
let isDragging = false;        // Is user currently dragging
let dragStartX = 0;            // Mouse X position when drag started
let dragStartY = 0;            // Mouse Y position when drag started
let dragStartPanX = 0;         // Pan X when drag started
let dragStartPanY = 0;         // Pan Y when drag started

let config = {
    shortcuts: {
        next: 'ArrowDown',
        prev: 'ArrowUp',
        clear: 'c',
        classes: { '1': '1', '2': '2' }
    }
};
let classifications = {}; // filename -> class_name

const normalizePath = (value) => (value || '').replace(/\\/g, '/');
const trimTrailingSlash = (value) => {
    if (!value) return '';
    if (value === '/') return '/';
    return value.replace(/\/+$/, '');
};
const unwrapPayload = (payload) => {
    if (payload && typeof payload === 'object' && payload.data && typeof payload.data === 'object') {
        return { ...payload.data, ...payload };
    }
    return payload;
};
const joinPath = (...parts) => {
    const cleaned = parts
        .filter(Boolean)
        .map((part, index) => {
            let normalized = normalizePath(part);
            if (index > 0) {
                normalized = normalized.replace(/^\/+/, '');
            }
            return trimTrailingSlash(normalized);
        });
    return cleaned.join('/');
};

// Preload cache for single view images
const preloadCache = new Map();

// Load path from URL hash or default
window.addEventListener('load', async () => {
    pathInput.focus();
    await loadConfig();
    // Initialize grid size from localStorage or default
    const savedSize = localStorage.getItem('gridSize') || '150';
    gridSizeSlider.value = savedSize;
    updateGridSize(savedSize);

    // Initialize grid gap from localStorage or default
    const savedGap = localStorage.getItem('gridGap') || '10';
    gridGapSlider.value = savedGap;
    updateGridGap(savedGap);

    // Initialize theme (default: bilibili)
    const savedTheme = localStorage.getItem('theme') || 'bilibili';
    applyTheme(savedTheme);

    // Initialize thumbnail toggle from localStorage (default: false = original images)
    const savedUseThumbnails = localStorage.getItem('useThumbnails');
    useThumbnails = savedUseThumbnails === 'true';
    document.getElementById('use-thumbnails-toggle').checked = useThumbnails;

    // Initialize sort mode from localStorage
    currentSortMode = localStorage.getItem('sortMode') || 'name_desc';
    document.getElementById('sort-select').value = currentSortMode;

    // Initialize scroll mode from localStorage
    scrollMode = localStorage.getItem('scrollMode') || 'center';
    document.getElementById('scroll-mode-select').value = scrollMode;
});

function applyTheme(theme) {
    document.body.className = ''; // Clear existing themes
    if (theme !== 'nomacs') {
        document.body.classList.add(`theme-${theme}`);
    }
    // Update select if it exists (might be called from outside settings)
    if (themeSelect) themeSelect.value = theme;
}

async function loadConfig() {
    try {
        const res = await fetch('/api/viewer/config');
        if (res.ok) {
            const raw = await res.json();
            config = unwrapPayload(raw);
        }
    } catch (e) {
        console.error("Failed to load config", e);
    }
}

async function loadImages() {
    const rawPath = pathInput.value.trim();
    const normalizedPath = trimTrailingSlash(normalizePath(rawPath));
    if (!normalizedPath) return;

    try {
        const response = await fetch(`/api/viewer/images?path=${encodeURIComponent(normalizedPath)}&sort=${currentSortMode}`);
        if (!response.ok) {
            const err = await response.json();
            alert(err.error || err.message || '加载图片失败');
            return;
        }
        const raw = await response.json();
        const data = unwrapPayload(raw);
        currentImages = data.images;
        currentPath = trimTrailingSlash(normalizePath(data.path || normalizedPath));
        pathInput.value = currentPath;
        // Load historical classifications from backend
        classifications = data.classifications || {};
        renderGrid();
        updateClassificationStats();
        // 加载新文件夹时重置滚动位置到顶部
        mainContainer.scrollTop = 0;
    } catch (error) {
        console.error('Error loading images:', error);
        alert('加载图片失败');
    }
}

function renderGrid() {
    gridView.innerHTML = '';
    selectedGridIndex = -1; // Reset selection when re-rendering

    // Create intersection observer for lazy loading thumbnails
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                if (img.dataset.src) {
                    img.src = img.dataset.src;
                    img.removeAttribute('data-src');
                    observer.unobserve(img);
                }
            }
        });
    }, {
        rootMargin: '200px' // Start loading 200px before entering viewport
    });

    currentImages.forEach((filename, index) => {
        const container = document.createElement('div');
        container.className = 'thumbnail-container';
        container.dataset.filename = filename;
        container.dataset.index = String(index);

        const img = document.createElement('img');
        const fullPath = joinPath(currentPath, filename);
        // Use thumbnail or original image based on user preference
        const imageUrl = useThumbnails
            ? `/api/viewer/thumbnail?path=${encodeURIComponent(fullPath)}&size=300`
            : `/api/viewer/image?path=${encodeURIComponent(fullPath)}`;

        // Implement virtual scrolling: only load images near viewport
        img.dataset.src = imageUrl;
        img.className = 'thumbnail';

        // Load first 30 images immediately, lazy load the rest
        if (index < 30) {
            img.src = imageUrl;
        } else {
            // Placeholder: transparent 1px gif
            img.src = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7';
            observer.observe(img);
        }

        // Single click: select image
        img.onclick = (e) => {
            e.stopPropagation();
            selectGridImage(index);
        };

        // Double click: open single view
        img.ondblclick = (e) => {
            e.stopPropagation();
            openSingleView(index);
        };

        container.appendChild(img);

        if (classifications[filename]) {
            const badge = document.createElement('span');
            const className = classifications[filename];
            badge.className = 'class-badge';
            badge.textContent = className;

            // Apply dynamic color
            const color = config.shortcuts.class_colors ? (config.shortcuts.class_colors[className] || '#007bff') : '#007bff';
            badge.style.backgroundColor = color;

            container.appendChild(badge);
        }

        gridView.appendChild(container);
    });

    updateClassificationStats();
}

/** Update only the class badge at one grid cell (no full re-render, no scroll). */
function updateGridBadgeOnly(index, className) {
    if (index < 0 || index >= currentImages.length) return;
    const container = gridView.children[index];
    if (!container) return;
    const existingBadge = container.querySelector('.class-badge');
    if (existingBadge) existingBadge.remove();
    if (className) {
        const badge = document.createElement('span');
        badge.className = 'class-badge';
        badge.textContent = className;
        const color = config.shortcuts.class_colors ? (config.shortcuts.class_colors[className] || '#007bff') : '#007bff';
        badge.style.backgroundColor = color;
        container.appendChild(badge);
    }
}

/** Sync all grid badges from classifications (e.g. after closing single view). No full re-render. */
function syncGridBadges() {
    for (let i = 0; i < gridView.children.length; i++) {
        const container = gridView.children[i];
        const filename = container.dataset.filename;
        if (filename === undefined) continue;
        const className = classifications[filename] || null;
        updateGridBadgeOnly(i, className);
    }
}

/** Set grid selection visually without scrolling. */
function setGridSelectionWithoutScroll(index) {
    selectedGridIndex = index;
    const containers = gridView.querySelectorAll('.thumbnail-container');
    containers.forEach((container, i) => {
        container.classList.toggle('selected', i === index);
        // Also update thumbnail for backward compatibility
        const thumb = container.querySelector('.thumbnail');
        if (thumb) thumb.classList.toggle('selected', i === index);
    });
}

function selectGridImage(index) {
    if (index < 0 || index >= currentImages.length) return;
    selectedGridIndex = index;
    // Update visual selection on containers
    const containers = gridView.querySelectorAll('.thumbnail-container');
    containers.forEach((container, i) => {
        if (i === index) {
            container.classList.add('selected');
            const thumb = container.querySelector('.thumbnail');
            if (thumb) thumb.classList.add('selected');
        } else {
            container.classList.remove('selected');
            const thumb = container.querySelector('.thumbnail');
            if (thumb) thumb.classList.remove('selected');
        }
    });
    // Apply scroll mode
    const selectedContainer = containers[index];
    if (selectedContainer) {
        if (scrollMode === 'center') {
            // Mode 2: Always center the selected item
            selectedContainer.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
        } else {
            // Mode 1: Smart scroll - only scroll if not fully visible
            selectedContainer.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'smooth' });
        }
    }
}

function updateGridSize(size) {
    document.documentElement.style.setProperty('--grid-size', size + 'px');
    gridSizeValue.textContent = size + 'px';
    localStorage.setItem('gridSize', size);
}

function updateGridGap(size) {
    document.documentElement.style.setProperty('--grid-gap', size + 'px');
    gridGapValue.textContent = size + 'px';
    localStorage.setItem('gridGap', size);
}

const mainContainer = document.getElementById('main-container');

function openSingleView(index) {
    if (index < 0 || index >= currentImages.length) return;
    scrollTopBeforeSingleView = mainContainer.scrollTop;
    currentIndex = index;
    setGridSelectionWithoutScroll(currentIndex); // 单图打开时网格选中框同步
    zoomScale = 1.0;  // Reset zoom when opening
    updateSingleView();
    singleView.style.display = 'flex';
    singleImage.focus(); // for keyboard events if attached to image
}

function updateSingleView() {
    const filename = currentImages[currentIndex];
    const fullPath = joinPath(currentPath, filename);
    singleImage.src = `/api/viewer/image?path=${encodeURIComponent(fullPath)}`;

    // Reset zoom and pan when changing images
    zoomScale = 1.0;
    panX = 0;
    panY = 0;
    updateImageTransform();
    singleImage.classList.remove('zoomed');

    let info = `${currentIndex + 1} / ${currentImages.length} - ${filename}`;

    // Display classification with colored badge
    if (classifications[filename]) {
        const className = classifications[filename];
        const color = config.shortcuts.class_colors ? (config.shortcuts.class_colors[className] || '#007bff') : '#007bff';
        imageInfo.innerHTML = `<span>${info}</span><span class="info-class-badge" style="background-color: ${color};">${className}</span>`;
    } else {
        imageInfo.textContent = info;
    }

    // Smart preloading: load next and previous images in background
    preloadAdjacentImages(currentIndex);
}

function preloadAdjacentImages(index) {
    // Preload 2 ahead and 1 behind for smooth navigation
    const toPreload = [];

    // Next images
    if (index + 1 < currentImages.length) toPreload.push(index + 1);
    if (index + 2 < currentImages.length) toPreload.push(index + 2);

    // Previous image
    if (index - 1 >= 0) toPreload.push(index - 1);

    toPreload.forEach(i => {
        const filename = currentImages[i];
        const imagePath = joinPath(currentPath, filename);

        // Skip if already preloaded
        if (preloadCache.has(imagePath)) return;

        // Create new Image object for preloading
        const img = new Image();
        img.src = `/api/viewer/image?path=${encodeURIComponent(imagePath)}`;
        preloadCache.set(imagePath, img);

        // Limit cache size to 10 images
        if (preloadCache.size > 10) {
            const firstKey = preloadCache.keys().next().value;
            preloadCache.delete(firstKey);
        }
    });
}

function handleImageZoom(event) {
    event.preventDefault();

    // Determine zoom direction
    const delta = event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP;
    const newScale = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoomScale + delta));

    if (newScale !== zoomScale) {
        zoomScale = newScale;
        updateImageTransform();

        // Add/remove zoomed class for cursor styling
        if (zoomScale > 1.0) {
            singleImage.classList.add('zoomed');
        } else {
            singleImage.classList.remove('zoomed');
        }
    }
}

function updateImageTransform() {
    singleImage.style.transform = `translate(${panX}px, ${panY}px) scale(${zoomScale})`;
}

function handleMouseDown(event) {
    if (zoomScale > 1.0) {
        isDragging = true;
        dragStartX = event.clientX;
        dragStartY = event.clientY;
        dragStartPanX = panX;
        dragStartPanY = panY;
        event.preventDefault();
    }
}

function handleMouseMove(event) {
    if (isDragging) {
        const deltaX = event.clientX - dragStartX;
        const deltaY = event.clientY - dragStartY;
        panX = dragStartPanX + deltaX;
        panY = dragStartPanY + deltaY;
        updateImageTransform();
        event.preventDefault();
    }
}

function handleMouseUp(event) {
    if (isDragging) {
        isDragging = false;
        event.preventDefault();
    }
}

function closeSingleView() {
    singleView.style.display = 'none';
    const lastViewedIndex = currentIndex;
    currentIndex = -1;
    syncGridBadges();
    // 退出单图时按当前滚动规则（智能/居中）滚动一次，使选中项进入视口
    if (lastViewedIndex !== -1) {
        selectGridImage(lastViewedIndex);
    }
}

function showNext() {
    if (currentIndex < currentImages.length - 1) {
        currentIndex++;
        setGridSelectionWithoutScroll(currentIndex); // 切换图时网格选中框跟随
        updateSingleView();
    }
}

function showPrev() {
    if (currentIndex > 0) {
        currentIndex--;
        setGridSelectionWithoutScroll(currentIndex); // 切换图时网格选中框跟随
        updateSingleView();
    }
}

async function classifyImage(key) {
    if (currentIndex === -1) return;

    const className = config.shortcuts.classes[key];
    if (!className) return;

    const filename = currentImages[currentIndex];
    const fullPath = joinPath(currentPath, filename);

    try {
        const res = await fetch('/api/viewer/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_path: fullPath, class_name: className })
        });

        if (res.ok) {
            classifications[filename] = className;
            updateGridBadgeOnly(currentIndex, className); // 单图分类时网格角标实时更新
            updateClassificationStats();
            updateSingleView();
            // Auto advance
            showNext();
        } else {
            console.error("Classification failed");
        }
    } catch (e) {
        console.error("Error classifying", e);
    }
}

async function unclassifyImage() {
    if (currentIndex === -1) return;
    const filename = currentImages[currentIndex];
    const className = classifications[filename];
    if (!className) return; // Not classified

    const fullPath = joinPath(currentPath, filename);

    try {
        const res = await fetch('/api/viewer/unclassify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_path: fullPath, class_name: className })
        });

        if (res.ok) {
            delete classifications[filename];
            updateGridBadgeOnly(currentIndex, null); // 单图取消分类时网格角标实时更新
            updateClassificationStats();
            updateSingleView();
        }
    } catch (e) {
        console.error("Error unclassifying", e);
    }
}

// Settings UI Logic
function openSettings() {
    // Reset theme select to current saved theme
    const savedTheme = localStorage.getItem('theme') || 'nomacs';
    if (themeSelect) themeSelect.value = savedTheme;

    document.getElementById('key-next').value = config.shortcuts.next;
    document.getElementById('key-prev').value = config.shortcuts.prev;
    document.getElementById('key-clear').value = config.shortcuts.clear;

    classList.innerHTML = '';
    Object.entries(config.shortcuts.classes).forEach(([key, name]) => {
        const color = config.shortcuts.class_colors ? (config.shortcuts.class_colors[name] || '#007bff') : '#007bff';
        addClassRow(key, name, color);
    });

    settingsModal.style.display = 'flex';
}

function addClassRow(key = '', name = '', color = '#007bff') {
    const div = document.createElement('div');
    div.className = 'class-item';
    div.innerHTML = `
                <input type="text" placeholder="按键" value="${key}" class="class-key" style="width: 50px; font-size: 0.875rem;">
                <input type="text" placeholder="文件夹名称" value="${name}" class="class-name" style="flex-grow: 1; font-size: 0.875rem;">
                <input type="color" value="${color}" class="class-color" style="width: 50px; height: 30px; padding: 0; border: none; background: none;">
                <button onclick="this.parentElement.remove()" style="background-color: #d9534f; font-size: 0.875rem;">X</button>
            `;
    const keyInput = div.querySelector('.class-key');
    setupKeyCapture(keyInput);
    classList.appendChild(div);
}

async function saveSettings() {
    // Save theme
    if (themeSelect) {
        const newTheme = themeSelect.value;
        localStorage.setItem('theme', newTheme);
        applyTheme(newTheme);
    }

    const newConfig = {
        shortcuts: {
            next: document.getElementById('key-next').value,
            prev: document.getElementById('key-prev').value,
            clear: document.getElementById('key-clear').value,
            classes: {},
            class_colors: {}
        }
    };

    document.querySelectorAll('.class-item').forEach(item => {
        const key = item.querySelector('.class-key').value;
        const name = item.querySelector('.class-name').value;
        const color = item.querySelector('.class-color').value;
        if (key && name) {
            newConfig.shortcuts.classes[key] = name;
            newConfig.shortcuts.class_colors[name] = color;
        }
    });

    try {
        const res = await fetch('/api/viewer/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newConfig)
        });
        if (res.ok) {
            const raw = await res.json();
            config = unwrapPayload(raw);
            settingsModal.style.display = 'none';
        }
    } catch (e) {
        alert("保存设置失败");
    }
}

// Event Listeners
loadBtn.addEventListener('click', loadImages);
settingsBtn.addEventListener('click', openSettings);
saveSettingsBtn.addEventListener('click', saveSettings);
cancelSettingsBtn.addEventListener('click', () => settingsModal.style.display = 'none');
addClassBtn.addEventListener('click', () => addClassRow());

// Initialize key capture for static inputs
setupKeyCapture(document.getElementById('key-next'));
setupKeyCapture(document.getElementById('key-prev'));
setupKeyCapture(document.getElementById('key-clear'));

clearCacheBtn.addEventListener('click', async () => {
    if (!confirm('清除所有缓存的缩略图？这将释放磁盘空间，但缩略图需要重新生成。')) {
        return;
    }
    try {
        const res = await fetch('/api/viewer/thumbnails', { method: 'DELETE' });
        if (res.ok) {
            const raw = await res.json();
            const data = unwrapPayload(raw);
            alert(`✅ ${data.message || '缓存已清除'}`);
        } else {
            alert('❌ 清除缓存失败');
        }
    } catch (e) {
        console.error('Error clearing cache:', e);
        alert('❌ 清除缓存时出错');
    }
});

pathInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') loadImages();
});

pathInput.addEventListener('paste', (e) => {
    setTimeout(loadImages, 100);
});

closeBtn.addEventListener('click', closeSingleView);
nextBtn.addEventListener('click', showNext);
prevBtn.addEventListener('click', showPrev);

// Add wheel event listener for zoom
singleImage.addEventListener('wheel', handleImageZoom, { passive: false });

// Add mouse event listeners for drag/pan
singleImage.addEventListener('mousedown', handleMouseDown);
document.addEventListener('mousemove', handleMouseMove);
document.addEventListener('mouseup', handleMouseUp);

// Grid size slider
gridSizeSlider.addEventListener('input', (e) => {
    updateGridSize(e.target.value);
});

// Grid gap slider
gridGapSlider.addEventListener('input', (e) => {
    updateGridGap(e.target.value);
});

// Thumbnail toggle
document.getElementById('use-thumbnails-toggle').addEventListener('change', (e) => {
    useThumbnails = e.target.checked;
    localStorage.setItem('useThumbnails', useThumbnails);
    // Re-render grid to apply changes
    renderGrid();
    // Restore selection if any
    if (selectedGridIndex !== -1) {
        selectGridImage(selectedGridIndex);
    }
});

// Sort mode change
document.getElementById('sort-select').addEventListener('change', (e) => {
    currentSortMode = e.target.value;
    localStorage.setItem('sortMode', currentSortMode);
    // Reload images with new sort order
    loadImages();
});

// Scroll mode change
document.getElementById('scroll-mode-select').addEventListener('change', (e) => {
    scrollMode = e.target.value;
    localStorage.setItem('scrollMode', scrollMode);
});

// Brightness controls
brightnessSlider.addEventListener('input', (e) => {
    updateBrightness(e.target.value);
});

resetBrightnessBtn.addEventListener('click', () => {
    updateBrightness(100);
    brightnessSlider.value = 100;
});

function updateBrightness(val) {
    document.documentElement.style.setProperty('--brightness', val + '%');
    brightnessValue.textContent = val + '%';
}

// Shortcut Key Capture Logic
function setupKeyCapture(input) {
    input.addEventListener('focus', () => {
        input.style.backgroundColor = 'rgba(0, 123, 255, 0.2)';
        input.placeholder = '按下任意按键...';
    });

    input.addEventListener('blur', () => {
        input.style.backgroundColor = '';
        input.placeholder = input.classList.contains('class-key') ? '按键' : '';
    });

    input.addEventListener('keydown', (e) => {
        // Prevent default behavior for special keys used in shortcuts
        e.preventDefault();
        e.stopPropagation();

        // Capture the key name
        input.value = e.key;
        input.blur(); // Auto-save and move focus out
    });
}

// Keyboard navigation & Shortcuts
document.addEventListener('keydown', (e) => {
    // Ignore if in input fields
    if (e.target.tagName === 'INPUT') return;

    if (singleView.style.display === 'flex') {
        // Single view mode
        if (e.key === 'Escape') {
            closeSingleView();
            return;
        }

        // Navigation — 阻止默认滚动，避免每切换一张图网格就滚动
        if (e.key === config.shortcuts.next) {
            e.preventDefault();
            showNext();
            return;
        }
        if (e.key === config.shortcuts.prev) {
            e.preventDefault();
            showPrev();
            return;
        }

        // Classification
        if (config.shortcuts.classes[e.key]) {
            e.preventDefault();
            classifyImage(e.key);
            return;
        }

        // Clear
        if (e.key === config.shortcuts.clear) {
            e.preventDefault();
            unclassifyImage();
            return;
        }

        // Zoom controls
        if (e.key === '=' || e.key === '+') {
            e.preventDefault();
            handleImageZoom({ deltaY: -100, preventDefault: () => { } });
        } else if (e.key === '-') {
            e.preventDefault();
            handleImageZoom({ deltaY: 100, preventDefault: () => { } });
        } else if (e.key === '0') {
            e.preventDefault();
            zoomScale = 1.0;
            panX = 0;
            panY = 0;
            updateImageTransform();
            singleImage.classList.remove('zoomed');
        }

        // Space or Enter: close single view (accessibility)
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            closeSingleView();
            return;
        }
    } else {
        // Grid view mode
        if (selectedGridIndex !== -1) {
            // Classification shortcuts in grid mode
            if (config.shortcuts.classes[e.key]) {
                classifyGridImage(e.key);
            }

            // Clear classification
            if (e.key === config.shortcuts.clear) {
                unclassifyGridImage();
            }

            // Enter or Space: open single view
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                openSingleView(selectedGridIndex);
            }
        }

        // Arrow key navigation in grid
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight' ||
            e.key === 'ArrowUp' || e.key === 'ArrowDown') {
            e.preventDefault();
            navigateGrid(e.key);
        }
    }
});

async function classifyGridImage(key) {
    if (selectedGridIndex === -1) return;

    const className = config.shortcuts.classes[key];
    if (!className) return;

    const filename = currentImages[selectedGridIndex];
    const fullPath = joinPath(currentPath, filename);
    const currentIdx = selectedGridIndex; // preserve before render
    const nextIndex = Math.min(currentImages.length - 1, currentIdx + 1);

    try {
        const res = await fetch('/api/viewer/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_path: fullPath, class_name: className })
        });

        if (res.ok) {
            classifications[filename] = className;
            updateGridBadgeOnly(currentIdx, className);
            updateClassificationStats();
            if (nextIndex !== currentIdx) {
                selectGridImage(nextIndex);
            } else {
                setGridSelectionWithoutScroll(currentIdx);
            }
        } else {
            console.error("Classification failed");
        }
    } catch (e) {
        console.error("Error classifying", e);
    }
}

async function unclassifyGridImage() {
    if (selectedGridIndex === -1) return;
    const filename = currentImages[selectedGridIndex];
    const className = classifications[filename];
    if (!className) return;

    const fullPath = joinPath(currentPath, filename);

    try {
        const res = await fetch('/api/viewer/unclassify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image_path: fullPath, class_name: className })
        });

        if (res.ok) {
            delete classifications[filename];
            updateGridBadgeOnly(selectedGridIndex, null);
            updateClassificationStats();
            setGridSelectionWithoutScroll(selectedGridIndex);
        }
    } catch (e) {
        console.error("Error unclassifying", e);
    }
}

function navigateGrid(key) {
    if (currentImages.length === 0) return;

    // If no selection, select first image
    if (selectedGridIndex === -1) {
        selectGridImage(0);
        return;
    }

    // Calculate grid columns based on current grid size and gap
    const gridSize = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--grid-size'));
    const gridGap = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--grid-gap'));
    const containerWidth = gridView.offsetWidth;
    // 更准确地计算列数：容器宽度 / (网格项宽度 + 间距)
    const cols = Math.floor(containerWidth / (gridSize + gridGap)) || 1;

    let newIndex = selectedGridIndex;

    switch (key) {
        case 'ArrowLeft':
            newIndex = Math.max(0, selectedGridIndex - 1);
            break;
        case 'ArrowRight':
            newIndex = Math.min(currentImages.length - 1, selectedGridIndex + 1);
            break;
        case 'ArrowUp':
            newIndex = Math.max(0, selectedGridIndex - cols);
            break;
        case 'ArrowDown':
            newIndex = Math.min(currentImages.length - 1, selectedGridIndex + cols);
            break;
    }

    if (newIndex !== selectedGridIndex) {
        selectGridImage(newIndex);
        // Scrolling is now handled by selectGridImage() based on scrollMode
    }
}

function updateClassificationStats() {
    const statsContainer = document.getElementById('classification-stats');
    statsContainer.innerHTML = '';

    // Get all classification classes from config
    const classes = config.shortcuts.classes || {};
    const classColors = config.shortcuts.class_colors || {};

    Object.entries(classes).forEach(([key, className]) => {
        // Count images in this classification
        const count = Object.values(classifications).filter(c => c === className).length;

        // Get color for this class
        const color = classColors[className] || '#007bff';

        const item = document.createElement('div');
        item.className = 'classification-item';
        item.innerHTML = `
                    <div class="name">
                        <span class="color-dot" style="background-color: ${color};"></span>
                        <span>${className}</span>
                        <span class="shortcut">${key}</span>
                    </div>
                    <span class="count">${count}</span>
                `;
        statsContainer.appendChild(item);
    });

    // Add total count
    const totalItem = document.createElement('div');
    totalItem.className = 'classification-item';
    totalItem.style.borderTop = '1px solid rgba(255, 255, 255, 0.1)';
    totalItem.style.marginTop = '8px';
    totalItem.style.paddingTop = '8px';
    totalItem.innerHTML = `
                <div class="name">
                    <strong>Total Images</strong>
                </div>
                <span class="count">${currentImages.length}</span>
            `;
    statsContainer.appendChild(totalItem);
}

// Auto-hide info panel functionality
let infoPanelTimeout;
const infoPanel = document.getElementById('info-panel');
let isHoveringPanel = false;

function showInfoPanel() {
    infoPanel.classList.remove('hidden');
    // Clear existing timeout
    if (infoPanelTimeout) {
        clearTimeout(infoPanelTimeout);
    }
}

function hideInfoPanelDelayed() {
    // Clear existing timeout
    if (infoPanelTimeout) {
        clearTimeout(infoPanelTimeout);
    }
    // Set new timeout to hide after 2 seconds
    infoPanelTimeout = setTimeout(() => {
        infoPanel.classList.add('hidden');
    }, 2000);
}

function hideInfoPanelImmediate() {
    if (infoPanelTimeout) {
        clearTimeout(infoPanelTimeout);
    }
    infoPanel.classList.add('hidden');
}

// Track when mouse enters/leaves the panel
infoPanel.addEventListener('mouseenter', () => {
    isHoveringPanel = true;
    showInfoPanel(); // Keep it visible and cancel any hide timers
});

infoPanel.addEventListener('mouseleave', () => {
    isHoveringPanel = false;
    hideInfoPanelDelayed(); // Start 2-second countdown to hide
});

// Show panel only when mouse is near the right edge of the screen
document.addEventListener('mousemove', (e) => {
    const rightEdgeThreshold = 50; // pixels from right edge
    const distanceFromRightEdge = window.innerWidth - e.clientX;

    if (distanceFromRightEdge <= rightEdgeThreshold) {
        // Mouse is near right edge, show panel
        showInfoPanel();
    } else if (!isHoveringPanel && !infoPanel.classList.contains('hidden')) {
        // Mouse moved away from right edge and not hovering panel, hide with delay
        hideInfoPanelDelayed();
    }
});

// Start with panel hidden
infoPanel.classList.add('hidden');
