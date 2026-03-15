"""Governance Policies API."""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.models.orm_models import GovernancePolicy
from app.core.auth import require_permission, get_current_user
from app.modules.policy_engine import BUILT_IN_POLICIES
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

router = APIRouter()


class RuleCreate(BaseModel):
    field: str
    operator: str
    value: float
    action: str


class PolicyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    policy_type: str = "fairness"
    rules: Optional[List[RuleCreate]] = []
    severity: str = "medium"
    jurisdiction: str = "IN"


class ToggleBody(BaseModel):
    enabled: bool





@router.get("/")
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(GovernancePolicy))
    custom = result.scalars().all()
    built_in = [{"enabled": True, "created_at": "2026-01-01T00:00:00Z", **p} for p in BUILT_IN_POLICIES]
    custom_out = [{
        "id": p.id, "name": p.name, "description": p.description,
        "policy_type": p.policy_type, "rules": p.rules, "severity": p.severity,
        "jurisdiction": p.jurisdiction, "enabled": p.enabled,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    } for p in custom]
    return built_in + custom_out


@router.post("/")
async def create_policy(policy: PolicyCreate, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("policies:write"))):
    new = GovernancePolicy(
        id=str(uuid.uuid4()),
        name=policy.name,
        description=policy.description,
        policy_type=policy.policy_type,
        rules=[r.model_dump() for r in policy.rules],
        severity=policy.severity,
        jurisdiction=policy.jurisdiction,
    )
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return {"id": new.id, "name": new.name, "enabled": new.enabled}


@router.patch("/{policy_id}/toggle")
async def toggle_policy(policy_id: str, body: ToggleBody, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("policies:write"))):
    if policy_id.startswith("builtin"):
        raise HTTPException(status_code=400, detail="Cannot toggle built-in baseline policies — they are always active")
    result = await db.execute(select(GovernancePolicy).where(GovernancePolicy.id == policy_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    p.enabled = body.enabled
    await db.commit()
    return {"id": p.id, "enabled": p.enabled}


@router.delete("/{policy_id}")
async def delete_policy(policy_id: str, db: AsyncSession = Depends(get_db), current_user=Depends(require_permission("policies:delete"))):
    if policy_id.startswith("builtin"):
        raise HTTPException(status_code=400, detail="Cannot delete built-in baseline policies")
    result = await db.execute(select(GovernancePolicy).where(GovernancePolicy.id == policy_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Policy not found")
    await db.delete(p)
    await db.commit()
    return {"deleted": policy_id}
