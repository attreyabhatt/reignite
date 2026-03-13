(function () {
    const DEFAULT_CUSTOM_SCENARIO_LABEL = 'Custom Scenario';

    function getCsrfToken() {
        return document.querySelector('input[name=csrfmiddlewaretoken]')?.value || '';
    }

    function getResponsePanel() {
        return document.getElementById('responsePanel');
    }

    function getEmptyTemplate() {
        return document.getElementById('response-empty-template');
    }

    function resetResponsePanel() {
        const panel = getResponsePanel();
        const template = getEmptyTemplate();
        if (!panel || !template) {
            return;
        }
        panel.innerHTML = template.innerHTML.trim();
    }

    function updateCharCount() {
        const counter = document.getElementById('charCount');
        const textarea = document.getElementById('last-reply');
        if (!counter || !textarea) {
            return;
        }
        counter.textContent = String(textarea.value.length);
    }

    function normalizeOcrTranscript(text) {
        if (!text) {
            return '';
        }

        return String(text)
            .replace(/^\s*you\s*\[\s*\]\s*:/gim, 'You:')
            .replace(/^\s*her\s*\[\s*\]\s*:/gim, 'Her:');
    }

    function toggleInputVisibility() {
        const situation = document.getElementById('situation');
        const screenshotUpload = document.getElementById('screenshot-upload');
        const conversationArea = document.getElementById('conversation-paste-area');
        const herInfoDiv = document.getElementById('her-info-div');
        const replyForm = document.querySelector('form[data-web-reply-form]');

        if (!situation) {
            return;
        }

        const value = situation.value;
        const showConversationInputs = value !== 'just_matched';
        const forceShowUpload = replyForm?.getAttribute('data-force-show-upload') === '1';
        const showScreenshotUpload = showConversationInputs || (forceShowUpload && value === 'just_matched');
        const showHerInfo = value === 'just_matched' || value === 'spark_interest';

        if (screenshotUpload) {
            screenshotUpload.classList.toggle('hidden', !showScreenshotUpload);
        }
        if (conversationArea) {
            conversationArea.classList.toggle('hidden', !showConversationInputs);
        }
        if (herInfoDiv) {
            herInfoDiv.classList.toggle('hidden', !showHerInfo);
        }
    }

    function getSituationLabel(value) {
        const situation = document.getElementById('situation');
        if (!situation || !value) {
            return DEFAULT_CUSTOM_SCENARIO_LABEL;
        }

        const option = Array.from(situation.options).find(function (item) {
            return item.value === value;
        });
        return option ? option.textContent.trim() : DEFAULT_CUSTOM_SCENARIO_LABEL;
    }

    function closeCustomScenarioMenu() {
        const menu = document.querySelector('[data-situation-custom-menu]');
        const trigger = document.querySelector('[data-situation-custom-trigger]');
        if (menu) {
            menu.classList.add('hidden');
        }
        if (trigger) {
            trigger.setAttribute('aria-expanded', 'false');
        }
    }

    function syncSituationControls() {
        const situation = document.getElementById('situation');
        if (!situation) {
            return;
        }

        const selected = situation.value;
        const tags = document.querySelectorAll('[data-situation-tag]');
        let selectedFromPrimaryTags = false;

        tags.forEach(function (tag) {
            const isActive = tag.getAttribute('data-situation-tag') === selected;
            tag.classList.toggle('is-active', isActive);
            if (isActive) {
                selectedFromPrimaryTags = true;
            }
        });

        const customWrap = document.querySelector('[data-situation-custom-wrap]');
        const customLabel = document.querySelector('[data-situation-custom-label]');
        if (customWrap) {
            const isCustomSelected = !!selected && !selectedFromPrimaryTags;
            customWrap.classList.toggle('is-active', isCustomSelected);
            if (customLabel) {
                customLabel.textContent = isCustomSelected ? getSituationLabel(selected) : DEFAULT_CUSTOM_SCENARIO_LABEL;
            }
        }

        const moreSelect = document.querySelector('[data-situation-more]');
        if (moreSelect) {
            if (!selected || selectedFromPrimaryTags) {
                moreSelect.value = '';
                return;
            }

            const optionExists = Array.from(moreSelect.options).some(function (option) {
                return option.value === selected;
            });
            moreSelect.value = optionExists ? selected : '';
        }
    }

    function setSituationSelection(nextValue) {
        const situation = document.getElementById('situation');
        if (!situation || !nextValue) {
            return;
        }

        const optionExists = Array.from(situation.options).some(function (option) {
            return option.value === nextValue;
        });
        if (!optionExists) {
            return;
        }

        const changed = situation.value !== nextValue;
        situation.value = nextValue;

        if (changed) {
            situation.dispatchEvent(new Event('change', { bubbles: true }));
            return;
        }

        syncSituationControls();
        closeCustomScenarioMenu();
    }

    function setupSituationControls() {
        const situation = document.getElementById('situation');
        if (!situation) {
            return;
        }

        document.querySelectorAll('[data-situation-tag]').forEach(function (tag) {
            tag.addEventListener('click', function () {
                const nextValue = tag.getAttribute('data-situation-tag');
                setSituationSelection(nextValue);
                closeCustomScenarioMenu();
            });
        });

        const moreSelect = document.querySelector('[data-situation-more]');
        if (moreSelect) {
            moreSelect.addEventListener('change', function () {
                const nextValue = moreSelect.value;
                if (!nextValue) {
                    syncSituationControls();
                    return;
                }
                setSituationSelection(nextValue);
            });
        }

        const customTrigger = document.querySelector('[data-situation-custom-trigger]');
        const customMenu = document.querySelector('[data-situation-custom-menu]');
        if (customTrigger && customMenu) {
            customTrigger.addEventListener('click', function (event) {
                event.preventDefault();
                const nextHiddenState = !customMenu.classList.contains('hidden');
                customMenu.classList.toggle('hidden');
                customTrigger.setAttribute('aria-expanded', String(!nextHiddenState));
            });

            customMenu.querySelectorAll('[data-situation-custom-option]').forEach(function (option) {
                option.addEventListener('click', function () {
                    const nextValue = option.getAttribute('data-situation-custom-option');
                    if (!nextValue) {
                        return;
                    }
                    setSituationSelection(nextValue);
                    closeCustomScenarioMenu();
                });
            });

            document.addEventListener('click', function (event) {
                const insideCustomMenu = event.target.closest('[data-situation-custom-wrap]');
                if (!insideCustomMenu) {
                    closeCustomScenarioMenu();
                }
            });
        }

        situation.addEventListener('change', function () {
            toggleInputVisibility();
            syncSituationControls();
            closeCustomScenarioMenu();
        });

        toggleInputVisibility();
        syncSituationControls();
    }

    function setGenerateButtonLoading(form, isLoading) {
        const button = form?.querySelector('[data-generate-btn]');
        if (!button) {
            return;
        }

        if (isLoading) {
            if (!button.dataset.originalHtml) {
                button.dataset.originalHtml = button.innerHTML;
            }
            button.disabled = true;
            button.setAttribute('aria-busy', 'true');
            button.innerHTML = '<span class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin align-middle"></span><span class="ml-2">Generating...</span>';
            return;
        }

        button.disabled = false;
        button.removeAttribute('aria-busy');
        if (button.dataset.originalHtml) {
            button.innerHTML = button.dataset.originalHtml;
        }
    }

    function updateCredits(creditsLeft) {
        if (typeof creditsLeft === 'undefined' || creditsLeft === null) {
            return;
        }

        ['chatCredits', 'chatCreditsInline', 'chatCreditsCount'].forEach(function (id) {
            const node = document.getElementById(id);
            if (node) {
                node.textContent = String(creditsLeft);
            }
        });
    }

    function parseEventDetail(detail) {
        if (!detail) {
            return {};
        }

        if (detail.value && typeof detail.value === 'object') {
            return detail.value;
        }

        return detail;
    }

    function setSidebarVisibility() {
        const list = document.getElementById('convoList');
        const empty = document.getElementById('convoListEmpty');
        if (!list || !empty) {
            return;
        }

        const hasItems = list.querySelectorAll('li').length > 0;
        list.classList.toggle('hidden', !hasItems);
        empty.classList.toggle('hidden', hasItems);
    }

    function setActiveConversationItem(activeId) {
        const normalizedActiveId = activeId ? String(activeId) : '';
        document.querySelectorAll('[data-conversation-item-id]').forEach(function (item) {
            const itemId = item.getAttribute('data-conversation-item-id') || '';
            item.classList.toggle('is-active', normalizedActiveId !== '' && itemId === normalizedActiveId);
        });
    }

    function setConversationId(value) {
        const conversationInput = document.getElementById('conversation-id');
        if (conversationInput) {
            conversationInput.value = value ? String(value) : '';
        }
        setActiveConversationItem(value);
    }

    function escapeHtml(value) {
        return String(value)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/\"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function buildConversationItem(id, title) {
        const li = document.createElement('li');
        li.className = 'convo-item';
        li.dataset.conversationItemId = String(id);

        li.innerHTML = [
            '<div class="convo-item-frame flex items-center gap-2 px-2.5 py-2 rounded-xl">',
            '  <a href="#" class="convo-link flex-1 min-w-0 text-sm text-brand-text no-underline" data-id="' + String(id) + '">',
            '      <span class="truncate block">' + escapeHtml(title || 'Conversation') + '</span>',
            '  </a>',
            '  <button type="button" class="delete-convo-btn opacity-0 transition-opacity text-brand-muted hover:text-red-400 text-lg leading-none" data-id="' + String(id) + '" title="Delete">&times;</button>',
            '</div>'
        ].join('');

        return li;
    }

    function handleConversationCreated(event) {
        const payload = parseEventDetail(event.detail);
        const id = payload.id;
        if (!id) {
            return;
        }

        const list = document.getElementById('convoList');
        if (!list) {
            return;
        }

        const existing = list.querySelector('[data-conversation-item-id="' + String(id) + '"]');
        if (!existing) {
            list.prepend(buildConversationItem(id, payload.girl_title || 'Conversation'));
        }

        setConversationId(id);
        setSidebarVisibility();
    }

    function handleCreditsUpdated(event) {
        const payload = parseEventDetail(event.detail);
        updateCredits(payload.credits_left);
    }

    function setupHtmxFormLifecycle() {
        const form = document.querySelector('form[data-web-reply-form]');
        if (!form) {
            return;
        }

        form.addEventListener('htmx:beforeRequest', function () {
            setGenerateButtonLoading(form, true);
            const responsePanel = getResponsePanel();
            if (responsePanel) {
                responsePanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });

        form.addEventListener('htmx:afterRequest', function () {
            setGenerateButtonLoading(form, false);
        });

        form.addEventListener('submit', function () {
            const conversationText = document.getElementById('last-reply');
            if (conversationText && !conversationText.value) {
                updateCharCount();
            }
        });
    }

    function setupCopyButtons() {
        document.addEventListener('click', function (event) {
            const button = event.target.closest('.copy-btn');
            if (!button) {
                return;
            }

            const targetId = button.getAttribute('data-copy-target');
            const target = targetId ? document.getElementById(targetId) : null;
            if (!target) {
                return;
            }

            const text = target.innerText.trim();
            if (!text) {
                return;
            }

            navigator.clipboard.writeText(text).then(function () {
                const tooltip = button.querySelector('.copied-tooltip');
                if (!tooltip) {
                    return;
                }
                tooltip.style.display = 'inline-block';
                window.setTimeout(function () {
                    tooltip.style.display = 'none';
                }, 1000);
            }).catch(function () {
                // Clipboard may fail in older browsers; ignore silently.
            });

            const payload = {
                situation: document.getElementById('situation')?.value || '',
                her_info: document.getElementById('her_info')?.value || '',
                conversation_text: document.getElementById('last-reply')?.value || '',
                copied_message: text,
                conversation_id: document.getElementById('conversation-id')?.value || '',
            };

            fetch('/conversations/copy/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                },
                body: JSON.stringify(payload),
            }).catch(function () {
                // Non-critical analytics event.
            });
        });
    }

    function setupConversationLoadAndDelete() {
        const list = document.getElementById('convoList');
        if (!list) {
            return;
        }

        list.addEventListener('click', function (event) {
            const deleteButton = event.target.closest('.delete-convo-btn');
            if (deleteButton) {
                event.preventDefault();
                event.stopPropagation();

                const conversationId = deleteButton.getAttribute('data-id');
                if (!conversationId) {
                    return;
                }

                if (!window.confirm('Delete this conversation?')) {
                    return;
                }

                const formData = new FormData();
                formData.append('id', conversationId);

                fetch('/conversations/delete/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': getCsrfToken() },
                    body: formData,
                })
                    .then(function (response) { return response.json(); })
                    .then(function (data) {
                        if (!data.success) {
                            window.alert(data.error || 'Failed to delete conversation.');
                            return;
                        }

                        deleteButton.closest('li')?.remove();
                        if (document.getElementById('conversation-id')?.value === String(conversationId)) {
                            setConversationId('');
                            resetResponsePanel();
                        }
                        setSidebarVisibility();
                    })
                    .catch(function () {
                        window.alert('Failed to delete conversation.');
                    });

                return;
            }

            const link = event.target.closest('.convo-link');
            if (!link) {
                return;
            }

            event.preventDefault();
            const conversationId = link.getAttribute('data-id');
            if (!conversationId) {
                return;
            }

            fetch('/conversations/detail/' + String(conversationId) + '/', {
                headers: { 'X-CSRFToken': getCsrfToken() },
            })
                .then(function (response) { return response.json(); })
                .then(function (data) {
                    if (data.error) {
                        window.alert('Could not load conversation.');
                        return;
                    }

                    const text = document.getElementById('last-reply');
                    const situation = document.getElementById('situation');
                    const herInfo = document.getElementById('her_info');

                    if (text) {
                        text.value = normalizeOcrTranscript(data.content || '');
                    }
                    if (situation) {
                        situation.value = data.situation || 'stuck_after_reply';
                    }
                    if (herInfo) {
                        herInfo.value = data.her_info || '';
                    }

                    setConversationId(conversationId);
                    updateCharCount();
                    toggleInputVisibility();
                    syncSituationControls();
                    resetResponsePanel();
                })
                .catch(function () {
                    window.alert('Failed to load conversation.');
                });
        });
    }

    function setupOcrUpload() {
        const fileInput = document.getElementById('formFile');
        const status = document.getElementById('ocr-status');
        const conversationInput = document.getElementById('last-reply');

        if (!fileInput || !conversationInput) {
            return;
        }

        fileInput.addEventListener('change', function (event) {
            const file = event.target.files?.[0];
            if (!file) {
                return;
            }

            if (status) {
                status.classList.remove('hidden');
            }

            const formData = new FormData();
            formData.append('screenshot', file);

            fetch('/conversations/ocr-screenshot/', {
                method: 'POST',
                headers: { 'X-CSRFToken': getCsrfToken() },
                body: formData,
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return { ok: response.ok, data: data };
                    });
                })
                .then(function (result) {
                    const data = result.data || {};
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                        return;
                    }

                    if (!result.ok || !data.ocr_text) {
                        window.alert(data.error || 'Failed to extract text from image.');
                        return;
                    }

                    const normalizedOcrText = normalizeOcrTranscript(data.ocr_text);
                    const existing = conversationInput.value.trim();
                    conversationInput.value = existing ? (existing + '\n\n' + normalizedOcrText) : normalizedOcrText;
                    updateCharCount();
                })
                .catch(function () {
                    window.alert('Failed to OCR the screenshot.');
                })
                .finally(function () {
                    if (status) {
                        status.classList.add('hidden');
                    }
                    fileInput.value = '';
                });
        });
    }

    function setupKeyboardSubmit() {
        const textarea = document.getElementById('last-reply');
        const form = document.querySelector('form[data-web-reply-form]');
        if (!textarea || !form) {
            return;
        }

        textarea.addEventListener('keydown', function (event) {
            if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
                event.preventDefault();
                form.requestSubmit();
            }
        });
    }

    function initialize() {
        const textarea = document.getElementById('last-reply');

        if (textarea) {
            updateCharCount();
            textarea.addEventListener('input', updateCharCount);
        }

        setupSituationControls();

        setupKeyboardSubmit();
        setupHtmxFormLifecycle();
        setupCopyButtons();
        setupConversationLoadAndDelete();
        setupOcrUpload();
        setSidebarVisibility();
        setActiveConversationItem(document.getElementById('conversation-id')?.value || '');

        document.body.addEventListener('conversationCreated', handleConversationCreated);
        document.body.addEventListener('creditsUpdated', handleCreditsUpdated);
    }

    document.addEventListener('DOMContentLoaded', initialize);
})();
