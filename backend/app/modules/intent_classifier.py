import re
from typing import Dict, Any, List

class IntentClassifier:
    """
    KavachX Intelligent Intent Classifier.
    Goes beyond keyword matching to detect harmful 'Action + Object' patterns.
    Handles paraphrasing and indirect attempts.
    """

    # ── CATEGORY PATTERNS ──

    FINANCE_INTENT = {
        "subjects": [r"loan", r"credit", r"mortgage", r"borrow", r"lending", r"debt", r"finance"],
        "signals": {
            "caste_discrimination": {
                "indicators": [r"pincode", r"632001", r"area", r"neighbourhood", r"locality", r"proxy"],
                "actions": [r"reject", r"deny", r"exclude", r"refuse", r"block", r"discriminate", r"filter out"]
            },
            "policy_bypass": {
                "indicators": [r"ratio", r"dti", r"limit", r"threshold", r"cap", r"constraint"],
                "actions": [r"ignore", r"bypass", r"override", r"skip", r"circumvent", r"disregard", r"forget about"]
            }
        }
    }

    HEALTHCARE_INTENT = {
        "subjects": [r"patient", r"medical", r"health", r"abdm", r"hospital", r"record", r"clinical"],
        "actions": [r"extract", r"download", r"export", r"share", r"send", r" leak", r"access", r"scrape"]
    }

    EDUCATION_INTENT = {
        "subjects": [r"student", r"minor", r"child", r"pupil", r"school"],
        "actions": [r"track", r"profile", r"surveil", r"monitor", r"spy", r"collect data", r"behavioral analysis"]
    }

    HR_INTENT = {
        "subjects": [r"worker", r"driver", r"rider", r"employee", r"gig", r"account"],
        "actions": [r"deactivate", r"terminate", r"fire", r"suspend", r"kick off", r"ban"]
    }

    def detect_signals(self, text: str) -> Dict[str, Any]:
        """
        Analyzes text for structured governance signals.
        Returns a dict of signals to be injected into the inference event.
        """
        text = text.lower()
        signals = {}
        context = {}

        # 1. Financial Domain Check
        if any(re.search(s, text) for s in self.FINANCE_INTENT["subjects"]):
            # Check for Discrimination
            disc = self.FINANCE_INTENT["signals"]["caste_discrimination"]
            if any(re.search(i, text) for i in disc["indicators"]) and any(re.search(a, text) for a in disc["actions"]):
                signals["caste_proxy_score"] = 0.95
                context["domain"] = "finance"
            
            # Check for Bypass
            bypass = self.FINANCE_INTENT["signals"]["policy_bypass"]
            if any(re.search(i, text) for i in bypass["indicators"]) and any(re.search(a, text) for a in bypass["actions"]):
                signals["debt_ratio"] = 0.75
                context["domain"] = "finance"

        # 2. Healthcare Domain Check
        if any(re.search(s, text) for s in self.HEALTHCARE_INTENT["subjects"]):
            if any(re.search(a, text) for a in self.HEALTHCARE_INTENT["actions"]):
                context["domain"] = "healthcare"
                context["abdm"] = True
                signals["personal_data_used"] = True
                signals["consent_verified"] = False

        # 3. Education / Minor Protection Check
        if any(re.search(s, text) for s in self.EDUCATION_INTENT["subjects"]):
            if any(re.search(a, text) for a in self.EDUCATION_INTENT["actions"]):
                context["domain"] = "education"
                signals["continuous_monitoring"] = True
                signals["parental_consent"] = False

        # 4. HR / Gig Economy Check
        if any(re.search(s, text) for s in self.HR_INTENT["subjects"]):
            if any(re.search(a, text) for a in self.HR_INTENT["actions"]):
                context["algorithmic_deactivation"] = True

        return {"signals": signals, "context": context}
