// Frontend interactions for Content Generator UI

let currentJobId = null;
let pollInterval = null;

// Helper to set button text (handles span inside button)
function setButtonText(btn, text) {
    if (!btn) return;
    const span = btn.querySelector('span');
    if (span) {
        span.textContent = text;
    } else {
        btn.textContent = text;
    }
}

// Initialize on page load - check for active jobs
document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        // Add click handler
        generateBtn.addEventListener('click', generateNewPost);
    }

    // Setup style editor
    setupStyleEditor();
});

// Style editor functionality
function setupStyleEditor() {
    const toggleBtn = document.getElementById('toggleStyleBtn');
    const stylePanel = document.getElementById('stylePanel');
    const saveBtn = document.getElementById('saveStyleBtn');
    const resetBtn = document.getElementById('resetStyleBtn');
    const styleInput = document.getElementById('styleInput');
    
    if (!toggleBtn) return;
    
    // Toggle panel
    toggleBtn.addEventListener('click', () => {
        stylePanel.classList.toggle('hidden');
    });
    
    // Save style
    saveBtn.addEventListener('click', async () => {
        const newStyle = styleInput.value.trim();
        
        // Allow empty style (for when using style reference images)
        // if (!newStyle) {
        //     showError('Style cannot be empty');
        //     return;
        // }
        
        try {
            const response = await fetch('/update-style', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ style: newStyle })
            });
            
            const data = await response.json();
            
            if (response.ok) {
                showSuccess(data.message);
                stylePanel.classList.add('hidden');
            } else {
                showError(data.error || 'Failed to update style');
            }
        } catch (error) {
            showError('Failed to update style: ' + error.message);
        }
    });
    
    // Reset to default (empty)
    resetBtn.addEventListener('click', () => {
        styleInput.value = '';
        showSuccess('Style reset to empty (allows style references to work properly)');
    });
}

// Show success message
function showSuccess(message) {
    const successBar = document.createElement('div');
    successBar.className = 'success-bar';
    successBar.innerHTML = `<span>${message}</span>`;
    
    // Insert at the beginning of main container
    const container = document.querySelector('main.container');
    if (container) {
        container.insertBefore(successBar, container.firstChild);
    }
    
    setTimeout(() => {
        successBar.remove();
    }, 3000);
}

// Generate button click handler
async function generateNewPost() {
    const statusBar = document.getElementById('statusBar');
    const errorBar = document.getElementById('errorBar');
    const generateBtn = document.getElementById('generateBtn');
    
    // Hide error if visible
    errorBar.classList.add('hidden');
    
    // Show loading state
    statusBar.classList.remove('hidden');
    document.getElementById('statusText').textContent = 'AI agents are arguing about your carousel... This takes 2-3 min. They\'re perfectionists. 🤖';
    generateBtn.disabled = true;
    setButtonText(generateBtn, 'Generating...');
    
    try {
        // Trigger generation
        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to start generation');
        }
        
        const data = await response.json();
        
        if (response.status === 409) {
            // Already running
            showError('Generation already in progress. Please wait...');
            currentJobId = data.job_id;
            pollStatus();
            return;
        }
        
        currentJobId = data.job_id;
        
        // Start polling for status
        pollStatus();
        
    } catch (error) {
        showError(error.message);
        statusBar.classList.add('hidden');
        const generateBtn = document.getElementById('generateBtn');
        const generateTextBtn = document.getElementById('generateTextBtn');
        if (generateBtn) {
            generateBtn.disabled = false;
            setButtonText(generateBtn, '📊 Generate from Sheet');
        }
        if (generateTextBtn) {
            generateTextBtn.disabled = false;
            setButtonText(generateTextBtn, '✨ Generate from Text');
        }
    }
}

// Poll generation status
function pollStatus() {
    if (!currentJobId) return;
    
    pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/status/${currentJobId}`);
            const data = await response.json();
            
            if (data.status === 'complete') {
                clearInterval(pollInterval);

                // Re-enable buttons
                const generateBtn = document.getElementById('generateBtn');
                const generateTextBtn = document.getElementById('generateTextBtn');
                if (generateBtn) {
                    generateBtn.disabled = false;
                    setButtonText(generateBtn, '📊 Generate from Sheet');
                }
                if (generateTextBtn) {
                    generateTextBtn.disabled = false;
                    setButtonText(generateTextBtn, '✨ Generate from Text');
                }

                // Reload page to show new post in gallery
                window.location.reload();

            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                showError(data.error || 'Generation failed');

                document.getElementById('statusBar').classList.add('hidden');
                const generateBtn = document.getElementById('generateBtn');
                const generateTextBtn = document.getElementById('generateTextBtn');
                if (generateBtn) {
                    generateBtn.disabled = false;
                    setButtonText(generateBtn, '📊 Generate from Sheet');
                }
                if (generateTextBtn) {
                    generateTextBtn.disabled = false;
                    setButtonText(generateTextBtn, '✨ Generate from Text');
                }
            }
            // If status is 'running', continue polling
            
        } catch (error) {
            clearInterval(pollInterval);
            showError('Failed to check status: ' + error.message);

            // Re-enable buttons on error
            const generateBtn = document.getElementById('generateBtn');
            const generateTextBtn = document.getElementById('generateTextBtn');
            if (generateBtn) {
                generateBtn.disabled = false;
                setButtonText(generateBtn, '📊 Generate from Sheet');
            }
            if (generateTextBtn) {
                generateTextBtn.disabled = false;
                setButtonText(generateTextBtn, '✨ Generate from Text');
            }
        }
    }, 2000); // Poll every 2 seconds
}

// Show error message
function showError(message) {
    const errorBar = document.getElementById('errorBar');
    const errorText = document.getElementById('errorText');
    
    errorText.textContent = message;
    errorBar.classList.remove('hidden');
}

// Close error
function closeError() {
    document.getElementById('errorBar').classList.add('hidden');
}

// Auto-hide error after 10 seconds
setTimeout(() => {
    const errorBar = document.getElementById('errorBar');
    if (!errorBar.classList.contains('hidden')) {
        errorBar.classList.add('hidden');
    }
}, 10000);

// Show loader function (for text input modal)
function showLoader(jobId) {
    const statusBar = document.getElementById('statusBar');
    const generateBtn = document.getElementById('generateBtn');
    const generateTextBtn = document.getElementById('generateTextBtn');

    // Show loading state
    statusBar.classList.remove('hidden');
    document.getElementById('statusText').textContent = 'AI agents are crafting your carousel... This takes 2-3 min. 🤖';

    // Disable both buttons while this job runs
    if (generateBtn) {
        generateBtn.disabled = true;
        setButtonText(generateBtn, 'Generating...');
    }
    if (generateTextBtn) {
        generateTextBtn.disabled = true;
        setButtonText(generateTextBtn, 'Generating...');
    }

    currentJobId = jobId;
    pollStatus();
}

