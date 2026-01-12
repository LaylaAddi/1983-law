/**
 * Rights Analysis Feature
 * AI-powered analysis to suggest constitutional rights violations
 */

(function() {
    'use strict';

    // Will be set from template
    let ANALYZE_URL = '';
    let DOCUMENT_ID = '';

    // Human-readable names for rights
    const RIGHT_NAMES = {
        'first_amendment_speech': 'Freedom of Speech',
        'first_amendment_press': 'Freedom of the Press',
        'first_amendment_assembly': 'Freedom of Assembly',
        'first_amendment_petition': 'Right to Petition',
        'fourth_amendment_search': 'Unreasonable Search',
        'fourth_amendment_seizure': 'Unreasonable Seizure',
        'fourth_amendment_arrest': 'Unlawful Arrest/Detention',
        'fourth_amendment_force': 'Excessive Force',
        'fifth_amendment_self_incrimination': 'Self-Incrimination',
        'fifth_amendment_due_process': 'Due Process (Federal)',
        'fourteenth_amendment_due_process': 'Due Process (State)',
        'fourteenth_amendment_equal_protection': 'Equal Protection',
    };

    // Amendment display names
    const AMENDMENT_NAMES = {
        'first': '1st Amendment',
        'fourth': '4th Amendment',
        'fifth': '5th Amendment',
        'fourteenth': '14th Amendment',
    };

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        // Get config from data attributes
        const analyzeBtn = document.getElementById('analyzeRightsBtn');
        if (analyzeBtn) {
            DOCUMENT_ID = analyzeBtn.getAttribute('data-document-id');
            ANALYZE_URL = `/documents/${DOCUMENT_ID}/analyze-rights/`;
            initRightsAnalysis();
        }
    });

    function initRightsAnalysis() {
        const analyzeBtn = document.getElementById('analyzeRightsBtn');
        if (!analyzeBtn) return;

        // Create the results panel
        const panel = createResultsPanel();
        const panelContainer = document.getElementById('rightsAnalysisContainer');
        if (panelContainer) {
            panelContainer.appendChild(panel);
        }

        // Add click handler
        analyzeBtn.addEventListener('click', function(e) {
            e.preventDefault();
            handleAnalyzeClick(analyzeBtn, panel);
        });
    }

    function createResultsPanel() {
        const panel = document.createElement('div');
        panel.className = 'rights-analysis-panel';
        panel.id = 'rightsAnalysisPanel';

        panel.innerHTML = `
            <div class="rights-analysis-header">
                <h6><i class="bi bi-stars me-2"></i>AI Analysis Results</h6>
                <button type="button" class="rights-analysis-close" aria-label="Close">&times;</button>
            </div>
            <div class="rights-analysis-body">
                <div class="rights-analysis-loading">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Analyzing...</span>
                    </div>
                    <span>Analyzing your case...</span>
                    <small class="text-muted mt-2">This may take a few seconds</small>
                </div>
                <div class="rights-analysis-content" style="display: none;">
                    <div class="rights-analysis-summary"></div>
                    <div class="violation-suggestions"></div>
                </div>
                <div class="rights-analysis-error" style="display: none;">
                    <i class="bi bi-exclamation-triangle-fill"></i>
                    <span class="error-message"></span>
                </div>
            </div>
        `;

        // Add close handler
        const closeBtn = panel.querySelector('.rights-analysis-close');
        closeBtn.addEventListener('click', function() {
            panel.classList.remove('active');
        });

        return panel;
    }

    function handleAnalyzeClick(button, panel) {
        // Show panel and loading state
        panel.classList.add('active');
        showLoading(panel);

        // Disable button while processing
        button.disabled = true;
        button.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Analyzing...';

        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        // Make API request
        fetch(ANALYZE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({})
        })
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                showResults(panel, data.violations, data.summary);
            } else {
                showError(panel, data.error || 'An unknown error occurred');
            }
        })
        .catch(function(error) {
            console.error('Analysis error:', error);
            showError(panel, 'Network error. Please try again.');
        })
        .finally(function() {
            // Re-enable button
            button.disabled = false;
            button.innerHTML = '<i class="bi bi-search me-1"></i>Analyze My Case';
        });
    }

    function showLoading(panel) {
        panel.querySelector('.rights-analysis-loading').style.display = 'flex';
        panel.querySelector('.rights-analysis-content').style.display = 'none';
        panel.querySelector('.rights-analysis-error').style.display = 'none';
    }

    function showResults(panel, violations, summary) {
        panel.querySelector('.rights-analysis-loading').style.display = 'none';
        panel.querySelector('.rights-analysis-error').style.display = 'none';

        const contentDiv = panel.querySelector('.rights-analysis-content');
        const summaryDiv = panel.querySelector('.rights-analysis-summary');
        const suggestionsDiv = panel.querySelector('.violation-suggestions');

        // Show summary
        if (summary) {
            summaryDiv.innerHTML = `
                <h6><i class="bi bi-lightbulb me-2"></i>Summary</h6>
                <p>${escapeHtml(summary)}</p>
            `;
            summaryDiv.style.display = 'block';
        } else {
            summaryDiv.style.display = 'none';
        }

        // Show violations
        if (violations && violations.length > 0) {
            suggestionsDiv.innerHTML = `
                <h6 class="mb-3"><i class="bi bi-shield-exclamation me-2"></i>Suggested Violations (${violations.length})</h6>
                <p class="text-muted small mb-3">Review each suggestion below. Click "Check This Box" to select the violation, then copy the explanation to the details field.</p>
                ${violations.map(v => createViolationCard(v)).join('')}
            `;

            // Add event handlers for the action buttons
            suggestionsDiv.querySelectorAll('.btn-check-violation').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    handleCheckViolation(btn);
                });
            });

            suggestionsDiv.querySelectorAll('.btn-copy-explanation').forEach(function(btn) {
                btn.addEventListener('click', function() {
                    handleCopyExplanation(btn);
                });
            });
        } else {
            suggestionsDiv.innerHTML = `
                <div class="no-violations">
                    <i class="bi bi-question-circle"></i>
                    <h6>No Clear Violations Identified</h6>
                    <p class="text-muted">Based on the information provided, we couldn't identify specific constitutional violations. Try adding more detail to your Incident Narrative section.</p>
                </div>
            `;
        }

        contentDiv.style.display = 'block';
    }

    function createViolationCard(violation) {
        const rightName = RIGHT_NAMES[violation.right] || violation.right;
        const amendmentName = AMENDMENT_NAMES[violation.amendment] || violation.amendment;
        const badgeClass = `badge-${violation.amendment}`;

        // Determine which checkbox and details field to target
        const checkboxId = `id_${violation.right}`;
        const detailsFieldId = `id_${violation.amendment}_amendment_details`;

        return `
            <div class="violation-card" data-right="${violation.right}" data-amendment="${violation.amendment}">
                <div class="violation-card-header">
                    <span class="violation-right-name">
                        <i class="bi bi-shield-check"></i>
                        ${escapeHtml(rightName)}
                    </span>
                    <span>
                        <span class="badge ${badgeClass}">${escapeHtml(amendmentName)}</span>
                        <span class="applied-badge ms-2"><i class="bi bi-check-circle-fill"></i> Applied</span>
                    </span>
                </div>
                <div class="violation-card-body">
                    <p class="violation-explanation">${escapeHtml(violation.explanation)}</p>
                    <div class="violation-actions">
                        <button type="button" class="btn btn-outline-primary btn-sm btn-check-violation"
                                data-checkbox-id="${checkboxId}">
                            <i class="bi bi-check-square me-1"></i>Check This Box
                        </button>
                        <button type="button" class="btn btn-outline-secondary btn-sm btn-copy-explanation"
                                data-details-id="${detailsFieldId}"
                                data-explanation="${escapeHtml(violation.explanation)}">
                            <i class="bi bi-clipboard me-1"></i>Copy to Details
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    function handleCheckViolation(button) {
        const checkboxId = button.getAttribute('data-checkbox-id');
        const checkbox = document.getElementById(checkboxId);

        if (checkbox) {
            checkbox.checked = true;
            checkbox.dispatchEvent(new Event('change', { bubbles: true }));

            // Also check the parent amendment checkbox if it exists
            const card = button.closest('.violation-card');
            const amendment = card.getAttribute('data-amendment');
            const parentCheckbox = document.getElementById(`id_${amendment}_amendment`);
            if (parentCheckbox && !parentCheckbox.checked) {
                parentCheckbox.checked = true;
                parentCheckbox.dispatchEvent(new Event('change', { bubbles: true }));
            }

            // Mark card as applied
            card.classList.add('applied');

            // Update button
            button.innerHTML = '<i class="bi bi-check-lg me-1"></i>Checked!';
            button.classList.remove('btn-outline-primary');
            button.classList.add('btn-success');
            button.disabled = true;

            // Scroll to the checkbox so user can see it
            checkbox.closest('.form-check, .mb-3')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    }

    function handleCopyExplanation(button) {
        const detailsId = button.getAttribute('data-details-id');
        const explanation = button.getAttribute('data-explanation');
        const detailsField = document.getElementById(detailsId);

        if (detailsField && explanation) {
            // Append to existing content with a newline if there's already text
            if (detailsField.value.trim()) {
                detailsField.value += '\n\n' + explanation;
            } else {
                detailsField.value = explanation;
            }

            detailsField.dispatchEvent(new Event('change', { bubbles: true }));
            detailsField.dispatchEvent(new Event('input', { bubbles: true }));

            // Update button
            button.innerHTML = '<i class="bi bi-check-lg me-1"></i>Copied!';
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-success');

            // Reset button after 2 seconds
            setTimeout(function() {
                button.innerHTML = '<i class="bi bi-clipboard me-1"></i>Copy to Details';
                button.classList.remove('btn-success');
                button.classList.add('btn-outline-secondary');
            }, 2000);

            // Scroll to the details field
            detailsField.scrollIntoView({ behavior: 'smooth', block: 'center' });

            // Highlight briefly
            detailsField.style.backgroundColor = '#d1e7dd';
            setTimeout(function() {
                detailsField.style.backgroundColor = '';
            }, 1000);
        }
    }

    function showError(panel, message) {
        panel.querySelector('.rights-analysis-loading').style.display = 'none';
        panel.querySelector('.rights-analysis-content').style.display = 'none';

        const errorDiv = panel.querySelector('.rights-analysis-error');
        errorDiv.querySelector('.error-message').textContent = message;
        errorDiv.style.display = 'block';
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

})();
