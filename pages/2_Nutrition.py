# =====================================================
# FitFuel - Nutrition Page
# =====================================================
# This page handles:
# 1. Meal logging (description, calories, macros, photo)
# 2. Today's meal list with running totals
# 3. Daily macro breakdown visualization
# 4. Meal history with optional photos
#
# The photo upload stores images as base64 data URLs
# in Supabase.
# =====================================================

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import date, timedelta
import base64
from utils.supabase_client import (
    get_user_profile,
    log_nutrition,
    get_nutrition_logs_for_date,
    get_nutrition_logs,
    delete_nutrition_log,
)
from utils.config import COLORS, MEAL_TYPES

# ----- Page Configuration -----
st.set_page_config(page_title="FitFuel — Nutrition", page_icon="🍽️", layout="wide")

# ----- Auth Check -----
if "user_id" not in st.session_state or st.session_state.user_id is None:
    st.warning("Please select or create a profile on the main page.")
    st.stop()

# ----- Load Profile -----
profile = get_user_profile(st.session_state.user_id)
if not profile:
    st.error("Profile not found.")
    st.stop()

st.markdown("## 🍽️ Nutrition Tracking")
st.markdown("Log your meals and track your daily macro targets.")

# =====================================================
# SECTION 1: LOG A MEAL
# =====================================================
st.markdown("---")
st.markdown("### 📝 Log a Meal")

with st.form("log_meal_form", clear_on_submit=True):
    col1, col2 = st.columns(2)

    with col1:
        # Meal type selector
        meal_type = st.selectbox(
            "Meal Type",
            options=MEAL_TYPES,
            format_func=lambda x: {
                "breakfast": "🌅 Breakfast",
                "lunch": "☀️ Lunch",
                "dinner": "🌙 Dinner",
                "snack": "🍎 Snack",
            }[x],
        )
        # Meal description
        description = st.text_input(
            "What did you eat?",
            placeholder="e.g., Grilled chicken with rice and salad",
        )
        # Optional photo upload
        photo = st.file_uploader(
            "Upload a meal photo (optional)",
            type=["jpg", "jpeg", "png"],
            help="Photos are stored and displayed in your meal history",
        )

    with col2:
        # Nutritional values — user enters manually
        calories = st.number_input("Calories (kcal)", min_value=0.0,
                                    max_value=5000.0, value=0.0, step=10.0)
        protein = st.number_input("Protein (g)", min_value=0.0,
                                   max_value=500.0, value=0.0, step=1.0)
        carbs = st.number_input("Carbs (g)", min_value=0.0,
                                 max_value=500.0, value=0.0, step=1.0)
        fat = st.number_input("Fat (g)", min_value=0.0,
                               max_value=500.0, value=0.0, step=1.0)

    meal_date = st.date_input("Date", value=date.today(),
                               help="Change this to log meals from previous days")

    submitted = st.form_submit_button("🍽️ Log Meal", use_container_width=True)

    if submitted:
        if not description.strip():
            st.error("Please describe what you ate.")
        elif calories == 0:
            st.error("Please enter the calorie count.")
        else:
            # Process photo if uploaded
            photo_url = None
            if photo is not None:
                # Convert uploaded photo to base64 data URL
                # This stores the image directly in the database
                photo_bytes = photo.read()
                photo_b64 = base64.b64encode(photo_bytes).decode("utf-8")
                photo_url = f"data:image/{photo.type.split('/')[-1]};base64,{photo_b64}"

            # Save to database
            log_data = {
                "user_id": st.session_state.user_id,
                "meal_date": str(meal_date),
                "meal_type": meal_type,
                "description": description.strip(),
                "calories": calories,
                "protein_g": protein,
                "carbs_g": carbs,
                "fat_g": fat,
                "photo_url": photo_url,
            }

            result = log_nutrition(log_data)
            if result:
                st.success(f"✅ {meal_type.title()} logged: {description} ({calories:.0f} kcal)")
                st.rerun()
            else:
                st.error("Failed to log meal. Please try again.")

# =====================================================
# SECTION 2: TODAY'S MEALS & PROGRESS
# =====================================================
st.markdown("---")
st.markdown("### 📊 Today's Progress")

today = date.today()
today_meals = get_nutrition_logs_for_date(st.session_state.user_id, today)

# Calculate totals
total_cal = sum(m.get("calories", 0) for m in today_meals)
total_protein = sum(m.get("protein_g", 0) for m in today_meals)
total_carbs = sum(m.get("carbs_g", 0) for m in today_meals)
total_fat = sum(m.get("fat_g", 0) for m in today_meals)

# Targets
target_cal = profile.get("daily_calories", 2000)
target_protein = profile.get("protein_g", 150)
target_carbs = profile.get("carbs_g", 250)
target_fat = profile.get("fat_g", 65)

# Progress bars with percentages
col1, col2, col3, col4 = st.columns(4)

with col1:
    pct = min(100, (total_cal / target_cal * 100) if target_cal > 0 else 0)
    st.metric("Calories", f"{total_cal:.0f} / {target_cal:.0f}")
    st.progress(pct / 100)

with col2:
    pct = min(100, (total_protein / target_protein * 100) if target_protein > 0 else 0)
    st.metric("Protein", f"{total_protein:.0f}g / {target_protein:.0f}g")
    st.progress(pct / 100)

with col3:
    pct = min(100, (total_carbs / target_carbs * 100) if target_carbs > 0 else 0)
    st.metric("Carbs", f"{total_carbs:.0f}g / {target_carbs:.0f}g")
    st.progress(pct / 100)

with col4:
    pct = min(100, (total_fat / target_fat * 100) if target_fat > 0 else 0)
    st.metric("Fat", f"{total_fat:.0f}g / {target_fat:.0f}g")
    st.progress(pct / 100)

# Macro distribution pie chart
if total_cal > 0:
    col_pie, col_meals = st.columns([1, 2])

    with col_pie:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["Protein", "Carbs", "Fat"],
            values=[total_protein * 4, total_carbs * 4, total_fat * 9],  # Convert to calories
            marker=dict(colors=[COLORS["protein"], COLORS["carbs"], COLORS["fat"]]),
            hole=0.5,
            textinfo="label+percent",
            textfont=dict(color="#FAFAFA"),
        )])
        fig_pie.update_layout(
            title="Today's Macro Split",
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#FAFAFA"},
            showlegend=False,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_meals:
        st.markdown("**Today's Meals:**")
        if today_meals:
            for meal in today_meals:
                meal_emoji = {
                    "breakfast": "🌅", "lunch": "☀️",
                    "dinner": "🌙", "snack": "🍎"
                }.get(meal.get("meal_type", ""), "🍽️")

                with st.container():
                    mcol1, mcol2, mcol3 = st.columns([3, 2, 1])
                    with mcol1:
                        st.markdown(
                            f"**{meal_emoji} {meal.get('meal_type', '').title()}:** "
                            f"{meal.get('description', '')}"
                        )
                    with mcol2:
                        st.caption(
                            f"{meal.get('calories', 0):.0f} kcal | "
                            f"P: {meal.get('protein_g', 0):.0f}g | "
                            f"C: {meal.get('carbs_g', 0):.0f}g | "
                            f"F: {meal.get('fat_g', 0):.0f}g"
                        )
                    with mcol3:
                        # Delete button for each meal
                        if st.button("🗑️", key=f"del_{meal['id']}", help="Delete this meal"):
                            delete_nutrition_log(meal["id"])
                            st.rerun()

                    # Show photo if available
                    if meal.get("photo_url"):
                        st.image(meal["photo_url"], width=200, caption="Meal photo")
        else:
            st.info("No meals logged today. Use the form above to start tracking!")
else:
    st.info("No meals logged today yet. Use the form above to log your first meal!")

# =====================================================
# SECTION 3: MEAL HISTORY (PAST 7 DAYS)
# =====================================================
st.markdown("---")
st.markdown("### 📅 Meal History (Last 7 Days)")

# Date selector for viewing past days
view_date = st.date_input(
    "View meals for date:",
    value=today,
    max_value=today,
    min_value=today - timedelta(days=30),
    key="history_date",
)

if view_date != today:
    history_meals = get_nutrition_logs_for_date(st.session_state.user_id, view_date)

    if history_meals:
        # Daily summary
        hist_cal = sum(m.get("calories", 0) for m in history_meals)
        hist_protein = sum(m.get("protein_g", 0) for m in history_meals)
        hist_carbs = sum(m.get("carbs_g", 0) for m in history_meals)
        hist_fat = sum(m.get("fat_g", 0) for m in history_meals)

        st.markdown(
            f"**{view_date.strftime('%A, %B %d')}:** "
            f"{hist_cal:.0f} kcal | "
            f"P: {hist_protein:.0f}g | C: {hist_carbs:.0f}g | F: {hist_fat:.0f}g"
        )

        for meal in history_meals:
            meal_emoji = {
                "breakfast": "🌅", "lunch": "☀️",
                "dinner": "🌙", "snack": "🍎"
            }.get(meal.get("meal_type", ""), "🍽️")

            st.markdown(
                f"{meal_emoji} **{meal.get('meal_type', '').title()}:** "
                f"{meal.get('description', '')} — "
                f"{meal.get('calories', 0):.0f} kcal"
            )
            if meal.get("photo_url"):
                st.image(meal["photo_url"], width=200)
    else:
        st.info(f"No meals logged on {view_date.strftime('%B %d, %Y')}.")

# =====================================================
# SECTION 4: WEEKLY CALORIE ADHERENCE
# =====================================================
st.markdown("---")
st.markdown("### 📈 Weekly Calorie Adherence")

week_start = today - timedelta(days=6)
week_nutrition = get_nutrition_logs(st.session_state.user_id, week_start, today)

if week_nutrition:
    # Aggregate by date
    daily_totals = {}
    for log in week_nutrition:
        d = log.get("meal_date", "")
        if d not in daily_totals:
            daily_totals[d] = 0
        daily_totals[d] += log.get("calories", 0)

    # Build chart data including days with no logs
    chart_data = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).isoformat()
        cal = daily_totals.get(d, 0)
        chart_data.append({
            "date": d,
            "calories": cal,
            "target": target_cal,
            "adherence": "On Track" if abs(cal - target_cal) < target_cal * 0.1 else
                         "Over" if cal > target_cal else "Under",
        })

    df_chart = pd.DataFrame(chart_data)

    fig = go.Figure()
    # Actual calories bars
    fig.add_trace(go.Bar(
        x=df_chart["date"],
        y=df_chart["calories"],
        name="Actual",
        marker_color=[
            COLORS["primary"] if a == "On Track" else COLORS["danger"] if a == "Over" else COLORS["accent"]
            for a in df_chart["adherence"]
        ],
        text=[f"{c:.0f}" for c in df_chart["calories"]],
        textposition="outside",
        textfont=dict(color="#FAFAFA"),
    ))
    # Target line
    fig.add_hline(y=target_cal, line_dash="dash", line_color="#888",
                  annotation_text=f"Target ({target_cal:.0f})")

    fig.update_layout(
        yaxis_title="Calories (kcal)",
        height=350,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#FAFAFA"},
        xaxis=dict(gridcolor="#2a2d3e"),
        yaxis=dict(gridcolor="#2a2d3e"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # Summary stats
    avg_cal = sum(daily_totals.values()) / max(1, len(daily_totals))
    adherence_pct = (avg_cal / target_cal * 100) if target_cal > 0 else 0
    st.info(
        f"**Weekly average:** {avg_cal:.0f} kcal/day "
        f"({adherence_pct:.0f}% of target) | "
        f"Logged {len(daily_totals)} of 7 days"
    )
else:
    st.info("Start logging meals to see your weekly trends!")
