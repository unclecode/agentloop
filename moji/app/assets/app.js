// DOM Elements
const loginScreen = document.getElementById('login-screen');
const chatScreen = document.getElementById('chat-screen');
const loginForm = document.getElementById('login-form');
const emailInput = document.getElementById('email');
const loginButton = document.getElementById('login-button');
const loginError = document.getElementById('login-error');
const loginSpinner = document.getElementById('login-spinner');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const chatMessages = document.getElementById('chat-messages');
const clearMemoryBtn = document.getElementById('clear-memory-btn');
const reportBugBtn = document.getElementById('report-bug-btn');
const logoutBtn = document.getElementById('logout-btn');
const bugModal = document.getElementById('bug-modal');
const closeModalBtn = document.getElementById('close-modal-btn');
const bugDescription = document.getElementById('bug-description');
const submitBugBtn = document.getElementById('submit-bug-btn');
const cancelBugBtn = document.getElementById('cancel-bug-btn');
const clearMemoryModal = document.getElementById('clear-memory-modal');
const closeClearModalBtn = document.getElementById('close-clear-modal-btn');
const confirmClearBtn = document.getElementById('confirm-clear-btn');
const cancelClearBtn = document.getElementById('cancel-clear-btn');

// App State
const state = {
    userId: null,
    userToken: null,
    userProfile: null,
    isAuthenticated: false,
    isProcessing: false,
    currentResponse: '',
    typingTimeout: null,
    eventSource: null
};

// Event Listeners
document.addEventListener('DOMContentLoaded', init);
loginForm.addEventListener('submit', handleLogin);
messageForm.addEventListener('submit', handleSendMessage);
messageInput.addEventListener('input', handleInputChange);
clearMemoryBtn.addEventListener('click', () => toggleModal(clearMemoryModal, true));
reportBugBtn.addEventListener('click', () => toggleModal(bugModal, true));
logoutBtn.addEventListener('click', handleLogout);
closeModalBtn.addEventListener('click', () => toggleModal(bugModal, false));
submitBugBtn.addEventListener('click', handleBugReport);
cancelBugBtn.addEventListener('click', () => toggleModal(bugModal, false));
closeClearModalBtn.addEventListener('click', () => toggleModal(clearMemoryModal, false));
confirmClearBtn.addEventListener('click', handleClearMemory);
cancelClearBtn.addEventListener('click', () => toggleModal(clearMemoryModal, false));

// Suggestion buttons
document.querySelectorAll('.suggestion-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const message = btn.dataset.message;
        messageInput.value = message;
        handleInputChange();
        // Auto-submit after a short delay
        setTimeout(() => {
            if (messageInput.value === message) {
                messageForm.dispatchEvent(new Event('submit'));
            }
        }, 500);
    });
});

// Functions
function init() {
    // Check if user is already logged in (via localStorage)
    const savedUserId = localStorage.getItem('mojiUserId');
    const savedUserToken = localStorage.getItem('mojiUserToken');
    const savedUserProfile = localStorage.getItem('mojiUserProfile');
    
    if (savedUserId && savedUserToken) {
        state.userId = savedUserId;
        state.userToken = savedUserToken;
        
        // Try to parse the user profile
        try {
            state.userProfile = savedUserProfile ? JSON.parse(savedUserProfile) : {};
        } catch (e) {
            state.userProfile = {};
            console.error('Failed to parse saved user profile:', e);
        }
        
        authenticateUser();
    }
    
    // Enable/disable send button based on input
    handleInputChange();
}

function handleInputChange() {
    sendButton.disabled = !messageInput.value.trim();
}

async function handleLogin(e) {
    e.preventDefault();
    
    const email = emailInput.value.trim();
    if (!email) {
        showLoginError('Please enter your email');
        return;
    }
    
    try {
        // Show loading spinner
        loginSpinner.classList.add('active');
        loginError.textContent = '';
        
        const response = await fetch('/api/auth', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Authentication failed');
        }
        
        // Store credentials and user profile
        state.userId = data.user_id;
        state.userToken = data.user_token;
        state.userProfile = data.user_profile || {};
        
        // Save to localStorage
        localStorage.setItem('mojiUserId', state.userId);
        localStorage.setItem('mojiUserToken', state.userToken);
        localStorage.setItem('mojiUserProfile', JSON.stringify(state.userProfile));
        
        // Change to chat screen
        switchToChatScreen();
        
    } catch (error) {
        showLoginError(error.message);
    } finally {
        loginSpinner.classList.remove('active');
    }
}

function authenticateUser() {
    // Already have credentials, switch to chat screen
    if (state.userId && state.userToken) {
        switchToChatScreen();
    }
}

function switchToChatScreen() {
    state.isAuthenticated = true;
    loginScreen.classList.remove('active');
    chatScreen.classList.add('active');
    messageInput.focus();
}

function showLoginError(message) {
    loginError.textContent = message;
    emailInput.focus();
}

async function handleSendMessage(e) {
    e.preventDefault();
    
    const message = messageInput.value.trim();
    if (!message || state.isProcessing) return;
    
    state.isProcessing = true;
    
    // Add user message to chat
    addMessage(message, 'user');
    
    // Clear input
    messageInput.value = '';
    handleInputChange();
    
    // Show typing indicator
    const typingIndicator = addTypingIndicator();
    
    try {
        // Use the streaming API with user profile
        await processStreamingMessage(message, typingIndicator);
    } catch (error) {
        console.error('Error sending message:', error);
        removeElement(typingIndicator);
        addMessage(`Error: ${error.message}. Please try again.`, 'assistant');
    } finally {
        state.isProcessing = false;
        scrollToBottom();
    }
}

function processStreamingMessage(message, typingIndicator) {
    return new Promise((resolve, reject) => {
        // Reset current response
        state.currentResponse = '';
        
        // Current tool execution elements
        let currentToolDiv = null;
        let currentToolResultDiv = null;
        
        // Function to create message div only when we need it
        let assistantMessage = null;
        let assistantMessageContent = null;
        
        function getOrCreateAssistantMessage() {
            if (!assistantMessage) {
                // Create the assistant message
                assistantMessage = document.createElement('div');
                assistantMessage.className = 'message-container assistant-message';
                
                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                
                assistantMessageContent = document.createElement('div');
                assistantMessageContent.className = 'message-content';
                
                messageDiv.appendChild(assistantMessageContent);
                assistantMessage.appendChild(messageDiv);
                
                // Insert before typing indicator
                chatMessages.insertBefore(assistantMessage, typingIndicator);
            }
            return assistantMessageContent;
        }

        // Use a single GET request with query parameters for streaming
        const encodedMessage = encodeURIComponent(message);
        
        // Encode user profile for the stream URL
        let encodedUserProfile = '{}';
        if (state.userProfile) {
            try {
                encodedUserProfile = encodeURIComponent(JSON.stringify(state.userProfile));
            } catch (e) {
                console.error('Failed to encode user profile:', e);
            }
        }
        
        const streamUrl = `/api/chat/stream?user_id=${state.userId}&user_token=${state.userToken}&message=${encodedMessage}&user_profile=${encodedUserProfile}`;
        
        console.log('Establishing SSE connection with message data');
        
        // Create SSE connection with message data in URL
        const eventSource = new EventSource(streamUrl);
        
        // Store reference to allow closing
        state.eventSource = eventSource;
        
        // Configure event handlers
        eventSource.onopen = (e) => {
            console.log('EventSource connection opened');
        };
        
        eventSource.onmessage = (event) => {
            console.log('SSE message received:', event.data);
            try {
                const data = JSON.parse(event.data);
                
                // Handle connection ready event
                if (data.type === 'connection_ready') {
                    console.log('SSE connection ready for streaming');
                    return;
                }
                
                switch (data.type) {
                    case 'token':
                        // Accumulate tokens
                        state.currentResponse += data.data;
                        
                        // Update the content 
                        const contentDiv = getOrCreateAssistantMessage();
                        // Render markdown content
                        contentDiv.innerHTML = marked.parse(state.currentResponse);
                        
                        // Scroll to keep content in view
                        scrollToBottom();
                        break;
                    
                    case 'tool_start':
                        // Create tool execution UI
                        currentToolDiv = document.createElement('div');
                        currentToolDiv.className = 'tool-execution';
                        
                        const toolHeader = document.createElement('div');
                        toolHeader.className = 'tool-header';
                        toolHeader.innerHTML = `<i class="fas fa-cog fa-spin"></i> Executing: ${data.data.name}`;
                        
                        const toolArgs = document.createElement('pre');
                        toolArgs.textContent = JSON.stringify(data.data.args, null, 2);
                        
                        currentToolDiv.appendChild(toolHeader);
                        currentToolDiv.appendChild(toolArgs);
                        
                        // Add to assistant message or create one if needed
                        getOrCreateAssistantMessage().appendChild(currentToolDiv);
                        
                        // Create placeholder for results
                        currentToolResultDiv = document.createElement('div');
                        currentToolResultDiv.className = 'tool-result';
                        currentToolResultDiv.innerHTML = '<i>Processing...</i>';
                        currentToolDiv.appendChild(currentToolResultDiv);
                        
                        break;
                    
                    case 'tool_result':
                        // Update tool result if we have one
                        if (currentToolResultDiv) {
                            currentToolResultDiv.innerHTML = '';
                            
                            const resultPre = document.createElement('pre');
                            const resultStr = typeof data.data.result === 'object' 
                                ? JSON.stringify(data.data.result, null, 2)
                                : String(data.data.result);
                            
                            resultPre.textContent = resultStr;
                            currentToolResultDiv.appendChild(resultPre);
                            
                            // Clear references
                            currentToolDiv = null;
                            currentToolResultDiv = null;
                        }
                        break;
                    
                    case 'finish':
                        // Remove typing indicator
                        removeElement(typingIndicator);
                        
                        // We're done, close the connection
                        eventSource.close();
                        state.eventSource = null;
                        resolve();
                        break;
                        
                    case 'error':
                        console.error('Error in streaming response:', data.data);
                        eventSource.close();
                        state.eventSource = null;
                        reject(new Error(data.data.error));
                        break;
                        
                    default:
                        console.log('Unknown event type:', data.type);
                }
            } catch (error) {
                console.error('Error processing event:', error);
                eventSource.close();
                state.eventSource = null;
                reject(error);
            }
        };
        
        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            eventSource.close();
            state.eventSource = null;
            reject(new Error('Connection error'));
        };
    });
}

function addMessage(content, role) {
    const messageContainer = document.createElement('div');
    messageContainer.className = `message-container ${role}-message`;
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    if (role === 'user') {
        messageDiv.textContent = content;
    } else {
        // For assistant messages, parse markdown
        messageDiv.innerHTML = marked.parse(content);
    }
    
    messageContainer.appendChild(messageDiv);
    chatMessages.appendChild(messageContainer);
    
    scrollToBottom();
    return messageContainer;
}

function addTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'typing-indicator';
    typingDiv.innerHTML = '<span></span><span></span><span></span>';
    chatMessages.appendChild(typingDiv);
    
    scrollToBottom();
    return typingDiv;
}

function removeElement(element) {
    if (element && element.parentNode) {
        element.parentNode.removeChild(element);
    }
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function toggleModal(modal, show) {
    if (show) {
        modal.classList.add('active');
    } else {
        modal.classList.remove('active');
        
        // Reset fields if closing
        if (modal === bugModal) {
            bugDescription.value = '';
        }
    }
}

async function handleClearMemory() {
    try {
        const response = await fetch('/api/clear-memory', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: state.userId,
                user_token: state.userToken,
                user_profile: state.userProfile,
                reset_all: false
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Clear the chat UI
            chatMessages.innerHTML = '';
            
            // Add welcome message back
            const welcomeMessage = document.createElement('div');
            welcomeMessage.className = 'welcome-message';
            welcomeMessage.innerHTML = `
                <h3>Welcome to Moji Assistant!</h3>
                <p>I'm your movie companion. Ask me about movies, recommendations, or manage your favorite lists.</p>
                <div class="welcome-suggestions">
                    <button class="suggestion-btn" data-message="What movies are popular right now?">Popular movies</button>
                    <button class="suggestion-btn" data-message="Create a list of sci-fi movies">Create a list</button>
                    <button class="suggestion-btn" data-message="Recommend me a comedy movie">Comedy recommendation</button>
                </div>
            `;
            chatMessages.appendChild(welcomeMessage);
            
            // Reattach event listeners to suggestion buttons
            welcomeMessage.querySelectorAll('.suggestion-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    const message = btn.dataset.message;
                    messageInput.value = message;
                    handleInputChange();
                    setTimeout(() => {
                        if (messageInput.value === message) {
                            messageForm.dispatchEvent(new Event('submit'));
                        }
                    }, 500);
                });
            });
            
            // Add system message
            addMessage('Memory cleared. How can I help you today?', 'assistant');
            
            // Close modal
            toggleModal(clearMemoryModal, false);
        } else {
            throw new Error(data.error || 'Failed to clear memory');
        }
    } catch (error) {
        console.error('Error clearing memory:', error);
        addMessage(`Error: ${error.message}. Please try again.`, 'assistant');
        toggleModal(clearMemoryModal, false);
    }
}

async function handleBugReport() {
    const description = bugDescription.value.trim();
    if (!description) {
        alert('Please describe the issue before submitting.');
        return;
    }
    
    try {
        // Collect additional info for the bug report
        const reportData = {
            description: description,
            browser: navigator.userAgent,
            timestamp: new Date().toISOString(),
            screen: {
                width: window.innerWidth,
                height: window.innerHeight
            }
        };
        
        const response = await fetch('/api/report-bug', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: state.userId,
                report_data: reportData
            })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Close modal
            toggleModal(bugModal, false);
            
            // Add confirmation message
            addMessage('Bug report submitted. Thank you for helping improve Moji Assistant!', 'assistant');
        } else {
            throw new Error(data.error || 'Failed to submit bug report');
        }
    } catch (error) {
        console.error('Error submitting bug report:', error);
        alert(`Error submitting report: ${error.message}`);
    }
}

function handleLogout() {
    // Close any active connections
    if (state.eventSource) {
        state.eventSource.close();
        state.eventSource = null;
    }
    
    // Clear local storage
    localStorage.removeItem('mojiUserId');
    localStorage.removeItem('mojiUserToken');
    localStorage.removeItem('mojiUserProfile');
    
    // Reset state
    state.userId = null;
    state.userToken = null;
    state.userProfile = null;
    state.isAuthenticated = false;
    
    // Clear UI
    emailInput.value = '';
    chatMessages.innerHTML = '';
    
    // Add welcome message back
    const welcomeMessage = document.createElement('div');
    welcomeMessage.className = 'welcome-message';
    welcomeMessage.innerHTML = `
        <h3>Welcome to Moji Assistant!</h3>
        <p>I'm your movie companion. Ask me about movies, recommendations, or manage your favorite lists.</p>
        <div class="welcome-suggestions">
            <button class="suggestion-btn" data-message="What movies are popular right now?">Popular movies</button>
            <button class="suggestion-btn" data-message="Create a list of sci-fi movies">Create a list</button>
            <button class="suggestion-btn" data-message="Recommend me a comedy movie">Comedy recommendation</button>
        </div>
    `;
    chatMessages.appendChild(welcomeMessage);
    
    // Switch back to login screen
    chatScreen.classList.remove('active');
    loginScreen.classList.add('active');
}