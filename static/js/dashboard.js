// Dashboard Manager

const workspace = document.getElementById('workspace');
const emptyState = document.getElementById('emptyState');

// Tool mapping to their URLs
const TOOL_URLS = {
    'converter': '/converter',
    'cropper': '/cropper',
    'generator': '/generator',
    'splitter': '/splitter',
    'deduplicator': '/deduplicator',
    'matcher': '/matcher',
    'visualizer': '/visualizer'
};

// Tool Titles
const TOOL_TITLES = {
    'converter': '格式转换',
    'cropper': '滑窗裁剪',
    'generator': '数据集生成',
    'splitter': '数据集划分',
    'deduplicator': '图像去重',
    'matcher': '图像匹配',
    'visualizer': '标注可视化'
};

// Tool Icons
const TOOL_ICONS = {
    'converter': '🔄',
    'cropper': '✂️',
    'generator': '📦',
    'splitter': '📊',
    'deduplicator': '🗑️',
    'matcher': '🔍',
    'visualizer': '👁️'
};

// Counter for unique IDs
let toolCounter = 0;

/**
 * Add a tool to the workspace
 * @param {string} toolName - The key of the tool (e.g., 'splitter')
 */
async function addTool(toolName) {
    if (!TOOL_URLS[toolName]) {
        console.error('Unknown tool:', toolName);
        return;
    }

    // Hide empty state
    emptyState.style.display = 'none';

    // Create container
    const toolId = `tool-${toolName}-${++toolCounter}`;
    const container = document.createElement('div');
    container.className = 'tool-container';
    container.id = toolId;

    // Header
    container.innerHTML = `
        <div class="tool-header">
            <div class="tool-title">
                <span>${TOOL_ICONS[toolName]}</span>
                ${TOOL_TITLES[toolName]}
            </div>
            <div class="tool-controls">
                <button class="tool-btn close" onclick="removeTool('${toolId}')" title="关闭">✕</button>
            </div>
        </div>
        <div class="tool-body" id="${toolId}-body">
            <div class="spinner" style="margin: 20px auto;"></div>
        </div>
    `;

    workspace.appendChild(container);

    // Fetch content
    try {
        const response = await fetch(TOOL_URLS[toolName]);
        const html = await response.text();

        // Parse HTML
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');

        // Extract main content
        // We look for .main-content or .container
        const mainContent = doc.querySelector('.main-content') || doc.querySelector('.container');

        if (mainContent) {
            const body = container.querySelector('.tool-body');
            body.innerHTML = '';
            body.appendChild(mainContent);

            // Initialize script
            initializeToolScript(toolName, body);
        } else {
            throw new Error('Could not find content in tool page');
        }

    } catch (error) {
        console.error('Failed to load tool:', error);
        container.querySelector('.tool-body').innerHTML = `
            <div class="result-error" style="margin: 10px;">
                <p>加载失败: ${error.message}</p>
            </div>
        `;
    }
}

/**
 * Remove a tool from the workspace
 * @param {string} toolId 
 */
function removeTool(toolId) {
    const tool = document.getElementById(toolId);
    if (tool) {
        tool.remove();
    }

    // Show empty state if no tools left
    if (workspace.children.length <= 1) { // 1 because emptyState is a child
        emptyState.style.display = 'flex';
    }
}

/**
 * Initialize the specific script for the tool
 * This is the tricky part: we need to make sure the script runs 
 * and binds to the specific elements in THIS container, not global IDs.
 */
function initializeToolScript(toolName, container) {
    // This relies on the refactored JS files exposing an init function
    // Format: init{ToolName}(containerElement)

    const functionName = 'init' + toolName.charAt(0).toUpperCase() + toolName.slice(1);

    if (typeof window[functionName] === 'function') {
        window[functionName](container);
    } else {
        console.warn(`Initialization function ${functionName} not found. Tool might not work correctly.`);

        // Fallback: If the script was just loaded, it might have auto-initialized on document.
        // We might need to manually trigger logic if we haven't refactored the script yet.
    }
}
