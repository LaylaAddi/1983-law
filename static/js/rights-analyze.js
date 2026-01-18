/**
 * Rights Analysis Feature
 * AI-powered analysis to suggest constitutional rights violations
 */

(function() {
    'use strict';

    // Will be set from template
    let ANALYZE_URL = '';
    let DOCUMENT_ID = '';
    let progressInterval = null;
    let terminalLineIndex = 0;

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
        const loadingDiv = panel.querySelector('.rights-analysis-loading');
        loadingDiv.style.display = 'block';
        panel.querySelector('.rights-analysis-content').style.display = 'none';
        panel.querySelector('.rights-analysis-error').style.display = 'none';

        // Build terminal-style progress HTML
        loadingDiv.innerHTML = `
            <div class="rights-terminal-container">
                <div class="rights-terminal-header">
                    <div class="rights-terminal-buttons">
                        <span class="rights-terminal-btn close"></span>
                        <span class="rights-terminal-btn minimize"></span>
                        <span class="rights-terminal-btn maximize"></span>
                    </div>
                    <div class="rights-terminal-title">1983law — analyzing rights violations</div>
                </div>
                <div class="rights-terminal-body" id="rightsTerminalBody">
                </div>
                <div class="rights-terminal-progress-bar">
                    <div class="rights-terminal-progress-fill" id="rightsProgressFill"></div>
                </div>
                <div class="rights-terminal-status">
                    <span class="rights-terminal-status-text" id="rightsStatusText">Initializing analysis...</span>
                    <span class="rights-terminal-percentage" id="rightsPercentage">0%</span>
                </div>
            </div>
        `;

        // Start terminal animation
        terminalLineIndex = 0;
        startTerminalAnimation();
    }

    function generateRightsCommands() {
        return [
            {
                prompt: '~',
                text: 'load-narrative --from=incident_narrative',
                output: 'Loading incident narrative...'
            },
            {
                prompt: '~/analysis',
                text: 'grep -i "arrest|detained|search|seized" narrative.txt',
                output: 'Scanning for Fourth Amendment indicators...'
            },
            {
                prompt: '~/analysis',
                text: 'check-first-amendment --speech --press --assembly',
                output: 'Analyzing First Amendment issues...'
            },
            {
                prompt: '~/analysis',
                text: 'analyze-force --usc=42-1983 --graham-v-connor',
                output: 'Evaluating use of force claims...'
            },
            {
                prompt: '~/analysis',
                text: 'check-due-process --fifth --fourteenth',
                output: 'Reviewing due process violations...'
            },
            {
                prompt: '~/rights',
                text: 'match-violations --case-law --precedents',
                output: 'Matching to established case law...'
            },
            {
                prompt: '~/rights',
                text: 'generate-suggestions --confidence-scores',
                output: 'Generating violation suggestions...'
            },
            {
                prompt: '~',
                text: 'compile-results --format=json',
                output: 'Compiling analysis results...'
            }
        ];
    }

    function addTerminalLine(html) {
        const terminalBody = document.getElementById('rightsTerminalBody');
        if (!terminalBody) return;

        const line = document.createElement('div');
        line.className = 'rights-terminal-line';
        line.innerHTML = html;
        terminalBody.appendChild(line);

        // Auto-scroll to bottom
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }

    function startTerminalAnimation() {
        const commands = generateRightsCommands();
        const totalCommands = commands.length;
        let commandIndex = 0;

        // Clear any existing interval
        if (progressInterval) {
            clearInterval(progressInterval);
        }

        // Add initial comment
        addTerminalLine('<span class="rights-terminal-comment"># Analyzing constitutional rights violations...</span>');

        progressInterval = setInterval(function() {
            if (commandIndex < totalCommands) {
                const cmd = commands[commandIndex];
                const percent = Math.round(((commandIndex + 1) / totalCommands) * 90);

                // Add command line
                addTerminalLine(`
                    <span class="rights-terminal-prompt">❯</span>
                    <span class="rights-terminal-path">${cmd.prompt}</span>
                    <span class="rights-terminal-command"> ${escapeHtml(cmd.text)}</span>
                `);

                // Add output after small delay
                setTimeout(function() {
                    addTerminalLine('<span class="rights-terminal-output">→ ' + escapeHtml(cmd.output) + '</span>');
                }, 200);

                // Update progress
                const progressFill = document.getElementById('rightsProgressFill');
                const percentDisplay = document.getElementById('rightsPercentage');
                const statusText = document.getElementById('rightsStatusText');

                if (progressFill) progressFill.style.width = percent + '%';
                if (percentDisplay) percentDisplay.textContent = percent + '%';
                if (statusText) statusText.textContent = cmd.output;

                commandIndex++;
            } else {
                // Done with commands, show waiting state
                clearInterval(progressInterval);
                progressInterval = null;

                addTerminalLine('<span class="rights-terminal-info"><span class="rights-terminal-spinner"></span> Waiting for AI response...</span>');

                const statusText = document.getElementById('rightsStatusText');
                if (statusText) statusText.textContent = 'Waiting for analysis to complete...';
            }
        }, 600);
    }

    function stopProgressAnimation() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }

        // Update terminal to show completion
        const progressFill = document.getElementById('rightsProgressFill');
        const percentDisplay = document.getElementById('rightsPercentage');
        const statusText = document.getElementById('rightsStatusText');

        if (progressFill) progressFill.style.width = '100%';
        if (percentDisplay) percentDisplay.textContent = '100%';
        if (statusText) statusText.textContent = 'Analysis complete';

        // Add completion message to terminal
        addTerminalLine('<span class="rights-terminal-success">✓ Analysis complete — review suggestions below</span>');
    }

    function showResults(panel, violations, summary) {
        stopProgressAnimation();
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
            // Check if field already has content
            if (detailsField.value.trim()) {
                // Show confirmation dialog
                const choice = confirm(
                    'This field already has content.\n\n' +
                    'Click OK to REPLACE the existing text.\n' +
                    'Click Cancel to APPEND to the existing text.'
                );

                if (choice) {
                    // Replace
                    detailsField.value = explanation;
                } else {
                    // Append
                    detailsField.value += '\n\n' + explanation;
                }
            } else {
                // Field is empty, just set the value
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
        stopProgressAnimation();
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
