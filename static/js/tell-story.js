/**
 * Tell Your Story - AI-powered story parsing and form field extraction
 */

(function() {
    'use strict';

    let DOCUMENT_ID = '';
    let PARSE_URL = '';
    let selectedFields = new Set();

    // Section display names
    const SECTION_NAMES = {
        'incident_overview': 'Incident Overview',
        'incident_narrative': 'Incident Narrative',
        'defendants': 'Government Defendants',
        'witnesses': 'Witnesses',
        'evidence': 'Evidence',
        'damages': 'Damages',
        'rights_violated': 'Rights Violated'
    };

    // Field display names
    const FIELD_NAMES = {
        // Incident Overview
        'incident_date': 'Incident Date',
        'incident_time': 'Time',
        'incident_location': 'Location',
        'city': 'City',
        'state': 'State',
        // Incident Narrative
        'summary': 'Summary',
        'detailed_narrative': 'Detailed Narrative',
        'what_were_you_doing': 'What Were You Doing',
        'initial_contact': 'Initial Contact',
        'what_was_said': 'What Was Said',
        'physical_actions': 'Physical Actions',
        'how_it_ended': 'How It Ended',
        // Defendants
        'name': 'Name',
        'badge_number': 'Badge Number',
        'title': 'Title',
        'agency': 'Agency',
        'description': 'Description',
        // Witnesses
        'what_they_saw': 'What They Saw',
        // Evidence
        'type': 'Type',
        // Damages
        'physical_injuries': 'Physical Injuries',
        'emotional_distress': 'Emotional Distress',
        'financial_losses': 'Financial Losses',
        'other_damages': 'Other Damages'
    };

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        if (analyzeBtn) {
            DOCUMENT_ID = analyzeBtn.getAttribute('data-document-id');
            PARSE_URL = `/documents/${DOCUMENT_ID}/parse-story/`;
            initStoryParsing();
        }
    });

    function initStoryParsing() {
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        const closeResultsBtn = document.getElementById('closeResultsBtn');
        const selectAllBtn = document.getElementById('selectAllBtn');
        const applySelectedBtn = document.getElementById('applySelectedBtn');

        analyzeBtn.addEventListener('click', handleAnalyzeClick);
        closeResultsBtn.addEventListener('click', hideResults);
        selectAllBtn.addEventListener('click', handleSelectAll);
        applySelectedBtn.addEventListener('click', handleApplySelected);
    }

    function handleAnalyzeClick() {
        const storyText = document.getElementById('storyText').value.trim();

        if (!storyText) {
            alert('Please enter your story first.');
            return;
        }

        if (storyText.length < 50) {
            alert('Please provide more detail in your story. Try to include when, where, who, and what happened.');
            return;
        }

        // Show results panel and loading state
        showLoading();

        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                          getCookie('csrftoken');

        // Make API request
        fetch(PARSE_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ story: storyText })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showResults(data.sections);
            } else {
                showError(data.error || 'An error occurred while analyzing your story.');
            }
        })
        .catch(error => {
            console.error('Parse error:', error);
            showError('Network error. Please try again.');
        });
    }

    function showLoading() {
        const resultsPanel = document.getElementById('resultsPanel');
        const resultsLoading = document.getElementById('resultsLoading');
        const resultsContent = document.getElementById('resultsContent');
        const resultsError = document.getElementById('resultsError');

        resultsPanel.style.display = 'block';
        resultsLoading.style.display = 'block';
        resultsContent.style.display = 'none';
        resultsError.style.display = 'none';

        // Scroll to results
        resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Disable analyze button
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Analyzing...';
    }

    function showResults(sections) {
        const resultsLoading = document.getElementById('resultsLoading');
        const resultsContent = document.getElementById('resultsContent');
        const resultsError = document.getElementById('resultsError');
        const accordion = document.getElementById('sectionsAccordion');
        const questionsSection = document.getElementById('questionsSection');
        const questionsList = document.getElementById('questionsList');

        resultsLoading.style.display = 'none';
        resultsError.style.display = 'none';
        resultsContent.style.display = 'block';

        // Reset selections
        selectedFields.clear();
        updateSelectedCount();

        // Show questions if any
        if (sections.questions_to_ask && sections.questions_to_ask.length > 0) {
            questionsList.innerHTML = sections.questions_to_ask
                .map(q => `<li>${escapeHtml(q)}</li>`)
                .join('');
            questionsSection.style.display = 'block';
        } else {
            questionsSection.style.display = 'none';
        }

        // Build accordion sections
        accordion.innerHTML = '';
        let sectionIndex = 0;
        let totalFields = 0;
        let filledFields = 0;

        for (const [sectionKey, sectionData] of Object.entries(sections)) {
            if (sectionKey === 'questions_to_ask') continue;

            const sectionHtml = buildSectionAccordion(sectionKey, sectionData, sectionIndex);
            if (sectionHtml) {
                accordion.innerHTML += sectionHtml;
                sectionIndex++;
            }
        }

        // Add event listeners to checkboxes
        accordion.querySelectorAll('.field-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const fieldId = this.getAttribute('data-field-id');
                if (this.checked) {
                    selectedFields.add(fieldId);
                } else {
                    selectedFields.delete(fieldId);
                }
                updateSelectedCount();
            });
        });

        // Re-enable analyze button
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="bi bi-stars me-1"></i>Analyze My Story';
    }

    function buildSectionAccordion(sectionKey, sectionData, index) {
        if (!sectionData) return '';

        const sectionName = SECTION_NAMES[sectionKey] || sectionKey;
        const isExpanded = index === 0;
        const collapseId = `collapse-${sectionKey}`;

        // Handle array sections (defendants, witnesses, evidence)
        if (Array.isArray(sectionData)) {
            if (sectionData.length === 0) return '';

            let itemsHtml = '';
            sectionData.forEach((item, itemIndex) => {
                const itemFields = buildFieldsList(item, sectionKey, itemIndex);
                if (itemFields) {
                    itemsHtml += `
                        <div class="mb-3 p-3 bg-light rounded">
                            <h6 class="text-muted mb-3">${sectionName} #${itemIndex + 1}</h6>
                            ${itemFields}
                        </div>
                    `;
                }
            });

            if (!itemsHtml) return '';

            return buildAccordionItem(sectionName, collapseId, isExpanded, itemsHtml, sectionKey);
        }

        // Handle object sections (incident_overview, incident_narrative, damages)
        if (typeof sectionData === 'object') {
            // Special handling for rights_violated
            if (sectionKey === 'rights_violated' && sectionData.suggested_violations) {
                const violationsHtml = buildRightsViolatedSection(sectionData.suggested_violations);
                if (!violationsHtml) return '';
                return buildAccordionItem(sectionName, collapseId, isExpanded, violationsHtml, sectionKey);
            }

            const fieldsHtml = buildFieldsList(sectionData, sectionKey);
            if (!fieldsHtml) return '';
            return buildAccordionItem(sectionName, collapseId, isExpanded, fieldsHtml, sectionKey);
        }

        return '';
    }

    function buildAccordionItem(title, collapseId, isExpanded, content, sectionKey) {
        const fieldCount = (content.match(/field-checkbox/g) || []).length;
        const badge = fieldCount > 0 ? `<span class="badge bg-primary ms-2">${fieldCount} fields</span>` : '';

        return `
            <div class="accordion-item">
                <h2 class="accordion-header">
                    <button class="accordion-button ${isExpanded ? '' : 'collapsed'}" type="button"
                            data-bs-toggle="collapse" data-bs-target="#${collapseId}">
                        <i class="bi bi-folder me-2"></i>${title}${badge}
                    </button>
                </h2>
                <div id="${collapseId}" class="accordion-collapse collapse ${isExpanded ? 'show' : ''}"
                     data-bs-parent="#sectionsAccordion">
                    <div class="accordion-body">
                        ${content}
                    </div>
                </div>
            </div>
        `;
    }

    function buildFieldsList(data, sectionKey, itemIndex = null) {
        let fieldsHtml = '';

        for (const [fieldKey, fieldValue] of Object.entries(data)) {
            if (fieldValue === null || fieldValue === '' || fieldValue === undefined) continue;

            const fieldName = FIELD_NAMES[fieldKey] || fieldKey;
            const fieldId = itemIndex !== null
                ? `${sectionKey}-${itemIndex}-${fieldKey}`
                : `${sectionKey}-${fieldKey}`;

            fieldsHtml += `
                <div class="field-item mb-3 p-2 border rounded">
                    <div class="d-flex align-items-start">
                        <div class="form-check me-3">
                            <input class="form-check-input field-checkbox" type="checkbox"
                                   id="check-${fieldId}"
                                   data-field-id="${fieldId}"
                                   data-section="${sectionKey}"
                                   data-field="${fieldKey}"
                                   data-value="${escapeHtml(String(fieldValue))}"
                                   ${itemIndex !== null ? `data-item-index="${itemIndex}"` : ''}>
                        </div>
                        <div class="flex-grow-1">
                            <label class="form-check-label fw-bold" for="check-${fieldId}">
                                ${fieldName}
                            </label>
                            <div class="field-value mt-1 text-muted small">
                                ${escapeHtml(String(fieldValue))}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }

        return fieldsHtml;
    }

    function buildRightsViolatedSection(violations) {
        if (!violations || violations.length === 0) return '';

        let html = '<p class="text-muted small mb-3">Based on your story, these rights may have been violated:</p>';

        violations.forEach((violation, index) => {
            const fieldId = `rights_violated-${index}-${violation.right}`;
            const rightName = violation.right.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            html += `
                <div class="field-item mb-3 p-2 border rounded">
                    <div class="d-flex align-items-start">
                        <div class="form-check me-3">
                            <input class="form-check-input field-checkbox" type="checkbox"
                                   id="check-${fieldId}"
                                   data-field-id="${fieldId}"
                                   data-section="rights_violated"
                                   data-field="${violation.right}"
                                   data-amendment="${violation.amendment}"
                                   data-reason="${escapeHtml(violation.reason)}">
                        </div>
                        <div class="flex-grow-1">
                            <label class="form-check-label fw-bold" for="check-${fieldId}">
                                ${rightName}
                            </label>
                            <div class="text-muted small mt-1">
                                ${escapeHtml(violation.reason)}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });

        return html;
    }

    function showError(message) {
        const resultsLoading = document.getElementById('resultsLoading');
        const resultsContent = document.getElementById('resultsContent');
        const resultsError = document.getElementById('resultsError');
        const errorMessage = document.getElementById('errorMessage');

        resultsLoading.style.display = 'none';
        resultsContent.style.display = 'none';
        resultsError.style.display = 'block';
        errorMessage.textContent = message;

        // Re-enable analyze button
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="bi bi-stars me-1"></i>Analyze My Story';
    }

    function hideResults() {
        const resultsPanel = document.getElementById('resultsPanel');
        resultsPanel.style.display = 'none';
    }

    function handleSelectAll() {
        const checkboxes = document.querySelectorAll('.field-checkbox');
        const allChecked = Array.from(checkboxes).every(cb => cb.checked);

        checkboxes.forEach(cb => {
            cb.checked = !allChecked;
            const fieldId = cb.getAttribute('data-field-id');
            if (cb.checked) {
                selectedFields.add(fieldId);
            } else {
                selectedFields.delete(fieldId);
            }
        });

        updateSelectedCount();
    }

    function updateSelectedCount() {
        const countSpan = document.getElementById('acceptedCount');
        const applyBtn = document.getElementById('applySelectedBtn');

        countSpan.textContent = `${selectedFields.size} field${selectedFields.size !== 1 ? 's' : ''} selected`;
        applyBtn.disabled = selectedFields.size === 0;
    }

    function handleApplySelected() {
        if (selectedFields.size === 0) {
            alert('Please select at least one field to apply.');
            return;
        }

        // Collect all selected field data
        const fieldsToApply = [];
        document.querySelectorAll('.field-checkbox:checked').forEach(cb => {
            fieldsToApply.push({
                section: cb.getAttribute('data-section'),
                field: cb.getAttribute('data-field'),
                value: cb.getAttribute('data-value'),
                itemIndex: cb.getAttribute('data-item-index'),
                amendment: cb.getAttribute('data-amendment'),
                reason: cb.getAttribute('data-reason')
            });
        });

        // For now, show a summary and redirect to document
        // In the future, this could save directly via AJAX
        const message = `Selected ${fieldsToApply.length} field(s) to apply.\n\n` +
            `Note: In this version, you'll need to manually enter the suggested values into each section. ` +
            `The values have been analyzed and are shown above.\n\n` +
            `Click OK to go to your document and start filling in the sections.`;

        if (confirm(message)) {
            // Store selections in sessionStorage for potential future use
            sessionStorage.setItem('storyParsedFields', JSON.stringify(fieldsToApply));
            window.location.href = `/documents/${DOCUMENT_ID}/`;
        }
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

})();
