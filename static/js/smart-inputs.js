/**
 * Enhanced Smart Inputs Manager
 * Handles bidirectional auto-filling of paths and intelligent path inference
 */

class SmartInputManager {
    constructor() {
        // Support both old and new input ID conventions
        this.imagesInput = document.getElementById('imagesDir') || 
                          document.getElementById('inputPath') || 
                          document.getElementById('image_dir');
        this.annotationsInput = document.getElementById('annotationsDir') || 
                               document.getElementById('annotation_dir');
        this.outputInput = document.getElementById('output_dir') || 
                           document.getElementById('outputPath');
        this.formatSelect = document.getElementById('conversionType') || 
                            document.getElementById('annotationFormat') || 
                            document.getElementById('conversion_format');

        this.init();
    }

    init() {
        // Set up event listeners for image input
        if (this.imagesInput && this.annotationsInput) {
            this.imagesInput.addEventListener('input', (e) => this.handleImageInput(e));
            this.imagesInput.addEventListener('paste', (e) => this.handleImagePaste(e));
        }
        
        // Set up event listeners for annotation input (bidirectional inference)
        if (this.annotationsInput && this.imagesInput) {
            this.annotationsInput.addEventListener('input', (e) => this.handleAnnotationInput(e));
            this.annotationsInput.addEventListener('paste', (e) => this.handleAnnotationPaste(e));
        }
        
        // Set up format change listener to update placeholders and infer paths
        if (this.formatSelect) {
            this.formatSelect.addEventListener('change', () => this.handleFormatChange());
        }
        
        // Initialize placeholders and try to infer paths if values exist
        this.updatePlaceholders();
        this.tryInferAllPaths();
    }

    handleImageInput(e) {
        this.inferFromImagePath(e.target.value);
    }

    handleImagePaste(e) {
        setTimeout(() => {
            this.inferFromImagePath(e.target.value);
        }, 10);
    }
    
    handleAnnotationInput(e) {
        this.inferFromAnnotationPath(e.target.value);
    }
    
    handleAnnotationPaste(e) {
        setTimeout(() => {
            this.inferFromAnnotationPath(e.target.value);
        }, 10);
    }
    
    handleFormatChange() {
        this.updatePlaceholders();
        this.tryInferAllPaths();
    }
    
    tryInferAllPaths() {
        // Try to infer paths based on whichever input has a value
        if (this.imagesInput.value) {
            this.inferFromImagePath(this.imagesInput.value);
        } else if (this.annotationsInput.value) {
            this.inferFromAnnotationPath(this.annotationsInput.value);
        }
    }

    inferFromImagePath(imagePath) {
        if (!imagePath) return;

        const format = this.getFormat();
        
        // Infer annotation path if not already filled
        if (!this.annotationsInput.value) {
            const annotationPath = this.predictAnnotationPath(imagePath, format);
            if (annotationPath && annotationPath !== imagePath) {
                this.annotationsInput.value = annotationPath;
                this.showNotification('已自动推断标注文件路径', annotationPath);
            }
        }
        
        // Infer output path if not already filled
        if (this.outputInput && !this.outputInput.value) {
            const outputPath = this.predictOutputPath(imagePath, format);
            if (outputPath && outputPath !== imagePath && outputPath !== this.annotationsInput.value) {
                this.outputInput.value = outputPath;
                this.showNotification('已自动推断输出路径', outputPath);
            }
        }
    }
    
    inferFromAnnotationPath(annotationPath) {
        if (!annotationPath) return;

        const format = this.getFormat();
        
        // Infer image path if not already filled
        if (!this.imagesInput.value) {
            const imagePath = this.predictImagePath(annotationPath, format);
            if (imagePath && imagePath !== annotationPath) {
                this.imagesInput.value = imagePath;
                this.showNotification('已自动推断图片路径', imagePath);
            }
        }
        
        // Infer output path if not already filled
        if (this.outputInput && !this.outputInput.value) {
            const outputPath = this.predictOutputPath(annotationPath, format);
            if (outputPath && outputPath !== annotationPath && outputPath !== this.imagesInput.value) {
                this.outputInput.value = outputPath;
                this.showNotification('已自动推断输出路径', outputPath);
            }
        }
    }

    predictAnnotationPath(imagePath, format) {
        // Generate multiple possible paths based on common dataset structures
        const pathVariants = [];
        
        // Extract base directory
        const baseDir = this.extractBaseDir(imagePath);
        
        // 1. Try direct replacements based on common patterns
        const replacements = this.getCommonReplacements('image', format);
        for (const [search, replace] of Object.entries(replacements)) {
            if (imagePath.includes(search)) {
                pathVariants.push(imagePath.replace(search, replace));
            }
        }
        
        // 2. Try parallel directory structures
        if (format === 'voc' || format === 'xml') {
            pathVariants.push(
                `${baseDir}/Annotations`,
                `${baseDir}/annotations`,
                `${baseDir}/xmls`
            );
        } else if (format === 'yolo' || format === 'txt') {
            pathVariants.push(
                `${baseDir}/labels`,
                `${baseDir}/YOLO/labels`,
                `${baseDir}/annotations`
            );
        } else if (format === 'json') {
            pathVariants.push(
                `${baseDir}/annotations`,
                `${baseDir}/json`,
                `${baseDir}/labels`
            );
        }
        
        // Return the first valid variant
        return pathVariants.find(path => path !== imagePath) || '';
    }
    
    predictImagePath(annotationPath, format) {
        // Generate multiple possible paths based on common dataset structures
        const pathVariants = [];
        
        // Extract base directory
        const baseDir = this.extractBaseDir(annotationPath);
        
        // 1. Try direct replacements based on common patterns
        const replacements = this.getCommonReplacements('annotation', format);
        for (const [search, replace] of Object.entries(replacements)) {
            if (annotationPath.includes(search)) {
                pathVariants.push(annotationPath.replace(search, replace));
            }
        }
        
        // 2. Try parallel directory structures
        pathVariants.push(
            `${baseDir}/images`,
            `${baseDir}/JPEGImages`,
            `${baseDir}/img`,
            `${baseDir}/imgs`
        );
        
        // Return the first valid variant
        return pathVariants.find(path => path !== annotationPath) || '';
    }
    
    predictOutputPath(sourcePath, format) {
        // Extract base directory
        const baseDir = this.extractBaseDir(sourcePath);
        
        // Generate timestamp for unique output directories
        const timestamp = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
        
        // Generate output directory names based on format
        if (format === 'voc' || format === 'xml') {
            return `${baseDir}/output_voc_${timestamp}`;
        } else if (format === 'yolo' || format === 'txt') {
            return `${baseDir}/output_yolo_${timestamp}`;
        } else if (format === 'json') {
            return `${baseDir}/output_json_${timestamp}`;
        }
        
        // Default output directory
        return `${baseDir}/output_${timestamp}`;
    }
    
    getCommonReplacements(type, format) {
        const replacements = {};
        
        // Common image directory patterns
        if (type === 'image') {
            if (format === 'voc' || format === 'xml') {
                Object.assign(replacements, {
                    '/images/': '/Annotations/',
                    '\\images\\': '\\Annotations\\',
                    '/JPEGImages/': '/Annotations/',
                    '\\JPEGImages\\': '\\Annotations\\',
                    '/img/': '/Annotations/',
                    '\\img\\': '\\Annotations\\',
                    '/imgs/': '/Annotations/',
                    '\\imgs\\': '\\Annotations\\'
                });
            } else if (format === 'yolo' || format === 'txt') {
                Object.assign(replacements, {
                    '/images/': '/labels/',
                    '\\images\\': '\\labels\\',
                    '/JPEGImages/': '/labels/',
                    '\\JPEGImages\\': '\\labels\\',
                    '/img/': '/labels/',
                    '\\img\\': '\\labels\\',
                    '/imgs/': '/labels/',
                    '\\imgs\\': '\\labels\\'
                });
            } else if (format === 'json') {
                Object.assign(replacements, {
                    '/images/': '/annotations/',
                    '\\images\\': '\\annotations\\',
                    '/JPEGImages/': '/annotations/',
                    '\\JPEGImages\\': '\\annotations\\'
                });
            }
        } 
        // Common annotation directory patterns
        else if (type === 'annotation') {
            Object.assign(replacements, {
                '/Annotations/': '/images/',
                '\\Annotations\\': '\\images\\',
                '/annotations/': '/images/',
                '\\annotations\\': '\\images\\',
                '/labels/': '/images/',
                '\\labels\\': '\\images\\',
                '/xmls/': '/images/',
                '\\xmls\\': '\\images\\'
            });
        }
        
        return replacements;
    }
    
    extractBaseDir(path) {
        // Split path by either slash
        const pathParts = path.split(/[/\\]/).filter(part => part);
        
        // Common dataset directory names to detect
        const specialDirs = ['images', 'JPEGImages', 'Annotations', 'annotations', 
                            'labels', 'xmls', 'json', 'YOLO', 'VOC', 'output', 
                            'train', 'test', 'val', 'img', 'imgs'];
        
        // Find the last special directory in the path
        const lastSpecialIndex = pathParts.findLastIndex(part => 
            specialDirs.includes(part.toLowerCase())
        );
        
        // If found, return the path up to that directory
        if (lastSpecialIndex > -1) {
            return pathParts.slice(0, lastSpecialIndex).join('/');
        }
        
        // Otherwise, return the path up to the last directory
        if (pathParts.length > 1) {
            return pathParts.slice(0, -1).join('/');
        }
        
        // If it's just a filename or single directory, return current directory
        return '.';
    }

    getFormat() {
        if (!this.formatSelect) return 'unknown';

        const value = this.formatSelect.value.toLowerCase();
        if (value.includes('voc') || value.includes('xml')) return 'voc';
        if (value.includes('yolo') || value.includes('txt')) return 'yolo';
        if (value.includes('json')) return 'json';

        return 'unknown';
    }
    
    updatePlaceholders() {
        if (!this.annotationsInput || !this.formatSelect) return;
        
        const format = this.getFormat();
        
        if (format === 'voc') {
            this.annotationsInput.placeholder = 'Annotations目录 (如 path/to/Annotations)';
        } else if (format === 'yolo') {
            this.annotationsInput.placeholder = 'Labels目录 (如 path/to/labels)';
        } else if (format === 'json') {
            this.annotationsInput.placeholder = 'Annotations目录 (如 path/to/annotations)';
        }
        
        if (this.outputInput) {
            this.outputInput.placeholder = '输出目录 (自动推断)';
        }
    }

    showNotification(message, path = '') {
        // Try to use existing toast if available
        let toast = document.getElementById('autoFillToast');
        
        if (!toast) {
            // Create new toast element
            toast = document.createElement('div');
            toast.id = 'autoFillToast';
            toast.style.cssText = `
                position: fixed;
                bottom: 20px;
                right: 20px;
                background: var(--primary-color, #4CAF50);
                color: white;
                padding: 10px 15px;
                border-radius: 4px;
                font-size: 14px;
                z-index: 10000;
                opacity: 0;
                transition: opacity 0.3s ease;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);
                max-width: 300px;
                word-break: break-word;
            `;
            document.body.appendChild(toast);
        }
        
        // Set message
        toast.textContent = path ? `${message}: ${path}` : message;
        
        // Show toast
        clearTimeout(this.toastTimeout);
        toast.style.opacity = '0.9';
        
        // Hide after 3 seconds
        this.toastTimeout = setTimeout(() => {
            toast.style.opacity = '0';
        }, 3000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new SmartInputManager();
});