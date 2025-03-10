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

// Function to load conversation history from the server
async function loadConversationHistory() {
    try {
        // Clear any existing messages first
        chatMessages.innerHTML = '';

        // Add loading indicator
        const loadingIndicator = addTypingIndicator();

        // Fetch conversation history from the server
        const response = await fetch(`/api/history?user_id=${state.userId}&user_token=${state.userToken}`);
        const data = await response.json();

        // Remove loading indicator
        removeElement(loadingIndicator);

        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to load conversation history');
        }

        // Check if we have any messages
        if (data.messages && data.messages.length > 0) {
            // Process and group tool messages
            let currentAssistantMessage = null;
            let pendingToolMessages = [];
            
            data.messages.forEach(msg => {
                const content = msg.content;
                const role = msg.role;
                
                // If this is a tool message, collect it for later processing
                if (role === 'tool' || role === "tool-call" || role === "function") {
                    pendingToolMessages.push(msg);
                    return;
                }
                
                // If this is an assistant message and we have pending tool messages,
                // we need to render the tool messages before this assistant message
                if (role === 'assistant' && pendingToolMessages.length > 0) {
                    // Create or get the assistant message container to append tools to
                    if (!currentAssistantMessage) {
                        currentAssistantMessage = createAssistantMessageWithTools(pendingToolMessages);
                        chatMessages.appendChild(currentAssistantMessage);
                    } else {
                        // Add tools to existing assistant message
                        appendToolsToMessage(currentAssistantMessage, pendingToolMessages);
                    }
                    pendingToolMessages = [];
                }
                
                // Now add the regular message
                if (role === 'assistant') {
                    currentAssistantMessage = addMessage(content, role);
                } else if (role === 'user') {
                    addMessage(content, role);
                    currentAssistantMessage = null; // Reset when user message encountered
                } else {
                    // Skip other message types that aren't user, assistant, or tool
                    console.log(`Skipping unknown message type: ${role}`);
                }
            });
            
            // Process any remaining tool messages
            if (pendingToolMessages.length > 0 && currentAssistantMessage) {
                appendToolsToMessage(currentAssistantMessage, pendingToolMessages);
            }

            // Scroll to bottom
            scrollToBottom();
        } else {
            // If no messages, display welcome message
            displayWelcomeMessage();
        }
    } catch (error) {
        console.error('Error loading conversation history:', error);
        // If error, display welcome message
        displayWelcomeMessage();
    }
}

// Function to display welcome message
function displayWelcomeMessage() {
    // Clear chat messages
    chatMessages.innerHTML = '';

    // Add welcome message
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

        // Load conversation history
        loadConversationHistory();
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

        // Function to create message div only when we need it
        let assistantMessage = null;
        let assistantMessageContent = null;
        
        // Tool tracking
        let toolMessages = [];
        let toolsWrapper = null;
        let toolsContainer = null;
        let currentToolDiv = null;

        function getOrCreateAssistantMessage() {
            if (!assistantMessage) {
                // Create the assistant message
                assistantMessage = document.createElement('div');
                assistantMessage.className = 'message-container assistant-message';

                const messageDiv = document.createElement('div');
                messageDiv.className = 'message';
                
                // Create tools wrapper first (will be at the top)
                toolsWrapper = document.createElement('div');
                toolsWrapper.className = 'tools-wrapper collapsed';
                
                // Create toggle header
                const toggleHeader = document.createElement('div');
                toggleHeader.className = 'tools-toggle-header';
                toggleHeader.innerHTML = `<i class="fas fa-cogs"></i> Tool Executions <span class="tools-count">(0)</span>`;
                toggleHeader.addEventListener('click', () => {
                    toolsWrapper.classList.toggle('collapsed');
                });
                
                toolsWrapper.appendChild(toggleHeader);
                
                // Create tools container
                toolsContainer = document.createElement('div');
                toolsContainer.className = 'tools-container';
                toolsWrapper.appendChild(toolsContainer);
                
                // Hide tools wrapper initially - we'll show it when tools are added
                toolsWrapper.style.display = 'none';
                
                messageDiv.appendChild(toolsWrapper);

                // Create message content div for the actual response
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
                        toolHeader.innerHTML = `<i class="fas fa-cog fa-spin"></i> ${data.data.name}`;

                        const toolArgs = document.createElement('pre');
                        toolArgs.className = 'tool-args';
                        toolArgs.textContent = JSON.stringify(data.data.args, null, 2);

                        currentToolDiv.appendChild(toolHeader);
                        currentToolDiv.appendChild(toolArgs);
                        
                        // Create placeholder for results
                        const toolResultDiv = document.createElement('div');
                        toolResultDiv.className = 'tool-result';
                        toolResultDiv.innerHTML = '<i>Processing...</i>';
                        currentToolDiv.appendChild(toolResultDiv);

                        // Make sure we have the assistant message and tools container
                        getOrCreateAssistantMessage();
                        
                        // Show the tools wrapper if it was hidden
                        if (toolsWrapper.style.display === 'none') {
                            toolsWrapper.style.display = 'block';
                        }
                        
                        // Add the tool to the container
                        toolsContainer.appendChild(currentToolDiv);
                        
                        // Update the tool count
                        toolMessages.push(data.data);
                        const toolCountEl = toolsWrapper.querySelector('.tools-count');
                        toolCountEl.textContent = `(${toolMessages.length})`;
                        
                        // Scroll to bottom when tool call starts
                        scrollToBottom();
                        
                        break;

                    case 'tool_result':
                        // Find the most recent tool div without a result
                        const toolDivs = toolsContainer.querySelectorAll('.tool-execution');
                        let targetToolDiv = null;
                        
                        for (let i = toolDivs.length - 1; i >= 0; i--) {
                            const resultDiv = toolDivs[i].querySelector('.tool-result');
                            if (resultDiv && resultDiv.innerHTML === '<i>Processing...</i>') {
                                targetToolDiv = toolDivs[i];
                                break;
                            }
                        }
                        
                        if (targetToolDiv) {
                            const resultDiv = targetToolDiv.querySelector('.tool-result');
                            resultDiv.innerHTML = '';

                            const resultPre = document.createElement('pre');
                            const resultStr = typeof data.data.result === 'object'
                                ? JSON.stringify(data.data.result, null, 2)
                                : String(data.data.result);

                            resultPre.textContent = resultStr;
                            resultDiv.appendChild(resultPre);
                            
                            // Scroll to bottom when tool result is received
                            scrollToBottom();
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
                // Display error message in the chat window
                const contentDiv = getOrCreateAssistantMessage();
                if (contentDiv) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error-message';
                    errorDiv.textContent = 'Sorry, there was an error processing your request. Please try again.';
                    errorDiv.style.color = 'var(--error-color)';
                    errorDiv.style.padding = '10px';
                    errorDiv.style.margin = '5px 0';
                    errorDiv.style.borderRadius = '5px';
                    errorDiv.style.backgroundColor = 'rgba(244, 67, 54, 0.1)';
                    contentDiv.appendChild(errorDiv);
                }
                eventSource.close();
                state.eventSource = null;
                reject(error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('EventSource error:', error);
            // Display error message in the chat window
            const contentDiv = getOrCreateAssistantMessage();
            if (contentDiv) {
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message';
                errorDiv.textContent = 'Sorry, there was an error processing your request. Please try again.';
                errorDiv.style.color = 'var(--error-color)';
                errorDiv.style.padding = '10px';
                errorDiv.style.margin = '5px 0';
                errorDiv.style.borderRadius = '5px';
                errorDiv.style.backgroundColor = 'rgba(244, 67, 54, 0.1)';
                contentDiv.appendChild(errorDiv);
            }
            eventSource.close();
            state.eventSource = null;
            reject(new Error('Connection error'));
        };
    });
}

// Create a message container for the assistant that includes tool messages
function createAssistantMessageWithTools(toolMessages) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container assistant-message';

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';

    // Create the tool execution wrapper that will be collapsible
    const toolsWrapper = document.createElement('div');
    toolsWrapper.className = 'tools-wrapper collapsed';
    
    // Add the collapsed tools container with toggle button
    const toolsContainer = document.createElement('div');
    toolsContainer.className = 'tools-container';
    
    // Create toggle header
    const toggleHeader = document.createElement('div');
    toggleHeader.className = 'tools-toggle-header';
    toggleHeader.innerHTML = `<i class="fas fa-cogs"></i> Tool Executions <span class="tools-count">(${toolMessages.length})</span>`;
    toggleHeader.addEventListener('click', () => {
        toolsWrapper.classList.toggle('collapsed');
    });
    
    toolsWrapper.appendChild(toggleHeader);
    
    // Add each tool message to the container
    toolMessages.forEach(toolMsg => {
        const toolDiv = createToolExecutionElement(toolMsg.content);
        toolsContainer.appendChild(toolDiv);
    });
    
    toolsWrapper.appendChild(toolsContainer);
    messageDiv.appendChild(toolsWrapper);
    messageContainer.appendChild(messageDiv);
    
    return messageContainer;
}

// Add tool messages to an existing assistant message
function appendToolsToMessage(messageContainer, toolMessages) {
    // Find the message div inside the container
    const messageDiv = messageContainer.querySelector('.message');
    
    // Check if there's already a tools wrapper
    let toolsWrapper = messageDiv.querySelector('.tools-wrapper');
    
    if (!toolsWrapper) {
        // Create the tools wrapper if it doesn't exist
        toolsWrapper = document.createElement('div');
        toolsWrapper.className = 'tools-wrapper collapsed';
        
        // Create toggle header
        const toggleHeader = document.createElement('div');
        toggleHeader.className = 'tools-toggle-header';
        toggleHeader.innerHTML = `<i class="fas fa-cogs"></i> Tool Executions <span class="tools-count">(${toolMessages.length})</span>`;
        toggleHeader.addEventListener('click', () => {
            toolsWrapper.classList.toggle('collapsed');
        });
        
        toolsWrapper.appendChild(toggleHeader);
        
        // Create tools container
        const toolsContainer = document.createElement('div');
        toolsContainer.className = 'tools-container';
        toolsWrapper.appendChild(toolsContainer);
        
        // Add to the message div before any existing content
        messageDiv.insertBefore(toolsWrapper, messageDiv.firstChild);
    } else {
        // Update the tool count
        const currentCount = parseInt(toolsWrapper.querySelector('.tools-count').textContent.match(/\d+/)[0]);
        toolsWrapper.querySelector('.tools-count').textContent = `(${currentCount + toolMessages.length})`;
    }
    
    // Add each tool message to the container
    const toolsContainer = toolsWrapper.querySelector('.tools-container');
    toolMessages.forEach(toolMsg => {
        const toolDiv = createToolExecutionElement(toolMsg.content);
        toolsContainer.appendChild(toolDiv);
    });
}

// Create a single tool execution element
function createToolExecutionElement(content) {
    // Parse the content (could be JSON or text)
    let toolData = content;
    let toolName = 'Unknown Tool';
    let toolArgs = {};
    let toolResult = null;
    
    // Handle the content based on its type
    try {
        if (typeof content === 'string') {
            // Case 1: Function call format with "with args:" pattern
            // Example: "Function call: get_list_items with args: {'list_id': 'BIG_FIVE'}"
            if (content.includes('with args:')) {
                let functionMatch = content.match(/Function call:\s+(\w+)(?:\s+with\s+args:)?\s*(.*)/i);
                if (!functionMatch) {
                    // Try alternative pattern
                    functionMatch = content.match(/Tool call:\s+(\w+)(?:\s+with\s+args:)?\s*(.*)/i);
                }
                
                if (functionMatch) {
                    // Extract function name
                    toolName = functionMatch[1].trim();
                    
                    // Extract arguments
                    let argsText = functionMatch[2]?.trim() || '';
                    if (argsText) {
                        try {
                            // Try to parse as JSON - handle single quotes and convert to double quotes
                            argsText = argsText.replace(/'/g, '"')
                                              .replace(/(\w+):/g, '"$1":');
                            toolArgs = JSON.parse(argsText);
                        } catch (e) {
                            console.log('Failed to parse function args:', e);
                            toolArgs = { raw_args: argsText };
                        }
                    }
                }
            }
            // Case 2: Standard function call format
            else if (content.startsWith('Function call:') || content.startsWith('Tool call:')) {
                const lines = content.split('\n');
                
                // Extract tool name from first line (e.g., "Function call: get_movie_info")
                const callLine = lines[0];
                toolName = callLine.split(':')[1]?.trim() || 'Unknown Tool';
                
                // Try to extract arguments from subsequent lines
                if (lines.length > 1) {
                    try {
                        // Look for a JSON block in the remaining text
                        const argsText = lines.slice(1).join('\n').trim();
                        if (argsText) {
                            toolArgs = JSON.parse(argsText);
                        }
                    } catch (e) {
                        // If JSON parsing fails, just use the text as is
                        toolArgs = { 'raw_arguments': lines.slice(1).join('\n').trim() };
                    }
                }
            }
            // Case 3: Function result format
            // Example: "Function result: {"status": true, "message": "Retrieved 6 lists", ...}"
            else if (content.includes('Function result:') || content.includes('Tool result:')) {
                // Extract JSON from the result string
                let jsonStart = content.indexOf('{');
                if (jsonStart !== -1) {
                    try {
                        toolResult = JSON.parse(content.substring(jsonStart));
                        
                        // If we have a structured result with type/name, use it
                        if (toolResult.type) {
                            toolName = `${toolResult.type.charAt(0).toUpperCase() + toolResult.type.slice(1)} Result`;
                        }
                    } catch (e) {
                        console.log('Failed to parse function result:', e);
                        toolResult = { raw_result: content.substring(jsonStart) };
                    }
                } else {
                    // No JSON found, use the whole string after the prefix
                    const prefix = content.includes('Function result:') ? 'Function result:' : 'Tool result:';
                    toolResult = content.substring(content.indexOf(prefix) + prefix.length).trim();
                }
            }
            // Case 4: Plain JSON
            else {
                try {
                    toolData = JSON.parse(content);
                } catch (e) {
                    // Just use the content as text
                    toolResult = content;
                }
            }
        }
    } catch (e) {
        console.log('Failed to process tool content:', e);
    }
    
    // Extract information from toolData if it's an object
    if (toolData && typeof toolData === 'object') {
        // Extract tool name
        toolName = toolData.name || toolData.tool || toolData.function || toolName;
        
        // Extract arguments
        toolArgs = toolData.args || toolData.arguments || toolData.parameters || toolArgs;
        
        // Extract result
        toolResult = toolData.result || toolData.response || toolData.output || toolResult;
    }
    
    // Create the tool execution element
    const toolDiv = document.createElement('div');
    toolDiv.className = 'tool-execution';
    
    // Create tool header
    const toolHeader = document.createElement('div');
    toolHeader.className = 'tool-header';
    toolHeader.innerHTML = `<i class="fas fa-cog"></i> ${toolName}`;
    toolDiv.appendChild(toolHeader);
    
    // Create arguments section if we have arguments
    if (Object.keys(toolArgs).length > 0) {
        const toolArgsElement = document.createElement('pre');
        toolArgsElement.className = 'tool-args';
        toolArgsElement.textContent = typeof toolArgs === 'object' 
            ? JSON.stringify(toolArgs, null, 2) 
            : String(toolArgs);
        toolDiv.appendChild(toolArgsElement);
    }
    
    // Create result section if available
    if (toolResult !== null) {
        const toolResultDiv = document.createElement('div');
        toolResultDiv.className = 'tool-result';
        
        // Create formatted result display
        if (typeof toolResult === 'object') {
            // For data-rich results like movie lists, create a more structured view
            if (toolResult.data && toolResult.type === 'list') {
                const resultHeader = document.createElement('div');
                resultHeader.className = 'result-header';
                resultHeader.textContent = toolResult.message || 'Result';
                toolResultDiv.appendChild(resultHeader);
                
                if (toolResult.data.items && Array.isArray(toolResult.data.items)) {
                    const listElement = document.createElement('ul');
                    listElement.className = 'result-list';
                    
                    toolResult.data.items.forEach(item => {
                        const listItem = document.createElement('li');
                        listItem.textContent = item.name || String(item);
                        if (item.list_id) {
                            listItem.setAttribute('data-id', item.list_id);
                        }
                        listElement.appendChild(listItem);
                    });
                    
                    toolResultDiv.appendChild(listElement);
                }
            } else {
                // Standard JSON display
                const resultPre = document.createElement('pre');
                resultPre.textContent = JSON.stringify(toolResult, null, 2);
                toolResultDiv.appendChild(resultPre);
            }
        } else {
            // Text result
            const resultPre = document.createElement('pre');
            resultPre.textContent = String(toolResult);
            toolResultDiv.appendChild(resultPre);
        }
        
        toolDiv.appendChild(toolResultDiv);
    }
    
    return toolDiv;
}

function addMessage(content, role) {
    const messageContainer = document.createElement('div');
    messageContainer.className = `message-container ${role}-message`;

    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';

    if (role === 'user') {
        messageDiv.textContent = content;
    } else {
        // Create message content div
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // For assistant messages, parse markdown
        contentDiv.innerHTML = marked.parse(content);
        messageDiv.appendChild(contentDiv);
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
            // Display welcome message
            displayWelcomeMessage();

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

    // Switch back to login screen
    chatScreen.classList.remove('active');
    loginScreen.classList.add('active');
}
