/**
 * Theme Manager for Image Processing Tools
 * Handles theme switching and persistence
 */

const themes = [
    { id: 'default', name: 'Default', icon: '🎨' },
    { id: 'youtube', name: 'YouTube', icon: '▶️' },
    { id: 'bilibili', name: 'Bilibili', icon: '📺' },
    { id: 'tiktok', name: 'TikTok', icon: '🎵' }
];

class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'default';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createThemeSwitcher();
    }

    applyTheme(themeId) {
        document.body.className = ''; // Clear existing classes
        if (themeId !== 'default') {
            document.body.classList.add(`theme-${themeId}`);
        }
        this.currentTheme = themeId;
        localStorage.setItem('theme', themeId);
        
        // Update active state in switcher if it exists
        this.updateSwitcherState();
    }

    createThemeSwitcher() {
        const switcher = document.createElement('div');
        switcher.className = 'theme-switcher';
        switcher.innerHTML = `
            <button class="theme-toggle" id="themeToggle" title="Change Theme">
                <span class="theme-icon">🎨</span>
            </button>
            <div class="theme-menu" id="themeMenu">
                ${themes.map(theme => `
                    <button class="theme-option ${theme.id === this.currentTheme ? 'active' : ''}" 
                            data-theme="${theme.id}">
                        <span class="theme-option-icon">${theme.icon}</span>
                        <span class="theme-option-name">${theme.name}</span>
                    </button>
                `).join('')}
            </div>
        `;

        document.body.appendChild(switcher);
        this.addStyles();
        this.addEventListeners();
    }

    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .theme-switcher {
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 1000;
            }
            
            .theme-toggle {
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                color: var(--text-primary);
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: var(--shadow-md);
                transition: all 0.3s ease;
            }
            
            .theme-toggle:hover {
                transform: rotate(90deg);
                background: var(--bg-secondary);
            }
            
            .theme-menu {
                position: absolute;
                top: 50px;
                right: 0;
                background: var(--bg-card);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                padding: 8px;
                min-width: 150px;
                box-shadow: var(--shadow-lg);
                opacity: 0;
                transform: translateY(-10px);
                pointer-events: none;
                transition: all 0.3s ease;
                backdrop-filter: blur(20px);
            }
            
            .theme-switcher:hover .theme-menu {
                opacity: 1;
                transform: translateY(0);
                pointer-events: auto;
            }
            
            .theme-option {
                width: 100%;
                padding: 8px 12px;
                display: flex;
                align-items: center;
                gap: 8px;
                background: none;
                border: none;
                color: var(--text-secondary);
                cursor: pointer;
                border-radius: 8px;
                transition: all 0.2s ease;
                text-align: left;
            }
            
            .theme-option:hover {
                background: var(--bg-input);
                color: var(--text-primary);
            }
            
            .theme-option.active {
                background: var(--primary-gradient);
                color: white;
            }
            
            .theme-option-icon {
                font-size: 1.2rem;
            }
            
            .theme-option-name {
                font-size: 0.9rem;
                font-weight: 500;
            }
        `;
        document.head.appendChild(style);
    }

    addEventListeners() {
        const options = document.querySelectorAll('.theme-option');
        options.forEach(option => {
            option.addEventListener('click', () => {
                const themeId = option.dataset.theme;
                this.applyTheme(themeId);
            });
        });
    }

    updateSwitcherState() {
        const options = document.querySelectorAll('.theme-option');
        options.forEach(option => {
            if (option.dataset.theme === this.currentTheme) {
                option.classList.add('active');
            } else {
                option.classList.remove('active');
            }
        });
    }
}

// Initialize Theme Manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
});
