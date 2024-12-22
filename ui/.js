let setupAttempts = 0;
let _start = 0;

let selectedMessageIndex = null;
let whenLastSelection = null;
let whenLastNavHover = null;
let isNavDisplayed = false;  // Currently unused

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
    
    const navContent = navContainer.querySelector('.bgpl-nav-content');
    navContent.addEventListener('mouseenter', () => activateNavOverlay(navContent));
    navContent.addEventListener('mouseleave', () => startDeactivateNavOverlay(navContent));

    const leftNav = navContent.querySelector('.bgpl-nav-left');
    const rightNav = navContent.querySelector('.bgpl-nav-right');
    leftNav.addEventListener('click', () => navigateHistory('left'));
    rightNav.addEventListener('click', () => navigateHistory('right'));
    
    // const parent = document.querySelector('#chat');`
    document.body.appendChild(navContainer);
    console.log("Nav overlay created with elements:", {
        container: !!navContainer,
        content: !!navContent,
        posInfo: !!navContent.querySelector('.bgpl-nav-pos'),
        leftNav: !!leftNav,
        rightNav: !!rightNav
    });
}

function activateNavOverlay(navContent) {
    if (navContent) {
        whenLastNavHover = null;
        navContent.removeAttribute('hidden');
        navContent.setAttribute('activated', '');
    }
}

function startDeactivateNavOverlay(navContent, deactivateDelay=750, hideDelay=3000) {
    if (navContent) {
        const start = Date.now();
        whenLastNavHover = start;

        if (deactivateDelay) {
            setTimeout(() => {
                if (whenLastNavHover === start) {
                    navContent.removeAttribute('activated');
                }
            }, deactivateDelay);
        }
        if (hideDelay) {
            setTimeout(() => {
                if (whenLastNavHover === start) {
                    navContent.setAttribute('hidden', '');
                }
            }, hideDelay);
        }
    }
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
    navContainer.style.left = `${rect.right}px`;
}

function updateNavInfo(chatDataJSON=null) {
    chatDataJSON = chatDataJSON ?? gradioApp().querySelector('#bgpl_chat_data textarea');
    if (!chatDataJSON) return isNavDisplayed = false;
    const chatData = JSON.parse(chatDataJSON.value);
    const [currentPos, totalPos] = chatData[selectedMessageIndex] || [0, 0];

    const navContainer = document.querySelector('.bgpl-nav-container');
    if (!navContainer) return isNavDisplayed = false;

    if (totalPos > 1) {
        const posInfo = navContainer.querySelector('.bgpl-nav-pos');
        const leftArrow = navContainer.querySelector('.bgpl-nav-left');
        const rightArrow = navContainer.querySelector('.bgpl-nav-right');
        if (posInfo && leftArrow && rightArrow) {
            navContainer.style.display = 'block';
            posInfo.textContent = `${currentPos + 1}/${totalPos}`;
            
            currentPos > 0 ? leftArrow.setAttribute('activated', '') : leftArrow.removeAttribute('activated');
            currentPos < totalPos - 1 ? rightArrow.setAttribute('activated', '') : rightArrow.removeAttribute('activated');
            return isNavDisplayed = true;
        }
    }
    navContainer.style.display = 'none';
    return isNavDisplayed = false;
}

function setupPositionObserver() {
    const chatDataJSON = gradioApp().querySelector('#bgpl_chat_data textarea');
    if (!chatDataJSON) return;

    // Use input and change events (MutationObserver doesn't work for direct Gradio changes)
    const updateHandler = () => {
        const chatDataJSON = gradioApp().querySelector('#bgpl_chat_data textarea');
        const chatData = JSON.parse(chatDataJSON.value);
        const [currentPos, totalPos] = chatData[selectedMessageIndex] || [0, 0];

        const navContainer = document.querySelector('.bgpl-nav-container');
        if (navContainer && totalPos < 2) {
            navContainer.style.display = 'none';
        }
        else {
            const messages = document.querySelectorAll('#chat .messages .message');
            const element = messages[selectedMessageIndex].querySelector('.message-body');
            if (element) {
                updateNavInfo(chatDataJSON);
                // updateNavOverlay(element);
                // Can be annoying when spam-clicking, tho it looks cool
            }
            setupMessageHandlers();
        }
    };

    // Listen for both input and change events
    chatDataJSON.addEventListener('change', updateHandler);
}

function navigateHistory(direction) {
    if (selectedMessageIndex === null) return;  // Don't navigate if no message is selected
    const dirComponent = gradioApp().querySelector('#bgpl_direction textarea');
    if (dirComponent) {
        // Set direction and navigate
        updateGradioInput(dirComponent, direction);
        gradioApp().querySelector('#bgpl_navigate')?.click();
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

    const chatMapJSON = gradioApp().querySelector('#bgpl_chat_map textarea');
    if (chatMapJSON) {
        updateGradioInput(chatMapJSON, JSON.stringify(messageMap));
    }

    return messageMap;
}

function selectMessage(element, domIndex) {
    // Remove previous selection
    deselectMessages();

    // Add selection to clicked message
    if (element) {
        selectedMessageIndex = domIndex;
        element.classList.add('bgpl-selected-msg');

        const navContent = document.querySelector('.bgpl-nav-content');
        activateNavOverlay(navContent);
        startDeactivateNavOverlay(navContent, 750);

        // Get the history index and message type from our map
        const messageMap = buildMessageMap();
        if (domIndex >= 0 && domIndex < messageMap.length) {            
            // Call Gradio input update
            const indexInput = gradioApp().querySelector('#bgpl_chat_idx input[type="number"]');
            if (indexInput) {
                const start = Date.now();
                whenLastSelection = start;
                setTimeout(() => { 
                    if (whenLastSelection === start) {
                        updateGradioInput(indexInput, domIndex);
                    }
                }, 250);
            }
        } else {
            console.error("Message index out of range:", domIndex, messageMap);
        }

        if (updateNavInfo()) {
            updateNavOverlay(element);
        }
    }
}

function deselectMessages() {
    document.querySelectorAll('.bgpl-selected-msg').forEach(el => {
        el.classList.remove('bgpl-selected-msg');
    });
    selectedMessageIndex = null;
    selectedId = null;
    whenLastNavHover = null;
}

function updateGradioInput(element, value) {
    element.value = value;
    element.dispatchEvent(new Event('input', { bubbles: true }));
}

// Helper function to get Gradio app root
function gradioApp() {
    const elems = document.getElementsByTagName('gradio-app');
    const gradioShadowRoot = elems.length > 0 ? elems[0].shadowRoot : null;
    return gradioShadowRoot || document;
}

// Add hover handlers to messages
function setupMessageHandlers() {
    const messages = gradioApp().querySelectorAll('#chat .messages .message');
    
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

    const navContent = document.querySelector('.bgpl-nav-container .bgpl-nav-content');
    messages.forEach((msg, index) => {
        if (!msg.dataset.boogaplusHandled) {
            msg.dataset.boogaplusHandled = 'true';
            msg.style.cursor = 'default';
            
            const messageBody = msg.querySelector('.message-body');
            if (messageBody) {
                // Hover handler
                msg.addEventListener('mousemove', () => {
                    if (selectedMessageIndex !== index) {
                        selectMessage(messageBody, index);
                    } else if (updateNavInfo()) {
                        updateNavOverlay(messageBody);
                        activateNavOverlay(navContent);
                        startDeactivateNavOverlay(navContent, 500);
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
    console.log("Initializing message handlers for boogaPlus nav overlay...");
    setupMessageHandlers();
    
    // Create an observer for dynamic chat updates
    const chat = document.getElementById('chat');
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
        setupPositionObserver();
    });
} else {
    initializeHandlers();
    setupPositionObserver();
}