let setupAttempts = 0;
let _start = 0;

let messages = null;
let selectedMessageChatIndex = null;
let selectedMessageHistoryIndex = null;
let selectedMessageType = null;
let whenLastSelection = null;
let whenLastNavHover = null;

function navigateHistory(direction, index=null, type=null) {
    index = index === null ? selectedMessageHistoryIndex : index;
    type = type === null ? selectedMessageType : type;

    const gradio = gradioApp();

    const dirInput = gradio.querySelector('#bgpl_direction textarea');
    if (dirInput) {
        const historyIndexInput = gradio.querySelector('#bgpl_history_index input[type="number"]');
        const messageIndexInput = gradio.querySelector('#bgpl_message_type input[type="number"]');
        if (historyIndexInput && messageIndexInput) {
            // Set all Gradio inputs for navigation
            updateGradioInput(historyIndexInput, index);
            updateGradioInput(messageIndexInput, type);
            updateGradioInput(dirInput, direction);
            gradio.querySelector('#bgpl_navigate')?.click();
        }
    }
}

function selectMessage(element, index=null) {
    // Remove previous selection
    deselectMessages();

    // Add selection to clicked message
    if (element) {
        selectedMessageChatIndex = index;
        selectedMessageHistoryIndex = element.dataset.historyIndex;
        selectedMessageType = element.dataset.messageType;
        element.querySelector('.message-body').classList.add('selected-message');

        // const navContent = document.querySelector('.nav-container');
        // activateNavOverlay(navContent);
        // startDeactivateNavOverlay(navContent, 750);
    }
}

function deselectMessages() {
    document.querySelectorAll('.selected-message').forEach(el => {
        el.classList.remove('selected-message');
    });
    selectedMessageChatIndex = null;
    selectedMessageHistoryIndex = null;
    selectedMessageType = null;
    whenLastNavHover = null;
}

function updateGradioInput(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
}

// Helper function to get Gradio app root
function gradioApp() {
    const elems = document.querySelectorAll('gradio-app');
    const gradioShadowRoot = elems.length > 0 ? elems[0].shadowRoot : null;
    return gradioShadowRoot || document;
}

// Add hover handlers to messages
function setupMessageHandlers() {
    const gradio = gradioApp();
    messages = gradio.querySelectorAll('#chat .messages .message');
    
    if (!messages?.length) {  // Repeat until messages are found
        if (setupAttempts < 20) {
            setupAttempts++;
            setTimeout(setupMessageHandlers, 500);
            return;
        } else {
            throw new Error(`No messages found after ${setupAttempts} attempts`);
        }
    }

    const rootDataset = (gradio !== document) ? gradio.dataset : document.body.dataset; 
    if (!rootDataset.boogaplusHandled) {  // When all info is available, call startup
        const navEventHandler = gradio.querySelector('#bgpl_navigate');
        const startupHandler = gradio.querySelector('#bgpl_startup');
        if (navEventHandler && startupHandler) {
            console.log("Setting up nav event handler...");
            navEventHandler.addEventListener('change', setupMessageHandlers);
            console.log("Calling startup event handler...");
            startupHandler.click();
            
            rootDataset.boogaplusHandled = 'true';
            return;
        }
        setupAttempts++;
        setTimeout(setupMessageHandlers, 500);  // Redo setup until handlers are found
        return;
    }

    if (selectedMessageChatIndex !== null) {  // If a message is selected
        messages[selectedMessageChatIndex].querySelector('.message-body')?.classList.add('selected-message');
    }

    setupAttempts = 0;

    messages.forEach((msg, index) => {
        if (!msg.dataset.boogaplusHandled) {
            const historyIndex = msg.dataset.historyIndex;
            const type = msg.dataset.messageType;
            if (historyIndex && type) {
                const leftArrow = msg.querySelector('.nav-left');
                const rightArrow = msg.querySelector('.nav-right');
                leftArrow?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    selectMessage(msg, index);
                    navigateHistory('left', historyIndex, type);
                });
                rightArrow?.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    selectMessage(msg, index);
                    navigateHistory('right', historyIndex, type);
                });
            }

            msg.addEventListener('click', () => {
                if (msg.querySelector('.selected-message')) {  // Select - deselect swap
                    deselectMessages();
                } else {
                    selectMessage(msg, index);
                }
            });

            msg.dataset.boogaplusHandled = 'true';
        }
    });
}

// Global event listeners for dynamic setup
document.addEventListener('click', function(e) {
    const chat = e.target.closest('#chat');
    if (chat) {
        setupMessageHandlers();
        const leftArrow = e.target.closest('.nav-left');
        if (leftArrow) {
            leftArrow.click();
        }
        const rightArrow = e.target.closest('.nav-right');
        if (rightArrow) {
            rightArrow.click();
        }
    }
    if (!(e.target.closest('.message') || e.target.closest('button'))) {  // Deselect on click outside
        deselectMessages();
    }
});

// Handle keyboard navigation
document.addEventListener('keydown', function(e) {
    setupMessageHandlers();  // Ensure handlers are set up
    
    // Only handle if we're not in an input field and a message is selected
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || selectedMessageHistoryIndex === null) {
        return;
    }
    
    if (e.ctrlKey && !e.shiftKey) {
        if (e.key === 'ArrowLeft') {
            navigateHistory('left');
            e.preventDefault();
        } else if (e.key === 'ArrowRight') {
            navigateHistory('right');
            e.preventDefault();
        } else if (e.key === 'ArrowUp') {
            const index = selectedMessageChatIndex - 1;  // Up one element
            if (index >= 0) selectMessage(messages[index], index);
            e.preventDefault();
        } else if (e.key === 'ArrowDown') {
            const index = selectedMessageChatIndex + 1;  // Down one element
            if (index < messages.length) selectMessage(messages[index],index);
            e.preventDefault();
        }
    }
});

// Initial setup with retry
function initializeHandlers() {
    setupMessageHandlers();
    
    // Create an observer for dynamic chat updates
    const gradio = gradioApp();
    const chat = gradio.querySelector('#chat');
    if (chat) {
        const observer = new MutationObserver(() => {
            console.log("Updating message handlers for boogaPlus nav overlay...");
            setupMessageHandlers();
        });
        
        observer.observe(chat, {
            childList: true,
            subtree: true 
        });
    }
}

// Start initialization when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initializeHandlers();
    });
} else {
    initializeHandlers();
}