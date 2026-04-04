# =====================================================
# FitFuel - BMR, TDEE, and Macronutrient Calculations
# =====================================================
# This module implements the nutritional science formulas
# that form the foundation of every user's nutrition plan.
# All calculations follow established exercise science
# standards (Harris-Benedict equation).
# =====================================================

from utils.config import (
    ACTIVITY_MULTIPLIERS,
    GOAL_CALORIE_ADJUSTMENTS,
    MACRO_RATIOS,
    CALORIES_PER_GRAM,
)


def calculate_bmr(gender: str, weight_kg: float, height_cm: float, age: int) -> float:
    """
    Calculate Basal Metabolic Rate using the revised Harris-Benedict equation.

    BMR represents the number of calories the body burns at complete rest —
    just to keep organs functioning, blood circulating, and lungs breathing.

    The Harris-Benedict equation (revised by Roza & Shizgal, 1984):
    - Male:   88.362 + (13.397 × weight in kg) + (4.799 × height in cm) - (5.677 × age)
    - Female: 447.593 + (9.247 × weight in kg) + (3.098 × height in cm) - (4.330 × age)

    Args:
        gender: 'male' or 'female'
        weight_kg: Current body weight in kilograms
        height_cm: Height in centimeters
        age: Age in years

    Returns:
        BMR in calories per day (float)
    """
    if gender == "male":
        bmr = 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)
    else:
        bmr = 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
    return round(bmr, 2)


def calculate_tdee(bmr: float, activity_level: str) -> float:
    """
    Calculate Total Daily Energy Expenditure from BMR and activity level.

    TDEE = BMR × activity multiplier. This represents the total calories
    the user burns in a typical day including their normal activities
    and exercise habits.

    Args:
        bmr: Basal Metabolic Rate (from calculate_bmr)
        activity_level: One of 'sedentary', 'lightly_active',
                        'moderately_active', 'very_active'

    Returns:
        TDEE in calories per day (float)
    """
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.2)
    return round(bmr * multiplier, 2)


def calculate_daily_calories(tdee: float, goal: str) -> float:
    """
    Adjust TDEE based on the user's fitness goal.

    - Fat loss: 15% deficit (eat less than you burn → lose weight)
    - Muscle gain: 15% surplus (eat more than you burn → build muscle)
    - Maintenance: no adjustment (eat exactly what you burn)

    A 15% adjustment is considered mild and sustainable — aggressive
    deficits (>25%) lead to muscle loss and metabolic adaptation.

    Args:
        tdee: Total Daily Energy Expenditure
        goal: One of 'fat_loss', 'muscle_gain', 'maintenance'

    Returns:
        Daily calorie target (float)
    """
    adjustment = GOAL_CALORIE_ADJUSTMENTS.get(goal, 1.0)
    return round(tdee * adjustment, 2)


def calculate_macros(daily_calories: float, goal: str) -> dict:
    """
    Break down daily calories into protein, carbs, and fat targets.

    The macro split varies by goal:
    - Fat loss: higher protein (35%) to preserve muscle, moderate carbs (35%)
    - Muscle gain: highest carbs (45%) for energy, high protein (30%)
    - Maintenance: balanced split (30/40/30)

    Each gram of protein = 4 calories
    Each gram of carbs = 4 calories
    Each gram of fat = 9 calories

    Args:
        daily_calories: Target daily calorie intake
        goal: One of 'fat_loss', 'muscle_gain', 'maintenance'

    Returns:
        Dictionary with 'protein_g', 'carbs_g', 'fat_g' (all floats)
    """
    ratios = MACRO_RATIOS.get(goal, MACRO_RATIOS["maintenance"])

    # Calculate calories from each macro, then convert to grams
    protein_g = (daily_calories * ratios["protein"]) / CALORIES_PER_GRAM["protein"]
    carbs_g = (daily_calories * ratios["carbs"]) / CALORIES_PER_GRAM["carbs"]
    fat_g = (daily_calories * ratios["fat"]) / CALORIES_PER_GRAM["fat"]

    return {
        "protein_g": round(protein_g, 1),
        "carbs_g": round(carbs_g, 1),
        "fat_g": round(fat_g, 1),
    }


def calculate_all_nutrition(
    gender: str,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity_level: str,
    goal: str,
) -> dict:
    """
    Master function that runs the full nutrition calculation pipeline.

    This is the function called during onboarding and plan recalculations.
    It chains together all the individual calculations and returns
    everything the app needs to set up a user's nutrition plan.

    Args:
        gender: 'male' or 'female'
        weight_kg: Current body weight in kilograms
        height_cm: Height in centimeters
        age: Age in years
        activity_level: One of 'sedentary', 'lightly_active',
                        'moderately_active', 'very_active'
        goal: One of 'fat_loss', 'muscle_gain', 'maintenance'

    Returns:
        Dictionary containing bmr, tdee, daily_calories,
        protein_g, carbs_g, fat_g
    """
    bmr = calculate_bmr(gender, weight_kg, height_cm, age)
    tdee = calculate_tdee(bmr, activity_level)
    daily_calories = calculate_daily_calories(tdee, goal)
    macros = calculate_macros(daily_calories, goal)

    return {
        "bmr": bmr,
        "tdee": tdee,
        "daily_calories": daily_calories,
        "protein_g": macros["protein_g"],
        "carbs_g": macros["carbs_g"],
        "fat_g": macros["fat_g"],
    }


def estimate_weeks_to_goal(current_weight: float, goal_weight: float, goal: str) -> int:
    """
    Estimate how many weeks it will take to reach the goal weight.

    Assumes a safe rate of change:
    - Fat loss: ~0.5 kg per week (from the 15% deficit)
    - Muscle gain: ~0.25 kg per week (lean mass gain is slow)
    - Maintenance: 0 (already at goal)

    This is displayed on the dashboard to give users realistic expectations.

    Args:
        current_weight: Current weight in kg
        goal_weight: Target weight in kg
        goal: One of 'fat_loss', 'muscle_gain', 'maintenance'

    Returns:
        Estimated weeks to goal (integer, minimum 1)
    """
    weight_diff = abs(current_weight - goal_weight)

    if goal == "fat_loss":
        weekly_rate = 0.5  # kg per week
    elif goal == "muscle_gain":
        weekly_rate = 0.25  # kg per week
    else:
        return 0  # maintenance — already at goal

    if weight_diff == 0:
        return 0

    weeks = weight_diff / weekly_rate
    return max(1, round(weeks))
