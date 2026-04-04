# =====================================================
# FitFuel - Main Application Entry Point
# =====================================================
# This is the landing page of the app. It handles:
# 1. New user onboarding (detailed survey)
# 2. Profile selection for returning users
# 3. Profile settings & preferences management
# 4. Weekly feedback form for plan adaptation
#
# The app uses Streamlit's session_state to persist the
# current user's ID across page navigations.
# =====================================================

import streamlit as st
from datetime import date, timedelta
from utils.supabase_client import (
    create_user_profile,
    get_all_profiles,
    get_user_profile,
    update_user_profile,
    save_feedback,
    get_latest_feedback,
    get_active_workout_plan,
    save_workout_plan,
    log_plan_adjustment,
)
from utils.calculations import calculate_all_nutrition, estimate_weeks_to_goal
from utils.workout_engine import generate_workout_plan
from utils.ml_model import run_adaptation_pipeline
from utils.supabase_client import (
    get_workout_logs,
    get_nutrition_logs,
    get_weight_logs,
    get_unapplied_feedback,
    mark_feedback_applied,
)
from utils.config import (
    PHYSICAL_LIMITATIONS,
    EQUIPMENT_OPTIONS,
    FOCUS_PREFERENCES,
    COLORS,
)

# ----- Page Configuration -----
# Must be the first Streamlit command in the script
st.set_page_config(
    page_title="FitFuel — Your Adaptive Fitness Coach",
    page_icon="💪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----- Custom CSS for a polished look -----
st.markdown("""
<style>
    /* Main title styling */
    .main-title {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #4CAF50, #2196F3);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .subtitle {
        font-size: 1.1rem;
        color: #888;
        margin-bottom: 2rem;
    }
    /* Metric card styling */
    .metric-card {
        background: #1E2130;
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid #2a2d3e;
        text-align: center;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #4CAF50;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #888;
        margin-top: 0.3rem;
    }
    /* Section headers */
    .section-header {
        font-size: 1.3rem;
        font-weight: 600;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #4CAF50;
    }
    /* Success/info message styling */
    .stSuccess, .stInfo {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================
# Streamlit reruns the script on every interaction, so we
# use session_state to remember who is logged in.

if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "show_onboarding" not in st.session_state:
    st.session_state.show_onboarding = False


# =====================================================
# SIDEBAR — Profile Selection / Login
# =====================================================

with st.sidebar:
    st.markdown('<p class="main-title">💪 FitFuel</p>', unsafe_allow_html=True)
    st.markdown("Your Adaptive Fitness Coach")
    st.divider()

    # Fetch all existing profiles for the selection dropdown
    profiles = get_all_profiles()

    if profiles:
        # Build a mapping of display names to profile IDs
        profile_options = {f"{p['name']}": p["id"] for p in profiles}
        profile_options["➕ Create New Profile"] = "new"

        selected = st.selectbox(
            "Select Profile",
            options=list(profile_options.keys()),
            index=0,
        )

        if profile_options[selected] == "new":
            st.session_state.show_onboarding = True
            st.session_state.user_id = None
        else:
            st.session_state.user_id = profile_options[selected]
            st.session_state.show_onboarding = False
    else:
        # No profiles exist yet — show onboarding
        st.info("Welcome to FitFuel! Let's set up your profile.")
        st.session_state.show_onboarding = True

    st.divider()
    st.caption("FitFuel v1.0 — Built with Streamlit & Supabase")


# =====================================================
# MAIN CONTENT
# =====================================================

if st.session_state.show_onboarding or st.session_state.user_id is None:
    # =====================================================
    # ONBOARDING SURVEY — New User Registration
    # =====================================================
    st.markdown('<p class="main-title">Welcome to FitFuel 💪</p>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Let\'s build your personalized fitness plan. This takes about 2 minutes.</p>', unsafe_allow_html=True)

    with st.form("onboarding_form"):
        # ----- Section 1: Basic Information -----
        st.markdown('<p class="section-header">📋 Basic Information</p>', unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Your Name *", placeholder="e.g., Alex")
            age = st.number_input("Age *", min_value=14, max_value=100, value=25, step=1,
                                  help="Needed for accurate BMR calculation")
            height_cm = st.number_input("Height (cm) *", min_value=100.0, max_value=250.0,
                                         value=175.0, step=0.5,
                                         help="Used in the Harris-Benedict equation")

        with col2:
            gender = st.selectbox("Gender *", options=["male", "female"],
                                  help="The BMR formula uses different coefficients per gender")
            current_weight = st.number_input("Current Weight (kg) *", min_value=30.0,
                                              max_value=300.0, value=75.0, step=0.5)
            goal_weight = st.number_input("Goal Weight (kg) *", min_value=30.0,
                                           max_value=300.0, value=70.0, step=0.5)

        # ----- Section 2: Activity & Experience -----
        st.markdown('<p class="section-header">🏃 Activity & Experience</p>', unsafe_allow_html=True)
        col3, col4 = st.columns(2)

        with col3:
            activity_level = st.selectbox(
                "Daily Activity Level *",
                options=["sedentary", "lightly_active", "moderately_active", "very_active"],
                format_func=lambda x: {
                    "sedentary": "🪑 Sedentary (desk job, little exercise)",
                    "lightly_active": "🚶 Lightly Active (light exercise 1-3 days/week)",
                    "moderately_active": "🏃 Moderately Active (moderate exercise 3-5 days/week)",
                    "very_active": "🔥 Very Active (hard exercise 6-7 days/week)",
                }[x],
                help="This determines your TDEE multiplier"
            )
            training_experience = st.selectbox(
                "Training Experience *",
                options=["beginner", "intermediate", "advanced"],
                format_func=lambda x: {
                    "beginner": "🌱 Beginner (< 6 months of consistent training)",
                    "intermediate": "💪 Intermediate (6 months - 2 years)",
                    "advanced": "🏋️ Advanced (2+ years of structured training)",
                }[x],
                help="Determines exercise complexity and volume"
            )

        with col4:
            training_days = st.selectbox(
                "Training Days per Week *",
                options=[3, 4, 5],
                index=1,
                help="3 = Full Body split, 4 = Upper/Lower, 5 = Push/Pull/Legs"
            )
            preferred_duration = st.selectbox(
                "Preferred Workout Duration *",
                options=["short", "moderate", "long"],
                index=1,
                format_func=lambda x: {
                    "short": "⚡ Short (under 45 minutes)",
                    "moderate": "⏱️ Moderate (45-60 minutes)",
                    "long": "🕐 Long (60+ minutes)",
                }[x],
                help="Controls how many exercises per session"
            )

        # ----- Section 3: Goal -----
        st.markdown('<p class="section-header">🎯 Your Goal</p>', unsafe_allow_html=True)
        primary_goal = st.selectbox(
            "Primary Goal *",
            options=["fat_loss", "muscle_gain", "maintenance"],
            format_func=lambda x: {
                "fat_loss": "🔥 Fat Loss — Lose weight while preserving muscle",
                "muscle_gain": "💪 Muscle Gain — Build muscle with a calorie surplus",
                "maintenance": "⚖️ Maintenance — Maintain current weight and fitness",
            }[x],
        )

        # ----- Section 4: Equipment -----
        st.markdown('<p class="section-header">🏋️ Equipment & Gym Access</p>', unsafe_allow_html=True)
        gym_access = st.checkbox("I have access to a gym", value=True)
        available_equipment = st.multiselect(
            "Available Equipment *",
            options=EQUIPMENT_OPTIONS,
            default=["Bodyweight only"],
            help="Select all equipment you have access to"
        )

        # ----- Section 5: Physical Limitations -----
        st.markdown('<p class="section-header">⚕️ Physical Limitations</p>', unsafe_allow_html=True)
        physical_limitations = st.multiselect(
            "Do you have any physical limitations? (select all that apply)",
            options=PHYSICAL_LIMITATIONS,
            default=[],
            help="We'll avoid exercises that could aggravate these conditions"
        )

        # ----- Submit Button -----
        st.divider()
        submitted = st.form_submit_button("🚀 Create My Personalized Plan", use_container_width=True)

        if submitted:
            if not name.strip():
                st.error("Please enter your name.")
            elif not available_equipment:
                st.error("Please select at least one equipment option.")
            else:
                # Step 1: Calculate nutrition targets
                nutrition = calculate_all_nutrition(
                    gender=gender,
                    weight_kg=current_weight,
                    height_cm=height_cm,
                    age=age,
                    activity_level=activity_level,
                    goal=primary_goal,
                )

                # Step 2: Build the profile data
                profile_data = {
                    "name": name.strip(),
                    "age": age,
                    "gender": gender,
                    "height_cm": height_cm,
                    "current_weight_kg": current_weight,
                    "goal_weight_kg": goal_weight,
                    "activity_level": activity_level,
                    "training_experience": training_experience,
                    "training_days_per_week": training_days,
                    "preferred_workout_duration": preferred_duration,
                    "primary_goal": primary_goal,
                    "gym_access": gym_access,
                    "available_equipment": available_equipment,
                    "physical_limitations": physical_limitations,
                    "bmr": nutrition["bmr"],
                    "tdee": nutrition["tdee"],
                    "daily_calories": nutrition["daily_calories"],
                    "protein_g": nutrition["protein_g"],
                    "carbs_g": nutrition["carbs_g"],
                    "fat_g": nutrition["fat_g"],
                }

                # Step 3: Save to Supabase
                created_profile = create_user_profile(profile_data)

                if created_profile:
                    # Step 4: Generate initial workout plan
                    plan = generate_workout_plan(
                        goal=primary_goal,
                        experience=training_experience,
                        training_days=training_days,
                        available_equipment=available_equipment,
                        physical_limitations=physical_limitations,
                        preferred_duration=preferred_duration,
                    )

                    # Calculate the Monday of the current week
                    today = date.today()
                    monday = today - timedelta(days=today.weekday())

                    save_workout_plan(
                        user_id=created_profile["id"],
                        week_start=monday,
                        plan_data=plan,
                    )

                    # Step 5: Set session state and refresh
                    st.session_state.user_id = created_profile["id"]
                    st.session_state.show_onboarding = False
                    st.success("🎉 Your personalized plan is ready! Navigate to the Dashboard to get started.")
                    st.rerun()
                else:
                    st.error("Something went wrong creating your profile. Please try again.")

else:
    # =====================================================
    # PROFILE & PREFERENCES PAGE — Returning Users
    # =====================================================

    # Load the current user's profile
    profile = get_user_profile(st.session_state.user_id)

    if not profile:
        st.error("Profile not found. Please create a new profile.")
        st.session_state.user_id = None
        st.rerun()

    st.markdown(f'<p class="main-title">Profile & Preferences</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitle">Welcome back, {profile["name"]}! Manage your settings and give feedback here.</p>', unsafe_allow_html=True)

    # ----- Current Nutrition Summary -----
    st.markdown('<p class="section-header">📊 Your Current Nutrition Targets</p>', unsafe_allow_html=True)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("BMR", f"{profile.get('bmr', 0):.0f} kcal")
    with col2:
        st.metric("TDEE", f"{profile.get('tdee', 0):.0f} kcal")
    with col3:
        st.metric("Daily Target", f"{profile.get('daily_calories', 0):.0f} kcal")
    with col4:
        st.metric("Protein", f"{profile.get('protein_g', 0):.0f}g")
    with col5:
        st.metric("Carbs", f"{profile.get('carbs_g', 0):.0f}g")
    with col6:
        st.metric("Fat", f"{profile.get('fat_g', 0):.0f}g")

    # Estimated time to goal
    weeks = estimate_weeks_to_goal(
        profile.get("current_weight_kg", 70),
        profile.get("goal_weight_kg", 70),
        profile.get("primary_goal", "maintenance"),
    )
    if weeks > 0:
        st.info(f"📅 Estimated time to reach {profile.get('goal_weight_kg', 0):.1f} kg: **~{weeks} weeks**")

    # ----- Two tabs: Edit Profile / Give Feedback -----
    tab1, tab2, tab3 = st.tabs(["✏️ Edit Profile", "📝 Weekly Feedback", "🤖 Adapt My Plan"])

    # ===== TAB 1: Edit Profile =====
    with tab1:
        st.markdown("Update your profile information. Changes will recalculate your nutrition targets.")

        with st.form("edit_profile_form"):
            col1, col2 = st.columns(2)

            with col1:
                new_age = st.number_input("Age", value=profile.get("age", 25),
                                           min_value=14, max_value=100)
                new_height = st.number_input("Height (cm)", value=float(profile.get("height_cm", 175)),
                                              min_value=100.0, max_value=250.0, step=0.5)
                new_weight = st.number_input("Current Weight (kg)",
                                              value=float(profile.get("current_weight_kg", 75)),
                                              min_value=30.0, max_value=300.0, step=0.5)
                new_goal_weight = st.number_input("Goal Weight (kg)",
                                                   value=float(profile.get("goal_weight_kg", 70)),
                                                   min_value=30.0, max_value=300.0, step=0.5)

            with col2:
                activity_options = ["sedentary", "lightly_active", "moderately_active", "very_active"]
                new_activity = st.selectbox(
                    "Activity Level",
                    options=activity_options,
                    index=activity_options.index(profile.get("activity_level", "sedentary")),
                    format_func=lambda x: {
                        "sedentary": "🪑 Sedentary",
                        "lightly_active": "🚶 Lightly Active",
                        "moderately_active": "🏃 Moderately Active",
                        "very_active": "🔥 Very Active",
                    }[x],
                )
                exp_options = ["beginner", "intermediate", "advanced"]
                new_experience = st.selectbox(
                    "Training Experience",
                    options=exp_options,
                    index=exp_options.index(profile.get("training_experience", "beginner")),
                )
                goal_options = ["fat_loss", "muscle_gain", "maintenance"]
                new_goal = st.selectbox(
                    "Primary Goal",
                    options=goal_options,
                    index=goal_options.index(profile.get("primary_goal", "maintenance")),
                    format_func=lambda x: {
                        "fat_loss": "🔥 Fat Loss",
                        "muscle_gain": "💪 Muscle Gain",
                        "maintenance": "⚖️ Maintenance",
                    }[x],
                )
                new_days = st.selectbox(
                    "Training Days per Week",
                    options=[3, 4, 5],
                    index=[3, 4, 5].index(profile.get("training_days_per_week", 4)),
                )

            # Equipment and limitations
            new_equipment = st.multiselect(
                "Available Equipment",
                options=EQUIPMENT_OPTIONS,
                default=profile.get("available_equipment", ["Bodyweight only"]),
            )
            new_limitations = st.multiselect(
                "Physical Limitations",
                options=PHYSICAL_LIMITATIONS,
                default=profile.get("physical_limitations", []),
            )

            update_submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

            if update_submitted:
                # Recalculate nutrition with new values
                new_nutrition = calculate_all_nutrition(
                    gender=profile.get("gender", "male"),
                    weight_kg=new_weight,
                    height_cm=new_height,
                    age=new_age,
                    activity_level=new_activity,
                    goal=new_goal,
                )

                updates = {
                    "age": new_age,
                    "height_cm": new_height,
                    "current_weight_kg": new_weight,
                    "goal_weight_kg": new_goal_weight,
                    "activity_level": new_activity,
                    "training_experience": new_experience,
                    "primary_goal": new_goal,
                    "training_days_per_week": new_days,
                    "available_equipment": new_equipment,
                    "physical_limitations": new_limitations,
                    "bmr": new_nutrition["bmr"],
                    "tdee": new_nutrition["tdee"],
                    "daily_calories": new_nutrition["daily_calories"],
                    "protein_g": new_nutrition["protein_g"],
                    "carbs_g": new_nutrition["carbs_g"],
                    "fat_g": new_nutrition["fat_g"],
                }

                update_user_profile(st.session_state.user_id, updates)
                st.success("✅ Profile updated successfully! Nutrition targets recalculated.")
                st.rerun()

    # ===== TAB 2: Weekly Feedback =====
    with tab2:
        st.markdown("Tell us how last week went. Your feedback helps the AI adapt your plan.")

        # Show latest feedback if exists
        latest = get_latest_feedback(st.session_state.user_id)
        if latest:
            st.info(f"📅 Last feedback submitted: {latest.get('submitted_at', 'N/A')[:10]}")

        with st.form("feedback_form"):
            col1, col2 = st.columns(2)

            with col1:
                workout_difficulty = st.select_slider(
                    "How did this week's workouts feel?",
                    options=["too_easy", "just_right", "too_hard"],
                    value="just_right",
                    format_func=lambda x: {
                        "too_easy": "😴 Too Easy",
                        "just_right": "👍 Just Right",
                        "too_hard": "😰 Too Hard",
                    }[x],
                )
                nutrition_feeling = st.select_slider(
                    "How was the nutrition plan to follow?",
                    options=["not_enough", "about_right", "too_much"],
                    value="about_right",
                    format_func=lambda x: {
                        "not_enough": "😋 Not Enough Food",
                        "about_right": "👍 About Right",
                        "too_much": "😫 Too Much Food",
                    }[x],
                )

            with col2:
                new_training_days = st.selectbox(
                    "Change training days per week?",
                    options=[3, 4, 5],
                    index=[3, 4, 5].index(profile.get("training_days_per_week", 4)),
                )
                duration_options = ["short", "moderate", "long"]
                new_duration = st.selectbox(
                    "Preferred workout duration?",
                    options=duration_options,
                    index=duration_options.index(profile.get("preferred_workout_duration", "moderate")),
                    format_func=lambda x: {
                        "short": "⚡ Short (under 45 min)",
                        "moderate": "⏱️ Moderate (45-60 min)",
                        "long": "🕐 Long (60+ min)",
                    }[x],
                )

            areas_to_avoid = st.multiselect(
                "Any areas to avoid or be careful with?",
                options=PHYSICAL_LIMITATIONS,
                default=profile.get("physical_limitations", []),
            )

            focus_prefs = st.multiselect(
                "What would you like more of?",
                options=FOCUS_PREFERENCES,
                default=[],
            )

            feedback_submitted = st.form_submit_button("📤 Submit Feedback", use_container_width=True)

            if feedback_submitted:
                today = date.today()
                monday = today - timedelta(days=today.weekday())

                feedback_data = {
                    "user_id": st.session_state.user_id,
                    "week_start_date": str(monday),
                    "workout_difficulty": workout_difficulty,
                    "nutrition_feeling": nutrition_feeling,
                    "areas_to_avoid": areas_to_avoid,
                    "focus_preferences": focus_prefs,
                    "preferred_training_days": new_training_days,
                    "preferred_duration": new_duration,
                }

                save_feedback(feedback_data)
                st.success("✅ Feedback submitted! Go to 'Adapt My Plan' to apply it.")

    # ===== TAB 3: Adapt My Plan (ML) =====
    with tab3:
        st.markdown("Let the AI analyze your progress and feedback to optimize your plan.")
        st.markdown("The system looks at your workout completion rates, calorie adherence, weight trends, and feedback to make smart adjustments.")

        if st.button("🤖 Analyze & Adapt My Plan", use_container_width=True):
            with st.spinner("Analyzing your data and training the ML model..."):
                # Gather all the data
                workout_logs = get_workout_logs(st.session_state.user_id)
                nutrition_logs = get_nutrition_logs(st.session_state.user_id)
                weight_logs = get_weight_logs(st.session_state.user_id)
                feedback_list = get_unapplied_feedback(st.session_state.user_id)
                latest_fb = feedback_list[0] if feedback_list else {}

                # Run the ML pipeline
                adjustments, updated_values = run_adaptation_pipeline(
                    workout_logs=workout_logs,
                    nutrition_logs=nutrition_logs,
                    weight_logs=weight_logs,
                    profile=profile,
                    feedback=latest_fb,
                )

                # Display the recommendations
                st.markdown("### 📋 Recommendations")
                for reason in adjustments.get("reasons", []):
                    st.markdown(f"- {reason}")

                # Show before vs after
                st.markdown("### 📊 Plan Changes")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Before:**")
                    st.write(f"Calories: {profile.get('daily_calories', 0):.0f} kcal")
                    st.write(f"Protein: {profile.get('protein_g', 0):.0f}g")
                    st.write(f"Carbs: {profile.get('carbs_g', 0):.0f}g")
                    st.write(f"Fat: {profile.get('fat_g', 0):.0f}g")
                with col2:
                    st.markdown("**After:**")
                    st.write(f"Calories: {updated_values.get('daily_calories', 0):.0f} kcal")
                    st.write(f"Protein: {updated_values.get('protein_g', 0):.0f}g")
                    st.write(f"Carbs: {updated_values.get('carbs_g', 0):.0f}g")
                    st.write(f"Fat: {updated_values.get('fat_g', 0):.0f}g")

                # Apply changes button
                if st.button("✅ Apply These Changes", use_container_width=True):
                    # Save previous values for audit trail
                    prev = {
                        "daily_calories": profile.get("daily_calories"),
                        "protein_g": profile.get("protein_g"),
                        "carbs_g": profile.get("carbs_g"),
                        "fat_g": profile.get("fat_g"),
                    }

                    # Update profile with new values
                    update_user_profile(st.session_state.user_id, updated_values)

                    # Log the adjustment
                    log_plan_adjustment(
                        user_id=st.session_state.user_id,
                        adjustment_type="both",
                        previous_values=prev,
                        new_values=updated_values,
                        reason="; ".join(adjustments.get("reasons", [])),
                    )

                    # Generate new workout plan if volume/days changed
                    if (adjustments.get("volume_adjustment", 0) != 0 or
                            adjustments.get("training_days_change", 0) != 0):
                        updated_profile = get_user_profile(st.session_state.user_id)
                        new_plan = generate_workout_plan(
                            goal=updated_profile.get("primary_goal", "maintenance"),
                            experience=updated_profile.get("training_experience", "beginner"),
                            training_days=updated_profile.get("training_days_per_week", 4),
                            available_equipment=updated_profile.get("available_equipment", []),
                            physical_limitations=updated_profile.get("physical_limitations", []),
                            preferred_duration=updated_profile.get("preferred_workout_duration", "moderate"),
                            focus_preferences=adjustments.get("focus_preferences", []),
                        )
                        today = date.today()
                        monday = today - timedelta(days=today.weekday())
                        save_workout_plan(st.session_state.user_id, monday, new_plan)

                    # Mark feedback as applied
                    for fb in feedback_list:
                        mark_feedback_applied(fb["id"])

                    st.success("🎉 Plan updated successfully!")
                    st.rerun()
