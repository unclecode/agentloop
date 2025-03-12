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
const streamToggle = document.getElementById('stream-toggle');

// App State
const state = {
    userId: null,
    userToken: null,
    userProfile: null,
    isAuthenticated: false,
    isProcessing: false,
    currentResponse: '',
    typingTimeout: null,
    eventSource: null,
    streamingMode: true
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
streamToggle.addEventListener('change', toggleStreamingMode);

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
    
    // Initialize streaming mode from localStorage or default to toggle's checked state
    const savedStreamingMode = localStorage.getItem('mojiStreamingMode');
    if (savedStreamingMode !== null) {
        // Convert string 'true'/'false' to boolean
        state.streamingMode = savedStreamingMode === 'true';
        // Update the toggle to match the saved state
        streamToggle.checked = state.streamingMode;
    } else {
        // Default to the toggle's initial state
        state.streamingMode = streamToggle.checked;
    }

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
                    // Check if the message content is JSON
                    try {
                        // First check if content is already an object
                        if (typeof content === 'object' && content !== null) {
                            // Content is already an object, use directly
                            currentAssistantMessage = addJSONMessage(content);
                        } 
                        // Then check if content is a JSON string
                        else if (typeof content === 'string' && 
                                (content.trim().startsWith('{') || content.trim().startsWith('['))) {
                            try {
                                // Try to parse it as JSON
                                const jsonContent = JSON.parse(content);
                                // Create a custom message with the JSON and rendered views
                                currentAssistantMessage = addJSONMessage(jsonContent);
                            } catch (jsonError) {
                                // If JSON parsing fails, treat as regular message
                                console.log('Failed to parse message as JSON:', jsonError);
                                currentAssistantMessage = addMessage(content, role);
                            }
                        } else {
                            // Regular text message
                            currentAssistantMessage = addMessage(content, role);
                        }
                    } catch (e) {
                        // If any error occurs, treat as regular message
                        console.log('Error processing message:', e);
                        currentAssistantMessage = addMessage(content, role);
                    }
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

function toggleStreamingMode(e) {
    state.streamingMode = e.target.checked;
    // Save streaming mode preference to localStorage
    localStorage.setItem('mojiStreamingMode', state.streamingMode);
    console.log(`Streaming mode ${state.streamingMode ? 'enabled' : 'disabled'}`);
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
        if (state.streamingMode) {
            // Use the streaming API with user profile
            await processStreamingMessage(message, typingIndicator);
        } else {
            // Use the non-streaming API
            await processNonStreamingMessage(message, typingIndicator);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        removeElement(typingIndicator);
        addMessage(`Error: ${error.message}. Please try again.`, 'assistant');
    } finally {
        state.isProcessing = false;
        scrollToBottom();
    }
}

async function processNonStreamingMessage(message, typingIndicator) {
    try {
        console.log('Processing non-streaming message');
        
        // Encode user profile for the request
        let userProfileData = {};
        if (state.userProfile) {
            try {
                userProfileData = state.userProfile;
            } catch (e) {
                console.error('Failed to process user profile:', e);
            }
        }
        
        // Make the request to the non-streaming API
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: state.userId,
                user_token: state.userToken,
                message: message,
                user_profile: userProfileData
            })
        });
        
        const data = await response.json();
        
        if (!response.ok || !data.success) {
            throw new Error(data.error || 'Failed to process message');
        }
        
        // Remove typing indicator
        removeElement(typingIndicator);
        
        // Handle JSON response
        const responseData = data.response;
        
        if (typeof responseData === 'object') {
            // Use our shared function to create JSON message with toggle
            addJSONMessage(responseData);
        } else {
            // Regular text message
            addMessage(responseData, 'assistant');
        }
        
    } catch (error) {
        console.error('Error in non-streaming request:', error);
        throw error;
    }
}

// UI Generators for different response types
function createMoviesDataUI(data) {
    const container = document.createElement('div');
    container.className = 'movies-data-container';
    
    // Add status and explanation if available
    if (data.status !== undefined) {
        const statusBar = document.createElement('div');
        statusBar.className = `status-bar ${data.status ? 'success' : 'error'}`;
        statusBar.innerHTML = data.status 
            ? '<i class="fas fa-check-circle"></i> Movies found' 
            : '<i class="fas fa-exclamation-circle"></i> No movies found';
        container.appendChild(statusBar);
    }
    
    if (data.explanation) {
        const explanation = document.createElement('p');
        explanation.className = 'movie-explanation';
        explanation.textContent = data.explanation;
        container.appendChild(explanation);
    }
    
    // Create movie grid
    if (data.movies && data.movies.length > 0) {
        const movieGrid = document.createElement('div');
        movieGrid.className = 'movie-grid';
        
        data.movies.forEach(movie => {
            const movieCard = document.createElement('div');
            movieCard.className = 'movie-card';
            
            // Movie poster
            const posterContainer = document.createElement('div');
            posterContainer.className = 'movie-poster';
            
            // For movie suggestions, we have tmdb_id which we can use to create a poster URL
            if (movie.tmdb_id) {
                // Create a fetch request to get the actual poster path using a public API
                fetch(`/api/movie-poster?tmdb_id=${movie.tmdb_id}&type=${movie.t}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.poster_path) {
                            const posterUrl = `https://image.tmdb.org/t/p/w500${data.poster_path}`;
                            posterContainer.innerHTML = `<img src="${posterUrl}" alt="${movie.n}" onerror="this.onerror=null; this.parentNode.innerHTML='<div class=\\'poster-placeholder\\'><i class=\\'fas fa-film\\'></i><span>${movie.n}</span></div>';">`;
                        } else {
                            // Fallback to placeholder
                            posterContainer.innerHTML = `
                                <div class="poster-placeholder">
                                    <i class="fas fa-film"></i>
                                    <span>${movie.n}</span>
                                </div>`;
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching poster:', error);
                        // Fallback to placeholder on error
                        posterContainer.innerHTML = `
                            <div class="poster-placeholder">
                                <i class="fas fa-film"></i>
                                <span>${movie.n}</span>
                            </div>`;
                    });
                
                // Start with placeholder while loading
                posterContainer.innerHTML = `
                    <div class="poster-placeholder loading">
                        <i class="fas fa-spinner fa-spin"></i>
                        <span>${movie.n}</span>
                    </div>`;
            } else if (movie.poster_path) {
                if (movie.poster_path.startsWith('http')) {
                    // Direct poster URL
                    posterContainer.innerHTML = `<img src="${movie.poster_path}" alt="${movie.n}" onerror="this.onerror=null; this.parentNode.innerHTML='<div class=\\'poster-placeholder\\'><i class=\\'fas fa-film\\'></i><span>${movie.n}</span></div>';">`;
                } else if (movie.poster_path.startsWith('/')) {
                    // TMDB poster path format
                    const tmdbPosterUrl = `https://image.tmdb.org/t/p/w500${movie.poster_path}`;
                    posterContainer.innerHTML = `<img src="${tmdbPosterUrl}" alt="${movie.n}" onerror="this.onerror=null; this.parentNode.innerHTML='<div class=\\'poster-placeholder\\'><i class=\\'fas fa-film\\'></i><span>${movie.n}</span></div>';">`;
                }
            } else {
                // Fallback to placeholder with title
                posterContainer.innerHTML = `
                    <div class="poster-placeholder">
                        <i class="fas fa-film"></i>
                        <span>${movie.n}</span>
                    </div>`;
            }
            
            // Movie info
            const movieInfo = document.createElement('div');
            movieInfo.className = 'movie-info';
            
            const movieTitle = document.createElement('h3');
            movieTitle.className = 'movie-title';
            movieTitle.textContent = movie.n;
            
            const movieYear = document.createElement('div');
            movieYear.className = 'movie-year';
            movieYear.textContent = movie.y;
            
            const movieType = document.createElement('div');
            movieType.className = 'movie-type';
            movieType.textContent = movie.t === 'm' ? 'Movie' : 'TV Show';
            
            // Assemble movie card
            movieInfo.appendChild(movieTitle);
            movieInfo.appendChild(movieYear);
            movieInfo.appendChild(movieType);
            
            movieCard.appendChild(posterContainer);
            movieCard.appendChild(movieInfo);
            
            // Add trailer button if available
            if (movie.trailer_url) {
                const trailerBtn = document.createElement('button');
                trailerBtn.className = 'trailer-btn';
                trailerBtn.innerHTML = '<i class="fas fa-play"></i> Trailer';
                trailerBtn.setAttribute('data-trailer-url', movie.trailer_url);
                trailerBtn.addEventListener('click', (e) => {
                    // Open trailer in a modal or new window
                    window.open(movie.trailer_url, '_blank');
                });
                movieCard.appendChild(trailerBtn);
            }
            
            movieGrid.appendChild(movieCard);
        });
        
        container.appendChild(movieGrid);
    } else {
        // No movies message
        const noMovies = document.createElement('div');
        noMovies.className = 'no-movies';
        noMovies.innerHTML = '<i class="fas fa-film"></i> No movies available';
        container.appendChild(noMovies);
    }
    
    return container;
}

function createTrailerDataUI(data) {
    const container = document.createElement('div');
    container.className = 'trailer-data-container';
    
    // Movie info section
    const movieInfo = document.createElement('div');
    movieInfo.className = 'trailer-movie-info';
    
    const movieTitle = document.createElement('h3');
    movieTitle.textContent = data.movie_title;
    
    const movieDetails = document.createElement('div');
    movieDetails.className = 'trailer-movie-details';
    movieDetails.innerHTML = `
        <div class="release-date"><i class="fas fa-calendar"></i> ${data.release_date}</div>
    `;
    
    const movieOverview = document.createElement('p');
    movieOverview.className = 'trailer-movie-overview';
    movieOverview.textContent = data.overview;
    
    movieInfo.appendChild(movieTitle);
    movieInfo.appendChild(movieDetails);
    movieInfo.appendChild(movieOverview);
    
    // Video player section
    const videoContainer = document.createElement('div');
    videoContainer.className = 'trailer-video-container';
    
    // Extract YouTube ID if it's a YouTube URL
    let videoId = '';
    if (data.trailer_url && data.trailer_url.includes('youtube.com')) {
        const url = new URL(data.trailer_url);
        videoId = url.searchParams.get('v');
    } else if (data.trailer_url && data.trailer_url.includes('youtu.be')) {
        videoId = data.trailer_url.split('/').pop();
    }
    
    if (videoId) {
        // Create thumbnail with play button instead of embedding iframe
        videoContainer.innerHTML = `
            <div class="video-thumbnail" data-video-id="${videoId}">
                <img src="https://img.youtube.com/vi/${videoId}/0.jpg" alt="Trailer thumbnail">
                <div class="play-button">
                    <i class="fas fa-play"></i>
                </div>
            </div>
            <a href="${data.trailer_url}" target="_blank" class="watch-on-youtube">
                <i class="fab fa-youtube"></i> Watch on YouTube
            </a>
        `;
        
        // Add click handler to open YouTube
        const thumbnail = videoContainer.querySelector('.video-thumbnail');
        thumbnail.addEventListener('click', () => {
            window.open(data.trailer_url, '_blank');
        });
    } else {
        // Fallback if not a YouTube URL
        videoContainer.innerHTML = `
            <div class="trailer-link">
                <a href="${data.trailer_url}" target="_blank">
                    <i class="fas fa-external-link-alt"></i> Watch Trailer
                </a>
            </div>
        `;
    }
    
    container.appendChild(movieInfo);
    container.appendChild(videoContainer);
    
    return container;
}

function createMovieInfoUI(data) {
    const container = document.createElement('div');
    container.className = 'movie-info-container';
    
    // Original question
    const questionSection = document.createElement('div');
    questionSection.className = 'movie-info-question';
    questionSection.innerHTML = `<i class="fas fa-question-circle"></i> <span>${data.question}</span>`;
    
    // Answer section
    const answerSection = document.createElement('div');
    answerSection.className = 'movie-info-answer';
    answerSection.innerHTML = marked.parse(data.answer);
    
    container.appendChild(questionSection);
    container.appendChild(answerSection);
    
    // Related movies if available
    if (data.related_movies && data.related_movies.length > 0) {
        const relatedMoviesSection = document.createElement('div');
        relatedMoviesSection.className = 'related-movies-section';
        
        const relatedTitle = document.createElement('h4');
        relatedTitle.textContent = 'Related Movies';
        relatedMoviesSection.appendChild(relatedTitle);
        
        const moviesList = document.createElement('div');
        moviesList.className = 'related-movies-list';
        
        data.related_movies.forEach(movie => {
            const movieItem = document.createElement('div');
            movieItem.className = 'related-movie-item';
            
            // Check if we have poster information
            let movieIconHTML = '';
            
            // For movie suggestions with tmdb_id, fetch the poster
            if (movie.tmdb_id) {
                // Create a loading placeholder
                movieIconHTML = `<i class="fas fa-spinner fa-spin"></i>`;
                
                // Fetch the poster path
                fetch(`/api/movie-poster?tmdb_id=${movie.tmdb_id}&type=${movie.t}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.success && data.poster_path) {
                            const posterUrl = `https://image.tmdb.org/t/p/w92${data.poster_path}`;
                            const posterImg = `<img src="${posterUrl}" alt="${movie.n}" onerror="this.onerror=null; this.src=''; this.parentNode.innerHTML='<i class=\\'fas fa-film\\'></i>';">`;
                            movieItem.querySelector('.related-movie-icon').innerHTML = posterImg;
                        } else {
                            movieItem.querySelector('.related-movie-icon').innerHTML = `<i class="fas fa-film"></i>`;
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching poster for related movie:', error);
                        movieItem.querySelector('.related-movie-icon').innerHTML = `<i class="fas fa-film"></i>`;
                    });
            } else if (movie.poster_path && movie.poster_path.startsWith('http')) {
                // Direct poster URL
                movieIconHTML = `<img src="${movie.poster_path}" alt="${movie.n}" onerror="this.onerror=null; this.src=''; this.parentNode.innerHTML='<i class=\\'fas fa-film\\'></i>';">`;
            } else if (movie.poster_path && movie.poster_path.startsWith('/')) {
                // TMDB poster path format
                const tmdbPosterUrl = `https://image.tmdb.org/t/p/w92${movie.poster_path}`;
                movieIconHTML = `<img src="${tmdbPosterUrl}" alt="${movie.n}" onerror="this.onerror=null; this.src=''; this.parentNode.innerHTML='<i class=\\'fas fa-film\\'></i>';">`;
            } else {
                // Fallback to icon
                movieIconHTML = `<i class="fas fa-film"></i>`;
            }
            
            movieItem.innerHTML = `
                <div class="related-movie-icon">${movieIconHTML}</div>
                <div class="related-movie-details">
                    <div class="related-movie-title">${movie.n}</div>
                    <div class="related-movie-year">${movie.y}</div>
                </div>
            `;
            
            moviesList.appendChild(movieItem);
        });
        
        relatedMoviesSection.appendChild(moviesList);
        container.appendChild(relatedMoviesSection);
    }
    
    // Sources if available
    if (data.sources && data.sources.length > 0) {
        const sourcesSection = document.createElement('div');
        sourcesSection.className = 'sources-section';
        
        const sourcesTitle = document.createElement('div');
        sourcesTitle.className = 'sources-title';
        sourcesTitle.innerHTML = '<i class="fas fa-book"></i> Sources';
        
        const sourcesList = document.createElement('ul');
        sourcesList.className = 'sources-list';
        
        data.sources.forEach(source => {
            const sourceItem = document.createElement('li');
            sourceItem.textContent = source;
            sourcesList.appendChild(sourceItem);
        });
        
        sourcesSection.appendChild(sourcesTitle);
        sourcesSection.appendChild(sourcesList);
        container.appendChild(sourcesSection);
    }
    
    return container;
}

function createTextResponseUI(data) {
    const container = document.createElement('div');
    container.className = 'text-response-container';
    
    // Main content
    const contentSection = document.createElement('div');
    contentSection.className = 'text-response-content';
    contentSection.innerHTML = marked.parse(data.content);
    
    container.appendChild(contentSection);
    
    // Relevant docs if available
    if (data.relevant_docs && data.relevant_docs.length > 0) {
        const docsSection = document.createElement('div');
        docsSection.className = 'relevant-docs-section';
        
        const docsTitle = document.createElement('div');
        docsTitle.className = 'docs-title';
        docsTitle.innerHTML = '<i class="fas fa-file-alt"></i> Relevant Documents';
        
        const docsList = document.createElement('ul');
        docsList.className = 'docs-list';
        
        data.relevant_docs.forEach(doc => {
            const docItem = document.createElement('li');
            docItem.textContent = doc;
            docsList.appendChild(docItem);
        });
        
        docsSection.appendChild(docsTitle);
        docsSection.appendChild(docsList);
        container.appendChild(docsSection);
    }
    
    return container;
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

function addJSONMessage(responseData) {
    const messageContainer = document.createElement('div');
    messageContainer.className = 'message-container assistant-message';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    
    // Create a formatted JSON display with toggle
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Create the view toggle
    const viewToggle = document.createElement('div');
    viewToggle.className = 'view-toggle';
    
    const toggleButton = document.createElement('button');
    toggleButton.className = 'toggle-view-btn';
    toggleButton.innerHTML = '<i class="fas fa-exchange-alt"></i> Show JSON';
    viewToggle.appendChild(toggleButton);
    
    contentDiv.appendChild(viewToggle);
    
    // Container for both views
    const viewsContainer = document.createElement('div');
    viewsContainer.className = 'views-container';
    
    // JSON view
    const jsonView = document.createElement('div');
    jsonView.className = 'view json-view';
    
    const jsonPre = document.createElement('pre');
    jsonPre.className = 'json-response';
    jsonPre.textContent = JSON.stringify(responseData, null, 2);
    
    jsonView.appendChild(jsonPre);
    viewsContainer.appendChild(jsonView);
    
    // Rendered view
    const renderedView = document.createElement('div');
    renderedView.className = 'view rendered-view active';
    
    // Determine the type of response and create appropriate UI
    responseData.type = responseData.type || responseData.output_type;
    if (responseData.type) {
        console.log(`Creating UI for response type: ${responseData.type}`);
        switch (responseData.type) {
            case 'movie_json':
                renderedView.appendChild(createMoviesDataUI(responseData.data));
                break;
            case 'trailer_json':
                renderedView.appendChild(createTrailerDataUI(responseData.data));
                break;
            case 'movie_info':
                renderedView.appendChild(createMovieInfoUI(responseData.data));
                break;
            case 'text_response':
            case 'text':
                renderedView.appendChild(createTextResponseUI(responseData.data));
                break;
            default:
                // Fallback for unknown types
                const unknownTypeMessage = document.createElement('div');
                unknownTypeMessage.className = 'unknown-type-message';
                unknownTypeMessage.textContent = `Unknown response type: ${responseData.type}`;
                renderedView.appendChild(unknownTypeMessage);
        }
    } else {
        // Generic UI for unknown structure
        console.log('Creating generic UI for JSON without type field:', responseData);
        const genericUI = document.createElement('div');
        genericUI.className = 'generic-json-ui';
        genericUI.innerHTML = '<p>Custom JSON response</p>';
        
        // Try to extract meaningful data from various properties
        if (responseData.content) {
            const contentPara = document.createElement('p');
            contentPara.textContent = responseData.content;
            genericUI.appendChild(contentPara);
        } else if (responseData.message) {
            const messagePara = document.createElement('p');
            messagePara.textContent = responseData.message;
            genericUI.appendChild(messagePara);
        } else if (responseData.response) {
            const responsePara = document.createElement('p');
            responsePara.textContent = responseData.response;
            genericUI.appendChild(responsePara);
        }
        
        // Look for movie data even without explicit type
        if (responseData.movies || responseData.data?.movies) {
            const movieData = responseData.movies ? responseData : responseData.data;
            renderedView.innerHTML = ''; // Clear previous content
            renderedView.appendChild(createMoviesDataUI(movieData));
        }
        
        renderedView.appendChild(genericUI);
    }
    
    viewsContainer.appendChild(renderedView);
    contentDiv.appendChild(viewsContainer);
    
    // Add toggle functionality
    toggleButton.addEventListener('click', () => {
        jsonView.classList.toggle('active');
        renderedView.classList.toggle('active');
        toggleButton.innerHTML = jsonView.classList.contains('active') 
            ? '<i class="fas fa-exchange-alt"></i> Show Rendered' 
            : '<i class="fas fa-exchange-alt"></i> Show JSON';
    });
    
    messageDiv.appendChild(contentDiv);
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
