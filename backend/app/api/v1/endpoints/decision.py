from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from app.services.decision_engine import DecisionEngine


router = APIRouter()

decision_engine = DecisionEngine()


@router.post("/evaluate")
async def evaluate_decision(
    payload: Dict[str, Any]
):

    try:

        result = decision_engine.synthesize_decision(
            payload
        )

        return result

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Decision evaluation failed: {str(e)}"
        )