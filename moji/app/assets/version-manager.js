/**
 * Version Manager for Moji Assistant PWA
 * Handles version checking and app updates
 */

class VersionManager {
  constructor() {
    // Get stored version from localStorage or use default
    this.currentVersion = localStorage.getItem('app_version') || '1.0.0';
    
    // Element to display version info
    this.versionElement = null;
    
    // Update notification elements
    this.updateToast = null;
    this.updateButton = null;
    
    // Check interval in minutes
    this.checkInterval = 60;
    
    // Flag to prevent multiple update toasts
    this.updateInProgress = false;
    
    // Initialize the manager
    this.init();
  }
  
  /**
   * Initialize the version manager
   */
  init() {
    // Create version display in settings
    this.createVersionUI();
    
    // Create update toast notification
    this.createUpdateToast();
    
    // Check if we just completed an update
    const justUpdated = sessionStorage.getItem('app_updated') === 'true';
    if (justUpdated) {
      // Clear the flag
      sessionStorage.removeItem('app_updated');
      // Show success message
      setTimeout(() => this.showInfoToast('App successfully updated!'), 1000);
    }
    
    // Initial version check after app loads (with delay to allow page to render)
    window.addEventListener('load', () => {
      setTimeout(() => this.checkForUpdates(false), 2000);
    });
    
    // Set up periodic version checks
    setInterval(() => this.checkForUpdates(false), this.checkInterval * 60 * 1000);
    
    // Handle service worker updates
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        console.log('Service Worker controller changed - page will reload');
        // Only reload if we initiated the update
        if (this.isUpdating) {
          window.location.reload();
        }
      });
    }
  }
  
  /**
   * Create version UI elements in the settings menu
   */
  createVersionUI() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this.createVersionUI());
      return;
    }
    
    const settingsMenu = document.getElementById('settings-menu');
    if (!settingsMenu) return;
    
    // Create version display element
    const versionContainer = document.createElement('div');
    versionContainer.className = 'version-container';
    versionContainer.innerHTML = `
      <div class="version-info">
        <span>Version: <span id="app-version">${this.currentVersion}</span></span>
      </div>
      <button id="check-updates-btn" class="settings-action-btn" title="Check for updates">
        <i class="fas fa-sync-alt"></i>
      </button>
    `;
    
    // Add version container to settings menu
    settingsMenu.appendChild(versionContainer);
    
    // Store reference to version element
    this.versionElement = document.getElementById('app-version');
    
    // Add event listener to update button
    const checkUpdatesBtn = document.getElementById('check-updates-btn');
    if (checkUpdatesBtn) {
      checkUpdatesBtn.addEventListener('click', () => this.checkForUpdates(true));
    }
  }
  
  /**
   * Create update toast notification
   */
  createUpdateToast() {
    // Create toast element
    this.updateToast = document.createElement('div');
    this.updateToast.className = 'update-toast';
    this.updateToast.innerHTML = `
      <div class="toast-content">
        <i class="fas fa-sync-alt"></i>
        <div class="toast-message">
          <span class="toast-title">Update Available</span>
          <span class="toast-text">A new version of Moji Assistant is available</span>
        </div>
      </div>
      <div class="toast-actions">
        <button id="update-now-btn">Update Now</button>
        <button id="update-later-btn">Later</button>
      </div>
    `;
    
    // Initially hide the toast
    this.updateToast.style.display = 'none';
    
    // Add toast to body
    document.body.appendChild(this.updateToast);
    
    // Add event listeners to buttons
    document.getElementById('update-now-btn').addEventListener('click', () => {
      this.updateApp();
      this.hideUpdateToast();
    });
    
    document.getElementById('update-later-btn').addEventListener('click', () => {
      this.hideUpdateToast();
    });
  }
  
  /**
   * Check for updates by comparing version with server
   * @param {boolean} manual - Whether the check was manually triggered
   */
  checkForUpdates(manual = false) {
    console.log(`Checking for updates... (${manual ? 'manual' : 'automatic'})`);
    
    // Don't check if update is already in progress
    if (this.updateInProgress) {
      console.log('Update already in progress, skipping check');
      return;
    }
    
    // Fetch the current version from server
    fetch('/api/version')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        const serverVersion = data.version;
        console.log(`Server version: ${serverVersion}, Current version: ${this.currentVersion}`);
        
        // Update version display
        if (this.versionElement) {
          this.versionElement.textContent = this.currentVersion;
        }
        
        // Compare versions
        if (this.isNewerVersion(serverVersion, this.currentVersion)) {
          console.log('New version available!');
          
          // Store the new version to update to
          this.newVersion = serverVersion;
          
          // Only show toast if no update is in progress
          if (!this.updateInProgress) {
            this.showUpdateToast(serverVersion);
          }
        } else if (manual) {
          // Show toast for manual check even if up to date
          this.showInfoToast('You have the latest version');
        }
      })
      .catch(error => {
        console.error('Error checking for updates:', error);
        if (manual) {
          this.showInfoToast('Could not check for updates');
        }
      });
  }
  
  /**
   * Compare version strings to determine if server version is newer
   * @param {string} serverVersion - Version from server
   * @param {string} currentVersion - Current app version
   * @returns {boolean} True if server version is newer
   */
  isNewerVersion(serverVersion, currentVersion) {
    const serverParts = serverVersion.split('.').map(Number);
    const currentParts = currentVersion.split('.').map(Number);
    
    for (let i = 0; i < serverParts.length; i++) {
      // If server has more parts or larger part, it's newer
      if (!currentParts[i] || serverParts[i] > currentParts[i]) {
        return true;
      }
      // If current has larger part, server is not newer
      if (serverParts[i] < currentParts[i]) {
        return false;
      }
    }
    
    // Versions are equal
    return false;
  }
  
  /**
   * Show update toast notification
   * @param {string} newVersion - New version available
   */
  showUpdateToast(newVersion) {
    // Update toast message with version
    const toastText = this.updateToast.querySelector('.toast-text');
    toastText.textContent = `Version ${newVersion} is available`;
    
    // Show the toast
    this.updateToast.style.display = 'flex';
    this.updateToast.classList.add('show-toast');
    
    // Auto-hide after 15 seconds
    setTimeout(() => {
      if (this.updateToast.classList.contains('show-toast')) {
        this.hideUpdateToast();
      }
    }, 15000);
  }
  
  /**
   * Show info toast notification
   * @param {string} message - Information message
   */
  showInfoToast(message) {
    // Create and show a temporary info toast
    const infoToast = document.createElement('div');
    infoToast.className = 'update-toast info-toast';
    infoToast.innerHTML = `
      <div class="toast-content">
        <i class="fas fa-info-circle"></i>
        <div class="toast-message">
          <span class="toast-text">${message}</span>
        </div>
      </div>
    `;
    
    // Add to body
    document.body.appendChild(infoToast);
    
    // Show with animation
    setTimeout(() => infoToast.classList.add('show-toast'), 10);
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
      infoToast.classList.remove('show-toast');
      setTimeout(() => infoToast.remove(), 300);
    }, 3000);
  }
  
  /**
   * Hide update toast notification
   */
  hideUpdateToast() {
    this.updateToast.classList.remove('show-toast');
    setTimeout(() => {
      this.updateToast.style.display = 'none';
    }, 300);
  }
  
  /**
   * Update the application
   * - Unregister service worker
   * - Clear caches
   * - Reload the page
   */
  updateApp() {
    // Set flags for update in progress
    this.updateInProgress = true;
    this.isUpdating = true;
    
    // Store the new version in localStorage before reload
    if (this.newVersion) {
      localStorage.setItem('app_version', this.newVersion);
      this.currentVersion = this.newVersion;
      
      // Update displayed version if element exists
      if (this.versionElement) {
        this.versionElement.textContent = this.currentVersion;
      }
    }
    
    // Show updating message
    this.showInfoToast('Updating application...');
    
    // Get all service worker registrations
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistration()
        .then(registration => {
          if (registration) {
            // Unregister the service worker
            return registration.unregister();
          }
        })
        .then(() => {
          // Clear all caches
          return caches.keys()
            .then(cacheNames => {
              return Promise.all(
                cacheNames.map(cacheName => {
                  console.log(`Deleting cache: ${cacheName}`);
                  return caches.delete(cacheName);
                })
              );
            });
        })
        .then(() => {
          // Reload the page to get the new version
          console.log('Update complete, reloading page...');
          
          // Set a flag in session storage to show success message after reload
          sessionStorage.setItem('app_updated', 'true');
          
          // Hard reload to get fresh assets
          window.location.reload(true);
        })
        .catch(error => {
          console.error('Error during update:', error);
          this.updateInProgress = false;
          this.isUpdating = false;
          this.showInfoToast('Update failed. Please try again.');
        });
    } else {
      // If service worker not supported, just reload
      sessionStorage.setItem('app_updated', 'true');
      window.location.reload(true);
    }
  }
}

// Create instance of version manager
const versionManager = new VersionManager();

// Export for potential use in other modules
window.versionManager = versionManager;