"""Onboarding endpoints."""
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user, OnboardingStepResponse, OnboardingAnswerRequest
from app.models.db.user import UserDB

router = APIRouter()


@router.get("/onboarding/start", response_model=OnboardingStepResponse)
async def start_onboarding(user: UserDB = Depends(get_current_user)):
    """Start or resume onboarding flow"""
    from app.workflows.onboarding import get_step_data, ONBOARDING_STEPS, OnboardingSteps

    if user.last_onboarding_update:
        return get_step_data(OnboardingSteps.COMPLETE, user)

    current_step = OnboardingSteps.OCCUPATION
    if not user.occupation or user.occupation == "employee":
        current_step = OnboardingSteps.OCCUPATION
    elif not user.available_times or len(user.available_times) == 0:
        current_step = OnboardingSteps.SCHEDULE
    elif user.daily_minutes == 30:
        current_step = OnboardingSteps.DURATION
    elif not user.current_habits or len(user.current_habits) == 0:
        current_step = OnboardingSteps.HABITS
    else:
        current_step = OnboardingSteps.PARTNERS

    return get_step_data(current_step, user)


@router.get("/onboarding/step/{step_id}", response_model=OnboardingStepResponse)
async def get_specific_step(
    step_id: str,
    user: UserDB = Depends(get_current_user)
):
    """Get a specific onboarding step data"""
    from app.workflows.onboarding import get_step_data, ONBOARDING_STEPS

    if step_id not in ONBOARDING_STEPS:
        raise HTTPException(status_code=400, detail="Invalid step")
        
    return get_step_data(step_id, user)


@router.post("/onboarding/answer", response_model=OnboardingStepResponse)
async def answer_onboarding(
    payload: OnboardingAnswerRequest,
    user: UserDB = Depends(get_current_user),
):
    """Process onboarding step answer and return next step"""
    from app.workflows.onboarding import get_step_data, get_next_step, ONBOARDING_STEPS, save_onboarding_progress, OnboardingSteps

    step_info = ONBOARDING_STEPS.get(payload.step)
    if not step_info:
        raise HTTPException(status_code=400, detail="Invalid step")

    # Save progress
    if payload.answers is not None:
        val = payload.answers
    elif payload.answer is not None:
        val = payload.answer
    else:
        val = None

    if val is not None:
        await save_onboarding_progress(user.id, payload.step, val)
        # Need to re-fetch user after save to get updated value for next step
        # But actually next step usually doesn't need current user data unless it's going backwards
        # So we can just pass user as is for now

    next_step = get_next_step(payload.step)
    if not next_step:
        return get_step_data(OnboardingSteps.COMPLETE, user)
        
    return get_step_data(next_step, user)
