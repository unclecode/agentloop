/**
 * click-fix.js - Fixes click responsiveness issues in PWAs
 * 
 * This script addresses common issues with button clicks in PWA environments,
 * particularly the 300ms delay on mobile devices and click event propagation problems.
 */

document.addEventListener('DOMContentLoaded', function() {
    // Fix for 300ms tap delay on mobile devices
    fixTapDelay();
    
    // Fix button click issues in PWA mode
    fixButtonClicks();
    
    // Apply iOS-specific fixes
    applyIOSFixes();
});

/**
 * Fixes the 300ms tap delay on mobile devices
 */
function fixTapDelay() {
    // Check if FastClick is available, if not, implement basic touch handler
    if (typeof FastClick !== 'undefined') {
        // Use FastClick library if available
        FastClick.attach(document.body);
    } else {
        // Simple implementation to prevent delay
        document.addEventListener('touchstart', function() {}, {passive: true});
    }
}

/**
 * Fixes button click issues in PWA mode
 */
function fixButtonClicks() {
    // Select all buttons and elements that should respond to clicks
    const clickableElements = document.querySelectorAll('button, .button, [role="button"], .action-button, .send-button');
    
    // Add touch event listeners to all clickable elements
    clickableElements.forEach(element => {
        // Add touch event listeners with active state
        element.addEventListener('touchstart', handleTouchStart, {passive: true});
        element.addEventListener('touchend', handleTouchEnd);
        element.addEventListener('touchcancel', handleTouchCancel);
        
        // Make sure the icons inside buttons don't block click events
        const icons = element.querySelectorAll('i, svg, img');
        icons.forEach(icon => {
            icon.style.pointerEvents = 'none';
        });
    });
    
    // Observer for dynamically added elements
    observeDynamicElements();
}

/**
 * Handle touchstart event for visual feedback
 */
function handleTouchStart(e) {
    this.classList.add('touch-active');
}

/**
 * Handle touchend event to trigger click and manage visual feedback
 */
function handleTouchEnd(e) {
    const element = this;
    
    // Remove active state
    element.classList.remove('touch-active');
    
    // If this is within a form and has type="submit", don't auto-submit the form
    // Let the app's event handlers take care of it
    if (element.type === 'submit' && element.form) {
        e.preventDefault();
        // We'll let the form's own submit handler take care of this
        // The form already has preventDefault in its submit handlers
    }
    
    // Ensure click event is properly triggered
    if (!element.disabled) {
        // Prevent ghost clicks
        e.preventDefault();
        
        // Dispatch a synthetic click event
        const clickEvent = new MouseEvent('click', {
            bubbles: true,
            cancelable: true,
            view: window
        });
        
        element.dispatchEvent(clickEvent);
    }
}

/**
 * Handle touch cancel
 */
function handleTouchCancel(e) {
    this.classList.remove('touch-active');
}

/**
 * Watch for dynamically added elements and apply the same fixes
 */
function observeDynamicElements() {
    // Create a MutationObserver to watch for new elements
    const observer = new MutationObserver(mutations => {
        mutations.forEach(mutation => {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach(node => {
                    // Check if the node is an element and is clickable
                    if (node.nodeType === 1 && 
                        (node.tagName === 'BUTTON' || 
                         node.classList.contains('button') || 
                         node.getAttribute('role') === 'button' ||
                         node.classList.contains('action-button') ||
                         node.classList.contains('send-button'))) {
                        
                        // Add event listeners
                        node.addEventListener('touchstart', handleTouchStart, {passive: true});
                        node.addEventListener('touchend', handleTouchEnd);
                        node.addEventListener('touchcancel', handleTouchCancel);
                        
                        // Fix icons inside this element
                        const icons = node.querySelectorAll('i, svg, img');
                        icons.forEach(icon => {
                            icon.style.pointerEvents = 'none';
                        });
                    }
                });
            }
        });
    });
    
    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
}

/**
 * Apply iOS-specific fixes
 */
function applyIOSFixes() {
    // Check if running on iOS
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    
    if (isIOS) {
        // Fix for iOS button activation state
        document.body.addEventListener('touchend', () => {}, false);
        
        // Add iOS-specific CSS class for further adjustments
        document.documentElement.classList.add('ios-device');
        
        // Fix for double-tap issue on iOS
        const style = document.createElement('style');
        style.textContent = `
            /* Apply -webkit-tap-highlight-color to prevent the gray highlight */
            * {
                -webkit-tap-highlight-color: rgba(0,0,0,0);
            }
            
            /* For iOS button issues */
            button, .button, [role="button"], .action-button, .send-button {
                cursor: pointer;
                touch-action: manipulation;
            }
            
            /* Fix onclick issues by using :active styling */
            .touch-active {
                opacity: 0.8 !important;
                transform: scale(0.98) !important;
            }
        `;
        document.head.appendChild(style);
    }
}