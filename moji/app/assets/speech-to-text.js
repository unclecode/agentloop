/**
 * speech-to-text.js - Handles speech recognition and transcription functionality
 * for the Moji application using the Web Speech API for browser recording
 * and OpenAI Whisper API for accurate transcription.
 */

// MediaRecorder and audio context configuration
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioContext = null;
let micButton = null;
let messageInputCtrl = null;
let startTime = null;

// Safari detection
const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;

// Initialize speech-to-text functionality
function initSpeechToText() {
    console.log('Initializing speech-to-text functionality');
    
    // Get DOM elements
    micButton = document.getElementById('mic-button');
    messageInputCtrl = document.getElementById('message-input');
    
    if (!micButton) {
        console.error('Microphone button not found');
        return;
    }
    
    // Check if browser supports getUserMedia
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('Browser does not support audio recording');
        micButton.style.display = 'none';
        return;
    }

    // Add event listener for microphone button
    micButton.addEventListener('click', toggleRecording);
    
    // Make sure the full button is clickable, not just the icon
    const ensureClickable = () => {
        // Make sure the icon doesn't capture clicks instead of the button
        const micIcon = micButton.querySelector('i');
        if (micIcon) {
            micIcon.style.pointerEvents = 'none';
        }
        
        // Ensure the entire button is clickable
        micButton.style.position = 'relative';
        micButton.style.zIndex = '1';
    };
    
    // Apply fix for button clickability
    ensureClickable();
    
    // Set initial state
    setButtonState('idle');
}

// Toggle recording state
async function toggleRecording() {
    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }
}

// Start recording audio
async function startRecording() {
    try {
        audioChunks = [];
        
        // Set button to recording state
        setButtonState('recording');
        
        // Get audio stream with properly configured constraints
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                // Safari has issues with sampleRate/channelCount settings
                ...(isSafari ? {} : { sampleRate: 44100, channelCount: 1 })
            }
        });
        
        // Create or reset AudioContext
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Configure MediaRecorder with appropriate MIME type for browser compatibility
        let mimeType = 'audio/webm';
        
        // Safari needs MP4 format
        if (isSafari || isIOS) {
            mimeType = 'audio/mp4';
        }
        
        // Create MediaRecorder instance with optimal settings
        try {
            mediaRecorder = new MediaRecorder(stream, { 
                mimeType: mimeType,
                audioBitsPerSecond: 128000
            });
        } catch (e) {
            // Fallback if browser doesn't support specified MIME type
            console.warn('Specified MIME type not supported, using default', e);
            mediaRecorder = new MediaRecorder(stream);
        }
        
        // Set up event handlers
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };
        
        // Handle recording stop
        mediaRecorder.onstop = handleRecordingStop;
        
        // Start recording
        startTime = Date.now();
        mediaRecorder.start(100); // Collect data in 100ms chunks
        isRecording = true;
        
        console.log('Recording started');
        
        // Set a maximum recording duration (30 seconds)
        setTimeout(() => {
            if (isRecording) {
                console.log('Maximum recording duration reached');
                stopRecording();
            }
        }, 30000);
        
    } catch (error) {
        console.error('Error starting recording:', error);
        setButtonState('idle');
        showToast('Could not access microphone. Please check permissions.');
    }
}

// Stop recording audio
function stopRecording() {
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        return;
    }
    
    // Set button to processing state
    setButtonState('processing');
    
    // Stop the media recorder
    mediaRecorder.stop();
    isRecording = false;
    
    // Stop all tracks on the active stream
    if (mediaRecorder.stream) {
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
    }
    
    console.log('Recording stopped');
}

// Handle recording stop event
async function handleRecordingStop() {
    // Check if we have enough audio data (at least 0.5 seconds)
    const duration = Date.now() - startTime;
    if (duration <.500) {
        console.log('Recording too short, ignoring');
        setButtonState('idle');
        return;
    }

    try {
        // Create audio blob
        const audioType = isSafari || isIOS ? 'audio/m4a' : 'audio/webm';
        const audioBlob = new Blob(audioChunks, { type: audioType });
        
        // Create a file from the blob with appropriate extension
        const extension = isSafari || isIOS ? 'm4a' : 'webm';
        const fileName = `recording_${new Date().getTime()}.${extension}`;
        const audioFile = new File([audioBlob], fileName, { type: audioType });
        
        console.log(`Created audio file: ${fileName}`, audioFile);
        
        // Transcribe audio
        await transcribeAudio(audioFile);
    } catch (error) {
        console.error('Error processing recording:', error);
        setButtonState('idle');
        showToast('Error processing audio. Please try again.');
    }
}

// Send audio to server for transcription
async function transcribeAudio(audioFile) {
    try {
        // Create form data to send to server
        const formData = new FormData();
        formData.append('audio', audioFile);
        
        // Send to server
        const response = await fetch('/api/speech-to-text', {
            method: 'POST',
            body: formData,
        });
        
        const result = await response.json();
        
        if (!result.success) {
            throw new Error(result.error || 'Transcription failed');
        }
        
        // Set transcribed text to message input
        if (result.text && result.text.trim()) {
            messageInputCtrl.value = result.text.trim();
            messageInputCtrl.dispatchEvent(new Event('input'));
            
            // Focus on the input to allow immediate edits if needed
            messageInputCtrl.focus();
        } else {
            showToast('No speech detected. Please try again.');
        }
    } catch (error) {
        console.error('Error transcribing audio:', error);
        showToast('Error converting speech to text. Please try again.');
    } finally {
        // Reset button state
        setButtonState('idle');
    }
}

// Set microphone button state
function setButtonState(state) {
    if (!micButton) return;
    
    // Clear all existing classes
    micButton.className = 'action-button mic-button';
    micButton.innerHTML = '<i class="fas fa-microphone"></i>';
    
    // Set appropriate state
    switch (state) {
        case 'recording':
            micButton.classList.add('recording');
            micButton.innerHTML = '<i class="fas fa-stop"></i>';
            showPulseAnimation(true);
            break;
        case 'processing':
            micButton.classList.add('processing');
            micButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            showPulseAnimation(false);
            break;
        case 'idle':
        default:
            showPulseAnimation(false);
            break;
    }
}

// Show/hide pulse animation around the mic button
function showPulseAnimation(show) {
    // Remove existing pulse if any
    const existingPulse = document.querySelector('.mic-pulse');
    if (existingPulse) {
        existingPulse.remove();
    }
    
    if (show && micButton) {
        // Create pulse element
        const pulse = document.createElement('div');
        pulse.className = 'mic-pulse';
        
        // Insert pulse before the mic button
        micButton.parentNode.insertBefore(pulse, micButton);
    }
}

// Show a toast message
function showToast(message) {
    // Check if a toast container exists, create if not
    let toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Create new toast element
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    toastContainer.appendChild(toast);
    
    // Show the toast with animation
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Auto-remove after 3 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Initialize speech-to-text when DOM is loaded
document.addEventListener('DOMContentLoaded', initSpeechToText);