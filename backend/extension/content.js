/**
 * KavachX Browser Extension - Universal AI Platform Content Interceptor
 * Monitors prompts across ChatGPT, Claude, Gemini, Copilot, Perplexity,
 * DeepSeek, Mistral, HuggingFace, Poe, and ANY other web-based AI tools.
 */

(function() {
    console.log("🛡️ Kavach AI Shield: Active Enforcement Active on", window.location.hostname);

    let isValidating = false;
    let bypassValidation = false;

    const findPrompt = () => {
        const selectors = [
            '#prompt-textarea',                              // ChatGPT
            'div[contenteditable="true"][aria-label*="Prompt"]', // Gemini / Claude
            'div[contenteditable="true"][role="textbox"]',    // Rich editors
            'textarea[placeholder*="Message"]',              // ChatGPT alt
            '.ProseMirror',                                  // Claude
            'textarea[placeholder*="Talk to"]',              // Gemini Alt
            '#editable-content-area',                         // Gemini Alt 2
            '.ql-editor',                                    // Various AI editors
            'textarea[placeholder*="Ask"]', 
            'textarea[placeholder*="Type"]', 
            'textarea[placeholder*="Send"]',
            'textarea', 'input[type="text"]'
        ];
        
        for (const s of selectors) {
            const elements = document.querySelectorAll(s);
            for (const el of elements) {
                if (el.offsetWidth === 0 || el.offsetHeight === 0) continue;
                // For contenteditable, we need innerText. For textarea, we need value.
                const val = (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' ? el.value : el.innerText).trim();
                // Filter out very short strings or UI buttons
                if (val.length > 2 && !/^(Send|Message|Ask)$/i.test(val)) {
                    return { text: val, element: el };
                }
            }
        }
        return null;
    };

    const showBlockingModal = (reason, policy) => {
        const modal = document.createElement('div');
        modal.id = 'kavach-block-modal';
        modal.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); z-index: 999999; display: flex; align-items: center; justify-content: center; font-family: sans-serif;">
                <div style="background: white; padding: 32px; border-radius: 12px; max-width: 450px; width: 90%; text-align: center; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.1);">
                    <div style="color: #ef4444; margin-bottom: 16px;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    </div>
                    <h2 style="margin: 0 0 8px 0; color: #111827; font-size: 20px;">Governance Block</h2>
                    <p style="color: #4b5563; font-size: 14px; line-height: 1.5; margin-bottom: 24px;">
                        This prompt violates enterprise safety policies.<br>
                        <strong>Policy:</strong> ${policy || 'General Safety'}<br>
                        <strong>Reason:</strong> ${reason}
                    </p>
                    <button id="kavach-close-modal" style="background: #111827; color: white; border: none; padding: 10px 24px; border-radius: 6px; cursor: pointer; font-weight: 600;">Dismiss</button>
                    <div style="margin-top: 16px; font-size: 11px; color: #9ca3af;">Secured by KavachX Governance Engine</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        document.getElementById('kavach-close-modal').onclick = () => modal.remove();
    };

    const handleIntercept = async (e, type, targetElement) => {
        if (bypassValidation || isValidating) return;

        const promptData = findPrompt();
        if (!promptData || promptData.text.length < 3) {
            console.log("🛡️ KavachX: No valid prompt found to validate.");
            return;
        }

        console.log(`🛡️ KavachX: Intercepting ${type} for validation: "${promptData.text.substring(0, 50)}..."`);
        isValidating = true;

        // stop the original event
        e.preventDefault();
        e.stopPropagation();

        try {
            chrome.runtime.sendMessage({ 
                action: 'evaluate_prompt', 
                prompt: promptData.text,
                domain: window.location.hostname
            }, (response) => {
                isValidating = false;
                if (!response) {
                    console.error("🛡️ KavachX: No response from background script.");
                    bypassValidation = true;
                    // Re-trigger original action
                    if (type === 'click') targetElement.click();
                    return;
                }

                console.log("🛡️ KavachX: Governance decision:", response.enforcement_decision);

                if (response.enforcement_decision === 'BLOCK') {
                    const reason = response.explanation?.reason || response.reason || "Corporate safety policy violation";
                    const policy = response.explanation?.policy_triggered || "Safety & Compliance";
                    showBlockingModal(reason, policy);
                } else {
                    // Re-trigger the submission
                    console.log("🛡️ KavachX: Allowing prompt submission.");
                    bypassValidation = true;
                    if (type === 'click') {
                        targetElement.click();
                    } else if (type === 'keydown') {
                        // For modern React/Next.js apps like Gemini/ChatGPT
                        const promptEl = promptData.element;
                        const enterDown = new KeyboardEvent('keydown', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true });
                        const enterUp = new KeyboardEvent('keyup', { key: 'Enter', code: 'Enter', keyCode: 13, which: 13, bubbles: true });
                        promptEl.dispatchEvent(enterDown);
                        promptEl.dispatchEvent(enterUp);
                    }
                    setTimeout(() => { bypassValidation = false; }, 200);
                }
            });
        } catch (err) {
            console.error("🛡️ KavachX: Error in message flow:", err);
            isValidating = false;
            bypassValidation = true; 
        }
    };

    // 1. Keyboard Interceptor
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !bypassValidation) {
            handleIntercept(e, 'keydown', e.target);
        }
    }, true);

    // 2. Click Interceptor
    document.addEventListener('mousedown', (e) => {
        if (bypassValidation) return;
        const btn = e.target.closest('button') || e.target.closest('[role="button"]');
        if (btn) {
            // Check if it looks like a send button
            const isSend = btn.querySelector('svg') || /send|ask|submit/i.test(btn.innerText + btn.ariaLabel);
            if (isSend) {
                handleIntercept(e, 'click', btn);
            }
        }
    }, true);

})();
