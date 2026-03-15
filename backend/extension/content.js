/**
 * KavachX Browser Extension - Production-Grade Universal Interceptor
 * Implements "Intercept -> Evaluate -> Release" Governance Pattern.
 */

(function() {
    console.log("🛡️ KavachX: Production Governance Engine Active");

    let isValidating = false;
    let bypassValidation = false;
    const localCache = new Map(); // Local policy cache for latency optimization

    // ── ROBUST HEURISTIC DETECTION ──
    const findPromptElement = () => {
        // 1. Recursive Shadow DOM Search
        const searchShadow = (root) => {
            const elements = root.querySelectorAll('div[contenteditable="true"], textarea, [role="textbox"]');
            for (let el of elements) {
                if (isRealInput(el)) return el;
            }
            const hosts = root.querySelectorAll('*');
            for (let host of hosts) {
                if (host.shadowRoot) {
                    const found = searchShadow(host.shadowRoot);
                    if (found) return found;
                }
            }
            return null;
        };

        const isRealInput = (el) => {
            if (el.offsetWidth === 0 || el.offsetHeight === 0) return false;
            const text = (el.innerText || el.value || "").trim();
            // Heuristic: Must not be a nav item or a tiny button
            return el.scrollHeight > 10 || el.tagName === 'TEXTAREA';
        };

        // Try standard selectors first
        const selectors = [
            '#prompt-textarea', 'div[contenteditable="true"][aria-label*="Prompt"]',
            'div[contenteditable="true"][role="textbox"]', '.ProseMirror',
            'textarea[placeholder*="Message"]', 'textarea[placeholder*="Talk to"]',
            '#editable-content-area'
        ];
        
        for (const s of selectors) {
            const el = document.querySelector(s);
            if (el && isRealInput(el)) return el;
        }

        // Fallback to Shadow DOM pierce
        return searchShadow(document);
    };

    const getElementValue = (el) => {
        if (!el) return "";
        return (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT' ? el.value : el.innerText).trim();
    };

    const showBlockingModal = (reason, policy) => {
        if (document.getElementById('kavach-block-modal')) return;
        const modal = document.createElement('div');
        modal.id = 'kavach-block-modal';
        modal.innerHTML = `
            <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); z-index: 2147483647; display: flex; align-items: center; justify-content: center; font-family: 'Inter', sans-serif; backdrop-filter: blur(4px);">
                <div style="background: #ffffff; padding: 40px; border-radius: 16px; max-width: 480px; width: 90%; text-align: center; box-shadow: 0 25px 50px -12px rgba(0,0,0,0.25); border: 1px solid #e5e7eb;">
                    <div style="background: #fee2e2; width: 80px; height: 80px; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px;">
                        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#dc2626" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                    </div>
                    <h2 style="margin: 0 0 12px 0; color: #111827; font-size: 24px; font-weight: 800;">Governance Block</h2>
                    <p style="color: #4b5563; font-size: 15px; line-height: 1.6; margin-bottom: 28px;">
                        This prompt was intercepted by <span style="font-weight: 700; color: #111827;">KavachX</span> because it violates enterprise security policies.<br><br>
                        <span style="display: block; background: #f9fafb; padding: 12px; border-radius: 8px; border: 1px solid #f3f4f6; text-align: left;">
                            <strong>Policy:</strong> ${policy || 'Corporate Safety'}<br>
                            <strong>Reason:</strong> ${reason}
                        </span>
                    </p>
                    <button id="kavach-close-modal" style="background: #111827; color: white; border: none; padding: 14px 32px; border-radius: 8px; cursor: pointer; font-weight: 600; font-size: 15px; width: 100%; transition: all 0.2s;">Understood</button>
                    <div style="margin-top: 20px; font-size: 11px; color: #9ca3af; letter-spacing: 0.05em; text-transform: uppercase;">Protected by KavachX Universal AI Shield</div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        document.getElementById('kavach-close-modal').onclick = () => modal.remove();
    };

    // ── INTERCEPT & EVALUATE ──
    const handleIntercept = async (e, type, targetElement) => {
        if (bypassValidation || isValidating) return;

        const inputEl = findPromptElement();
        const prompt = getElementValue(inputEl);
        
        if (!prompt || prompt.length < 3) return;

        // Latency Optimization: Local Cache Check
        if (localCache.has(prompt) && localCache.get(prompt) === 'PASS') {
            console.log("🛡️ KavachX: Local Cache Hit (PASS)");
            return;
        }

        console.log(`🛡️ KavachX: Intercepting prompt for evaluation...`);
        isValidating = true;
        e.preventDefault();
        e.stopImmediatePropagation();

        try {
            chrome.runtime.sendMessage({ 
                action: 'evaluate_prompt', 
                prompt: prompt,
                domain: window.location.hostname
            }, (response) => {
                isValidating = false;
                if (!response) {
                    console.warn("🛡️ KavachX: Engine unresponsive, failing safe (ALLOW)");
                    releaseEvent(type, targetElement);
                    return;
                }

                if (response.enforcement_decision === 'BLOCK') {
                    const reason = response.explanation?.reason || "Policy violation";
                    const policy = response.explanation?.policy_triggered || "Safety Compliance";
                    showBlockingModal(reason, policy);
                } else {
                    // Cache the success for this specific session
                    localCache.set(prompt, 'PASS');
                    releaseEvent(type, targetElement);
                }
            });
        } catch (err) {
            isValidating = false;
            releaseEvent(type, targetElement);
        }
    };

    const releaseEvent = (type, target) => {
        console.log("🛡️ KavachX: Releasing prompt submission.");
        bypassValidation = true;
        if (type === 'click') {
            target.click();
        } else {
            // Re-trigger Enter key
            const event = new KeyboardEvent('keydown', {
                key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
                bubbles: true, cancelable: true
            });
            target.dispatchEvent(event);
        }
        setTimeout(() => { bypassValidation = false; }, 300);
    };

    // ── EVENT LISTENERS (CAPTURE PHASE) ──
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !bypassValidation) {
            handleIntercept(e, 'keydown', e.target);
        }
    }, true);

    document.addEventListener('mousedown', (e) => {
        if (bypassValidation) return;
        const btn = e.target.closest('button') || e.target.closest('[role="button"]');
        if (btn && (btn.querySelector('svg') || /send|ask|submit/i.test(btn.innerText + btn.ariaLabel))) {
            handleIntercept(e, 'click', btn);
        }
    }, true);

})();
