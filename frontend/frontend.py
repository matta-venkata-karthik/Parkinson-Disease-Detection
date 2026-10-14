import base64
import time
from pathlib import Path

import requests
import streamlit as st

from utils.api_client import (
    get_analytics,
    get_patient_history,
    get_reports,
    get_api_url,
)

from utils.session import initialize_session


# ==========================================================
# PROJECT PATHS
# ==========================================================

FRONTEND_DIR = Path(__file__).resolve().parent
ASSETS_DIR = FRONTEND_DIR / "assets"
IMAGES_DIR = ASSETS_DIR / "images"

FAVICON_PATH = ASSETS_DIR / "favicon.ico"
LOGO_PATH = ASSETS_DIR / "logo.png"
FRONTEND_BANNER = IMAGES_DIR / "frontend_banner.png"


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="Parkinson Disease Detection Agent",
    page_icon=str(FAVICON_PATH) if FAVICON_PATH.exists() else "🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ==========================================================
# LOGO
# ==========================================================

if LOGO_PATH.exists():
    try:
        st.logo(str(LOGO_PATH), size="large")
    except Exception:
        pass


# ==========================================================
# INITIALIZE SESSION
# ==========================================================

initialize_session()


# ==========================================================
# BACKEND CONNECTION
# ==========================================================

def check_backend_connection(
    max_attempts=4,
    force_check=False,
):
    """
    Check the Render FastAPI backend.

    Makes several attempts to allow a sleeping Render
    service time to wake up. Stores the result in the
    Streamlit session to avoid checking on every rerun.
    """

    if (
        not force_check
        and st.session_state.get("backend_checked", False)
    ):
        return st.session_state.get(
            "backend_available",
            False,
        )

    st.session_state["backend_checked"] = True
    st.session_state["backend_available"] = False

    base_url = get_api_url().rstrip("/")
    health_url = f"{base_url}/health"

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                health_url,
                timeout=(10, 30),
            )

            if response.ok:
                st.session_state["backend_available"] = True
                st.session_state["backend_last_error"] = None
                return True

            error_message = (
                f"Health endpoint returned HTTP "
                f"{response.status_code}"
            )

        except requests.exceptions.Timeout:
            error_message = "Backend health check timed out."

        except requests.exceptions.ConnectionError:
            error_message = "Could not connect to the backend."

        except requests.exceptions.RequestException as exc:
            error_message = str(exc)

        except Exception as exc:
            error_message = str(exc)

        st.session_state["backend_last_error"] = error_message

        if attempt < max_attempts:
            time.sleep(attempt * 2)

    return False


# ==========================================================
# CONNECT TO BACKEND ON STARTUP
# ==========================================================

# The retry button is shown before the connection check so
# a user can initiate another attempt after a failure.

force_backend_check = False

if (
    st.session_state.get("backend_checked", False)
    and not st.session_state.get("backend_available", False)
):
    st.warning(
        "The backend has not responded yet. "
        "Render may still be starting the service."
    )

    if st.button(
        "🔄 Retry Backend Connection",
        key="retry_backend_startup",
    ):
        force_backend_check = True

if (
    not st.session_state.get("backend_checked", False)
    or force_backend_check
):
    with st.spinner("🔄 Connecting to backend..."):
        backend_available = check_backend_connection(
            max_attempts=4,
            force_check=force_backend_check,
        )
else:
    backend_available = st.session_state.get(
        "backend_available",
        False,
    )


# ==========================================================
# RESPONSIVE FRONTEND BANNER
# ==========================================================

if FRONTEND_BANNER.exists():
    banner_base64 = base64.b64encode(
        FRONTEND_BANNER.read_bytes()
    ).decode("utf-8")

    st.html(
        f"""
        <style>
        .frontend-banner-wrapper {{
            width: 100%;
            margin: 0 0 1rem 0;
            padding: 0;
        }}

        .frontend-banner {{
            width: 100%;
            max-width: 1600px;
            height: auto;
            display: block;
            margin: 0 auto;
            object-fit: contain;
            border-radius: 12px;
        }}

        @media (max-width: 768px) {{
            .frontend-banner {{
                width: 100%;
            }}
        }}

        @media (min-width: 769px) {{
            .frontend-banner {{
                width: 100%;
                max-width: 1600px;
            }}
        }}
        </style>

        <div class="frontend-banner-wrapper">
            <img
                class="frontend-banner"
                src="data:image/png;base64,{banner_base64}"
                alt="Parkinson Disease Detection Agent"
            >
        </div>
        """
    )
else:
    st.warning("Frontend banner image was not found.")


# ==========================================================
# HELPER FUNCTIONS
# ==========================================================

def safe_list(value):
    """Convert common API responses into a list."""

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        result = (
            value.get("data")
            or value.get("items")
            or value.get("records")
            or value.get("predictions")
            or value.get("history")
            or value.get("reports")
            or []
        )

        return result if isinstance(result, list) else []

    return []


def get_metric(data, keys, default=0):
    """Safely retrieve a numeric metric."""

    if not isinstance(data, dict):
        return default

    for key in keys:
        value = data.get(key)

        if value is not None:
            try:
                return int(float(value))
            except (TypeError, ValueError, OverflowError):
                return default

    return default


# ==========================================================
# HEADER
# ==========================================================

st.title("🧠 Parkinson Disease Detection Agent")

st.write(
    """
AI-assisted Parkinson's disease screening,
patient management, prediction history,
analytics, reports, and health assistance.
"""
)

st.divider()


# ==========================================================
# SESSION / USER INFORMATION
# ==========================================================

# Preserve the existing application's session behavior.
# Replace this default authentication assignment with your
# real login flow if authentication is handled elsewhere.

st.session_state["logged_in"] = True

username = st.session_state.get("username", "User")
role = st.session_state.get("role", "User")

st.success(f"Welcome, {username}")


# ==========================================================
# SIDEBAR
# ==========================================================

with st.sidebar:
    st.markdown(
        '<div style="text-align:center; font-size:18px; '
        'font-weight:700;">Parkinson Disease Detection Agent</div>',
        unsafe_allow_html=True,
    )

    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=170)
    else:
        st.markdown(
            '<div style="text-align:center; font-size:42px;">🧠</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    if backend_available:
        st.success("🟢 Backend Connected")
    else:
        st.error("🔴 Backend Unavailable")

    st.caption(f"Backend: {get_api_url()}")

    if not backend_available:
        st.caption(
            "The backend may be waking up or temporarily unavailable."
        )

    st.divider()

    st.markdown("### 🧭 Quick Navigation")
    st.caption(
        "Use the navigation menu to open the different sections "
        "of the application."
    )

    st.divider()
    st.caption(f"👤 User: {username}")
    st.caption(f"🔐 Role: {role}")


# ==========================================================
# LOAD DASHBOARD DATA
# ==========================================================

analytics = {}
history = []
reports = []

analytics_loaded = False
history_loaded = False
reports_loaded = False

if backend_available:
    with st.spinner("Loading dashboard..."):
        try:
            analytics = get_analytics()
            analytics_loaded = analytics is not None
        except Exception:
            analytics = {}

        try:
            history = get_patient_history()
            history_loaded = history is not None
        except Exception:
            history = []

        try:
            reports = get_reports()
            reports_loaded = reports is not None
        except Exception:
            reports = []
else:
    st.warning(
        "⚠️ The backend is currently unavailable. "
        "Dashboard data may be empty until the backend responds."
    )


# ==========================================================
# NORMALIZE DATA
# ==========================================================

history_list = safe_list(history)
reports_list = safe_list(reports)

if not isinstance(analytics, dict):
    analytics = {}

dashboard_data = analytics.get("dashboard", {})
if not isinstance(dashboard_data, dict):
    dashboard_data = {}

prediction_data = analytics.get("prediction", {})
if not isinstance(prediction_data, dict):
    prediction_data = {}


# ==========================================================
# CALCULATE DASHBOARD METRICS
# ==========================================================

history_prediction_count = len(history_list)

analytics_prediction_count = get_metric(
    prediction_data,
    ["total_predictions"],
    0,
)

analytics_dashboard_predictions = get_metric(
    dashboard_data,
    ["total_predictions"],
    0,
)

total_predictions = (
    history_prediction_count
    or analytics_prediction_count
    or analytics_dashboard_predictions
)

total_reports = len(reports_list)

if total_reports == 0:
    total_reports = get_metric(
        dashboard_data,
        ["total_reports"],
        0,
    )

total_patients = get_metric(
    dashboard_data,
    ["total_patients"],
    0,
)

if total_patients == 0:
    patient_data = analytics.get("patient", {})

    if isinstance(patient_data, dict):
        total_patients = get_metric(
            patient_data,
            ["total_patients", "count"],
            0,
        )

high_risk = get_metric(
    dashboard_data,
    ["high_risk_cases", "high_risk"],
    0,
)

medium_risk = get_metric(
    dashboard_data,
    ["medium_risk_cases", "medium_risk"],
    0,
)

low_risk = get_metric(
    dashboard_data,
    ["low_risk_cases", "low_risk"],
    0,
)


# ==========================================================
# DASHBOARD OVERVIEW
# ==========================================================

st.subheader("📊 Dashboard Overview")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("👤 Patients", total_patients)

with col2:
    st.metric("🧠 Predictions", total_predictions)

with col3:
    st.metric("📄 Reports", total_reports)

with col4:
    st.metric("⚠️ High Risk", high_risk)

st.divider()


# ==========================================================
# RISK OVERVIEW
# ==========================================================

st.subheader("⚠️ Risk Overview")

risk_col1, risk_col2, risk_col3 = st.columns(3)

with risk_col1:
    st.metric("🔴 High Risk", high_risk)

with risk_col2:
    st.metric("🟠 Medium Risk", medium_risk)

with risk_col3:
    st.metric("🟢 Low Risk", low_risk)

st.divider()


# ==========================================================
# QUICK ACTIONS
# ==========================================================

st.subheader("🚀 Quick Actions")

action1, action2, action3, action4 = st.columns(4)

with action1:
    if st.button("🩺 New Prediction", use_container_width=True):
        st.switch_page("pages/2_Prediction.py")

with action2:
    if st.button("📋 Patient History", use_container_width=True):
        st.switch_page("pages/3_Patient_History.py")

with action3:
    if st.button("📄 Reports", use_container_width=True):
        st.switch_page("pages/5_Reports.py")

with action4:
    if st.button("📊 Analytics", use_container_width=True):
        st.switch_page("pages/6_Analytics.py")

st.divider()


# ==========================================================
# RECENT PREDICTIONS
# ==========================================================

st.subheader("📝 Recent Predictions")

if history_list:
    recent = history_list[:5]
    rows = []

    for item in recent:
        if not isinstance(item, dict):
            continue

        patient_name = (
            item.get("patient_name")
            or item.get("name")
            or "Unknown"
        )

        diagnosis = (
            item.get("diagnosis")
            or item.get("prediction")
            or item.get("prediction_result")
            or "Unknown"
        )

        risk_level = (
            item.get("risk_level")
            or item.get("risk_category")
            or "Unknown"
        )

        risk_score = item.get("risk_score")

        created_at = (
            item.get("created_at")
            or item.get("timestamp")
            or item.get("date")
            or "N/A"
        )

        formatted_risk_score = "N/A"

        if risk_score is not None:
            try:
                formatted_risk_score = f"{float(risk_score):.2f}%"
            except (TypeError, ValueError):
                formatted_risk_score = str(risk_score)

        rows.append(
            {
                "Patient": patient_name,
                "Diagnosis": diagnosis,
                "Risk Level": risk_level,
                "Risk Score": formatted_risk_score,
                "Date": created_at,
            }
        )

    if rows:
        st.dataframe(
            rows,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No prediction records available.")
else:
    st.info("No prediction history available yet.")

st.divider()


# ==========================================================
# SYSTEM STATUS
# ==========================================================

st.subheader("💻 System Status")

status1, status2, status3, status4 = st.columns(4)

with status1:
    if backend_available and analytics_loaded:
        st.success("🟢 Analytics")
    else:
        st.error("🔴 Analytics")

with status2:
    if backend_available and history_loaded:
        st.success("🟢 Predictions")
    else:
        st.error("🔴 Predictions")

with status3:
    if backend_available and reports_loaded:
        st.success("🟢 Reports")
    else:
        st.error("🔴 Reports")

with status4:
    if backend_available:
        st.success("🟢 AI Assistant")
    else:
        st.error("🔴 AI Assistant")

st.divider()


# ==========================================================
# ABOUT
# ==========================================================

st.subheader("ℹ️ About")

st.markdown(
    """
### Parkinson Disease Detection Agent

This platform provides:

- 🩺 AI-assisted Parkinson's screening
- 🎙️ Voice-based analysis
- 👤 Patient management
- 📋 Prediction history
- 📄 Medical report management
- 📊 Analytics
- 🤖 AI Health Assistant
- 🛠️ Administrator management

**Important:** Prediction results are AI-assisted screening
information and should not be treated as a medical diagnosis.
"""
)


# ==========================================================
# MEDICAL DISCLAIMER
# ==========================================================

st.warning(
    """
⚠️ **Medical Disclaimer**

This application provides educational and AI-assisted
screening information.

Prediction results are not a diagnosis and should not replace
professional medical advice, diagnosis, or treatment.

If you have persistent or concerning symptoms, consult a
qualified healthcare professional.
"""
)

st.divider()


# ==========================================================
# FOOTER
# ==========================================================

st.caption(
    "© 2026 Parkinson Disease Detection Agent | "
    "Streamlit + FastAPI + Scikit-learn"
)
```
