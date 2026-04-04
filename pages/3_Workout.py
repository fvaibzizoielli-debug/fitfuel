# =====================================================
# FitFuel - Workout Page
# =====================================================
# This page handles:
# 1. Displaying today's prescribed workout
# 2. Rep-by-rep logging for each exercise
# 3. Workout completion tracking
# 4. Workout history and progression view
# 5. Option to regenerate the workout plan
#
# Users see their daily exercises with prescribed sets/reps
# and enter actual reps completed per set. This granular
# tracking feeds into the ML model for adaptive planning.
# =====================================================

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import json
from datetime import date, timedelta
from utils.supabase_client import (
    get_user_profile,
    get_active_workout_plan,
    get_workout_logs_for_date,
    get_workout_logs,
    log_workout,
    save_workout_plan,
)
from utils.workout_engine import generate_workout_plan, calculate_workout_completion
from utils.config import COLORS

# ----- Page Configuration -----
st.set_page_config(page_title="FitFuel — Workout", page_icon="🏋️", layout="wide")

# ----- Auth Check -----
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please select or create a profile on the main page.")
    st.stop()

# ----- Load Profile -----
profile = get_user_profile(st.session_state.user_id)
if not profile:
    st.error("Profile not found.")
    st.stop()

st.markdown("## 🏋️ Workout Tracker")
st.markdown("View your daily workout and log your performance.")

# =====================================================
# LOAD ACTIVE PLAN & TODAY'S DATA
# =====================================================

plan = get_active_workout_plan(st.session_state.user_id)
today = date.today()
today_logs = get_workout_logs_for_date(st.session_state.user_id, today)

# Build a set of exercise names already logged today
logged_exercises = {}
for log in today_logs:
    logged_exercises[log.get("exercise_name", "")] = log.get("actual_reps", [])

# =====================================================
# SECTION 1: TODAY'S WORKOUT
# =====================================================

if plan and plan.get("plan_data"):
    plan_data = plan["plan_data"]

    st.markdown("---")
    st.markdown(f"### 📋 Current Plan: **{plan_data.get('split_name', 'Custom')} Split** "
                f"({plan_data.get('training_days', '?')} days/week)")

    # Determine today's workout day
    day_keys = list(plan_data.get("days", {}).keys())
    day_of_week = today.weekday()  # 0=Monday

    # Map weekday to training day (spread training days across the week)
    today_day_key = None
    if day_of_week < len(day_keys):
        today_day_key = day_keys[day_of_week]

    if today_day_key and today_day_key in plan_data.get("days", {}):
        today_plan = plan_data["days"][today_day_key]

        st.markdown(
            f"### Today ({today.strftime('%A')}): "
            f"**{today_plan.get('focus', 'Workout')}**"
        )
        st.caption(
            f"Muscle groups: {', '.join(today_plan.get('muscle_groups', []))}"
        )

        exercises = today_plan.get("exercises", [])

        if not exercises:
            st.warning("No exercises found for today. Try regenerating your plan.")
        else:
            # Overall completion tracker
            total_exercises = len(exercises)
            completed_exercises = sum(1 for ex in exercises if ex["name"] in logged_exercises)
            completion_pct = (completed_exercises / total_exercises * 100) if total_exercises > 0 else 0

            st.progress(completion_pct / 100,
                        text=f"Workout Progress: {completed_exercises}/{total_exercises} exercises ({completion_pct:.0f}%)")

            # ----- Exercise Cards -----
            for i, exercise in enumerate(exercises):
                is_logged = exercise["name"] in logged_exercises
                status_icon = "✅" if is_logged else "🔄"
                prescribed_sets = exercise.get("prescribed_sets", 3)
                prescribed_reps = exercise.get("prescribed_reps", 10)

                with st.expander(
                    f"{status_icon} {exercise['name']} — "
                    f"{prescribed_sets} sets × {prescribed_reps} reps "
                    f"({'Completed' if is_logged else 'Not logged yet'})",
                    expanded=not is_logged,
                ):
                    # Show exercise info
                    col_info, col_log = st.columns([1, 2])

                    with col_info:
                        st.markdown(f"**Muscle group:** {exercise.get('muscle_group', 'N/A').title()}")
                        st.markdown(f"**Equipment:** {', '.join(exercise.get('equipment', ['N/A']))}")
                        st.markdown(f"**Prescribed:** {prescribed_sets} sets × {prescribed_reps} reps")

                    with col_log:
                        if is_logged:
                            # Already logged — show results
                            actual = logged_exercises[exercise["name"]]
                            completion = calculate_workout_completion(prescribed_reps, actual)

                            st.markdown("**Your performance:**")
                            for s_idx, reps in enumerate(actual):
                                reps_color = "🟢" if reps >= prescribed_reps else "🟡" if reps >= prescribed_reps * 0.7 else "🔴"
                                st.markdown(f"Set {s_idx + 1}: {reps_color} {reps}/{prescribed_reps} reps")
                            st.metric("Completion", f"{completion:.0f}%")
                        else:
                            # Not logged yet — show input form
                            st.markdown("**Log your reps:**")
                            with st.form(f"exercise_form_{i}", clear_on_submit=False):
                                actual_reps = []
                                cols = st.columns(prescribed_sets)
                                for s_idx in range(prescribed_sets):
                                    with cols[s_idx]:
                                        reps = st.number_input(
                                            f"Set {s_idx + 1}",
                                            min_value=0,
                                            max_value=prescribed_reps * 2,
                                            value=prescribed_reps,
                                            step=1,
                                            key=f"reps_{i}_{s_idx}",
                                        )
                                        actual_reps.append(reps)

                                # Optional weight tracking
                                weight_used = st.number_input(
                                    "Weight used (kg, optional)",
                                    min_value=0.0, max_value=500.0,
                                    value=0.0, step=2.5,
                                    key=f"weight_{i}",
                                )

                                if st.form_submit_button(f"💾 Save {exercise['name']}", use_container_width=True):
                                    log_data = {
                                        "user_id": st.session_state.user_id,
                                        "workout_plan_id": plan.get("id"),
                                        "workout_date": str(today),
                                        "day_name": today_day_key,
                                        "exercise_name": exercise["name"],
                                        "prescribed_sets": prescribed_sets,
                                        "prescribed_reps": prescribed_reps,
                                        "actual_reps": actual_reps,
                                        "weight_used": weight_used if weight_used > 0 else None,
                                    }
                                    result = log_workout(log_data)
                                    if result:
                                        completion = calculate_workout_completion(prescribed_reps, actual_reps)
                                        st.success(f"✅ {exercise['name']} logged! ({completion:.0f}% completion)")
                                        st.rerun()
                                    else:
                                        st.error("Failed to save. Please try again.")

            # Celebration when all exercises are done
            if completed_exercises == total_exercises and total_exercises > 0:
                st.balloons()
                st.success("🎉 Workout complete! Great job today!")

    else:
        st.success(f"🎉 Rest day ({today.strftime('%A')})! No workout scheduled.")
        st.markdown("Use this time to recover, stretch, or do light activity.")

    # =====================================================
    # SECTION 2: FULL WEEKLY PLAN VIEW
    # =====================================================
    st.markdown("---")
    st.markdown("### 📅 Full Weekly Plan")

    # Create tabs for each training day
    if day_keys:
        tabs = st.tabs([f"{dk}: {plan_data['days'][dk].get('focus', 'Workout')}" for dk in day_keys])

        for tab, dk in zip(tabs, day_keys):
            with tab:
                day_plan = plan_data["days"][dk]
                st.markdown(f"**Focus:** {day_plan.get('focus', 'N/A')}")
                st.markdown(f"**Muscle groups:** {', '.join(day_plan.get('muscle_groups', []))}")

                # Exercise table
                exercises = day_plan.get("exercises", [])
                if exercises:
                    for ex in exercises:
                        st.markdown(
                            f"- **{ex['name']}** — "
                            f"{ex.get('prescribed_sets', 3)} sets × {ex.get('prescribed_reps', 10)} reps "
                            f"({ex.get('muscle_group', '').title()})"
                        )
                else:
                    st.info("No exercises assigned to this day.")

else:
    st.warning("No active workout plan found. Please generate one on the Profile page.")

    if st.button("🔄 Generate New Plan", use_container_width=True):
        new_plan = generate_workout_plan(
            goal=profile.get("primary_goal", "maintenance"),
            experience=profile.get("training_experience", "beginner"),
            training_days=profile.get("training_days_per_week", 4),
            available_equipment=profile.get("available_equipment", ["Bodyweight only"]),
            physical_limitations=profile.get("physical_limitations", []),
            preferred_duration=profile.get("preferred_workout_duration", "moderate"),
        )
        monday = today - timedelta(days=today.weekday())
        save_workout_plan(st.session_state.user_id, monday, new_plan)
        st.success("✅ New workout plan generated!")
        st.rerun()

# =====================================================
# SECTION 3: REGENERATE PLAN
# =====================================================
if plan:
    st.markdown("---")
    st.markdown("### 🔄 Regenerate Plan")
    st.caption("Not happy with the current plan? Generate a fresh one with different exercise selections.")

    if st.button("🔄 Generate New Workout Plan", use_container_width=True):
        new_plan = generate_workout_plan(
            goal=profile.get("primary_goal", "maintenance"),
            experience=profile.get("training_experience", "beginner"),
            training_days=profile.get("training_days_per_week", 4),
            available_equipment=profile.get("available_equipment", ["Bodyweight only"]),
            physical_limitations=profile.get("physical_limitations", []),
            preferred_duration=profile.get("preferred_workout_duration", "moderate"),
        )
        monday = today - timedelta(days=today.weekday())
        save_workout_plan(st.session_state.user_id, monday, new_plan)
        st.success("✅ New workout plan generated with fresh exercises!")
        st.rerun()

# =====================================================
# SECTION 4: WORKOUT HISTORY & PROGRESSION
# =====================================================
st.markdown("---")
st.markdown("### 📈 Workout History")

# Date range selector
history_range = st.selectbox(
    "Show history for:",
    options=["Last 7 days", "Last 14 days", "Last 30 days"],
    index=0,
)
days_back = {"Last 7 days": 7, "Last 14 days": 14, "Last 30 days": 30}[history_range]
history_start = today - timedelta(days=days_back)

history_logs = get_workout_logs(st.session_state.user_id, history_start, today)

if history_logs:
    # Group by date for summary
    daily_summary = {}
    exercise_progression = {}

    for log in history_logs:
        d = log.get("workout_date", "")
        ex_name = log.get("exercise_name", "")

        # Daily summary
        if d not in daily_summary:
            daily_summary[d] = {"exercises": 0, "total_prescribed": 0, "total_actual": 0}
        daily_summary[d]["exercises"] += 1
        prescribed = log.get("prescribed_reps", 0)
        actual = log.get("actual_reps", [])
        if prescribed > 0 and actual:
            daily_summary[d]["total_prescribed"] += prescribed * len(actual)
            daily_summary[d]["total_actual"] += sum(actual)

        # Per-exercise progression (for strength tracking)
        if ex_name not in exercise_progression:
            exercise_progression[ex_name] = []
        if log.get("weight_used") and log.get("weight_used") > 0:
            exercise_progression[ex_name].append({
                "date": d,
                "weight": log.get("weight_used"),
                "reps": sum(actual) if actual else 0,
            })

    # Daily completion chart
    completion_data = []
    for d, vals in sorted(daily_summary.items()):
        pct = (vals["total_actual"] / vals["total_prescribed"] * 100) if vals["total_prescribed"] > 0 else 0
        completion_data.append({
            "date": d,
            "completion": min(100, pct),
            "exercises": vals["exercises"],
        })

    df_completion = pd.DataFrame(completion_data)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df_completion["date"],
        y=df_completion["completion"],
        marker_color=[
            COLORS["primary"] if c >= 80 else COLORS["accent"] if c >= 60 else COLORS["danger"]
            for c in df_completion["completion"]
        ],
        text=[f"{c:.0f}%" for c in df_completion["completion"]],
        textposition="outside",
        textfont=dict(color="#FAFAFA"),
        hovertemplate="Date: %{x}<br>Completion: %{y:.0f}%<br><extra></extra>",
    ))
    fig.add_hline(y=80, line_dash="dash", line_color="#888",
                  annotation_text="Target (80%)")
    fig.update_layout(
        title="Workout Completion Rate",
        yaxis_title="Completion %",
        yaxis=dict(range=[0, 115], gridcolor="#2a2d3e"),
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FAFAFA"},
        xaxis=dict(gridcolor="#2a2d3e"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Exercise progression chart (if weight data exists)
    exercises_with_weight = {k: v for k, v in exercise_progression.items() if len(v) >= 2}

    if exercises_with_weight:
        st.markdown("### 📊 Strength Progression")
        selected_exercise = st.selectbox(
            "Select exercise to view progression:",
            options=list(exercises_with_weight.keys()),
        )

        if selected_exercise:
            prog_data = exercises_with_weight[selected_exercise]
            df_prog = pd.DataFrame(prog_data)

            fig_prog = go.Figure()
            fig_prog.add_trace(go.Scatter(
                x=df_prog["date"],
                y=df_prog["weight"],
                mode="lines+markers",
                name="Weight (kg)",
                line=dict(color=COLORS["secondary"], width=3),
                marker=dict(size=8),
            ))
            fig_prog.update_layout(
                title=f"{selected_exercise} — Weight Progression",
                yaxis_title="Weight (kg)",
                height=300,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#FAFAFA"},
                xaxis=dict(gridcolor="#2a2d3e"),
                yaxis=dict(gridcolor="#2a2d3e"),
            )
            st.plotly_chart(fig_prog, use_container_width=True)
else:
    st.info("No workout history yet. Complete today's workout to start tracking your progress!")
