// Frontend interactions for Content Generator UI

let currentJobId = null;
let pollInterval = null;

// Initialize on page load - check for active jobs
document.addEventListener('DOMContentLoaded', () => {
    const generateBtn = document.getElementById('generateBtn');
    if (generateBtn) {
        // Add click handler
        generateBtn.addEventListener('click', generateNewPost);
        
        // If button is disabled on load, keep it disabled
        if (generateBtn.disabled) {
            generateBtn.textContent = 'Generating...';
        }
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
        
        if (!newStyle) {
            showError('Style cannot be empty');
            return;
        }
        
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
    
    // Reset to default
    resetBtn.addEventListener('click', () => {
        styleInput.value = 'pastel colors, soft lighting, elegant, clean style, 3d render, high detail, 3d plasticine';
    });
}

// Show success message
function showSuccess(message) {
    const successBar = document.createElement('div');
    successBar.className = 'success-bar';
    successBar.innerHTML = `<span>${message}</span>`;
    document.querySelector('.container').insertBefore(successBar, document.querySelector('.controls-section'));
    
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
    generateBtn.textContent = 'Generating...';
    
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
        generateBtn.disabled = false;
        generateBtn.textContent = '+ Generate New Post';
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
                
                // Re-enable button before redirect
                const generateBtn = document.getElementById('generateBtn');
                if (generateBtn) {
                    generateBtn.disabled = false;
                    generateBtn.textContent = '+ Generate New Post';
                }
                
                // Redirect to new post
                if (data.post_id) {
                    window.location.href = `/post/${data.post_id}`;
                } else {
                    // Reload page to show new post in gallery
                    window.location.reload();
                }
                
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                showError(data.error || 'Generation failed');
                
                document.getElementById('statusBar').classList.add('hidden');
                const generateBtn = document.getElementById('generateBtn');
                generateBtn.disabled = false;
                generateBtn.textContent = '+ Generate New Post';
            }
            // If status is 'running', continue polling
            
        } catch (error) {
            clearInterval(pollInterval);
            showError('Failed to check status');
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

