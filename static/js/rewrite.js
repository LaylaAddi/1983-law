/**
 * ChatGPT Rewrite Feature
 * Provides AI-powered text rewriting for legal documents
 */

(function() {
    'use strict';

    // Configuration
    const REWRITE_URL = '/documents/rewrite-text/';

    // Fields that support rewriting (incident_narrative section)
    const REWRITABLE_FIELDS = [
        'summary',
        'detailed_narrative',
        'what_were_you_doing',
        'initial_contact',
        'what_was_said',
        'physical_actions',
        'how_it_ended'
    ];

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initRewriteFeature();
    });

    function initRewriteFeature() {
        // Find all rewritable textarea fields
        REWRITABLE_FIELDS.forEach(function(fieldName) {
            const textarea = document.getElementById('id_' + fieldName);
            if (textarea && textarea.tagName === 'TEXTAREA') {
                setupRewriteButton(textarea, fieldName);
            }
        });
    }

    function setupRewriteButton(textarea, fieldName) {
        // Find the label for this field
        const label = document.querySelector('label[for="' + textarea.id + '"]');
        if (!label) return;

        // Create the rewrite button
        const rewriteBtn = document.createElement('button');
        rewriteBtn.type = 'button';
        rewriteBtn.className = 'btn btn-outline-info btn-sm rewrite-btn';
        rewriteBtn.innerHTML = '<i class="bi bi-magic me-1"></i>Help me rewrite';
        rewriteBtn.title = 'Use AI to improve this text for legal format';
        rewriteBtn.setAttribute('data-field', fieldName);
        rewriteBtn.setAttribute('data-textarea-id', textarea.id);

        // Add button next to label
        label.appendChild(rewriteBtn);

        // Create the comparison panel (hidden by default)
        const panel = createComparisonPanel(fieldName, textarea.id);
        textarea.parentNode.insertBefore(panel, textarea.nextSibling);

        // Add click handler
        rewriteBtn.addEventListener('click', function(e) {
            e.preventDefault();
            handleRewriteClick(textarea, fieldName, panel, rewriteBtn);
        });
    }

    function createComparisonPanel(fieldName, textareaId) {
        const panel = document.createElement('div');
        panel.className = 'rewrite-panel';
        panel.id = 'rewrite-panel-' + fieldName;
        panel.setAttribute('data-textarea-id', textareaId);

        panel.innerHTML = `
            <div class="rewrite-panel-header">
                <h6><i class="bi bi-magic me-2"></i>AI Suggestion</h6>
                <button type="button" class="rewrite-panel-close" aria-label="Close">&times;</button>
            </div>
            <div class="rewrite-panel-body">
                <div class="rewrite-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <span>Generating suggestion...</span>
                </div>
                <div class="rewrite-comparison" style="display: none;">
                    <div class="rewrite-column original">
                        <div class="rewrite-column-header">
                            <i class="bi bi-file-text me-1"></i>Your Original
                        </div>
                        <div class="rewrite-column-content"></div>
                    </div>
                    <div class="rewrite-column suggested">
                        <div class="rewrite-column-header">
                            <i class="bi bi-stars me-1"></i>Suggested Rewrite
                        </div>
                        <div class="rewrite-column-content">
                            <textarea class="suggested-text" placeholder="AI suggestion will appear here..."></textarea>
                        </div>
                    </div>
                </div>
                <div class="rewrite-error" style="display: none;">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <span class="error-message"></span>
                </div>
                <div class="rewrite-actions" style="display: none;">
                    <button type="button" class="btn btn-outline-secondary btn-use-original">
                        <i class="bi bi-arrow-counterclockwise me-1"></i>Keep Original
                    </button>
                    <button type="button" class="btn btn-success btn-use-suggested">
                        <i class="bi bi-check-lg me-1"></i>Use Suggestion
                    </button>
                </div>
            </div>
        `;

        // Add event handlers for panel buttons
        const closeBtn = panel.querySelector('.rewrite-panel-close');
        closeBtn.addEventListener('click', function() {
            closePanel(panel);
        });

        const useOriginalBtn = panel.querySelector('.btn-use-original');
        useOriginalBtn.addEventListener('click', function() {
            closePanel(panel);
        });

        const useSuggestedBtn = panel.querySelector('.btn-use-suggested');
        useSuggestedBtn.addEventListener('click', function() {
            applySuggestion(panel);
        });

        return panel;
    }

    function handleRewriteClick(textarea, fieldName, panel, button) {
        const text = textarea.value.trim();

        if (!text) {
            alert('Please enter some text first before requesting a rewrite.');
            return;
        }

        // Show panel and loading state
        panel.classList.add('active');
        showLoading(panel);

        // Disable button while processing
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Processing...';

        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        // Make API request
        fetch(REWRITE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
                text: text,
                field_name: fieldName
            })
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                showComparison(panel, data.original, data.rewritten);
            } else {
                showError(panel, data.error || 'An unknown error occurred');
            }
        })
        .catch(function(error) {
            console.error('Rewrite error:', error);
            showError(panel, 'Network error. Please try again.');
        })
        .finally(function() {
            // Re-enable button
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-magic me-1"></i>Help me rewrite';
        });
    }

    function showLoading(panel) {
        panel.querySelector('.rewrite-loading').style.display = 'flex';
        panel.querySelector('.rewrite-comparison').style.display = 'none';
        panel.querySelector('.rewrite-error').style.display = 'none';
        panel.querySelector('.rewrite-actions').style.display = 'none';
    }

    function showComparison(panel, original, suggested) {
        panel.querySelector('.rewrite-loading').style.display = 'none';
        panel.querySelector('.rewrite-error').style.display = 'none';

        // Set the content
        panel.querySelector('.original .rewrite-column-content').textContent = original;
        panel.querySelector('.suggested-text').value = suggested;

        // Show comparison and actions
        panel.querySelector('.rewrite-comparison').style.display = 'grid';
        panel.querySelector('.rewrite-actions').style.display = 'flex';
    }

    function showError(panel, message) {
        panel.querySelector('.rewrite-loading').style.display = 'none';
        panel.querySelector('.rewrite-comparison').style.display = 'none';
        panel.querySelector('.rewrite-actions').style.display = 'none';

        const errorDiv = panel.querySelector('.rewrite-error');
        errorDiv.querySelector('.error-message').textContent = message;
        errorDiv.style.display = 'block';
    }

    function closePanel(panel) {
        panel.classList.remove('active');
    }

    function applySuggestion(panel) {
        const textareaId = panel.getAttribute('data-textarea-id');
        const textarea = document.getElementById(textareaId);
        const suggestedText = panel.querySelector('.suggested-text').value;

        if (textarea && suggestedText) {
            textarea.value = suggestedText;

            // Trigger change event so any listeners know the value changed
            textarea.dispatchEvent(new Event('change', { bubbles: true }));
            textarea.dispatchEvent(new Event('input', { bubbles: true }));

            // Close panel
            closePanel(panel);

            // Show success feedback
            showSuccessFeedback(textarea);
        }
    }

    function showSuccessFeedback(textarea) {
        // Create success message
        const feedback = document.createElement('div');
        feedback.className = 'rewrite-success';
        feedback.innerHTML = '<i class="bi bi-check-circle-fill"></i>Text updated with AI suggestion';

        textarea.parentNode.insertBefore(feedback, textarea.nextSibling);

        // Remove after 3 seconds
        setTimeout(function() {
            feedback.remove();
        }, 3000);

        // Highlight the textarea briefly
        textarea.style.backgroundColor = '#d1e7dd';
        setTimeout(function() {
            textarea.style.backgroundColor = '';
        }, 1000);
    }

})();
