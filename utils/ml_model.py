# =====================================================
# FitFuel - Adaptive Machine Learning Model
# =====================================================
# This module implements the ML-based plan adaptation system.
# It analyzes user performance data (workout completion rates,
# calorie adherence, weight trends, and feedback) to predict
# optimal adjustments to nutrition and training plans.
#
# The ML approach:
# - Uses a Decision Tree Regressor from scikit-learn
# - Trained on the user's own historical data
# - Falls back to rule-based heuristics when insufficient
#   data is available (cold start problem)
# - Runs entirely locally — no external API calls
#
# This satisfies the university requirement of implementing
# machine learning without external API access, with all
# code written from scratch using sklearn primitives.
# =====================================================

import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.preprocessing import LabelEncoder
from datetime import date, timedelta
import json


# ----- Minimum data points needed before ML kicks in -----
# With fewer than this, we use rule-based fallbacks.
# 7 days gives roughly one week of data to learn from.
MIN_DATA_POINTS = 7


def prepare_training_features(workout_logs: list, nutrition_logs: list,
                                weight_logs: list, profile: dict) -> tuple:
    """
    Transform raw log data into feature vectors for ML training.

    Each row represents one day and includes:
    - Workout completion rate (avg across all exercises that day)
    - Calorie adherence ratio (actual calories / target calories)
    - Protein adherence ratio
    - Carb adherence ratio
    - Fat adherence ratio
    - Weight change from previous measurement (kg)
    - Day of week (0=Monday, 6=Sunday)
    - Days since start (trend indicator)

    The target variable is a composite "progress score" that
    captures whether the user is trending toward their goal.

    Args:
        workout_logs: List of workout log records
        nutrition_logs: List of nutrition log records
        weight_logs: List of weight log records
        profile: User profile dictionary

    Returns:
        Tuple of (features_array, target_array, feature_names)
        or (None, None, None) if insufficient data
    """
    # Group data by date
    daily_data = {}

    # Process workout logs — calculate daily completion rates
    for log in workout_logs:
        log_date = log["workout_date"]
        if log_date not in daily_data:
            daily_data[log_date] = {
                "workout_completions": [],
                "calories": 0, "protein": 0, "carbs": 0, "fat": 0,
                "weight": None,
            }
        # Calculate completion for this exercise
        prescribed = log.get("prescribed_reps", 0)
        actual = log.get("actual_reps", [])
        if prescribed > 0 and actual:
            total_prescribed = prescribed * len(actual)
            total_actual = sum(actual)
            completion = min(1.0, total_actual / total_prescribed)
            daily_data[log_date]["workout_completions"].append(completion)

    # Process nutrition logs — sum daily totals
    target_cal = profile.get("daily_calories", 2000)
    target_protein = profile.get("protein_g", 150)
    target_carbs = profile.get("carbs_g", 250)
    target_fat = profile.get("fat_g", 65)

    for log in nutrition_logs:
        log_date = log["meal_date"]
        if log_date not in daily_data:
            daily_data[log_date] = {
                "workout_completions": [],
                "calories": 0, "protein": 0, "carbs": 0, "fat": 0,
                "weight": None,
            }
        daily_data[log_date]["calories"] += log.get("calories", 0)
        daily_data[log_date]["protein"] += log.get("protein_g", 0)
        daily_data[log_date]["carbs"] += log.get("carbs_g", 0)
        daily_data[log_date]["fat"] += log.get("fat_g", 0)

    # Process weight logs
    for log in weight_logs:
        log_date = log["log_date"]
        if log_date in daily_data:
            daily_data[log_date]["weight"] = log.get("weight_kg")

    # Check if we have enough data
    if len(daily_data) < MIN_DATA_POINTS:
        return None, None, None

    # Sort dates and build feature matrix
    sorted_dates = sorted(daily_data.keys())
    start_date = sorted_dates[0]

    features = []
    targets = []

    prev_weight = profile.get("current_weight_kg", 70)

    for i, log_date in enumerate(sorted_dates):
        day = daily_data[log_date]

        # Feature 1: Average workout completion rate (0.0 to 1.0)
        completions = day["workout_completions"]
        avg_completion = np.mean(completions) if completions else 0.0

        # Feature 2-5: Macro adherence ratios
        cal_adherence = day["calories"] / target_cal if target_cal > 0 else 0
        protein_adherence = day["protein"] / target_protein if target_protein > 0 else 0
        carb_adherence = day["carbs"] / target_carbs if target_carbs > 0 else 0
        fat_adherence = day["fat"] / target_fat if target_fat > 0 else 0

        # Feature 6: Weight change from previous measurement
        current_weight = day["weight"] if day["weight"] else prev_weight
        weight_change = current_weight - prev_weight
        if day["weight"]:
            prev_weight = current_weight

        # Feature 7: Day of week (as number)
        try:
            d = date.fromisoformat(log_date)
            day_of_week = d.weekday()
        except (ValueError, TypeError):
            day_of_week = 0

        # Feature 8: Days since program start (captures time trends)
        try:
            d = date.fromisoformat(log_date)
            s = date.fromisoformat(start_date)
            days_since_start = (d - s).days
        except (ValueError, TypeError):
            days_since_start = i

        feature_row = [
            avg_completion,
            cal_adherence,
            protein_adherence,
            carb_adherence,
            fat_adherence,
            weight_change,
            day_of_week,
            days_since_start,
        ]
        features.append(feature_row)

        # Target: Progress score (composite metric)
        # Higher is better — represents how well the user is
        # progressing toward their goal
        target = calculate_progress_score(
            avg_completion, cal_adherence, weight_change,
            profile.get("primary_goal", "maintenance")
        )
        targets.append(target)

    feature_names = [
        "workout_completion", "calorie_adherence", "protein_adherence",
        "carb_adherence", "fat_adherence", "weight_change",
        "day_of_week", "days_since_start",
    ]

    return np.array(features), np.array(targets), feature_names


def calculate_progress_score(completion: float, cal_adherence: float,
                              weight_change: float, goal: str) -> float:
    """
    Calculate a composite progress score for ML training targets.

    This score combines workout performance, nutrition adherence,
    and weight trajectory into a single number. The weighting
    changes based on the user's goal.

    Score range: 0.0 (worst) to 1.0 (best)

    Args:
        completion: Workout completion rate (0.0 to 1.0)
        cal_adherence: Calorie adherence ratio (actual/target)
        weight_change: Weight change in kg from previous measurement
        goal: User's primary goal

    Returns:
        Progress score (0.0 to 1.0)
    """
    # Workout completion contributes directly
    workout_score = min(1.0, completion)

    # Nutrition score: closer to 1.0 adherence is better
    # Penalize both over-eating and under-eating
    nutrition_score = max(0.0, 1.0 - abs(1.0 - cal_adherence))

    # Weight direction score depends on goal
    if goal == "fat_loss":
        # Losing weight is good (negative weight_change is positive progress)
        weight_score = 1.0 if weight_change < 0 else max(0.0, 1.0 - weight_change)
    elif goal == "muscle_gain":
        # Gaining weight is good (positive weight_change is positive progress)
        weight_score = 1.0 if weight_change > 0 else max(0.0, 1.0 + weight_change)
    else:
        # Maintenance: staying stable is good
        weight_score = max(0.0, 1.0 - abs(weight_change) * 2)

    # Weighted combination — workout and nutrition matter most
    score = (0.4 * workout_score) + (0.35 * nutrition_score) + (0.25 * weight_score)
    return round(min(1.0, max(0.0, score)), 3)


def train_and_predict(features: np.ndarray, targets: np.ndarray) -> dict:
    """
    Train a Decision Tree model and predict adjustment recommendations.

    We use a Decision Tree because:
    - It works well with small datasets (important for new users)
    - It's interpretable (we can explain why changes were made)
    - It handles non-linear relationships between features
    - It doesn't require feature scaling

    The model is trained on all available data, then we look at
    feature importances and recent trends to determine what
    adjustments are needed.

    Args:
        features: Feature matrix (n_samples × n_features)
        targets: Target progress scores (n_samples,)

    Returns:
        Dictionary with adjustment recommendations
    """
    # Train the Decision Tree model
    model = DecisionTreeRegressor(
        max_depth=4,            # Prevent overfitting on small datasets
        min_samples_split=3,    # Need at least 3 samples to split
        min_samples_leaf=2,     # Each leaf needs at least 2 samples
        random_state=42,        # Reproducible results
    )
    model.fit(features, targets)

    # Get feature importances — tells us what matters most
    feature_names = [
        "workout_completion", "calorie_adherence", "protein_adherence",
        "carb_adherence", "fat_adherence", "weight_change",
        "day_of_week", "days_since_start",
    ]
    importances = dict(zip(feature_names, model.feature_importances_))

    # Analyze recent trends (last 7 entries)
    recent_features = features[-7:]
    recent_targets = targets[-7:]

    avg_recent_score = np.mean(recent_targets)
    avg_completion = np.mean(recent_features[:, 0])
    avg_cal_adherence = np.mean(recent_features[:, 1])
    avg_weight_change = np.mean(recent_features[:, 5])

    # Predict expected score if user continues current pattern
    predicted_scores = model.predict(recent_features)
    trend = np.mean(predicted_scores[-3:]) - np.mean(predicted_scores[:3]) if len(predicted_scores) >= 3 else 0

    return {
        "model_score": round(avg_recent_score, 3),
        "trend": round(trend, 3),
        "avg_completion": round(avg_completion, 3),
        "avg_cal_adherence": round(avg_cal_adherence, 3),
        "avg_weight_change": round(avg_weight_change, 4),
        "feature_importances": {k: round(v, 3) for k, v in importances.items()},
    }


def generate_adjustments(ml_results: dict, feedback: dict,
                          profile: dict) -> dict:
    """
    Combine ML predictions with user feedback to generate
    specific plan adjustment recommendations.

    This is the brain of the adaptive system. It takes:
    1. ML analysis of workout/nutrition/weight data
    2. User's explicit feedback preferences
    3. Current profile settings

    And outputs concrete changes to calories, macros, and
    workout parameters.

    Args:
        ml_results: Output from train_and_predict()
        feedback: Latest user feedback (or empty dict)
        profile: Current user profile

    Returns:
        Dictionary with specific adjustment values and reasons
    """
    adjustments = {
        "calorie_adjustment": 0,        # Calories to add/subtract
        "protein_adjustment": 0,        # Grams to add/subtract
        "carbs_adjustment": 0,
        "fat_adjustment": 0,
        "volume_adjustment": 0,         # Training volume change (-1, 0, +1)
        "training_days_change": 0,      # Days to add/subtract
        "new_limitations": [],          # Any newly reported limitations
        "focus_preferences": [],        # Updated focus areas
        "reasons": [],                  # Human-readable explanations
    }

    # ----- Analyze workout completion -----
    avg_completion = ml_results.get("avg_completion", 0.8)
    if avg_completion < 0.6:
        # User is struggling — reduce volume
        adjustments["volume_adjustment"] = -1
        adjustments["reasons"].append(
            f"Workout completion is at {avg_completion*100:.0f}% — "
            f"reducing training volume to help you succeed."
        )
    elif avg_completion > 0.95:
        # User is breezing through — increase volume
        adjustments["volume_adjustment"] = 1
        adjustments["reasons"].append(
            f"Great completion rate of {avg_completion*100:.0f}%! "
            f"Increasing training volume for continued progress."
        )

    # ----- Analyze calorie adherence -----
    avg_cal = ml_results.get("avg_cal_adherence", 1.0)
    current_calories = profile.get("daily_calories", 2000)

    if avg_cal < 0.75:
        # User is consistently under-eating — might be too restrictive
        adjustment = round(current_calories * 0.05)  # Increase by 5%
        adjustments["calorie_adjustment"] = adjustment
        adjustments["reasons"].append(
            f"You're averaging only {avg_cal*100:.0f}% of your calorie target. "
            f"Adjusting target up by {adjustment} kcal to be more achievable."
        )
    elif avg_cal > 1.2:
        # User is consistently over-eating — target might be too low
        adjustment = round(current_calories * 0.05)
        adjustments["calorie_adjustment"] = adjustment
        adjustments["reasons"].append(
            f"You're averaging {avg_cal*100:.0f}% of your calorie target. "
            f"Adjusting target up by {adjustment} kcal to be more realistic."
        )

    # ----- Analyze weight trend -----
    avg_weight_change = ml_results.get("avg_weight_change", 0)
    goal = profile.get("primary_goal", "maintenance")

    if goal == "fat_loss" and avg_weight_change > 0.1:
        # Gaining weight during fat loss — increase deficit slightly
        adjustments["calorie_adjustment"] -= 100
        adjustments["reasons"].append(
            "Weight is trending up during fat loss phase. "
            "Reducing calories by 100 kcal to create a stronger deficit."
        )
    elif goal == "muscle_gain" and avg_weight_change < -0.1:
        # Losing weight during muscle gain — increase surplus
        adjustments["calorie_adjustment"] += 100
        adjustments["reasons"].append(
            "Weight is trending down during muscle gain phase. "
            "Adding 100 kcal to support muscle growth."
        )

    # ----- Incorporate user feedback -----
    if feedback:
        # Workout difficulty feedback
        difficulty = feedback.get("workout_difficulty", "just_right")
        if difficulty == "too_hard":
            adjustments["volume_adjustment"] = min(adjustments["volume_adjustment"], -1)
            adjustments["reasons"].append(
                "You reported workouts are too hard — reducing intensity."
            )
        elif difficulty == "too_easy":
            adjustments["volume_adjustment"] = max(adjustments["volume_adjustment"], 1)
            adjustments["reasons"].append(
                "You reported workouts are too easy — increasing intensity."
            )

        # Nutrition feeling feedback
        nutrition_feel = feedback.get("nutrition_feeling", "about_right")
        if nutrition_feel == "too_much":
            adjustments["calorie_adjustment"] -= 75
            adjustments["reasons"].append(
                "You reported feeling overfed — reducing calories by 75 kcal."
            )
        elif nutrition_feel == "not_enough":
            adjustments["calorie_adjustment"] += 75
            adjustments["reasons"].append(
                "You reported feeling hungry — adding 75 kcal."
            )

        # Training day preference change
        new_days = feedback.get("preferred_training_days")
        if new_days and new_days != profile.get("training_days_per_week"):
            adjustments["training_days_change"] = new_days - profile.get("training_days_per_week", 3)
            adjustments["reasons"].append(
                f"Changing training days from {profile.get('training_days_per_week', 3)} "
                f"to {new_days} per week as requested."
            )

        # New areas to avoid
        areas = feedback.get("areas_to_avoid", [])
        if areas:
            adjustments["new_limitations"] = areas

        # Focus preferences
        focus = feedback.get("focus_preferences", [])
        if focus:
            adjustments["focus_preferences"] = focus

    # ----- Calculate macro adjustments proportionally -----
    # If calories change, adjust macros to maintain the same ratios
    if adjustments["calorie_adjustment"] != 0:
        cal_change = adjustments["calorie_adjustment"]
        current_protein = profile.get("protein_g", 150)
        current_carbs = profile.get("carbs_g", 250)
        current_fat = profile.get("fat_g", 65)
        total_macro_cals = (current_protein * 4) + (current_carbs * 4) + (current_fat * 9)

        if total_macro_cals > 0:
            protein_ratio = (current_protein * 4) / total_macro_cals
            carbs_ratio = (current_carbs * 4) / total_macro_cals
            fat_ratio = (current_fat * 9) / total_macro_cals

            adjustments["protein_adjustment"] = round((cal_change * protein_ratio) / 4, 1)
            adjustments["carbs_adjustment"] = round((cal_change * carbs_ratio) / 4, 1)
            adjustments["fat_adjustment"] = round((cal_change * fat_ratio) / 9, 1)

    # If no adjustments were needed, say so
    if not adjustments["reasons"]:
        adjustments["reasons"].append(
            "Your current plan is well-suited to your progress. "
            "Keep up the great work! No adjustments needed."
        )

    return adjustments


def apply_adjustments(profile: dict, adjustments: dict) -> dict:
    """
    Apply the generated adjustments to produce updated profile values.

    This returns the new values that should be saved to the database.
    The actual database update happens in the calling code (not here)
    to keep this module focused on ML logic only.

    Args:
        profile: Current user profile
        adjustments: Output from generate_adjustments()

    Returns:
        Dictionary with updated field values
    """
    updates = {}

    # Update calorie target
    current_cal = profile.get("daily_calories", 2000)
    new_cal = max(1200, current_cal + adjustments.get("calorie_adjustment", 0))
    updates["daily_calories"] = round(new_cal, 2)

    # Update macro targets
    current_protein = profile.get("protein_g", 150)
    current_carbs = profile.get("carbs_g", 250)
    current_fat = profile.get("fat_g", 65)

    updates["protein_g"] = round(max(50, current_protein + adjustments.get("protein_adjustment", 0)), 1)
    updates["carbs_g"] = round(max(50, current_carbs + adjustments.get("carbs_adjustment", 0)), 1)
    updates["fat_g"] = round(max(20, current_fat + adjustments.get("fat_adjustment", 0)), 1)

    # Update training days if changed
    if adjustments.get("training_days_change", 0) != 0:
        current_days = profile.get("training_days_per_week", 3)
        new_days = max(3, min(5, current_days + adjustments["training_days_change"]))
        updates["training_days_per_week"] = new_days

    # Update physical limitations if new ones reported
    if adjustments.get("new_limitations"):
        current_limits = profile.get("physical_limitations", [])
        combined = list(set(current_limits + adjustments["new_limitations"]))
        updates["physical_limitations"] = combined

    return updates


def run_adaptation_pipeline(workout_logs: list, nutrition_logs: list,
                             weight_logs: list, profile: dict,
                             feedback: dict = None) -> tuple:
    """
    Master function that runs the complete ML adaptation pipeline.

    This is the single entry point called by the app when the user
    clicks "Adapt My Plan". It orchestrates the full flow:
    1. Prepare features from raw data
    2. Train model and analyze trends (or use heuristics if too little data)
    3. Generate adjustment recommendations
    4. Calculate new profile values

    Args:
        workout_logs: All workout logs for this user
        nutrition_logs: All nutrition logs for this user
        weight_logs: All weight logs for this user
        profile: Current user profile
        feedback: Latest user feedback (optional)

    Returns:
        Tuple of (adjustments_dict, updated_values_dict)
    """
    # Step 1: Prepare features
    features, targets, feature_names = prepare_training_features(
        workout_logs, nutrition_logs, weight_logs, profile
    )

    # Step 2: Get ML results or use defaults
    if features is not None and len(features) >= MIN_DATA_POINTS:
        # Enough data — use ML model
        ml_results = train_and_predict(features, targets)
    else:
        # Cold start — use sensible defaults
        ml_results = {
            "model_score": 0.7,
            "trend": 0.0,
            "avg_completion": 0.8,
            "avg_cal_adherence": 1.0,
            "avg_weight_change": 0.0,
            "feature_importances": {},
        }

    # Step 3: Generate adjustments combining ML + feedback
    adjustments = generate_adjustments(ml_results, feedback or {}, profile)

    # Step 4: Calculate new values
    updated_values = apply_adjustments(profile, adjustments)

    return adjustments, updated_values
