import time
import uuid
from typing import Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import traceback

from app.models.schemas import InferenceRequest, GovernanceResult, EnforcementDecision, ExplanationOutput
from app.models.orm_models import InferenceEvent, AIModel, AuditLog
from app.modules.policy_engine import PolicyEngine
from app.modules.fairness_monitor import FairnessMonitor
from app.modules.explainability import ExplainabilityEngine
from app.modules.risk_scorer import RiskScorer
from app.modules.safety_scanner import SafetyScanner
from app.services.debug_logger import debug_logger


class GovernanceService:
    def __init__(self):
        self.policy_engine = PolicyEngine()
        self.fairness_monitor = FairnessMonitor()
        self.explainability_engine = ExplainabilityEngine()
        self.risk_scorer = RiskScorer()
        self.safety_scanner = SafetyScanner()

    async def evaluate_inference(
        self, 
        request: InferenceRequest, 
        db: AsyncSession, 
        model: AIModel,
        is_simulation: bool = False
    ) -> GovernanceResult:
        import traceback
        try:
            return await self._evaluate_internal(request, db, model, is_simulation)
        except Exception as e:
            debug_logger.log("evaluate_inference", "ERROR", error=str(e), details={"traceback": traceback.format_exc()})
            print(f"🛑 CRITICAL GOVERNANCE FAILURE: {str(e)}")
            print(traceback.format_exc())
            raise e

    async def _evaluate_internal(
        self, 
        request: InferenceRequest, 
        db: AsyncSession, 
        model: AIModel,
        is_simulation: bool = False
    ) -> GovernanceResult:
        debug_logger.log("inference_evaluation", "START", details={"model_id": model.id, "simulation": is_simulation})
        start_time = time.time()
        
        # Ensure context and input_data are dicts
        if request.context is None: request.context = {}
        if request.input_data is None: request.input_data = {}
        if request.prediction is None: request.prediction = {}
        
        # Fairness evaluation
        raw_flags = self.fairness_monitor.evaluate(request.input_data, request.prediction, request.confidence)
        from app.models.schemas import FairnessFlag as FF
        fairness_flags = []
        for f in raw_flags:
            try:
                from app.core.config import settings
                fairness_flags.append(FF(
                    metric=f.get("metric", "unknown"),
                    group_a=f.get("group_a", "group_a"),
                    group_b=f.get("group_b", "group_b"),
                    disparity=float(f.get("disparity", 0.0)),
                    threshold=float(f.get("threshold", settings.FAIRNESS_DISPARITY_THRESHOLD)),
                    passed=bool(f.get("passed", False)),
                ))
            except Exception:
                pass

        inference_data = {
            "input_data": request.input_data, 
            "confidence": request.confidence, 
            "context": request.context or {}
        }
        
        # ===================================================================
        # INTENT-BASED MONITORING LAYER
        # Only trigger policy signals when there is clear NEGATIVE INTENT.
        # Normal analytical queries → PASS (no signals injected).
        # ===================================================================
        input_text = str(request.input_data.get("prompt", request.input_data.get("text", ""))).lower()
        output_text = str(request.prediction.get("content", request.prediction.get("text", ""))).lower()
        
        # Safe platform detection
        platform = "unknown"
        if request.input_data and "platform" in request.input_data:
            platform = str(request.input_data["platform"])
        elif request.context and "platform" in request.context:
            platform = str(request.context["platform"])
        
        print(f"DEBUG: Platform detected as {platform}")

        # ── CATEGORY 1: BLOCK triggers (clear policy violations) ──
        
        # 1a. Financial Bias — pincode/caste proxy discrimination
        if ("loan" in input_text or "credit" in input_text) and ("632001" in input_text or "pincode" in input_text):
            # Only block if there's a discriminatory action context
            if any(w in input_text for w in ["reject", "deny", "exclude", "block", "refuse"]):
                request.input_data["caste_proxy_score"] = 0.85
                request.context["domain"] = "finance"

        # 1b. Financial Policy Bypass — explicit attempts to override DTI limits
        if ("loan" in input_text or "credit" in input_text) and any(w in input_text for w in ["ignore", "bypass", "override", "skip", "circumvent"]):
            if any(w in input_text for w in ["debt", "income", "ratio", "dti", "limit", "cap"]):
                request.input_data["debt_ratio"] = 0.55
                request.context["domain"] = "finance"

        # 1c. Healthcare Privacy Breach — accessing patient data without consent
        if any(w in input_text for w in ["patient", "abdm", "medical record", "health record"]):
            if any(w in input_text for w in ["extract", "download", "export", "share", "leak", "send"]):
                request.context["domain"] = "healthcare"
                request.context["abdm"] = True
                request.input_data["personal_data_used"] = True
                request.input_data["consent_verified"] = False

        # 1d. Student Surveillance — profiling minors without consent
        if any(w in input_text for w in ["student", "minor", "child"]):
            if any(w in input_text for w in ["track", "profile", "surveil", "monitor behavior", "spy"]):
                request.context["domain"] = "education"
                request.input_data["continuous_monitoring"] = True
                request.input_data["parental_consent"] = False

        # ── CATEGORY 2: HUMAN_REVIEW triggers (ambiguous risk, needs judgment) ──
        
        # 2a. DTI ratio checks (legitimate compliance query)
        if ("loan" in input_text or "credit" in input_text) and ("debt" in input_text or "income" in input_text or "ratio" in input_text):
            if "debt_ratio" not in request.input_data:  # Don't override if BLOCK already set
                request.input_data["debt_ratio"] = 0.45
                request.context["domain"] = "finance"

        # 2b. Worker deactivation / gig economy decisions
        if any(w in input_text for w in ["deactivate", "terminate", "fire", "suspend"]):
            if any(w in input_text for w in ["worker", "driver", "rider", "employee", "account"]):
                request.context["algorithmic_deactivation"] = True

        # 2c. Insurance claim decisions needing explainability
        if ("insurance" in input_text or "claim" in input_text) and any(w in input_text for w in ["reject", "deny", "approve", "process", "decide"]):
            request.context["domain"] = "insurance"
            request.input_data["explainability_score"] = 0.25

        # 2d. Low confidence prompt (user expresses uncertainty)
        if any(w in input_text for w in ["not sure", "unsure", "uncertain", "confused about"]):
            request.confidence = 0.45

        # ── CATEGORY 3: ALERT triggers (monitoring, no action needed) ──
        # Analytical technical queries now PASS by default (no signals injected)
        # to align with user requirement: "Likely allow unless a real policy risk exists"
        
        # 3a. Model drift alert — Only trigger if it's a NEGATIVE INTENT or CRITICAL levels
        # (Previously this triggered ALERT, now we just log it in context without score)
        if "model" in input_text and any(w in input_text for w in ["drift", "degrade", "degradation", "psi"]):
            request.context["performance_check"] = True

        # 3b. Economic equity analysis — explicit disparity measurement
        # (Previously this triggered ALERT, now we just log it in context)
        if any(w in input_text for w in ["disparity", "bias report", "equity gap", "inclusion audit"]):
            if any(w in input_text for w in ["analyze", "report", "measure", "assess", "check"]):
                request.context["equity_analysis"] = True

        # ── NO triggers for normal/benign prompts ──
        # "Analyze the economic disparity gap" → triggers 3b (ALERT) only  
        # "Run a performance check" → NO trigger (normal query = PASS)
        # "Help me write code" → NO trigger (normal query = PASS)
        # "What is machine learning?" → NO trigger (normal query = PASS)

        # Safety scan — always run for toxicity/injection detection
        if not request.input_data.get("toxicity_score") and not request.input_data.get("prompt_injection_score"):
            safety_results = self.safety_scanner.analyze_exchange(input_text, output_text)
            request.input_data.update(safety_results)
            inference_data["input_data"] = request.input_data

        flag_dicts = [f.model_dump() for f in fairness_flags]
        
        # Policy Evaluation (Pass 1 — without risk score)
        policy_violations, _ = self.policy_engine.evaluate(inference_data, flag_dicts, 0.0)
        
        # Risk Scoring (derived from violations + flags)
        risk_score = self.risk_scorer.compute(request.confidence, flag_dicts, policy_violations, request.context or {})
        risk_level = self.risk_scorer.get_risk_level(risk_score)
        
        # Final Enforcement (Pass 2 — check if risk score triggers additional policies)
        violations_with_risk, final_decision = self.policy_engine.evaluate(inference_data, flag_dicts, risk_score)
        policy_violations = violations_with_risk

        # ── Build human-readable reason ──
        if policy_violations:
            primary_reason = policy_violations[0].get("message", "Policy violation detected")
            policy_name = policy_violations[0].get("policy_name", "Unknown Policy")
        elif risk_score > 0.60:
            primary_reason = f"Elevated Risk ({int(risk_score*100)}%) — monitoring advised"
            policy_name = "Systemic Risk Threshold"
        else:
            primary_reason = "No policy violation detected."
            policy_name = "None"

        # Explainability
        domain = (request.context or {}).get("domain", "default")
        explanation = self.explainability_engine.explain(request.input_data, request.prediction, request.confidence, domain)
        explanation["reason"] = primary_reason
        explanation["policy_triggered"] = policy_name

        inference_id = str(uuid.uuid4())
        processing_ms = round((time.time() - start_time) * 1000, 2)

        # Context metadata
        context_metadata = {**(request.context or {}), "processing_ms": processing_ms, "platform": platform}
        if is_simulation:
            context_metadata["source"] = "simulation"

        # Prepare prompt text for logging/audit
        prompt_text = str(request.input_data.get("prompt", request.input_data.get("text", "")))[:200]
        
        print(f"DEBUG: Creating InferenceEvent {inference_id} for prompt: {prompt_text[:50]}...")
        event = InferenceEvent(
            id=inference_id,
            model_id=model.id,
            input_data=request.input_data,
            prediction=request.prediction,
            confidence=request.confidence,
            risk_score=risk_score,
            enforcement_decision=final_decision.value,
            fairness_flags=flag_dicts,
            policy_violations=policy_violations,
            explanation=explanation,
            context_metadata=context_metadata,
            session_id=request.session_id,
        )
        db.add(event)
        print(f"DEBUG: InferenceEvent added to session.")

        # ── Audit Logs ──
        audit_actor = request.model_id if not is_simulation else f"simulation/{domain}"
        
        audit_details = {
            "risk_score": risk_score, 
            "reason": primary_reason,
            "prompt": prompt_text,
            "policy_triggered": policy_name,
            "decision": final_decision.value,
            "platform": platform,
            "session_id": request.session_id,
            "violations": [v.get("policy_name") for v in policy_violations],
            "fairness_flags": len(fairness_flags), 
            "scenario": domain if is_simulation else None
        }

        db.add(AuditLog(
            event_type="inference_evaluated",
            entity_id=inference_id,
            entity_type="inference",
            actor=audit_actor,
            action=f"decision={final_decision.value}",
            details=audit_details,
            risk_level=risk_level.value,
        ))

        if final_decision == EnforcementDecision.BLOCK:
            db.add(AuditLog(
                event_type="model_blocked",
                entity_id=model.id,
                entity_type="ai_model",
                actor="governance_engine",
                action="blocked inference due to policy violation",
                details={"inference_id": inference_id, "reason": primary_reason, "prompt": prompt_text, "violations": policy_violations[:3]},
                risk_level="critical"
            ))
        elif policy_violations:
            db.add(AuditLog(
                event_type="policy_violated", 
                entity_id=inference_id, 
                entity_type="inference",
                actor=audit_actor, 
                action="policy violation detected",
                details={"reason": primary_reason, "prompt": prompt_text, "violations": policy_violations[:3]}, 
                risk_level=risk_level.value
            ))
        else:
            db.add(AuditLog(
                event_type="inference_passed", 
                entity_id=inference_id, 
                entity_type="inference",
                actor=audit_actor, 
                action="inference passed all checks",
                details={"prompt": prompt_text, "platform": platform}, 
                risk_level="low"
            ))

        fairness_failed = [f for f in fairness_flags if not f.passed]
        if fairness_failed:
            db.add(AuditLog(
                event_type="fairness_issue_detected", 
                entity_id=inference_id, 
                entity_type="inference",
                actor=audit_actor, 
                action="fairness threshold exceeded",
                details={"flags": [f.model_dump() for f in fairness_failed]}, 
                risk_level="high"
            ))

        try:
            await db.commit()
            debug_logger.log("database_commit", "SUCCESS", details={"inference_id": inference_id})
            print(f"DEBUG: Database commit SUCCESS for {inference_id}")
        except Exception as e:
            await db.rollback()
            debug_logger.log("database_commit", "FAILED", error=str(e))
            print(f"DEBUG: Database commit FAILED: {str(e)}")
            raise e
        
        # Invalidate dashboard cache
        from app.db.cache import dashboard_cache
        dashboard_cache.invalidate("dashboard_stats")

        # Broadcast real-time update over WebSocket
        try:
            from app.services.websocket_manager import manager
            asyncio.create_task(manager.broadcast({
                "type": "new_inference",
                "inference_id": inference_id,
                "risk_score": risk_score,
                "enforcement_decision": final_decision.value,
            }))
        except Exception as ws_err:
            print(f"DEBUG: WebSocket broadcast failed (ignoring): {ws_err}")

        return GovernanceResult(
            inference_id=inference_id,
            model_id=model.id,
            risk_score=risk_score,
            risk_level=risk_level,
            enforcement_decision=final_decision,
            fairness_flags=fairness_flags,
            policy_violations=policy_violations,
            risk_analysis={
                "composite_risk": risk_score,
                "risk_level": risk_level.value,
                "violation_count": len(policy_violations),
                "fairness_flags": len(fairness_flags),
                "platform": platform
            },
            explanation=ExplanationOutput(**explanation),
            timestamp=datetime.now(timezone.utc),
            processing_time_ms=processing_ms,
        )

# Global service instance
governance_service = GovernanceService()
