# =====================================================
# FitFuel - Workout Plan Generation Engine
# =====================================================
# This module contains the rule-based system that creates
# personalized weekly training plans. It filters exercises
# based on the user's equipment, experience, physical
# limitations, and goals — then assembles them into a
# structured weekly split.
# =====================================================

import random
from utils.config import (
    EXERCISE_DATABASE,
    TRAINING_SPLITS,
    EXPERIENCE_VOLUME_MULTIPLIER,
    DURATION_EXERCISE_COUNT,
)


def filter_exercises(
    muscle_group: str,
    available_equipment: list,
    physical_limitations: list,
    goal: str,
    experience: str,
) -> list:
    """
    Filter the exercise database to find suitable exercises.

    An exercise is suitable if:
    1. It targets the requested muscle group
    2. The user has at least one piece of required equipment
    3. It doesn't conflict with any of the user's physical limitations
    4. It's appropriate for the user's goal
    5. It's at or below the user's experience level

    Args:
        muscle_group: Target muscle group (e.g., 'chest', 'back', 'legs')
        available_equipment: List of equipment the user has
        physical_limitations: List of the user's physical limitations
        goal: User's primary goal ('fat_loss', 'muscle_gain', 'maintenance')
        experience: Training experience level

    Returns:
        List of exercise dictionaries that pass all filters
    """
    # Map experience levels to a hierarchy for difficulty filtering
    experience_hierarchy = {"beginner": 0, "intermediate": 1, "advanced": 2}
    user_level = experience_hierarchy.get(experience, 0)

    suitable = []
    for exercise in EXERCISE_DATABASE:
        # Check 1: Correct muscle group
        if exercise["muscle_group"] != muscle_group:
            continue

        # Check 2: User has the required equipment
        # An exercise is available if the user has ANY of its equipment options
        has_equipment = any(
            eq in available_equipment for eq in exercise["equipment"]
        )
        if not has_equipment:
            continue

        # Check 3: No conflicts with physical limitations
        has_conflict = any(
            lim in physical_limitations for lim in exercise["limitation_conflicts"]
        )
        if has_conflict:
            continue

        # Check 4: Exercise suits the user's goal
        if goal not in exercise["goal_suitability"]:
            continue

        # Check 5: Exercise difficulty is within user's level
        exercise_level = experience_hierarchy.get(exercise["difficulty"], 0)
        if exercise_level > user_level:
            continue

        suitable.append(exercise)

    return suitable


def select_exercises_for_muscle_group(
    muscle_group: str,
    count: int,
    available_equipment: list,
    physical_limitations: list,
    goal: str,
    experience: str,
) -> list:
    """
    Select a specific number of exercises for a muscle group.

    From the filtered pool, we randomly select the requested
    number of exercises. Randomization adds variety between
    plan regenerations while ensuring all selected exercises
    are appropriate for the user.

    Args:
        muscle_group: Target muscle group
        count: How many exercises to select
        available_equipment: List of equipment the user has
        physical_limitations: List of the user's physical limitations
        goal: User's primary goal
        experience: Training experience level

    Returns:
        List of selected exercise dictionaries with adjusted sets/reps
    """
    pool = filter_exercises(
        muscle_group, available_equipment, physical_limitations, goal, experience
    )

    if not pool:
        return []

    # Select up to 'count' exercises, avoiding duplicates
    selected = random.sample(pool, min(count, len(pool)))

    # Adjust sets and reps based on experience level
    volume = EXPERIENCE_VOLUME_MULTIPLIER.get(experience, {"sets_mult": 1.0, "reps_mult": 1.0})
    for exercise in selected:
        exercise["prescribed_sets"] = max(2, round(exercise["default_sets"] * volume["sets_mult"]))
        exercise["prescribed_reps"] = max(5, round(exercise["default_reps"] * volume["reps_mult"]))

    return selected


def generate_workout_plan(
    goal: str,
    experience: str,
    training_days: int,
    available_equipment: list,
    physical_limitations: list,
    preferred_duration: str = "moderate",
    focus_preferences: list = None,
) -> dict:
    """
    Generate a complete weekly workout plan.

    This is the main function called when a user completes onboarding
    or when the ML model triggers a plan regeneration.

    The process:
    1. Select the appropriate training split based on days/week
    2. For each training day, determine which muscle groups to hit
    3. Allocate exercise slots per muscle group based on session duration
    4. Select specific exercises from the filtered pool
    5. Package everything into a structured plan

    Args:
        goal: User's primary goal
        experience: Training experience level
        training_days: Number of training days per week (3, 4, or 5)
        available_equipment: List of equipment the user has
        physical_limitations: List of the user's physical limitations
        preferred_duration: 'short', 'moderate', or 'long'
        focus_preferences: Optional list of focus areas (e.g., ['More upper body'])

    Returns:
        Dictionary with the complete plan structure
    """
    # Step 1: Get the training split template
    split = TRAINING_SPLITS.get(training_days, TRAINING_SPLITS[3])

    # Step 2: Determine how many exercises per session
    duration_config = DURATION_EXERCISE_COUNT.get(preferred_duration, DURATION_EXERCISE_COUNT["moderate"])
    # Use the middle of the range as our target
    target_exercises = (duration_config["min"] + duration_config["max"]) // 2

    # Step 3: Build the plan day by day
    plan = {
        "split_name": split["name"],
        "training_days": training_days,
        "days": {},
    }

    for day_key, day_config in split["days"].items():
        muscle_groups = day_config["muscle_groups"]

        # Distribute exercise slots across muscle groups
        # Give roughly equal slots, with extras going to priority groups
        exercises_per_group = distribute_exercise_slots(
            muscle_groups, target_exercises, focus_preferences
        )

        # Select exercises for each muscle group
        day_exercises = []
        for mg, count in exercises_per_group.items():
            selected = select_exercises_for_muscle_group(
                mg, count, available_equipment, physical_limitations,
                goal, experience
            )
            day_exercises.extend(selected)

        # Add optional cardio for fat loss goals
        if goal == "fat_loss" and "cardio" not in muscle_groups:
            cardio = select_exercises_for_muscle_group(
                "cardio", 1, available_equipment, physical_limitations,
                goal, experience
            )
            day_exercises.extend(cardio)

        plan["days"][day_key] = {
            "focus": day_config["focus"],
            "muscle_groups": muscle_groups,
            "exercises": [
                {
                    "name": ex["name"],
                    "muscle_group": ex["muscle_group"],
                    "prescribed_sets": ex["prescribed_sets"],
                    "prescribed_reps": ex["prescribed_reps"],
                    "equipment": ex["equipment"],
                }
                for ex in day_exercises
            ],
        }

    return plan


def distribute_exercise_slots(
    muscle_groups: list,
    total_exercises: int,
    focus_preferences: list = None,
) -> dict:
    """
    Distribute exercise slots across muscle groups for a training day.

    Base distribution is roughly equal, but focus preferences
    can shift slots toward specific groups. For example, if the
    user wants "More upper body", chest/back/shoulders get extra slots.

    Args:
        muscle_groups: List of muscle groups for this training day
        total_exercises: Total number of exercises for the session
        focus_preferences: Optional user focus preferences

    Returns:
        Dictionary mapping each muscle group to its exercise count
    """
    if not muscle_groups:
        return {}

    # Start with equal distribution
    base_count = max(1, total_exercises // len(muscle_groups))
    distribution = {mg: base_count for mg in muscle_groups}

    # Apply focus preferences (shift slots toward preferred areas)
    if focus_preferences:
        upper_groups = {"chest", "back", "shoulders", "arms", "triceps"}
        lower_groups = {"legs"}
        core_groups = {"core"}

        for pref in focus_preferences:
            if pref == "More upper body":
                for mg in muscle_groups:
                    if mg in upper_groups:
                        distribution[mg] = distribution.get(mg, 1) + 1
            elif pref == "More lower body":
                for mg in muscle_groups:
                    if mg in lower_groups:
                        distribution[mg] = distribution.get(mg, 1) + 1
            elif pref == "More core work":
                for mg in muscle_groups:
                    if mg in core_groups:
                        distribution[mg] = distribution.get(mg, 1) + 1

    # Ensure we don't exceed total exercises by too much
    total_assigned = sum(distribution.values())
    if total_assigned > total_exercises + 2:
        # Scale back proportionally
        scale = total_exercises / total_assigned
        distribution = {mg: max(1, round(count * scale)) for mg, count in distribution.items()}

    return distribution


def calculate_workout_completion(prescribed_reps: int, actual_reps: list) -> float:
    """
    Calculate workout completion percentage for a single exercise.

    Compares what was prescribed (sets × reps) to what was actually
    performed. Used for progress tracking and ML model input.

    Example: Prescribed 3 sets of 10 reps, actual = [10, 8, 7]
    Total prescribed = 30, total actual = 25, completion = 83.3%

    Args:
        prescribed_reps: Reps per set that were prescribed
        actual_reps: List of actual reps completed per set

    Returns:
        Completion percentage (0.0 to 100.0)
    """
    if not actual_reps or prescribed_reps == 0:
        return 0.0

    total_prescribed = prescribed_reps * len(actual_reps)
    total_actual = sum(actual_reps)

    # Cap at 100% — exceeding prescribed reps counts as 100%
    return min(100.0, round((total_actual / total_prescribed) * 100, 1))
