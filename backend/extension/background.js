/**
 * KavachX Browser Extension - Background Service Worker
 * Communicates with the hosted KavachX Governance Engine.
 * Supports: ChatGPT, Claude, Gemini, Copilot, and other web AI platforms.
 */

// Replace this with your actual Render URL after deployment
const KAVACH_SERVER_URL = "http://localhost:8005"; 
const API_KEY = "kavachx-demo-key";

// Map browser hostnames to human-readable platform names
const PLATFORM_MAP = {
    "chatgpt.com": "ChatGPT",
    "chat.openai.com": "ChatGPT",
    "claude.ai": "Claude",
    "gemini.google.com": "Gemini",
    "aistudio.google.com": "Gemini",
    "bard.google.com": "Gemini",
    "copilot.microsoft.com": "Microsoft Copilot",
    "bing.com/chat": "Microsoft Copilot",
    "github.com": "GitHub Copilot",
    "perplexity.ai": "Perplexity",
    "deepseek.com": "DeepSeek",
    "chat.mistral.ai": "Mistral",
    "huggingface.co": "HuggingFace",
    "poe.com": "Poe",
    "grok.com": "Grok",
    "x.com/i/grok": "Grok",
    "character.ai": "Character.ai",
    "pi.ai": "Inflection Pi",
};

function getPlatformName(hostname) {
    if (!hostname) return "Universal AI";
    for (const [key, name] of Object.entries(PLATFORM_MAP)) {
        if (hostname.includes(key)) return name;
    }
    // Clean up hostname (e.g. app.otherai.com -> otherai.com)
    const parts = hostname.split('.');
    if (parts.length >= 2) return parts.slice(-2).join('.');
    return hostname || "Universal AI";
}

const KAVACH_URL = "http://localhost:8005/api/v1/governance/evaluate";
let sessionId = null;

// Initialize session ID on startup
chrome.runtime.onInstalled.addListener(() => {
    chrome.storage.local.get(['sessionId'], (result) => {
        if (!result.sessionId) {
            sessionId = self.crypto.randomUUID();
            chrome.storage.local.set({ sessionId });
        } else {
            sessionId = result.sessionId;
        }
    });
});

// Helper to get session ID
const getSessionId = async () => {
    if (sessionId) return sessionId;
    const res = await chrome.storage.local.get(['sessionId']);
    return res.sessionId;
};

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("📨 Background received message:", request.action, "from", request.domain);
    if (request.action === 'evaluate_prompt') {
        processGovernance(request.prompt, request.domain).then(result => {
            sendResponse(result);
        });
        return true; // Keep channel open for async response
    }
});

async function processGovernance(prompt, domain) {
    const platform = getPlatformName(domain);
    try {
        const response = await fetch(`${KAVACH_SERVER_URL}/api/v1/governance/simulate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': API_KEY
            },
                body: JSON.stringify({
                    model_id: "kavach-sentinel-v1",
                    session_id: await getSessionId(),
                    input_data: { 
                        prompt: prompt,
                        source: "browser_extension",
                        platform: platform
                    },
                    prediction: { text: "Pending Kavach Review" },
                    confidence: 0.95,
                    context: { 
                        domain: "external_governance", 
                        browser_source: domain,
                        platform: platform
                    }
                })
        });

        const result = await response.json();
        handleDecision(result, prompt, platform);
        return result;
        
    } catch (error) {
        console.error("❌ Kavach Governance Connection Error:", error);
        return { enforcement_decision: "PASS", error: true }; // Allow on error to not block user productivity
    }
}

function handleDecision(result, prompt, platform) {
    const decision = result.enforcement_decision;
    
    if (decision === 'BLOCK') {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: '🚨 Kavach Security Alert',
            message: `Prompt BLOCKED on ${platform}: Policy violation detected.`,
            priority: 2
        });
    } else if (decision === 'HUMAN_REVIEW') {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon128.png',
            title: '⚠️ Kavach Review Required',
            message: `Prompt on ${platform} flagged for manual governance review.`,
            priority: 1
        });
    } else if (decision === 'ALERT') {
        console.warn(`⚠️ Kavach Alert on ${platform}:`, prompt.substring(0, 80));
    } else {
        console.log(`✅ Kavach PASS on ${platform}: No policy violation.`);
    }
}
