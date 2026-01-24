/**
 * Tell Your Story - AI-powered story parsing and form field extraction
 */

(function() {
    'use strict';

    let DOCUMENT_ID = '';
    let PARSE_URL = '';
    let STATUS_URL = '';
    let pollingInterval = null;
    let parsedSections = null; // Store all parsed sections for auto-apply
    let reliefSuggestions = null; // Store relief suggestions from AI
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
        'rights_violated': 'Rights Violated',
        'relief_sought': 'Relief Sought'
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

    // Analysis steps for progress display
    const ANALYSIS_STEPS = [
        { key: 'incident_overview', label: 'Incident Overview', icon: 'bi-calendar-event' },
        { key: 'incident_narrative', label: 'Incident Narrative', icon: 'bi-file-text' },
        { key: 'defendants', label: 'Government Defendants', icon: 'bi-person-badge' },
        { key: 'witnesses', label: 'Witnesses', icon: 'bi-people' },
        { key: 'evidence', label: 'Evidence', icon: 'bi-camera' },
        { key: 'damages', label: 'Damages', icon: 'bi-bandaid' },
        { key: 'rights_violated', label: 'Rights Violated', icon: 'bi-shield-exclamation' },
        { key: 'relief_sought', label: 'Relief Sought', icon: 'bi-trophy' }
    ];

    let progressInterval = null;
    let waitingInterval = null;
    let terminalLineIndex = 0;
    let currentStoryText = '';

    // Continuous processing commands to show while waiting for AI
    const WAITING_COMMANDS = [
        { cmd: 'validate-usc --section=42-1983', out: 'Verifying statutory requirements...' },
        { cmd: 'check-jurisdiction --federal=true', out: 'Confirming federal jurisdiction...' },
        { cmd: 'cross-ref --case-law --recent=5y', out: 'Cross-referencing case law...' },
        { cmd: 'analyze-precedent --circuit=all', out: 'Analyzing circuit precedents...' },
        { cmd: 'verify-standing --plaintiff', out: 'Verifying plaintiff standing...' },
        { cmd: 'compute-damages --type=compensatory', out: 'Computing potential damages...' },
        { cmd: 'scan-qualified-immunity --factors', out: 'Evaluating qualified immunity...' },
        { cmd: 'map-violations --to-amendments', out: 'Mapping violations to amendments...' },
        { cmd: 'build-timeline --chronological', out: 'Building incident timeline...' },
        { cmd: 'extract-quotes --from-narrative', out: 'Extracting key quotes...' },
        { cmd: 'identify-witnesses --potential', out: 'Identifying potential witnesses...' },
        { cmd: 'catalog-evidence --available', out: 'Cataloging available evidence...' },
        { cmd: 'assess-credibility --factors=7', out: 'Assessing credibility factors...' },
        { cmd: 'generate-causes-of-action', out: 'Generating causes of action...' },
        { cmd: 'draft-prayer-for-relief', out: 'Drafting prayer for relief...' },
        { cmd: 'validate-complaint --schema=federal', out: 'Validating complaint structure...' },
        { cmd: 'optimize-narrative --clarity', out: 'Optimizing narrative clarity...' },
        { cmd: 'check-statute-of-limitations', out: 'Checking statute of limitations...' },
        { cmd: 'verify-exhaustion --admin-remedies', out: 'Verifying administrative remedies...' },
        { cmd: 'analyze-municipal-liability', out: 'Analyzing municipal liability...' },
        { cmd: 'review-monell-claims --policy', out: 'Reviewing Monell claim viability...' },
        { cmd: 'calculate-fee-shifting --1988', out: 'Calculating fee-shifting basis...' },
        { cmd: 'index-constitutional-provisions', out: 'Indexing constitutional provisions...' },
        { cmd: 'finalize-defendant-list', out: 'Finalizing defendant identifications...' },
        { cmd: 'compile-factual-allegations', out: 'Compiling factual allegations...' },
        { cmd: 'structure-legal-arguments', out: 'Structuring legal arguments...' },
        { cmd: 'verify-service-addresses', out: 'Verifying service addresses...' },
        { cmd: 'format-caption --court=federal', out: 'Formatting case caption...' },
        { cmd: 'prepare-verification --pro-se', out: 'Preparing verification statement...' },
        { cmd: 'finalize-json --sections=all', out: 'Finalizing section data...' }
    ];

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        if (analyzeBtn) {
            DOCUMENT_ID = analyzeBtn.getAttribute('data-document-id');
            PARSE_URL = `/documents/${DOCUMENT_ID}/parse-story/`;
            STATUS_URL = `/documents/${DOCUMENT_ID}/parse-story/status/`;

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

        // Make API request to start background processing
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
            if (data.success && data.status === 'processing') {
                // Start polling for results
                startPolling();
            } else if (data.success && data.status === 'completed') {
                // Results returned immediately (shouldn't happen but handle it)
                reliefSuggestions = data.relief_suggestions || null;
                showResults(data.sections);
            } else if (data.limit_reached) {
                // AI limit reached - show upgrade message
                showLimitReachedError(data.error);
            } else {
                showError(data.error || 'An error occurred while analyzing your story.');
            }
        })
        .catch(error => {
            console.error('Parse error:', error);
            showError('Network error. Please try again.');
        });
    }

    function startPolling() {
        // Clear any existing polling interval
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }

        // Poll every 3 seconds
        pollingInterval = setInterval(() => {
            fetch(STATUS_URL, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'completed') {
                    // Stop polling
                    stopPolling();
                    // Update AI usage display in banner
                    updateAIUsageBanner(data.ai_usage_display);
                    // Show results
                    reliefSuggestions = data.relief_suggestions || null;
                    showResults(data.sections);
                } else if (data.status === 'failed') {
                    // Stop polling
                    stopPolling();
                    // Show error
                    showError(data.error || 'Analysis failed. Please try again.');
                }
                // If still 'processing', continue polling
            })
            .catch(error => {
                console.error('Polling error:', error);
                // Don't stop polling on network error, it might be temporary
            });
        }, 3000);
    }

    function stopPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
            pollingInterval = null;
        }
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

        // Store current story for command generation
        currentStoryText = document.getElementById('storyText').value.trim();

        // Build terminal-style progress HTML
        let progressHtml = `
            <div class="terminal-container">
                <div class="terminal-header">
                    <div class="terminal-buttons">
                        <span class="terminal-btn close"></span>
                        <span class="terminal-btn minimize"></span>
                        <span class="terminal-btn maximize"></span>
                    </div>
                    <div class="terminal-title">1983law — analyzing story</div>
                </div>
                <div class="terminal-body" id="terminalBody">
                    <!-- Commands will be added here dynamically -->
                </div>
                <div class="terminal-progress-bar">
                    <div class="terminal-progress-fill" id="terminalProgressFill"></div>
                </div>
                <div class="terminal-status">
                    <span class="terminal-status-text" id="terminalStatusText">Initializing analysis...</span>
                    <span class="terminal-percentage" id="terminalPercentage">0%</span>
                </div>
            </div>
        `;

        resultsLoading.innerHTML = progressHtml;

        // Scroll to results
        resultsPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });

        // Disable analyze button
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<i class="bi bi-terminal me-1"></i>Analyzing...';

        // Start terminal animation
        terminalLineIndex = 0;
        startTerminalAnimation();
    }

    function extractStoryContext(story) {
        // Extract useful snippets from the story for commands
        const context = {
            date: null,
            location: null,
            officer: null,
            city: null,
            action: null
        };

        // Try to extract date patterns
        const dateMatch = story.match(/(?:on\s+)?(\w+\s+\d{1,2}(?:st|nd|rd|th)?(?:,?\s+\d{4})?|\d{1,2}\/\d{1,2}\/\d{2,4})/i);
        if (dateMatch) context.date = dateMatch[1].trim().substring(0, 20);

        // Try to extract officer/person names
        const officerMatch = story.match(/(?:officer|deputy|sergeant|detective|agent|trooper)\s+(\w+)/i);
        if (officerMatch) context.officer = officerMatch[0].trim().substring(0, 25);

        // Try to extract location
        const locationMatch = story.match(/(?:at|outside|in|near)\s+(?:the\s+)?([^,.]{3,30})/i);
        if (locationMatch) context.location = locationMatch[1].trim().substring(0, 25);

        // Try to extract city
        const cityMatch = story.match(/(?:in|at)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?),?\s*(?:[A-Z]{2})?/);
        if (cityMatch) context.city = cityMatch[1].trim().substring(0, 20);

        // Try to extract an action word
        const actionMatch = story.match(/(?:arrested|detained|searched|seized|handcuffed|pushed|grabbed|tased|shot|threatened)/i);
        if (actionMatch) context.action = actionMatch[0].toLowerCase();

        return context;
    }

    function generateTerminalCommands(story) {
        const ctx = extractStoryContext(story);
        const wordCount = story.split(/\s+/).length;

        const commands = [
            // Initial setup commands
            {
                type: 'command',
                prompt: '~',
                text: `cat story.txt | wc -w`,
                output: `${wordCount} words loaded`
            },
            {
                type: 'command',
                prompt: '~',
                text: `parse-1983 --init --analyze-narrative`,
                output: 'Initialized Section 1983 complaint parser'
            },

            // Date/time extraction
            {
                type: 'command',
                prompt: '~/incident',
                text: ctx.date
                    ? `grep -oE "\\b${ctx.date.split(' ')[0]}[^.]*" story.txt`
                    : `awk '/[0-9]{1,2}[\\/\\-][0-9]{1,2}/ {print}' story.txt`,
                output: ctx.date ? `Found: "${ctx.date}"` : 'Scanning for date patterns...'
            },

            // Location extraction
            {
                type: 'command',
                prompt: '~/incident',
                text: ctx.location
                    ? `extract --location "${ctx.location.substring(0, 15)}..."`
                    : `nlp extract --type=location story.txt`,
                output: ctx.location ? `Location identified: ${ctx.location}` : 'Analyzing location context...'
            },

            // Defendant identification
            {
                type: 'command',
                prompt: '~/defendants',
                text: ctx.officer
                    ? `grep -i "officer\\|deputy\\|sergeant" story.txt | head -3`
                    : `parse-defendants --scan-titles story.txt`,
                output: ctx.officer ? `Defendant found: "${ctx.officer}"` : 'Scanning for government actors...'
            },

            // Agency lookup
            {
                type: 'command',
                prompt: '~/defendants',
                text: ctx.city
                    ? `lookup-agency --city="${ctx.city}" --infer`
                    : `infer-agency --from-context story.txt`,
                output: ctx.city ? `Searching ${ctx.city} agencies...` : 'Inferring agency from narrative...'
            },

            // Narrative parsing
            {
                type: 'command',
                prompt: '~/narrative',
                text: `nlp parse --chronological --extract-quotes story.txt`,
                output: 'Building incident timeline...'
            },

            // Rights analysis
            {
                type: 'command',
                prompt: '~/rights',
                text: ctx.action
                    ? `analyze-rights --action="${ctx.action}" --amendments=1,4,5,14`
                    : `analyze-rights --scan-violations story.txt`,
                output: 'Analyzing constitutional violations...'
            },

            // Evidence scan
            {
                type: 'command',
                prompt: '~/evidence',
                text: `grep -iE "video|photo|recording|body.?cam|witness" story.txt`,
                output: 'Cataloging potential evidence...'
            },

            // Damages assessment
            {
                type: 'command',
                prompt: '~/damages',
                text: `extract --type=damages --categories=physical,emotional,financial`,
                output: 'Assessing documented harms...'
            },

            // Relief suggestions
            {
                type: 'command',
                prompt: '~/relief',
                text: `suggest-relief --based-on=violations,damages --usc=42-1983`,
                output: 'Generating relief recommendations...'
            },

            // Final compilation
            {
                type: 'command',
                prompt: '~',
                text: `compile-sections --output=complaint.json --validate`,
                output: 'Compiling all sections...'
            }
        ];

        return commands;
    }

    function addTerminalLine(html, delay = 0) {
        const terminalBody = document.getElementById('terminalBody');
        if (!terminalBody) return;

        const line = document.createElement('div');
        line.className = 'terminal-line';
        line.style.animationDelay = delay + 'ms';
        line.innerHTML = html;
        terminalBody.appendChild(line);

        // Auto-scroll to bottom
        terminalBody.scrollTop = terminalBody.scrollHeight;
    }

    function startTerminalAnimation() {
        const commands = generateTerminalCommands(currentStoryText);
        const totalCommands = commands.length;
        let commandIndex = 0;

        // Clear any existing interval
        if (progressInterval) {
            clearInterval(progressInterval);
        }

        // Add initial line
        addTerminalLine(`<span class="terminal-comment"># Analyzing civil rights complaint narrative...</span>`);

        progressInterval = setInterval(() => {
            if (commandIndex < totalCommands) {
                const cmd = commands[commandIndex];
                const percent = Math.round(((commandIndex + 1) / totalCommands) * 95);

                // Add command line
                addTerminalLine(`
                    <span class="terminal-prompt">❯</span>
                    <span class="terminal-path">${cmd.prompt}</span>
                    <span class="terminal-command"> ${escapeHtml(cmd.text)}</span>
                `);

                // Add output after small delay
                setTimeout(() => {
                    addTerminalLine(`<span class="terminal-output">→ ${escapeHtml(cmd.output)}</span>`);
                }, 200);

                // Update progress
                const progressFill = document.getElementById('terminalProgressFill');
                const percentDisplay = document.getElementById('terminalPercentage');
                const statusText = document.getElementById('terminalStatusText');

                if (progressFill) progressFill.style.width = percent + '%';
                if (percentDisplay) percentDisplay.textContent = percent + '%';
                if (statusText) statusText.textContent = cmd.output;

                commandIndex++;
            } else {
                // Done with initial commands, start continuous waiting animation
                clearInterval(progressInterval);
                progressInterval = null;

                // Start the continuous waiting commands
                startWaitingAnimation();
            }
        }, 800);
    }

    function startWaitingAnimation() {
        let waitingIndex = 0;
        const shuffled = [...WAITING_COMMANDS].sort(() => Math.random() - 0.5);

        // Add initial waiting message
        addTerminalLine(`<span class="terminal-comment"># Awaiting AI analysis results...</span>`);

        waitingInterval = setInterval(() => {
            const cmd = shuffled[waitingIndex % shuffled.length];

            // Add command
            addTerminalLine(`
                <span class="terminal-prompt">❯</span>
                <span class="terminal-path">~/processing</span>
                <span class="terminal-command"> ${escapeHtml(cmd.cmd)}</span>
            `);

            // Add output after small delay
            setTimeout(() => {
                addTerminalLine(`<span class="terminal-output">→ ${escapeHtml(cmd.out)}</span>`);
            }, 150);

            // Update status text
            const statusText = document.getElementById('terminalStatusText');
            if (statusText) statusText.textContent = cmd.out;

            waitingIndex++;

            // Re-shuffle when we've gone through all commands
            if (waitingIndex % shuffled.length === 0) {
                shuffled.sort(() => Math.random() - 0.5);
            }
        }, 1200);
    }

    function stopWaitingAnimation() {
        if (waitingInterval) {
            clearInterval(waitingInterval);
            waitingInterval = null;
        }
    }

    function stopProgressAnimation() {
        if (progressInterval) {
            clearInterval(progressInterval);
            progressInterval = null;
        }

        // Also stop waiting animation
        stopWaitingAnimation();

        // Update terminal to show completion
        const progressFill = document.getElementById('terminalProgressFill');
        const percentDisplay = document.getElementById('terminalPercentage');
        const statusText = document.getElementById('terminalStatusText');

        if (progressFill) progressFill.style.width = '100%';
        if (percentDisplay) percentDisplay.textContent = '100%';
        if (statusText) statusText.textContent = 'Analysis complete';

        // Add completion message to terminal
        addTerminalLine(`<span class="terminal-success">✓ Analysis complete — sections ready for review</span>`);
    }

    function showResults(sections) {
        // Stop polling and progress animation
        stopPolling();
        stopProgressAnimation();

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

        // Add Relief Sought section if we have suggestions
        if (reliefSuggestions) {
            const reliefHtml = buildReliefSoughtSection(reliefSuggestions);
            if (reliefHtml) {
                accordion.innerHTML += buildAccordionItem('Relief Sought', 'collapse-relief_sought', false, reliefHtml, 'relief_sought', Object.keys(reliefSuggestions).length);
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
        const isAgencyInferred = data.agency_inferred === true || data.agency_inferred === 'true';

        for (const [fieldKey, fieldValue] of Object.entries(data)) {
            if (fieldValue === null || fieldValue === '' || fieldValue === undefined) continue;
            // Skip the agency_inferred meta field from display
            if (fieldKey === 'agency_inferred') continue;

            const fieldName = FIELD_NAMES[fieldKey] || fieldKey;

            // Show warning for inferred agency
            const isInferredAgency = fieldKey === 'agency' && isAgencyInferred;
            const warningHtml = isInferredAgency
                ? '<div class="text-warning small mt-1"><i class="bi bi-exclamation-triangle me-1"></i>AI suggested - please verify this is correct</div>'
                : '';
            const borderClass = isInferredAgency ? 'border-warning' : '';

            fieldsHtml += `
                <div class="field-item mb-2 p-2 border rounded bg-light ${borderClass}">
                    <div class="fw-bold small text-primary">${fieldName}</div>
                    <div class="field-value text-dark">
                        ${escapeHtml(String(fieldValue))}
                    </div>
                    ${warningHtml}
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

    function buildReliefSoughtSection(relief) {
        if (!relief) return '';

        const reliefTypes = {
            'compensatory_damages': 'Compensatory Damages',
            'punitive_damages': 'Punitive Damages',
            'declaratory_relief': 'Declaratory Relief',
            'injunctive_relief': 'Injunctive Relief',
            'attorney_fees': "Attorney's Fees",
            'jury_trial': 'Jury Trial'
        };

        let html = '<p class="text-muted small mb-3">Based on your case, AI recommends the following relief:</p>';

        for (const [key, label] of Object.entries(reliefTypes)) {
            const item = relief[key];
            if (!item) continue;

            const recommended = item.recommended === true || item.recommended === 'true';
            const iconClass = recommended ? 'bi-check-circle-fill text-success' : 'bi-x-circle text-muted';
            const bgClass = recommended ? 'bg-light' : 'bg-white';

            html += `
                <div class="field-item mb-2 p-2 border rounded ${bgClass}">
                    <div class="d-flex align-items-center">
                        <i class="bi ${iconClass} me-2"></i>
                        <span class="fw-bold ${recommended ? 'text-primary' : 'text-muted'}">${label}</span>
                    </div>
                    <div class="text-muted small mt-1 ms-4">
                        ${escapeHtml(item.reason || '')}
                    </div>
                    ${item.suggested_declaration ? `<div class="text-info small mt-1 ms-4"><strong>Declaration:</strong> ${escapeHtml(item.suggested_declaration)}</div>` : ''}
                    ${item.suggested_injunction ? `<div class="text-info small mt-1 ms-4"><strong>Injunction:</strong> ${escapeHtml(item.suggested_injunction)}</div>` : ''}
                </div>
            `;
        }

        return html;
    }

    function showError(message) {
        // Stop polling and progress animation
        stopPolling();
        stopProgressAnimation();

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

    function showLimitReachedError(message) {
        // Stop polling and progress animation
        stopPolling();
        stopProgressAnimation();

        const resultsLoading = document.getElementById('resultsLoading');
        const resultsContent = document.getElementById('resultsContent');
        const resultsError = document.getElementById('resultsError');

        resultsLoading.style.display = 'none';
        resultsContent.style.display = 'none';
        resultsError.style.display = 'block';

        // Show upgrade message with button
        resultsError.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-exclamation-triangle-fill text-warning" style="font-size: 3rem;"></i>
                <h5 class="mt-3 text-warning">AI Limit Reached</h5>
                <p class="text-muted">${escapeHtml(message)}</p>
                <a href="/documents/${DOCUMENT_ID}/checkout/" class="btn btn-primary mt-2">
                    <i class="bi bi-unlock me-1"></i>Upgrade Now
                </a>
                <p class="text-muted small mt-3">Upgrade to continue using AI features and generate your legal document.</p>
            </div>
        `;

        // Re-enable analyze button
        const analyzeBtn = document.getElementById('analyzeStoryBtn');
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<i class="bi bi-stars me-1"></i>Analyze My Story';
    }

    function hideResults() {
        stopPolling();
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

        // Add relief suggestions to fields
        if (reliefSuggestions) {
            for (const [key, item] of Object.entries(reliefSuggestions)) {
                if (!item) continue;
                const recommended = item.recommended === true || item.recommended === 'true';
                fieldsToApply.push({
                    section: 'relief_sought',
                    field: key,
                    value: recommended,
                    reason: item.suggested_declaration || item.suggested_injunction || ''
                });
            }
        }

        if (fieldsToApply.length === 0) {
            alert('No fields found to apply.');
            return;
        }

        // Debug: Log relief_sought fields being sent
        const reliefFields = fieldsToApply.filter(f => f.section === 'relief_sought');
        console.log('Relief fields to apply:', reliefFields);

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
                // Log any section-specific errors for debugging
                if (data.errors && data.errors.length > 0) {
                    console.warn('Some sections had errors:', data.errors);
                }
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

    function updateAIUsageBanner(displayText) {
        // Update the AI usage display in the status banner
        const aiUsageDisplay = document.getElementById('aiUsageDisplay');
        if (aiUsageDisplay && displayText) {
            aiUsageDisplay.textContent = displayText;
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
