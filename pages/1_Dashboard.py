# =====================================================
# FitFuel - Dashboard Page
# =====================================================
# The central hub showing:
# 1. Today's calorie & macro progress (visual gauges)
# 2. Today's workout summary
# 3. Weekly & historical trend charts
# 4. Weight tracking over time
# 5. Recent plan adjustment history
#
# This page is data-visualization heavy, satisfying the
# university requirement for useful data visualization.
# =====================================================

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import date, timedelta
from utils.supabase_client import (
    get_user_profile,
    get_nutrition_logs_for_date,
    get_nutrition_logs,
    get_workout_logs_for_date,
    get_workout_logs,
    get_weight_logs,
    get_active_workout_plan,
    get_plan_adjustments,
    log_weight,
)
from utils.config import COLORS

# ----- Page Configuration -----
st.set_page_config(page_title="FitFuel — Dashboard", page_icon="📊", layout="wide")

# ----- Check if user is logged in -----
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please select or create a profile on the main page.")
    st.stop()

# ----- Load Profile -----
profile = get_user_profile(st.session_state.user_id)
if not profile:
    st.error("Profile not found.")
    st.stop()

# ----- Page Title -----
st.markdown(f"## 📊 Dashboard")
st.markdown(f"Welcome back, **{profile['name']}**! Here's your overview for today.")

# =====================================================
# ROW 1: TODAY'S NUTRITION PROGRESS
# =====================================================
st.markdown("---")
st.markdown("### 🍽️ Today's Nutrition")

# Get today's meals
today = date.today()
today_meals = get_nutrition_logs_for_date(st.session_state.user_id, today)

# Calculate consumed totals
consumed_calories = sum(m.get("calories", 0) for m in today_meals)
consumed_protein = sum(m.get("protein_g", 0) for m in today_meals)
consumed_carbs = sum(m.get("carbs_g", 0) for m in today_meals)
consumed_fat = sum(m.get("fat_g", 0) for m in today_meals)

# Targets from profile
target_calories = profile.get("daily_calories", 2000)
target_protein = profile.get("protein_g", 150)
target_carbs = profile.get("carbs_g", 250)
target_fat = profile.get("fat_g", 65)


def create_gauge(consumed, target, label, color):
    """
    Create a Plotly gauge chart for a single nutrient.

    The gauge shows a half-circle from 0 to the target value,
    with the needle pointing to the consumed amount.
    Color changes to red if the user exceeds their target.

    Args:
        consumed: Amount consumed so far
        target: Daily target amount
        label: Display label (e.g., "Calories")
        color: Color for the gauge bar

    Returns:
        Plotly Figure object
    """
    # Calculate percentage for display
    pct = (consumed / target * 100) if target > 0 else 0
    # Determine bar color — green if within target, red if exceeded
    bar_color = COLORS["danger"] if consumed > target else color

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=consumed,
        number={"font": {"size": 28, "color": "#FAFAFA"}},
        delta={"reference": target, "relative": False, "position": "bottom",
               "increasing": {"color": COLORS["danger"]},
               "decreasing": {"color": COLORS["primary"]}},
        title={"text": label, "font": {"size": 14, "color": "#888"}},
        gauge={
            "axis": {"range": [0, target * 1.2], "tickwidth": 1,
                     "tickcolor": "#444", "tickfont": {"color": "#888"}},
            "bar": {"color": bar_color},
            "bgcolor": "#1E2130",
            "borderwidth": 0,
            "steps": [
                {"range": [0, target], "color": "#2a2d3e"},
            ],
            "threshold": {
                "line": {"color": "#FAFAFA", "width": 2},
                "thickness": 0.75,
                "value": target,
            },
        },
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FAFAFA"},
    )
    return fig


# Display the four gauges in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.plotly_chart(
        create_gauge(consumed_calories, target_calories, "Calories (kcal)", COLORS["calories"]),
        use_container_width=True, key="gauge_cal"
    )
with col2:
    st.plotly_chart(
        create_gauge(consumed_protein, target_protein, "Protein (g)", COLORS["protein"]),
        use_container_width=True, key="gauge_protein"
    )
with col3:
    st.plotly_chart(
        create_gauge(consumed_carbs, target_carbs, "Carbs (g)", COLORS["carbs"]),
        use_container_width=True, key="gauge_carbs"
    )
with col4:
    st.plotly_chart(
        create_gauge(consumed_fat, target_fat, "Fat (g)", COLORS["fat"]),
        use_container_width=True, key="gauge_fat"
    )

# Remaining macros summary
remaining_cal = max(0, target_calories - consumed_calories)
remaining_protein = max(0, target_protein - consumed_protein)
remaining_carbs = max(0, target_carbs - consumed_carbs)
remaining_fat = max(0, target_fat - consumed_fat)

st.info(
    f"**Remaining today:** {remaining_cal:.0f} kcal | "
    f"{remaining_protein:.0f}g protein | "
    f"{remaining_carbs:.0f}g carbs | "
    f"{remaining_fat:.0f}g fat"
)

# =====================================================
# ROW 2: TODAY'S WORKOUT SUMMARY
# =====================================================
st.markdown("---")
st.markdown("### 🏋️ Today's Workout")

# Get active workout plan and today's logs
plan = get_active_workout_plan(st.session_state.user_id)
today_logs = get_workout_logs_for_date(st.session_state.user_id, today)

if plan and plan.get("plan_data"):
    plan_data = plan["plan_data"]
    training_days = plan_data.get("training_days", 4)

    # Determine which day of the training split today corresponds to
    day_keys = list(plan_data.get("days", {}).keys())
    day_of_week = today.weekday()  # 0=Monday

    # Simple mapping: spread training days across the week
    # For 4 days: Mon, Tue, Thu, Fri → indices 0,1,3,4
    if day_of_week < len(day_keys):
        today_day_key = day_keys[day_of_week] if day_of_week < len(day_keys) else None
    else:
        today_day_key = None

    if today_day_key and today_day_key in plan_data.get("days", {}):
        today_plan = plan_data["days"][today_day_key]
        st.markdown(f"**{today_day_key}: {today_plan.get('focus', 'Workout')}**")

        # Show exercises with completion status
        exercises = today_plan.get("exercises", [])
        logged_exercise_names = [log.get("exercise_name") for log in today_logs]

        for ex in exercises:
            is_done = ex["name"] in logged_exercise_names
            status = "✅" if is_done else "⬜"
            st.markdown(
                f"{status} **{ex['name']}** — "
                f"{ex.get('prescribed_sets', 3)} sets × {ex.get('prescribed_reps', 10)} reps"
            )

        # Overall completion percentage
        if exercises:
            done_count = sum(1 for ex in exercises if ex["name"] in logged_exercise_names)
            completion_pct = (done_count / len(exercises)) * 100
            st.progress(completion_pct / 100, text=f"Workout {completion_pct:.0f}% complete")
    else:
        st.success("🎉 Rest day! No workout scheduled for today.")
else:
    st.info("No workout plan found. Go to Profile & Preferences to generate one.")

# =====================================================
# ROW 3: WEEKLY TRENDS
# =====================================================
st.markdown("---")
st.markdown("### 📈 Weekly Trends")

# Get the past 7 days of nutrition data
week_start = today - timedelta(days=6)
week_nutrition = get_nutrition_logs(st.session_state.user_id, week_start, today)
week_workouts = get_workout_logs(st.session_state.user_id, week_start, today)

if week_nutrition:
    # Aggregate daily nutrition
    daily_nutrition = {}
    for log in week_nutrition:
        d = log.get("meal_date", "")
        if d not in daily_nutrition:
            daily_nutrition[d] = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}
        daily_nutrition[d]["calories"] += log.get("calories", 0)
        daily_nutrition[d]["protein_g"] += log.get("protein_g", 0)
        daily_nutrition[d]["carbs_g"] += log.get("carbs_g", 0)
        daily_nutrition[d]["fat_g"] += log.get("fat_g", 0)

    # Create DataFrame for plotting
    df_nutrition = pd.DataFrame([
        {"date": d, **vals} for d, vals in sorted(daily_nutrition.items())
    ])

    if not df_nutrition.empty:
        col1, col2 = st.columns(2)

        with col1:
            # Calorie trend line chart
            fig_cal = go.Figure()
            fig_cal.add_trace(go.Scatter(
                x=df_nutrition["date"],
                y=df_nutrition["calories"],
                mode="lines+markers",
                name="Actual",
                line=dict(color=COLORS["calories"], width=3),
                marker=dict(size=8),
            ))
            # Target reference line
            fig_cal.add_hline(
                y=target_calories,
                line_dash="dash",
                line_color="#888",
                annotation_text="Target",
                annotation_position="top right",
            )
            fig_cal.update_layout(
                title="Daily Calories (Last 7 Days)",
                yaxis_title="Calories (kcal)",
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#FAFAFA"},
                xaxis=dict(gridcolor="#2a2d3e"),
                yaxis=dict(gridcolor="#2a2d3e"),
            )
            st.plotly_chart(fig_cal, use_container_width=True)

        with col2:
            # Macro breakdown stacked bar chart
            fig_macro = go.Figure()
            fig_macro.add_trace(go.Bar(
                x=df_nutrition["date"], y=df_nutrition["protein_g"],
                name="Protein", marker_color=COLORS["protein"],
            ))
            fig_macro.add_trace(go.Bar(
                x=df_nutrition["date"], y=df_nutrition["carbs_g"],
                name="Carbs", marker_color=COLORS["carbs"],
            ))
            fig_macro.add_trace(go.Bar(
                x=df_nutrition["date"], y=df_nutrition["fat_g"],
                name="Fat", marker_color=COLORS["fat"],
            ))
            fig_macro.update_layout(
                title="Daily Macros (Last 7 Days)",
                barmode="stack",
                yaxis_title="Grams",
                height=350,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font={"color": "#FAFAFA"},
                xaxis=dict(gridcolor="#2a2d3e"),
                yaxis=dict(gridcolor="#2a2d3e"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig_macro, use_container_width=True)
else:
    st.info("📝 No nutrition data yet for this week. Start logging meals on the Nutrition page!")

# =====================================================
# ROW 4: WEIGHT TREND & LOGGING
# =====================================================
st.markdown("---")
st.markdown("### ⚖️ Weight Tracking")

col_weight_log, col_weight_chart = st.columns([1, 2])

with col_weight_log:
    st.markdown("**Log Today's Weight**")
    with st.form("weight_log_form"):
        new_weight = st.number_input(
            "Weight (kg)",
            value=float(profile.get("current_weight_kg", 75)),
            min_value=30.0, max_value=300.0, step=0.1,
        )
        if st.form_submit_button("📏 Log Weight", use_container_width=True):
            log_weight(st.session_state.user_id, new_weight, today)
            st.success(f"Weight logged: {new_weight} kg")
            st.rerun()

with col_weight_chart:
    # Weight trend chart (last 90 days)
    weight_data = get_weight_logs(st.session_state.user_id)
    if weight_data:
        df_weight = pd.DataFrame(weight_data)
        fig_weight = go.Figure()
        fig_weight.add_trace(go.Scatter(
            x=df_weight["log_date"],
            y=df_weight["weight_kg"],
            mode="lines+markers",
            name="Weight",
            line=dict(color=COLORS["secondary"], width=3),
            marker=dict(size=6),
            fill="tozeroy",
            fillcolor="rgba(33, 150, 243, 0.1)",
        ))
        # Goal weight reference line
        fig_weight.add_hline(
            y=profile.get("goal_weight_kg", 70),
            line_dash="dash",
            line_color=COLORS["primary"],
            annotation_text="Goal",
            annotation_position="top right",
        )
        fig_weight.update_layout(
            title="Weight Trend",
            yaxis_title="Weight (kg)",
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#FAFAFA"},
            xaxis=dict(gridcolor="#2a2d3e"),
            yaxis=dict(gridcolor="#2a2d3e"),
        )
        st.plotly_chart(fig_weight, use_container_width=True)
    else:
        st.info("📏 No weight data yet. Log your first weight entry to see trends!")

# =====================================================
# ROW 5: WORKOUT COMPLETION TRENDS
# =====================================================
if week_workouts:
    st.markdown("---")
    st.markdown("### 💪 Workout Completion (Last 7 Days)")

    # Calculate daily completion rates
    daily_completion = {}
    for log in week_workouts:
        d = log.get("workout_date", "")
        if d not in daily_completion:
            daily_completion[d] = {"total_prescribed": 0, "total_actual": 0}
        prescribed = log.get("prescribed_reps", 0)
        actual = log.get("actual_reps", [])
        if prescribed > 0 and actual:
            daily_completion[d]["total_prescribed"] += prescribed * len(actual)
            daily_completion[d]["total_actual"] += sum(actual)

    completion_data = []
    for d, vals in sorted(daily_completion.items()):
        pct = (vals["total_actual"] / vals["total_prescribed"] * 100) if vals["total_prescribed"] > 0 else 0
        completion_data.append({"date": d, "completion": min(100, pct)})

    if completion_data:
        df_completion = pd.DataFrame(completion_data)
        fig_completion = go.Figure()
        fig_completion.add_trace(go.Bar(
            x=df_completion["date"],
            y=df_completion["completion"],
            marker_color=[COLORS["primary"] if c >= 80 else COLORS["accent"] if c >= 60 else COLORS["danger"]
                          for c in df_completion["completion"]],
            text=[f"{c:.0f}%" for c in df_completion["completion"]],
            textposition="outside",
            textfont=dict(color="#FAFAFA"),
        ))
        fig_completion.add_hline(y=80, line_dash="dash", line_color="#888",
                                  annotation_text="Target (80%)")
        fig_completion.update_layout(
            yaxis_title="Completion %",
            yaxis=dict(range=[0, 110], gridcolor="#2a2d3e"),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#FAFAFA"},
            xaxis=dict(gridcolor="#2a2d3e"),
            showlegend=False,
        )
        st.plotly_chart(fig_completion, use_container_width=True)

# =====================================================
# ROW 6: PLAN ADJUSTMENT HISTORY
# =====================================================
adjustments = get_plan_adjustments(st.session_state.user_id, limit=5)
if adjustments:
    st.markdown("---")
    st.markdown("### 🤖 Recent Plan Adjustments")
    for adj in adjustments:
        with st.expander(f"📅 {adj.get('adjusted_at', '')[:10]} — {adj.get('adjustment_type', '').title()} adjustment"):
            st.markdown(f"**Reason:** {adj.get('reason', 'No reason provided')}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Previous values:**")
                st.json(adj.get("previous_values", {}))
            with col2:
                st.markdown("**New values:**")
                st.json(adj.get("new_values", {}))
