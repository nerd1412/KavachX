"""
Governance API - Core inference evaluation and retrieval.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.database import get_db
from app.models.schemas import InferenceRequest, GovernanceResult
from app.models.orm_models import InferenceEvent, AIModel
from app.core.auth import require_permission
from app.services.governance_service import governance_service
from app.services.ai_response_service import ai_response_service

router = APIRouter()


def _fmt_ts(dt):
    """Return ISO-8601 UTC string with 'Z' suffix, or None."""
    if not dt:
        return None
    iso = dt.isoformat()
    if iso.endswith("Z"):
        return iso
    return iso.replace("+00:00", "Z") + ("" if "+" in iso or iso.endswith("Z") else "Z")


@router.post("/evaluate", response_model=GovernanceResult)
async def evaluate_inference(
    request: InferenceRequest, 
    db: AsyncSession = Depends(get_db), 
    current_user=Depends(require_permission("governance:evaluate"))
):
    result = await db.execute(select(AIModel).where(AIModel.id == request.model_id))
    model = result.scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{request.model_id}' not registered. Please register it first.")
    if model.status == "suspended":
        raise HTTPException(status_code=403, detail="Model is suspended from inference")

    # Delegate to Service Layer
    return await governance_service.evaluate_inference(request, db, model, is_simulation=False)


@router.post("/simulate", response_model=GovernanceResult)
async def simulate_inference(request: InferenceRequest, db: AsyncSession = Depends(get_db)):
    """Demo simulation endpoint — no auth required. Auto-creates model if needed.
    Persists InferenceEvent + AuditLog to DB so all platform pages see the data.
    """
    try:
        model_id = request.model_id or "kavachx-demo-model"
        
        # Check if model exists
        result = await db.execute(select(AIModel).where(AIModel.id == model_id))
        model = result.scalar_one_or_none()
        if not model:
            # Also try by name
            result2 = await db.execute(select(AIModel).where(AIModel.name == model_id))
            model = result2.scalar_one_or_none()
        if not model:
            # Create demo model on the fly
            model = AIModel(
                id=model_id,
                name="KavachX Demo Model",
                version="v1.0",
                model_type="classification",
                owner="Simulation Engine",
                description="Auto-created for simulation scenarios",
                status="active",
            )
            db.add(model)
            await db.flush()  # assign id before FK reference

        # Delegate to Service Layer
        result = await governance_service.evaluate_inference(request, db, model, is_simulation=True)

        # Realistic Integration: Generate AI response if governance allows
        # This replaces the 'Simulation' behavior with 'Production-Ready' behavior.
        if result.enforcement_decision in [EnforcementDecision.PASS, EnforcementDecision.ALERT]:
            prompt = str(request.input_data.get("prompt", ""))
            result.ai_response = await ai_response_service.get_response(prompt, model.id)
        
        return result

    except Exception as e:
        import traceback
        print(f"ERROR in simulate_inference: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Inference Error: {str(e)}")


@router.get("/recent")
async def get_recent_inferences(skip: int = Query(default=0, ge=0), limit: int = Query(default=20, le=100), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InferenceEvent).order_by(InferenceEvent.timestamp.desc()).offset(skip).limit(limit))
    inferences = result.scalars().all()
    return [
        {
            "id": i.id, "model_id": i.model_id, "risk_score": i.risk_score,
            "enforcement_decision": i.enforcement_decision, "confidence": i.confidence,
            "fairness_flags": i.fairness_flags or [], "policy_violations": i.policy_violations or [],
            "explanation": i.explanation or {},
            "input_data": i.input_data or {},
            "context_metadata": i.context_metadata or {},
            "timestamp": _fmt_ts(i.timestamp),
        }
        for i in inferences
    ]


@router.get("/inference/{inference_id}")
async def get_inference_detail(inference_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InferenceEvent).where(InferenceEvent.id == inference_id))
    inference = result.scalar_one_or_none()
    if not inference:
        raise HTTPException(status_code=404, detail="Inference not found")
    return {
        "id": inference.id, "model_id": inference.model_id,
        "input_data": inference.input_data, "prediction": inference.prediction,
        "confidence": inference.confidence, "risk_score": inference.risk_score,
        "enforcement_decision": inference.enforcement_decision,
        "fairness_flags": inference.fairness_flags, "policy_violations": inference.policy_violations,
        "explanation": inference.explanation,
        "timestamp": inference.timestamp.isoformat() if inference.timestamp else None,
    }


@router.get("/inferences")
async def list_inferences(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, le=100),
    model_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List recent inference events with offset pagination."""
    query = select(InferenceEvent).order_by(desc(InferenceEvent.timestamp)).offset(skip).limit(limit)
    if model_id:
        query = query.where(InferenceEvent.model_id == model_id)
    result = await db.execute(query)
    events = result.scalars().all()
    return [
        {
            "id": e.id, "model_id": e.model_id,
            "enforcement_decision": e.enforcement_decision,
            "risk_score": e.risk_score, "confidence": e.confidence,
            "fairness_flags": e.fairness_flags or [],
            "policy_violations": e.policy_violations or [],
            "explanation": e.explanation or {},
            "input_data": e.input_data or {},
            "context_metadata": e.context_metadata or {},
            "timestamp": _fmt_ts(e.timestamp),
        }
        for e in events
    ]


@router.get("/inferences/{inference_id}")
async def get_inference(inference_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(InferenceEvent).where(InferenceEvent.id == inference_id))
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Inference not found")
    return {
        "id": e.id, "model_id": e.model_id,
        "input_data": e.input_data, "prediction": e.prediction,
        "enforcement_decision": e.enforcement_decision,
        "risk_score": e.risk_score, "confidence": e.confidence,
        "fairness_flags": e.fairness_flags, "policy_violations": e.policy_violations,
        "explanation": e.explanation, "timestamp": _fmt_ts(e.timestamp),
    }
