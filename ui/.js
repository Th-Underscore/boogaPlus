let selectedMessageIndex = null;
let selectedId = null;
let selectedElement = null;
let setupAttempts = 0;

function createNavOverlay() {
    console.log("Creating boogaPlus nav overlay...");
    const navContainer = document.createElement('div');
    navContainer.className = 'bgpl-nav-container';
    navContainer.innerHTML = `
        <div class="bgpl-nav-content">
            <div class="bgpl-nav-left">
                <span class="bgpl-nav-arrow">←</span>
            </div>
            <div class="bgpl-nav-pos">0/0</div>
            <div class="bgpl-nav-right">
                <span class="bgpl-nav-arrow">→</span>
            </div>
        </div>
    `;
    
    // Add click handlers after creating elements
    const leftNav = navContainer.querySelector('.bgpl-nav-left');
    const rightNav = navContainer.querySelector('.bgpl-nav-right');
    
    leftNav.addEventListener('click', () => navigateHistory('left'));
    rightNav.addEventListener('click', () => navigateHistory('right'));
    
    document.body.appendChild(navContainer);
    console.log("Nav overlay created with elements:", {
        container: !!navContainer,
        posInfo: !!navContainer.querySelector('.bgpl-nav-pos'),
        leftNav: !!leftNav,
        rightNav: !!rightNav
    });
}

function updateNavOverlay(element) {
    const navContainer = document.querySelector('.bgpl-nav-container');
    if (!navContainer || !element) return;
    
    // Get element position
    const rect = element.getBoundingClientRect();
    const messageDiv = element.closest('.message');
    if (!messageDiv) return;
    
    // Position the nav container under the message
    navContainer.style.top = `${rect.bottom}px`;
    navContainer.style.left = `${rect.left}px`;
    navContainer.style.width = `${rect.width}px`;
    navContainer.style.display = 'block';
}

function updateNavInfo() {
    const totalPosInput = gradioApp().querySelector('#bgpl_total_pos input[type="number"]');
    const totalPos = parseInt(totalPosInput.value) || 1;
    if (totalPos > 0) {
        const currentPosInput = gradioApp().querySelector('#bgpl_current_pos input[type="number"]');
        const currentPos = parseInt(currentPosInput.value) || 0;

        const posInfo = document.querySelector('.bgpl-nav-pos');
        const leftArrow = document.querySelector('.bgpl-nav-left .bgpl-nav-arrow');
        const rightArrow = document.querySelector('.bgpl-nav-right .bgpl-nav-arrow');
        
        if (posInfo && leftArrow && rightArrow) {
            posInfo.textContent = `${currentPos + 1}/${totalPos}`;
            leftArrow.style.visibility = currentPos > 0 ? 'visible' : 'hidden';
            rightArrow.style.visibility = currentPos < totalPos - 1 ? 'visible' : 'hidden';
            
            const container = document.querySelector('.bgpl-nav-container');
            if (container) {
                container.style.display = totalPos > 1 ? 'block' : 'none';
            }
        }
    }
}

function setupPositionObserver() {
    const currentPosInput = gradioApp().querySelector('#bgpl_current_pos input[type="number"]');
    if (!currentPosInput) return;
    const totalPosInput = gradioApp().querySelector('#bgpl_total_pos input[type="number"]');
    if (!totalPosInput) return;

    // Use input and change events instead of MutationObserver
    const updateHandler = () => {
        const navContainer = document.querySelector('.bgpl-nav-container');
        if (!parseInt(totalPosInput.value) && navContainer) navContainer.style.display = 'none';
        else updateNavInfo();
    };

    // Listen for both input and change events
    currentPosInput.addEventListener('change', updateHandler);
    totalPosInput.addEventListener('change', updateHandler);
}

function navigateHistory(direction) {
    if (selectedMessageIndex === null) return;  // Don't navigate if no message is selected
    
    const btn = gradioApp().querySelector('#bgpl_navigate');
    const dirComponent = gradioApp().querySelector('#bgpl_direction textarea');
    
    if (btn && dirComponent) {
        // Set direction and navigate
        updateInput(dirComponent, direction);        
        // Small delay to ensure values are updated
        btn.click();
    }
}

function buildMessageMap() {
    const messages = document.querySelectorAll('#chat .messages .message');
    const messageMap = [];
    let historyIndex = 0;
    let lastType = null;

    messages.forEach((msg) => {
        const isUser = msg.querySelector('.circle-you') !== null;
        const currentType = isUser ? 0 : 1;

        // If this is a user message, always increment index
        // If this is a bot message, only increment if last message wasn't a user message
        if (currentType === 0 || (currentType === 1 && lastType !== 0)) {
            historyIndex++;
        }

        messageMap.push([historyIndex - 1, currentType]);
        lastType = currentType;
    });

    return messageMap;
}

function selectMessage(element, domIndex, id) {
    // Remove previous selection
    deselectMessage();

    // Add selection to clicked message
    if (element) {
        selectedMessageIndex = domIndex;
        selectedId = id;
        selectedElement = element;
        selectedElement.classList.add('bgpl-selected-msg');

        // Get the history index and message type from our map
        const messageMap = buildMessageMap();
        if (domIndex >= 0 && domIndex < messageMap.length) {
            const [historyIndex, messageType] = messageMap[domIndex];
            
            // Update Gradio components
            const indexInput = gradioApp().querySelector('#bgpl_history_index input[type="number"]');
            const typeInput = gradioApp().querySelector('#bgpl_msg_type input[type="number"]');
            
            if (indexInput && typeInput) {
                updateInput(indexInput, historyIndex);
                updateInput(typeInput, messageType);
                
                // Trigger the change event to update positions
                indexInput.dispatchEvent(new Event('change', { bubbles: true }));
                
                // Update navigation overlay position
                updateNavOverlay(element);
            }
        } else {
            console.error("Message index out of range:", domIndex, messageMap);
        }

        updateNavInfo();
    }
}

function deselectMessage() {
    document.querySelectorAll('.bgpl-selected-msg').forEach(el => {
        el.classList.remove('bgpl-selected-msg');
    });
    selectedMessageIndex = null;
    selectedId = null;
}

function updateInput(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
}

// Helper function to get Gradio app root
function gradioApp() {
    const elems = document.getElementsByTagName('gradio-app');
    const gradioShadowRoot = elems.length > 0 ? elems[0].shadowRoot : null;
    return gradioShadowRoot || document;
}

// Add hover handlers to messages
function setupMessageHandlers() {
    const messages = document.querySelectorAll('#chat .messages .message');
    
    if (messages.length === 0) {
        if (setupAttempts < 10) {
            setupAttempts++;
            setTimeout(setupMessageHandlers, 500);
            return;
        } else {
            throw new Error(`No messages found after ${setupAttempts} attempts`);
        }
    }
    setupAttempts = 0;

    messages.forEach((msg, index) => {
        if (!msg.dataset.boogaplusHandled) {
            msg.dataset.boogaplusHandled = 'true';
            msg.style.cursor = 'default';
            
            // Get the message text from the message-body
            const messageBody = msg.querySelector('.message-body');
            if (messageBody) {                
                // Add hover handler
                msg.addEventListener('mouseenter', () => {
                    const id = gradioApp().querySelector('input[class="svelte-1mhtq7j"]').value || gradioApp().querySelector('input[name="radio-7"]').value;
                    selectMessage(messageBody, index, id);
                });
                
                // Add mouseleave handler to hide nav if not selected
                msg.addEventListener('mouseleave', () => {
                    if (!messageBody.classList.contains('bgpl-selected-msg')) {
                        const navContainer = document.querySelector('.bgpl-nav-container');
                        if (navContainer) navContainer.style.display = 'none';
                    }
                });
            }
        }
    });
    
    // Create navigation overlay if not exists
    if (!document.querySelector('.bgpl-nav-container')) {
        createNavOverlay();
    }
}

// Global event listeners for dynamic setup
document.addEventListener('click', function(e) {
    if (e.target.closest('#chat')) {
        setupMessageHandlers();
    }
});

// Handle keyboard navigation
document.addEventListener('keydown', function(e) {
    setupMessageHandlers();  // Ensure handlers are set up
    
    // Only handle if we're not in an input field and a message is selected
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || selectedMessageIndex === null) {
        return;
    }
    
    if (e.ctrlKey && !e.shiftKey) {
        if (e.key === 'ArrowLeft') {
            navigateHistory('left');
            e.preventDefault();
        } else if (e.key === 'ArrowRight') {
            navigateHistory('right');
            e.preventDefault();
        }
    }
});

// Initial setup with retry
function initializeHandlers() {
    console.log("Initializing handlers...");
    setupMessageHandlers();
    
    // Create an observer for dynamic chat updates
    const chat = document.getElementById('chat');
    if (chat) {
        const observer = new MutationObserver(() => {
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
        setupPositionObserver();
    });
} else {
    initializeHandlers();
    setupPositionObserver();
}