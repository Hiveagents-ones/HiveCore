/**
 * Main application module for Hello World display
 * Handles internationalization, performance monitoring, and secure rendering
 */

// Configuration object with internationalization support
const APP_CONFIG = {
    // Default text and translations
    texts: {
        default: 'Hello World',
        'en-US': 'Hello World',
        'en-GB': 'Hello World',
        'es-ES': 'Hola Mundo',
        'fr-FR': 'Bonjour le monde',
        'de-DE': 'Hallo Welt',
        'ja-JP': 'こんにちは世界',
        'zh-CN': '你好世界',
        'zh-TW': '你好世界',
        'ko-KR': '안녕하세요 세계',
        'pt-BR': 'Olá Mundo',
        'ru-RU': 'Привет, мир',
        'ar-SA': 'مرحبا بالعالم'
    },

    // Display settings
    display: {
        ensureVisibility: true,
        fadeInDuration: 300
    },
    
    // Performance monitoring settings
    performance: {
        enabled: true,
        logLevel: 'info'
    },
    
    // Security settings
    security: {
        sanitizeInput: true,
        allowInlineScripts: false
    }
};

/**
 * Performance monitoring utility
 */
class PerformanceMonitor {
    static logRenderTime(startTime, endTime) {
        const duration = endTime - startTime;
        console.log(`[Performance] Render time: ${duration.toFixed(2)}ms`);
        
        // Log warning if render time exceeds threshold
        if (duration > 100) {
            console.warn(`[Performance] Slow render detected: ${duration.toFixed(2)}ms`);
        }
        
        return duration;
    }
    
    static logFCP() {
        if (window.performance && performance.getEntriesByType) {
            const fcpEntries = performance.getEntriesByType('paint');
            const fcpEntry = fcpEntries.find(entry => entry.name === 'first-contentful-paint');
            
            if (fcpEntry) {
                console.log(`[Performance] First Contentful Paint: ${fcpEntry.startTime.toFixed(2)}ms`);
                return fcpEntry.startTime;
            }
        }
        return null;
    }
}

/**
 * Internationalization utility
 */
class I18nManager {
    static getBrowserLanguage() {
        return navigator.language || navigator.userLanguage || 'en-US';
    }
    
    static getText(language = null) {
        const targetLang = language || this.getBrowserLanguage();
        
        // Try exact match first
        if (APP_CONFIG.texts[targetLang]) {
            return APP_CONFIG.texts[targetLang];
        }
        
        // Try language-only match (e.g., 'en' from 'en-US')
        const langOnly = targetLang.split('-')[0];
        const matchedKey = Object.keys(APP_CONFIG.texts).find(key => key.startsWith(langOnly));
        
        if (matchedKey) {
            return APP_CONFIG.texts[matchedKey];
        }
        
        // Fallback to default
        return APP_CONFIG.texts.default;
    }
}

/**
 * Security utility for safe DOM manipulation
 */
class SecurityUtils {

    /**
     * Ensures element is visible in viewport
     */
    static ensureElementVisible(element) {
        if (!element) return false;
        
        const rect = element.getBoundingClientRect();
        const isInViewport = (
            rect.top >= 0 &&
            rect.left >= 0 &&
            rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
            rect.right <= (window.innerWidth || document.documentElement.clientWidth)
        );
        
        if (!isInViewport) {
            element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        return true;
    }

    /**
     * Applies fade-in animation to element
     */
    static fadeIn(element, duration = 300) {
        if (!element) return;
        
        element.style.opacity = '0';
        element.style.transition = `opacity ${duration}ms ease-in`;
        
        // Trigger reflow
        element.offsetHeight;
        
        element.style.opacity = '1';
    }
    static sanitizeText(text) {
        if (typeof text !== 'string') {
            console.warn('[Security] Attempted to sanitize non-string value');
            return '';
        }
        
        // Basic sanitization - remove HTML tags
        return text.replace(/<[^>]*>/g, '');
    }
    
    static safeSetTextContent(element, text) {
        if (!element) {
            console.error('[Security] Invalid element provided');
            return false;
        }
        
        const sanitizedText = APP_CONFIG.security.sanitizeInput 
            ? this.sanitizeText(text) 
            : text;
        
        // Use textContent to prevent XSS
        element.textContent = sanitizedText;
        return true;
    }
}

/**
 * Main application class
 */
class HelloWorldApp {
    constructor() {
        this.element = null;
        this.isInitialized = false;
    }
    
    init() {
        try {
            this.element = document.getElementById('greeting');
            
            if (!this.element) {
                throw new Error('Target element not found');
            }
            
            this.render();
            this.isInitialized = true;
            
            // Log successful initialization
            console.log('[App] Successfully initialized');
            
        } catch (error) {
            console.error('[App] Initialization failed:', error);
            this.handleError(error);
        }
    }
    
    render(customText = null) {
        const startTime = performance.now();
        
        try {
            const text = customText || I18nManager.getText();
            const success = SecurityUtils.safeSetTextContent(this.element, text);
            
            // Apply display settings
            if (APP_CONFIG.display.ensureVisibility) {
                SecurityUtils.ensureElementVisible(this.element);
            }
            
            if (APP_CONFIG.display.fadeInDuration > 0) {
                SecurityUtils.fadeIn(this.element, APP_CONFIG.display.fadeInDuration);
            }
            
            if (!success) {
                throw new Error('Failed to set text content');
            }
            
            const endTime = performance.now();
            
            // Log performance metrics
            if (APP_CONFIG.performance.enabled) {
                PerformanceMonitor.logRenderTime(startTime, endTime);
                PerformanceMonitor.logFCP();
            }
            
            // Log render event
            console.log(`[App] Rendered text: "${text}"`);
            
        } catch (error) {
            console.error('[App] Render failed:', error);
            this.handleError(error);
        }
    }
    
    handleError(error) {
        // Log error with timestamp
        console.error(`[Error] ${new Date().toISOString()}:`, error.message);
        
        // Display fallback message
        if (this.element) {
            this.element.textContent = 'Error: Unable to display content';
            this.element.style.color = '#d73a49';
        }
    }
    
    // Public API for extensibility
    updateText(newText) {
        if (typeof newText === 'string' && newText.trim()) {
            this.render(newText);
            console.log(`[App] Text updated to: "${newText}"`);
        } else {
            console.warn('[App] Invalid text provided for update');
        }
    }
    
    getSupportedLanguages() {
        return Object.keys(APP_CONFIG.texts);
    }
}

/**
 * Application entry point
 */
(function() {
    'use strict';
    
    // Wait for DOM to be fully loaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeApp);
    } else {
        initializeApp();
    }
    
    function initializeApp() {
        // Create and initialize the app
        const app = new HelloWorldApp();
        app.init();
        
        // Expose app instance globally for extensibility
        window.HelloWorldApp = app;
        
        // Log initialization complete
        console.log('[System] Application initialization complete');
        
        // Add global error handler
        window.addEventListener('error', function(event) {
            console.error('[System] Unhandled error:', event.error);
        });
        
        // Add unhandled promise rejection handler
        window.addEventListener('unhandledrejection', function(event) {
            console.error('[System] Unhandled promise rejection:', event.reason);
        });
    }
})();