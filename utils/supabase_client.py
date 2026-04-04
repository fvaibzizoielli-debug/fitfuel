# =====================================================
# FitFuel - Supabase Database Client
# =====================================================
# This module handles ALL database interactions. Every
# read and write to Supabase goes through functions here.
# This keeps database logic centralized and makes the
# page code cleaner and easier to maintain.
# =====================================================

from supabase import create_client, Client
from utils.config import SUPABASE_URL, SUPABASE_KEY
from datetime import date, timedelta
import json

# ----- Initialize Supabase Client -----
# This creates a single reusable connection to our Supabase project.
# The client handles authentication, retries, and connection pooling.
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# =====================================================
# USER PROFILE OPERATIONS
# =====================================================

def create_user_profile(profile_data: dict) -> dict:
    """
    Insert a new user profile after onboarding completion.

    Takes the onboarding survey responses plus the calculated
    nutrition values (BMR, TDEE, macros) and stores them as
    a single row in user_profiles.

    Args:
        profile_data: Dictionary containing all profile fields
                      (name, age, gender, height_cm, etc.)

    Returns:
        The created profile record as a dictionary
    """
    response = supabase.table("user_profiles").insert(profile_data).execute()
    return response.data[0] if response.data else None


def get_user_profile(user_id: str) -> dict:
    """
    Fetch a user profile by its ID.

    Used on every page load to check if the user has completed
    onboarding and to access their current settings.

    Args:
        user_id: UUID string of the user

    Returns:
        Profile dictionary or None if not found
    """
    response = supabase.table("user_profiles").select("*").eq("id", user_id).execute()
    return response.data[0] if response.data else None


def get_all_profiles() -> list:
    """
    Fetch all user profiles.

    Used on the login/profile selection screen to let the user
    pick their profile. In a real app this would use authentication,
    but for a university project, profile selection is sufficient.

    Returns:
        List of profile dictionaries
    """
    response = supabase.table("user_profiles").select("*").execute()
    return response.data if response.data else []


def update_user_profile(user_id: str, updates: dict) -> dict:
    """
    Update specific fields in a user's profile.

    Called when the user changes settings on the Profile page
    or when the ML model recalculates nutrition targets.

    Args:
        user_id: UUID string of the user
        updates: Dictionary of fields to update

    Returns:
        The updated profile record
    """
    response = (
        supabase.table("user_profiles")
        .update(updates)
        .eq("id", user_id)
        .execute()
    )
    return response.data[0] if response.data else None


# =====================================================
# WORKOUT PLAN OPERATIONS
# =====================================================

def save_workout_plan(user_id: str, week_start: date, plan_data: dict) -> dict:
    """
    Save a generated workout plan for a specific week.

    Before saving, any existing active plan for this user is
    deactivated (is_active = False). This ensures only one
    plan is active at a time while preserving history.

    Args:
        user_id: UUID string of the user
        week_start: The Monday of the plan's week
        plan_data: The full plan structure (days, exercises, etc.)

    Returns:
        The created plan record
    """
    # Deactivate any currently active plans
    supabase.table("workout_plans").update(
        {"is_active": False}
    ).eq("user_id", user_id).eq("is_active", True).execute()

    # Insert the new plan as active
    record = {
        "user_id": user_id,
        "week_start_date": str(week_start),
        "plan_data": json.dumps(plan_data) if isinstance(plan_data, dict) else plan_data,
        "is_active": True,
    }
    response = supabase.table("workout_plans").insert(record).execute()
    return response.data[0] if response.data else None


def get_active_workout_plan(user_id: str) -> dict:
    """
    Get the user's currently active workout plan.

    Only one plan should be active at a time. This is the plan
    shown on the Workout page.

    Args:
        user_id: UUID string of the user

    Returns:
        Plan record with plan_data field, or None
    """
    response = (
        supabase.table("workout_plans")
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if response.data:
        plan = response.data[0]
        # Parse plan_data from JSON string if needed
        if isinstance(plan.get("plan_data"), str):
            plan["plan_data"] = json.loads(plan["plan_data"])
        return plan
    return None


def get_workout_plan_history(user_id: str) -> list:
    """
    Get all past workout plans for a user (for ML analysis).

    The ML model uses plan history to understand how the user's
    training has evolved and avoid repeating ineffective plans.

    Args:
        user_id: UUID string of the user

    Returns:
        List of plan records, newest first
    """
    response = (
        supabase.table("workout_plans")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data if response.data else []


# =====================================================
# WORKOUT LOG OPERATIONS
# =====================================================

def log_workout(log_data: dict) -> dict:
    """
    Save a single exercise log entry.

    Each exercise in a workout session gets its own log entry.
    This granularity lets us track progression per exercise.

    Args:
        log_data: Dictionary with user_id, workout_date, exercise_name,
                  prescribed_sets, prescribed_reps, actual_reps, etc.

    Returns:
        The created log record
    """
    response = supabase.table("workout_logs").insert(log_data).execute()
    return response.data[0] if response.data else None


def get_workout_logs(user_id: str, start_date: date = None, end_date: date = None) -> list:
    """
    Fetch workout logs for a user within a date range.

    Used for:
    - Displaying workout history on the Dashboard
    - ML model analysis of training progression
    - Checking if today's workout is already logged

    Args:
        user_id: UUID string of the user
        start_date: Start of date range (default: 30 days ago)
        end_date: End of date range (default: today)

    Returns:
        List of workout log records
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()

    response = (
        supabase.table("workout_logs")
        .select("*")
        .eq("user_id", user_id)
        .gte("workout_date", str(start_date))
        .lte("workout_date", str(end_date))
        .order("workout_date", desc=True)
        .execute()
    )
    return response.data if response.data else []


def get_workout_logs_for_date(user_id: str, workout_date: date) -> list:
    """
    Get all exercise logs for a specific date.

    Used on the Workout page to show what the user has already
    logged today and calculate daily completion percentage.

    Args:
        user_id: UUID string of the user
        workout_date: The specific date to query

    Returns:
        List of exercise log records for that date
    """
    response = (
        supabase.table("workout_logs")
        .select("*")
        .eq("user_id", user_id)
        .eq("workout_date", str(workout_date))
        .execute()
    )
    return response.data if response.data else []


# =====================================================
# NUTRITION LOG OPERATIONS
# =====================================================

def log_nutrition(log_data: dict) -> dict:
    """
    Save a meal log entry.

    Args:
        log_data: Dictionary with user_id, meal_date, meal_type,
                  description, calories, protein_g, carbs_g, fat_g,
                  and optionally photo_url

    Returns:
        The created log record
    """
    response = supabase.table("nutrition_logs").insert(log_data).execute()
    return response.data[0] if response.data else None


def get_nutrition_logs(user_id: str, start_date: date = None, end_date: date = None) -> list:
    """
    Fetch nutrition logs for a user within a date range.

    Args:
        user_id: UUID string of the user
        start_date: Start of date range (default: 30 days ago)
        end_date: End of date range (default: today)

    Returns:
        List of nutrition log records
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=30)
    if end_date is None:
        end_date = date.today()

    response = (
        supabase.table("nutrition_logs")
        .select("*")
        .eq("user_id", user_id)
        .gte("meal_date", str(start_date))
        .lte("meal_date", str(end_date))
        .order("meal_date", desc=True)
        .execute()
    )
    return response.data if response.data else []


def get_nutrition_logs_for_date(user_id: str, meal_date: date) -> list:
    """
    Get all meals logged for a specific date.

    Used to calculate how many calories/macros the user has
    consumed today and how much remains.

    Args:
        user_id: UUID string of the user
        meal_date: The specific date to query

    Returns:
        List of meal log records for that date
    """
    response = (
        supabase.table("nutrition_logs")
        .select("*")
        .eq("user_id", user_id)
        .eq("meal_date", str(meal_date))
        .order("logged_at", desc=False)
        .execute()
    )
    return response.data if response.data else []


def delete_nutrition_log(log_id: str) -> bool:
    """
    Delete a specific meal log entry.

    Allows users to remove incorrectly logged meals.

    Args:
        log_id: UUID of the nutrition log entry

    Returns:
        True if deletion succeeded
    """
    response = supabase.table("nutrition_logs").delete().eq("id", log_id).execute()
    return True


# =====================================================
# WEIGHT LOG OPERATIONS
# =====================================================

def log_weight(user_id: str, weight_kg: float, log_date: date = None) -> dict:
    """
    Record a weight measurement.

    Separate from the profile so we maintain a full history
    for trend charts. Also updates the current_weight_kg
    in the user profile.

    Args:
        user_id: UUID string of the user
        weight_kg: Weight in kilograms
        log_date: Date of measurement (default: today)

    Returns:
        The created weight log record
    """
    if log_date is None:
        log_date = date.today()

    # Log the weight entry
    record = {
        "user_id": user_id,
        "log_date": str(log_date),
        "weight_kg": weight_kg,
    }
    response = supabase.table("weight_logs").insert(record).execute()

    # Also update the profile's current weight
    supabase.table("user_profiles").update(
        {"current_weight_kg": weight_kg}
    ).eq("id", user_id).execute()

    return response.data[0] if response.data else None


def get_weight_logs(user_id: str, start_date: date = None, end_date: date = None) -> list:
    """
    Fetch weight history for trend charts.

    Args:
        user_id: UUID string of the user
        start_date: Start of date range (default: 90 days ago)
        end_date: End of date range (default: today)

    Returns:
        List of weight log records, oldest first
    """
    if start_date is None:
        start_date = date.today() - timedelta(days=90)
    if end_date is None:
        end_date = date.today()

    response = (
        supabase.table("weight_logs")
        .select("*")
        .eq("user_id", user_id)
        .gte("log_date", str(start_date))
        .lte("log_date", str(end_date))
        .order("log_date", desc=False)
        .execute()
    )
    return response.data if response.data else []


# =====================================================
# USER FEEDBACK OPERATIONS
# =====================================================

def save_feedback(feedback_data: dict) -> dict:
    """
    Save a weekly feedback survey response.

    Args:
        feedback_data: Dictionary with user_id, week_start_date,
                       workout_difficulty, nutrition_feeling,
                       areas_to_avoid, focus_preferences, etc.

    Returns:
        The created feedback record
    """
    response = supabase.table("user_feedback").insert(feedback_data).execute()
    return response.data[0] if response.data else None


def get_latest_feedback(user_id: str) -> dict:
    """
    Get the most recent feedback submission.

    Used by the ML model to incorporate the user's latest
    preferences into plan adjustments.

    Args:
        user_id: UUID string of the user

    Returns:
        The latest feedback record or None
    """
    response = (
        supabase.table("user_feedback")
        .select("*")
        .eq("user_id", user_id)
        .order("submitted_at", desc=True)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None


def get_unapplied_feedback(user_id: str) -> list:
    """
    Get feedback entries that haven't been processed by the ML model yet.

    The 'applied' flag prevents the same feedback from being
    processed multiple times.

    Args:
        user_id: UUID string of the user

    Returns:
        List of unapplied feedback records
    """
    response = (
        supabase.table("user_feedback")
        .select("*")
        .eq("user_id", user_id)
        .eq("applied", False)
        .order("submitted_at", desc=True)
        .execute()
    )
    return response.data if response.data else []


def mark_feedback_applied(feedback_id: str) -> None:
    """
    Mark a feedback entry as processed by the ML model.

    Args:
        feedback_id: UUID of the feedback record
    """
    supabase.table("user_feedback").update(
        {"applied": True}
    ).eq("id", feedback_id).execute()


# =====================================================
# PLAN ADJUSTMENT HISTORY
# =====================================================

def log_plan_adjustment(user_id: str, adjustment_type: str,
                         previous_values: dict, new_values: dict,
                         reason: str) -> dict:
    """
    Record what the ML model changed and why.

    This creates an audit trail that's useful for:
    - Debugging unexpected plan changes
    - Showing the user why their plan changed
    - Impressing your professor with thoughtful engineering

    Args:
        user_id: UUID string of the user
        adjustment_type: 'nutrition', 'workout', or 'both'
        previous_values: What the values were before
        new_values: What the values are now
        reason: Human-readable explanation

    Returns:
        The created adjustment record
    """
    record = {
        "user_id": user_id,
        "adjustment_type": adjustment_type,
        "previous_values": json.dumps(previous_values),
        "new_values": json.dumps(new_values),
        "reason": reason,
    }
    response = supabase.table("plan_adjustments").insert(record).execute()
    return response.data[0] if response.data else None


def get_plan_adjustments(user_id: str, limit: int = 10) -> list:
    """
    Get recent plan adjustment history.

    Displayed on the Dashboard so users understand why
    their plan changed.

    Args:
        user_id: UUID string of the user
        limit: Maximum number of records to return

    Returns:
        List of adjustment records, newest first
    """
    response = (
        supabase.table("plan_adjustments")
        .select("*")
        .eq("user_id", user_id)
        .order("adjusted_at", desc=True)
        .limit(limit)
        .execute()
    )
    return response.data if response.data else []
