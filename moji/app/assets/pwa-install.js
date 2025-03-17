// PWA Installation handler for Moji Assistant

// Store the install prompt event
let deferredPrompt;
let installButton;

// Handle the install button
document.addEventListener('DOMContentLoaded', () => {
  // Create the install button (initially hidden)
  installButton = document.createElement('button');
  installButton.id = 'install-button';
  installButton.className = 'install-button';
  installButton.innerHTML = '<i class="fas fa-download"></i> Install App';
  installButton.style.display = 'none';
  
  // Add button to the login screen
  const loginContainer = document.querySelector('.login-container');
  if (loginContainer) {
    loginContainer.appendChild(installButton);
  }
  
  // Add button to settings menu
  const settingsMenu = document.querySelector('#settings-menu');
  if (settingsMenu) {
    const installOption = document.createElement('div');
    installOption.className = 'toggle-container install-container';
    installOption.title = 'Install as app';
    installOption.style.display = 'none';
    installOption.innerHTML = `
      <span class="toggle-label">Install App</span>
      <button class="settings-action-btn">
        <i class="fas fa-download"></i>
      </button>
    `;
    settingsMenu.appendChild(installOption);
    
    // Store reference to settings install option
    const settingsInstallButton = installOption.querySelector('button');
    
    // Add click handler to settings install option
    if (settingsInstallButton) {
      settingsInstallButton.addEventListener('click', showInstallPrompt);
    }
  }
  
  // Add click handler to main install button
  installButton.addEventListener('click', showInstallPrompt);
  
  // Check if already installed
  if (window.matchMedia('(display-mode: standalone)').matches) {
    console.log('App is already installed');
    // Hide install buttons if they exist
    if (installButton) installButton.style.display = 'none';
    if (settingsMenu) {
      const installOption = settingsMenu.querySelector('.install-container');
      if (installOption) installOption.style.display = 'none';
    }
  }
});

// Listen for beforeinstallprompt event
window.addEventListener('beforeinstallprompt', (e) => {
  // Prevent the mini-infobar from appearing on mobile
  e.preventDefault();
  
  // Stash the event so it can be triggered later
  deferredPrompt = e;
  
  // Update UI to notify the user they can install the PWA
  if (installButton) {
    installButton.style.display = 'flex';
  }
  
  // Also show in settings menu
  const settingsMenu = document.querySelector('#settings-menu');
  if (settingsMenu) {
    const installOption = settingsMenu.querySelector('.install-container');
    if (installOption) installOption.style.display = 'flex';
  }
});

// Show install prompt
function showInstallPrompt() {
  if (!deferredPrompt) {
    console.log('No installation prompt available');
    return;
  }
  
  // Show the install prompt
  deferredPrompt.prompt();
  
  // Wait for the user to respond to the prompt
  deferredPrompt.userChoice.then((choiceResult) => {
    if (choiceResult.outcome === 'accepted') {
      console.log('User accepted the install prompt');
      // Hide the install button
      if (installButton) {
        installButton.style.display = 'none';
      }
      
      // Hide in settings menu
      const settingsMenu = document.querySelector('#settings-menu');
      if (settingsMenu) {
        const installOption = settingsMenu.querySelector('.install-container');
        if (installOption) installOption.style.display = 'none';
      }
    } else {
      console.log('User dismissed the install prompt');
    }
    
    // Clear the deferredPrompt variable
    deferredPrompt = null;
  });
}

// Listen for appinstalled event
window.addEventListener('appinstalled', (e) => {
  console.log('Moji Assistant was installed');
  
  // Hide the install button
  if (installButton) {
    installButton.style.display = 'none';
  }
  
  // Hide in settings menu
  const settingsMenu = document.querySelector('#settings-menu');
  if (settingsMenu) {
    const installOption = settingsMenu.querySelector('.install-container');
    if (installOption) installOption.style.display = 'none';
  }
  
  // Track analytics event (can be added later)
  // gtag('event', 'pwa_install', { 'event_category': 'engagement' });
});