# FitFuel - Configuration Constants
# Exercise database, activity multipliers, and app-wide settings

# =====================================================
# FitFuel - Configuration Constants
# =====================================================
# This file contains all static data the app relies on:
# exercise database, activity multipliers, equipment mappings,
# and UI configuration. Centralizing these here makes the
# codebase easier to maintain and extend.
# =====================================================

# ----- Supabase Credentials -----
# These connect the app to our Supabase database.
# In production you'd use environment variables, but for
# a university project this is fine.
SUPABASE_URL = "https://mqmaormkwxgbixxizdbn.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1xbWFvcm1rd3hnYml4eGl6ZGJuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzUzMzY3MDksImV4cCI6MjA5MDkxMjcwOX0.kSdq2lcTzgZkU2j128bEYEljcg92_O3Phgml7RiBlsg"

# ----- Activity Level Multipliers -----
# Used to convert BMR → TDEE (Total Daily Energy Expenditure).
# These are standard Harris-Benedict activity factors from
# exercise science literature.
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,           # Desk job, little to no exercise
    "lightly_active": 1.375,    # Light exercise 1-3 days/week
    "moderately_active": 1.55,  # Moderate exercise 3-5 days/week
    "very_active": 1.725,       # Hard exercise 6-7 days/week
}

# ----- Goal-Based Calorie Adjustments -----
# These multipliers are applied to the TDEE to set the daily
# calorie target. A mild deficit/surplus (10-15%) is safer and
# more sustainable than aggressive approaches.
GOAL_CALORIE_ADJUSTMENTS = {
    "fat_loss": 0.85,       # 15% deficit — promotes ~0.5kg/week loss
    "muscle_gain": 1.15,    # 15% surplus — supports lean muscle gain
    "maintenance": 1.0,     # No adjustment
}

# ----- Macronutrient Ratios by Goal -----
# Expressed as (protein%, carbs%, fat%) of total calories.
# Protein is prioritized for muscle gain, carbs are moderated
# for fat loss, and maintenance uses a balanced split.
MACRO_RATIOS = {
    "fat_loss": {"protein": 0.35, "carbs": 0.35, "fat": 0.30},
    "muscle_gain": {"protein": 0.30, "carbs": 0.45, "fat": 0.25},
    "maintenance": {"protein": 0.30, "carbs": 0.40, "fat": 0.30},
}

# ----- Calories per Gram of Each Macronutrient -----
# Standard nutritional constants used worldwide.
CALORIES_PER_GRAM = {
    "protein": 4,
    "carbs": 4,
    "fat": 9,
}

# ----- Physical Limitation Options -----
# These map directly to exercise substitution rules in the
# workout engine. Each limitation triggers specific exercise
# swaps to keep the user safe.
PHYSICAL_LIMITATIONS = [
    "Lower back issues",
    "Knee issues",
    "Shoulder issues",
    "Wrist/elbow issues",
    "Hip issues",
    "Neck issues",
]

# ----- Available Equipment Options -----
# Users select which equipment they have access to.
# The workout engine uses this to filter exercises.
EQUIPMENT_OPTIONS = [
    "Barbell",
    "Dumbbells",
    "Resistance bands",
    "Pull-up bar",
    "Cable machine",
    "Machines (leg press, chest fly, etc.)",
    "Bodyweight only",
]

# ----- Focus Preference Options (for feedback form) -----
# After each week, users can indicate what they want more of.
# The ML model and workout engine use these to adjust the plan.
FOCUS_PREFERENCES = [
    "More upper body",
    "More lower body",
    "More core work",
    "More cardio",
    "More flexibility/mobility",
    "Keep it balanced",
]

# ----- Workout Duration Mapping -----
# Maps the user's preferred duration to a rough number of
# exercises per session. This keeps workouts within the
# time window the user can commit to.
DURATION_EXERCISE_COUNT = {
    "short": {"min": 4, "max": 5},       # Under 45 minutes
    "moderate": {"min": 5, "max": 7},     # 45-60 minutes
    "long": {"min": 7, "max": 9},         # 60+ minutes
}

# ----- Training Split Templates -----
# These define which muscle groups are trained on which days,
# based on how many days per week the user wants to train.
# Each split is a well-established approach from exercise science.
TRAINING_SPLITS = {
    3: {
        # Full-body 3x/week — best for beginners, covers everything
        "name": "Full Body",
        "days": {
            "Day 1": {"focus": "Full Body A", "muscle_groups": ["chest", "back", "legs", "shoulders", "core"]},
            "Day 2": {"focus": "Full Body B", "muscle_groups": ["chest", "back", "legs", "arms", "core"]},
            "Day 3": {"focus": "Full Body C", "muscle_groups": ["chest", "back", "legs", "shoulders", "arms"]},
        }
    },
    4: {
        # Upper/Lower split — good balance for intermediates
        "name": "Upper/Lower",
        "days": {
            "Day 1": {"focus": "Upper Body A", "muscle_groups": ["chest", "back", "shoulders", "arms"]},
            "Day 2": {"focus": "Lower Body A", "muscle_groups": ["legs", "core"]},
            "Day 3": {"focus": "Upper Body B", "muscle_groups": ["chest", "back", "shoulders", "arms"]},
            "Day 4": {"focus": "Lower Body B", "muscle_groups": ["legs", "core"]},
        }
    },
    5: {
        # Push/Pull/Legs — higher volume for advanced users
        "name": "Push/Pull/Legs",
        "days": {
            "Day 1": {"focus": "Push", "muscle_groups": ["chest", "shoulders", "triceps"]},
            "Day 2": {"focus": "Pull", "muscle_groups": ["back", "biceps", "core"]},
            "Day 3": {"focus": "Legs", "muscle_groups": ["legs", "core"]},
            "Day 4": {"focus": "Upper Body", "muscle_groups": ["chest", "back", "shoulders", "arms"]},
            "Day 5": {"focus": "Full Body", "muscle_groups": ["legs", "chest", "back", "core"]},
        }
    },
}

# ----- Exercise Database -----
# Each exercise includes:
#   - muscle_group: which body part it targets
#   - equipment: what's needed to perform it
#   - difficulty: beginner/intermediate/advanced
#   - sets/reps: default prescription (adjusted by workout engine)
#   - limitation_conflicts: which physical limitations make this unsafe
#   - goal_suitability: which goals this exercise fits best
#
# The workout engine filters this list based on the user's profile
# to build a personalized plan.
EXERCISE_DATABASE = [
    # ===== CHEST =====
    {
        "name": "Barbell Bench Press",
        "muscle_group": "chest",
        "equipment": ["Barbell"],
        "difficulty": "intermediate",
        "default_sets": 4,
        "default_reps": 8,
        "limitation_conflicts": ["Shoulder issues", "Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Dumbbell Bench Press",
        "muscle_group": "chest",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Push-Ups",
        "muscle_group": "chest",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },
    {
        "name": "Incline Dumbbell Press",
        "muscle_group": "chest",
        "equipment": ["Dumbbells"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Cable Chest Fly",
        "muscle_group": "chest",
        "equipment": ["Cable machine"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Resistance Band Chest Press",
        "muscle_group": "chest",
        "equipment": ["Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": [],
        "goal_suitability": ["fat_loss", "maintenance"],
    },
    {
        "name": "Machine Chest Press",
        "muscle_group": "chest",
        "equipment": ["Machines (leg press, chest fly, etc.)"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },

    # ===== BACK =====
    {
        "name": "Barbell Bent-Over Row",
        "muscle_group": "back",
        "equipment": ["Barbell"],
        "difficulty": "intermediate",
        "default_sets": 4,
        "default_reps": 8,
        "limitation_conflicts": ["Lower back issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Dumbbell Row",
        "muscle_group": "back",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Pull-Ups",
        "muscle_group": "back",
        "equipment": ["Pull-up bar"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 8,
        "limitation_conflicts": ["Shoulder issues", "Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Lat Pulldown",
        "muscle_group": "back",
        "equipment": ["Cable machine"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Resistance Band Row",
        "muscle_group": "back",
        "equipment": ["Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": [],
        "goal_suitability": ["fat_loss", "maintenance"],
    },
    {
        "name": "Seated Cable Row",
        "muscle_group": "back",
        "equipment": ["Cable machine"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Inverted Rows",
        "muscle_group": "back",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["fat_loss", "maintenance"],
    },

    # ===== LEGS =====
    {
        "name": "Barbell Squat",
        "muscle_group": "legs",
        "equipment": ["Barbell"],
        "difficulty": "intermediate",
        "default_sets": 4,
        "default_reps": 8,
        "limitation_conflicts": ["Knee issues", "Lower back issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Goblet Squat",
        "muscle_group": "legs",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Knee issues"],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },
    {
        "name": "Bodyweight Squat",
        "muscle_group": "legs",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": ["Knee issues"],
        "goal_suitability": ["fat_loss", "maintenance"],
    },
    {
        "name": "Romanian Deadlift",
        "muscle_group": "legs",
        "equipment": ["Barbell", "Dumbbells"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Lower back issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Leg Press",
        "muscle_group": "legs",
        "equipment": ["Machines (leg press, chest fly, etc.)"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Knee issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Walking Lunges",
        "muscle_group": "legs",
        "equipment": ["Bodyweight only", "Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Knee issues", "Hip issues"],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },
    {
        "name": "Leg Extension",
        "muscle_group": "legs",
        "equipment": ["Machines (leg press, chest fly, etc.)"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Leg Curl",
        "muscle_group": "legs",
        "equipment": ["Machines (leg press, chest fly, etc.)"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Resistance Band Squat",
        "muscle_group": "legs",
        "equipment": ["Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": ["Knee issues"],
        "goal_suitability": ["fat_loss", "maintenance"],
    },
    {
        "name": "Hip Thrust",
        "muscle_group": "legs",
        "equipment": ["Barbell", "Bodyweight only"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Lower back issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },

    # ===== SHOULDERS =====
    {
        "name": "Overhead Press",
        "muscle_group": "shoulders",
        "equipment": ["Barbell"],
        "difficulty": "intermediate",
        "default_sets": 4,
        "default_reps": 8,
        "limitation_conflicts": ["Shoulder issues", "Lower back issues", "Neck issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Dumbbell Shoulder Press",
        "muscle_group": "shoulders",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Shoulder issues", "Neck issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Lateral Raises",
        "muscle_group": "shoulders",
        "equipment": ["Dumbbells", "Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": ["Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Front Raises",
        "muscle_group": "shoulders",
        "equipment": ["Dumbbells", "Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Face Pulls",
        "muscle_group": "shoulders",
        "equipment": ["Cable machine", "Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },

    # ===== ARMS (BICEPS & TRICEPS) =====
    {
        "name": "Barbell Curl",
        "muscle_group": "arms",
        "equipment": ["Barbell"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Dumbbell Curl",
        "muscle_group": "arms",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Hammer Curl",
        "muscle_group": "arms",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": [],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Tricep Pushdown",
        "muscle_group": "arms",
        "equipment": ["Cable machine"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Overhead Tricep Extension",
        "muscle_group": "arms",
        "equipment": ["Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Shoulder issues", "Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Diamond Push-Ups",
        "muscle_group": "arms",
        "equipment": ["Bodyweight only"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Resistance Band Curl",
        "muscle_group": "arms",
        "equipment": ["Resistance bands"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 15,
        "limitation_conflicts": [],
        "goal_suitability": ["fat_loss", "maintenance"],
    },
    {
        "name": "Tricep Dips",
        "muscle_group": "triceps",
        "equipment": ["Bodyweight only"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Shoulder issues", "Wrist/elbow issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },

    # ===== CORE =====
    {
        "name": "Plank",
        "muscle_group": "core",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 30,  # seconds
        "limitation_conflicts": ["Lower back issues"],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },
    {
        "name": "Bicycle Crunches",
        "muscle_group": "core",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 20,
        "limitation_conflicts": ["Neck issues", "Lower back issues"],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },
    {
        "name": "Hanging Leg Raises",
        "muscle_group": "core",
        "equipment": ["Pull-up bar"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Lower back issues", "Shoulder issues"],
        "goal_suitability": ["muscle_gain", "maintenance"],
    },
    {
        "name": "Cable Woodchops",
        "muscle_group": "core",
        "equipment": ["Cable machine"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 12,
        "limitation_conflicts": ["Lower back issues"],
        "goal_suitability": ["muscle_gain", "maintenance", "fat_loss"],
    },
    {
        "name": "Dead Bug",
        "muscle_group": "core",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": [],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },
    {
        "name": "Mountain Climbers",
        "muscle_group": "core",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 20,
        "limitation_conflicts": ["Wrist/elbow issues"],
        "goal_suitability": ["fat_loss", "maintenance"],
    },
    {
        "name": "Russian Twist",
        "muscle_group": "core",
        "equipment": ["Bodyweight only", "Dumbbells"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 20,
        "limitation_conflicts": ["Lower back issues"],
        "goal_suitability": ["fat_loss", "muscle_gain", "maintenance"],
    },

    # ===== CARDIO (for fat loss plans) =====
    {
        "name": "Jumping Jacks",
        "muscle_group": "cardio",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 30,
        "limitation_conflicts": ["Knee issues"],
        "goal_suitability": ["fat_loss"],
    },
    {
        "name": "Burpees",
        "muscle_group": "cardio",
        "equipment": ["Bodyweight only"],
        "difficulty": "intermediate",
        "default_sets": 3,
        "default_reps": 10,
        "limitation_conflicts": ["Knee issues", "Lower back issues", "Wrist/elbow issues"],
        "goal_suitability": ["fat_loss"],
    },
    {
        "name": "High Knees",
        "muscle_group": "cardio",
        "equipment": ["Bodyweight only"],
        "difficulty": "beginner",
        "default_sets": 3,
        "default_reps": 30,
        "limitation_conflicts": ["Knee issues", "Hip issues"],
        "goal_suitability": ["fat_loss"],
    },
]

# ----- Experience-Based Volume Adjustments -----
# Beginners need fewer sets to recover and learn form.
# Advanced lifters can handle higher volume.
# These multipliers are applied to the default sets/reps.
EXPERIENCE_VOLUME_MULTIPLIER = {
    "beginner": {"sets_mult": 0.75, "reps_mult": 1.0},
    "intermediate": {"sets_mult": 1.0, "reps_mult": 1.0},
    "advanced": {"sets_mult": 1.25, "reps_mult": 0.85},  # More sets, fewer reps, heavier weight implied
}

# ----- UI Configuration -----
# Color scheme for consistent data visualization across the app.
COLORS = {
    "primary": "#4CAF50",       # Green — brand color
    "secondary": "#2196F3",     # Blue — secondary actions
    "accent": "#FF9800",        # Orange — highlights/warnings
    "danger": "#F44336",        # Red — errors/over limits
    "protein": "#2196F3",       # Blue — protein in charts
    "carbs": "#FF9800",         # Amber — carbs in charts
    "fat": "#F44336",           # Red — fat in charts
    "calories": "#4CAF50",      # Green — calorie indicators
    "background": "#0E1117",    # Dark background
    "card": "#1E2130",          # Card/container background
    "text": "#FAFAFA",          # Primary text color
}

# ----- Meal Type Options -----
MEAL_TYPES = ["breakfast", "lunch", "dinner", "snack"]

# ----- Day Names (for workout plan display) -----
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
