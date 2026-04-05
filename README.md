# 💪 FitFuel — Your Adaptive Fitness Coach

FitFuel is an intelligent, adaptive fitness web application that unifies **nutrition tracking** and **workout planning** into a single platform. Unlike conventional fitness apps that treat diet and exercise as separate concerns, FitFuel recognizes that these are deeply interconnected — and uses **machine learning** to continuously optimize both based on the user's real-world progress.

Built with [Streamlit](https://streamlit.io/), [Supabase](https://supabase.com/), and [scikit-learn](https://scikit-learn.org/).

> **Live Demo:** [fitfuel.streamlit.app](https://fitfuel-demo.streamlit.app)

---

## The Problem

Most fitness apps fall into one of two categories: workout trackers or nutrition trackers. Users are forced to juggle separate tools that don't communicate with each other, even though nutrition and training are fundamentally linked. A workout plan without aligned nutrition targets leads to stalled progress, and a diet plan that ignores training load leads to under- or over-fueling.

Additionally, most plans are static. They don't adapt when a user consistently struggles with a prescribed volume, over-eats their calorie target, or changes their schedule. This rigidity is one of the primary reasons people abandon their fitness routines.

**FitFuel solves this** by combining both domains into one adaptive system that learns from the user's logged data and explicit feedback to continuously refine its recommendations.

---

## Features

### User Onboarding & Profile Management
New users complete a comprehensive survey covering body metrics, activity level, training experience, goals, equipment access, and physical limitations. This data feeds directly into the plan generation pipeline. Returning users can update their profile at any time, which triggers automatic recalculation of all targets.

### Nutrition Plan Generation
The app calculates each user's Basal Metabolic Rate (BMR) using the revised Harris-Benedict equation, derives Total Daily Energy Expenditure (TDEE) via an activity multiplier, and applies a goal-based calorie adjustment (15% deficit for fat loss, 15% surplus for muscle gain, or maintenance). Macronutrient targets (protein, carbs, fat) are then split according to goal-specific ratios grounded in exercise science literature.

### Workout Plan Generation
A rule-based engine generates personalized weekly training splits (Full Body, Upper/Lower, or Push/Pull/Legs) based on the user's preferred training frequency, experience level, available equipment, and physical limitations. Each exercise is filtered through five criteria — muscle group, equipment availability, limitation conflicts, goal suitability, and difficulty level — before being prescribed with experience-adjusted sets and reps.

### Daily Tracking
- **Nutrition Tracking:** Users log meals with a description, calorie count, macronutrient breakdown, and an optional photo. A real-time dashboard shows progress toward daily targets via interactive gauge charts.
- **Workout Tracking:** Users view their daily prescribed workout and log actual reps completed per set for each exercise. Completion percentage is calculated and visualized to provide immediate feedback.

### Adaptive Machine Learning
After accumulating sufficient data (≥ 7 days), FitFuel's ML pipeline analyzes the user's workout completion rates, calorie adherence, macronutrient consistency, and weight trajectory. A Decision Tree Regressor (scikit-learn) is trained on the user's own historical data to identify trends and predict optimal adjustments. The system modifies calorie targets, macronutrient splits, and training volume — then logs every change with a human-readable explanation for full transparency.

When insufficient data is available (cold start), the system falls back to rule-based heuristics derived from exercise science principles.

### Feedback-Driven Adjustment
Users can submit weekly feedback surveys indicating workout difficulty, nutrition satisfaction, preferred training days, focus areas, and any new physical limitations. This feedback is combined with the ML analysis to produce holistic plan adjustments that respect both data-driven insights and subjective user experience.

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit | Interactive web UI with multi-page navigation |
| Database | Supabase (PostgreSQL) | User profiles, workout plans, nutrition/workout logs, feedback, adjustment history |
| Visualization | Plotly | Gauge charts, trend lines, stacked bars, pie charts, progression tracking |
| Machine Learning | scikit-learn | Decision Tree Regressor for adaptive plan optimization |
| Data Processing | Pandas, NumPy | Feature engineering and data aggregation |
| Image Handling | Pillow | Meal photo processing |

---

## Project Structure

```
fitfuel/
├── app.py                        # Main entry point — onboarding, profile, feedback, ML adaptation
├── pages/
│   ├── 1_Dashboard.py            # Daily progress gauges, trend charts, weight tracking
│   ├── 2_Nutrition.py            # Meal logging, macro breakdown, calorie adherence charts
│   └── 3_Workout.py              # Daily workout view, rep tracking, strength progression
├── utils/
│   ├── config.py                 # Exercise database, constants, Supabase credentials
│   ├── calculations.py           # BMR, TDEE, and macronutrient calculations
│   ├── supabase_client.py        # All database read/write operations
│   ├── workout_engine.py         # Rule-based workout plan generation
│   └── ml_model.py               # Adaptive ML model (Decision Tree pipeline)
├── requirements.txt              # Python dependencies
└── .streamlit/
    └── config.toml               # Dark theme configuration
```

---

## Database Schema

FitFuel uses 7 tables in Supabase:

| Table | Purpose |
|-------|---------|
| `user_profiles` | Onboarding data, body metrics, calculated nutrition targets |
| `workout_plans` | Weekly training plans stored as JSON, with active/inactive flagging |
| `workout_logs` | Per-exercise performance logs with actual reps per set |
| `nutrition_logs` | Meal entries with calories, macros, and optional photo URLs |
| `weight_logs` | Weight measurements over time for trend analysis |
| `user_feedback` | Weekly feedback survey responses with processing flags |
| `plan_adjustments` | Audit trail of ML-driven plan changes with before/after values |

---

## Machine Learning Approach

The adaptive system uses a **Decision Tree Regressor** trained on 8 engineered features derived from the user's daily logs:

1. **Workout completion rate** — average across all exercises per day
2. **Calorie adherence ratio** — actual intake vs. target
3. **Protein adherence ratio**
4. **Carb adherence ratio**
5. **Fat adherence ratio**
6. **Weight change** — delta from previous measurement
7. **Day of week** — captures weekly behavioral patterns
8. **Days since program start** — captures long-term trends

The target variable is a composite **progress score** (0.0–1.0) that weighs workout performance (40%), nutrition adherence (35%), and goal-aligned weight trajectory (25%). The model is trained with controlled hyperparameters (`max_depth=4`, `min_samples_split=3`) to prevent overfitting on small datasets.

Feature importances from the trained model are used to determine which aspects of the user's behavior most impact their progress, enabling targeted recommendations.

---

## Installation & Local Development

### Prerequisites
- Python 3.9+
- A Supabase project (free tier works)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/fitfuel.git
   cd fitfuel
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Supabase:**
   - Create a project at [supabase.com](https://supabase.com)
   - Run the SQL schema (provided during development) in the SQL Editor
   - Update `SUPABASE_URL` and `SUPABASE_KEY` in `utils/config.py`

4. **Run the app:**
   ```bash
   streamlit run app.py
   ```

The app will open at `http://localhost:8501`.

---

## How It Works — User Flow

1. **Onboarding** → User fills out the profile survey → BMR/TDEE/macros are calculated → A personalized workout plan is generated → Everything is saved to Supabase.

2. **Daily Use** → User logs meals on the Nutrition page and tracks workout performance on the Workout page → Dashboard shows real-time progress with interactive charts.

3. **Weekly Adaptation** → User submits feedback on the Profile page → Clicks "Adapt My Plan" → The ML model analyzes all logged data + feedback → Recommends specific adjustments → User reviews and applies changes → A new workout plan is generated if needed.

4. **Continuous Improvement** → As more data accumulates, the ML model becomes more accurate at predicting what adjustments will drive progress → Plans evolve with the user.

---

## License

This project was built as part of a university computer science course. All code is original.
