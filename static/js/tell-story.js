/**
 * Tell Your Story - AI-powered story parsing and form field extraction
 */

(function() {
    'use strict';

    let DOCUMENT_ID = '';
    let PARSE_URL = '';
    let parsedSections = null; // Store all parsed sections for auto-apply
    let currentQuestions = []; // Store questions for re-analysis
    let markedNaItems = []; // Store N/A items to filter from future questions

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

            // Load previously marked N/A items from sessionStorage
            const storedNaItems = sessionStorage.getItem(`naItems-${DOCUMENT_ID}`);
            if (storedNaItems) {
                markedNaItems = JSON.parse(storedNaItems);
            }

            initStoryParsing();
        }
    });

    function initStoryParsing() {
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        const closeResultsBtn = document.getElementById('closeResultsBtn');
        const applySelectedBtn = document.getElementById('applySelectedBtn');
        const reanalyzeBtn = document.getElementById('reanalyzeBtn');

        analyzeBtn.addEventListener('click', handleAnalyzeClick);
        closeResultsBtn.addEventListener('click', hideResults);
        applySelectedBtn.addEventListener('click', handleApplyAll);

        if (reanalyzeBtn) {
            reanalyzeBtn.addEventListener('click', handleReanalyze);
        }
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

        analyzeStory(storyText);
    }

    function handleReanalyze() {
        // Get original story text
        let storyText = document.getElementById('storyText').value.trim();

        // Collect answers from missing info fields
        const additionalInfo = [];
        const newNaItems = [];

        document.querySelectorAll('.missing-info-input').forEach(input => {
            const naCheckbox = document.getElementById(input.id + '-na');
            const question = input.getAttribute('data-question');

            if (naCheckbox && naCheckbox.checked) {
                // Track N/A items so GPT won't ask again
                newNaItems.push(question);
                return;
            }
            const value = input.value.trim();
            if (value) {
                additionalInfo.push(`${question}: ${value}`);
            }
        });

        // Add new N/A items to persistent list (avoid duplicates)
        newNaItems.forEach(item => {
            if (!markedNaItems.includes(item)) {
                markedNaItems.push(item);
            }
        });

        // Save N/A items to sessionStorage for persistence
        sessionStorage.setItem(`naItems-${DOCUMENT_ID}`, JSON.stringify(markedNaItems));

        // Append additional info to story if any
        if (additionalInfo.length > 0) {
            storyText += '\n\nAdditional information:\n' + additionalInfo.join('\n');
        }

        // Append N/A items so GPT knows not to ask about them
        if (markedNaItems.length > 0) {
            storyText += '\n\nNot applicable or unknown:\n' + markedNaItems.map(q => `- ${q}`).join('\n');
        }

        // Update the textarea with the combined story
        if (additionalInfo.length > 0 || markedNaItems.length > 0) {
            document.getElementById('storyText').value = storyText;
        }

        analyzeStory(storyText);
    }

    function analyzeStory(storyText) {
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

        // Store sections for auto-apply
        parsedSections = sections;

        // Show questions with input fields if any
        if (sections.questions_to_ask && sections.questions_to_ask.length > 0) {
            // Filter out questions that match previously marked N/A items
            const filteredQuestions = sections.questions_to_ask.filter(question => {
                // Check if this question matches any N/A item (case-insensitive partial match)
                return !markedNaItems.some(naItem => {
                    const naLower = naItem.toLowerCase();
                    const questionLower = question.toLowerCase();
                    // Check for substantial overlap (either contains the other or similar keywords)
                    return naLower.includes(questionLower.slice(0, 20)) ||
                           questionLower.includes(naLower.slice(0, 20)) ||
                           naLower === questionLower;
                });
            });

            currentQuestions = filteredQuestions;

            if (filteredQuestions.length > 0) {
                questionsList.innerHTML = buildQuestionsInputs(filteredQuestions);
                questionsSection.style.display = 'block';

                // Add event listeners for N/A checkboxes
                document.querySelectorAll('.na-checkbox').forEach(cb => {
                    cb.addEventListener('change', function() {
                        const inputId = this.id.replace('-na', '');
                        const input = document.getElementById(inputId);
                        if (input) {
                            input.disabled = this.checked;
                            if (this.checked) {
                                input.value = '';
                                input.classList.add('bg-light');
                            } else {
                                input.classList.remove('bg-light');
                            }
                        }
                    });
                });
            } else {
                questionsSection.style.display = 'none';
            }
        } else {
            questionsSection.style.display = 'none';
        }

        // Build accordion sections (display only, no checkboxes)
        accordion.innerHTML = '';
        let sectionIndex = 0;

        for (const [sectionKey, sectionData] of Object.entries(sections)) {
            if (sectionKey === 'questions_to_ask') continue;

            const sectionHtml = buildSectionAccordion(sectionKey, sectionData, sectionIndex);
            if (sectionHtml) {
                accordion.innerHTML += sectionHtml;
                sectionIndex++;
            }
        }

        // Re-enable analyze button
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="bi bi-stars me-1"></i>Analyze My Story';
    }

    function buildQuestionsInputs(questions) {
        let html = '';
        questions.forEach((question, index) => {
            const inputId = `missing-info-${index}`;
            html += `
                <div class="mb-3">
                    <label for="${inputId}" class="form-label small fw-bold">${escapeHtml(question)}</label>
                    <div class="input-group">
                        <input type="text"
                               class="form-control missing-info-input"
                               id="${inputId}"
                               data-question="${escapeHtml(question)}"
                               placeholder="Enter your answer...">
                        <div class="input-group-text">
                            <input class="form-check-input mt-0 na-checkbox"
                                   type="checkbox"
                                   id="${inputId}-na"
                                   title="Not applicable / Don't know">
                            <label class="ms-1 small" for="${inputId}-na">N/A</label>
                        </div>
                    </div>
                </div>
            `;
        });
        return html;
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
            let fieldCount = 0;
            sectionData.forEach((item, itemIndex) => {
                const itemFields = buildFieldsList(item, sectionKey, itemIndex);
                if (itemFields) {
                    fieldCount += Object.values(item).filter(v => v !== null && v !== '' && v !== undefined).length;
                    itemsHtml += `
                        <div class="mb-3 p-3 border rounded">
                            <h6 class="text-muted mb-3">${sectionName} #${itemIndex + 1}</h6>
                            ${itemFields}
                        </div>
                    `;
                }
            });

            if (!itemsHtml) return '';

            return buildAccordionItem(sectionName, collapseId, isExpanded, itemsHtml, sectionKey, fieldCount);
        }

        // Handle object sections (incident_overview, incident_narrative, damages)
        if (typeof sectionData === 'object') {
            // Special handling for rights_violated
            if (sectionKey === 'rights_violated' && sectionData.suggested_violations) {
                const violationsHtml = buildRightsViolatedSection(sectionData.suggested_violations);
                if (!violationsHtml) return '';
                const fieldCount = sectionData.suggested_violations.length;
                return buildAccordionItem(sectionName, collapseId, isExpanded, violationsHtml, sectionKey, fieldCount);
            }

            const fieldsHtml = buildFieldsList(sectionData, sectionKey);
            if (!fieldsHtml) return '';
            const fieldCount = Object.values(sectionData).filter(v => v !== null && v !== '' && v !== undefined).length;
            return buildAccordionItem(sectionName, collapseId, isExpanded, fieldsHtml, sectionKey, fieldCount);
        }

        return '';
    }

    function buildAccordionItem(title, collapseId, isExpanded, content, sectionKey, fieldCount = 0) {
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

            fieldsHtml += `
                <div class="field-item mb-2 p-2 border rounded bg-light">
                    <div class="fw-bold small text-primary">${fieldName}</div>
                    <div class="field-value text-dark">
                        ${escapeHtml(String(fieldValue))}
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
            const rightName = violation.right.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

            html += `
                <div class="field-item mb-2 p-2 border rounded bg-light">
                    <div class="fw-bold text-primary">${rightName}</div>
                    <div class="text-muted small mt-1">
                        ${escapeHtml(violation.reason)}
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

    function handleApplyAll() {
        if (!parsedSections) {
            alert('No analysis results to apply. Please analyze your story first.');
            return;
        }

        // Convert parsed sections to fields array for the API
        const fieldsToApply = [];

        for (const [sectionKey, sectionData] of Object.entries(parsedSections)) {
            if (sectionKey === 'questions_to_ask') continue;

            // Handle array sections (defendants, witnesses, evidence)
            if (Array.isArray(sectionData)) {
                sectionData.forEach((item, itemIndex) => {
                    for (const [fieldKey, fieldValue] of Object.entries(item)) {
                        if (fieldValue === null || fieldValue === '' || fieldValue === undefined) continue;
                        fieldsToApply.push({
                            section: sectionKey,
                            field: fieldKey,
                            value: String(fieldValue),
                            itemIndex: String(itemIndex)
                        });
                    }
                });
            }
            // Handle rights_violated specially
            else if (sectionKey === 'rights_violated' && sectionData.suggested_violations) {
                sectionData.suggested_violations.forEach((violation) => {
                    fieldsToApply.push({
                        section: 'rights_violated',
                        field: violation.right,
                        amendment: violation.amendment,
                        reason: violation.reason
                    });
                });
            }
            // Handle object sections (incident_overview, incident_narrative, damages)
            else if (typeof sectionData === 'object') {
                for (const [fieldKey, fieldValue] of Object.entries(sectionData)) {
                    if (fieldValue === null || fieldValue === '' || fieldValue === undefined) continue;
                    fieldsToApply.push({
                        section: sectionKey,
                        field: fieldKey,
                        value: String(fieldValue)
                    });
                }
            }
        }

        if (fieldsToApply.length === 0) {
            alert('No fields found to apply.');
            return;
        }

        // Disable button and show saving state
        const applyBtn = document.getElementById('applySelectedBtn');
        applyBtn.disabled = true;
        applyBtn.innerHTML = '<i class="bi bi-hourglass-split me-1"></i>Saving...';

        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                          getCookie('csrftoken');

        // Save fields to database
        fetch(`/documents/${DOCUMENT_ID}/apply-story-fields/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({ fields: fieldsToApply })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Clear N/A items since we're done with this story
                sessionStorage.removeItem(`naItems-${DOCUMENT_ID}`);
                // Go to document
                window.location.href = `/documents/${DOCUMENT_ID}/`;
            } else {
                alert('Error saving fields: ' + (data.error || 'Unknown error'));
                applyBtn.disabled = false;
                applyBtn.innerHTML = '<i class="bi bi-arrow-right me-1"></i>Continue to Document';
            }
        })
        .catch(error => {
            console.error('Save error:', error);
            alert('Network error. Please try again.');
            applyBtn.disabled = false;
            applyBtn.innerHTML = '<i class="bi bi-arrow-right me-1"></i>Continue to Document';
        });
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
