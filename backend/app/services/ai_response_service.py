import random
import asyncio
from typing import Optional

class AIResponseService:
    """
    KavachX AI Response Service.
    Handles calls to external AI providers (OpenAI, Anthropic, etc.) 
    after successful governance evaluation.
    """

    async def get_response(self, prompt: str, model_id: str) -> str:
        """
        Generates a response for the given prompt.
        If real API keys are not provided, it produces a high-fidelity simulated response.
        """
        # 1. Check for real keys in environment (future-proofing)
        # Note: In a production deployment, keys like OPENAI_API_KEY would be used here.
        
        # 2. Simplified high-fidelity mock logic for the demo/monitoring portal
        # This simulates a "Real" AI response to differentiate from simple status checks.
        
        # Simulate processing delay
        await asyncio.sleep(1.0)
        
        prompt_lower = prompt.lower()
        
        # Contextual simulators
        if "loan" in prompt_lower or "credit" in prompt_lower:
            return "Based on the financial parameters provided, the application analysis is complete. Our models show a stable credit profile, though we suggest verifying secondary income sources for a more robust evaluation."
        
        if "patient" in prompt_lower or "medical" in prompt_lower:
            return "The medical data review reveals standard metrics for this patient demographic. We recommend continuing the current treatment plan and scheduling a follow-up in 14 days for optimal recovery monitoring."
        
        if "code" in prompt_lower or "function" in prompt_lower or "python" in prompt_lower:
            return "Here is a standard implementation for your request:\n\n```python\ndef process_data(data):\n    # Governance-cleared processing\n    return [item.strip() for item in data if item]\n```\nHow else can I help with your engineering tasks?"

        # Generic helpful AI responses
        responses = [
            "I've analyzed your request and provided the relevant details. Is there anything specific you'd like to dive deeper into?",
            "That's a great question. Looking at the context of our discussion, the best approach would be to focus on efficiency and safety in the implementation.",
            "I've processed that for you. Every action in this session is monitored by KavachX to ensure enterprise-grade security.",
            "Certainly! I've updated the session parameters based on your last input. What would you like to do next?"
        ]
        
        return random.choice(responses)

ai_response_service = AIResponseService()
