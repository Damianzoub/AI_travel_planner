from typing import Dict , List, Any
import json 
import time 
import logging
import streamlit as st 
from datetime import date , timedelta

import pandas as pd 
import plotly.express as px 

from google.adk.agents import Agent 
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from agents.orchestrator.orchestrator_adk import orchestrator,TripRequest
#debugging tool
logging.basicConfig(level=logging.INFO)

st.set_page_config(
    page_title="TravelAIgent",
    layout='wide',
    initial_sidebar_state='expanded'
)

#TODO: Include orchestrator agent here 


INTEREST_OPTIONS = [
    "food",
    "culture",
    "nightlife",
    "nature",
    "shopping",
    "history",
    "architecture",
    "beaches",
    "museums",
    "local markets",
]

PACE_OPTIONS = ["slow", "balanced", "fast"]

#session state
def init_session_state()->None:
    defaults = {
        "current_plan": None,
        "trip_history": [],
        "progress_log": [],
        "dark_cards":True,
        "selected_page": "Plan a Trip",
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key]=value

#mock data
def build_mock_plan(request: Dict[str, Any]) -> Dict[str, Any]:
    destination = request["destination"]
    start_date = request["start_date"]
    budget = request["budget"]

    itinerary = [
        {
            "day": 1,
            "title": f"Arrival and old town walk in {destination}",
            "activities": [
                {"time": "10:00", "name": "Check-in", "type": "hotel"},
                {"time": "12:00", "name": "Local lunch spot", "type": "food"},
                {"time": "15:00", "name": "Historic center walk", "type": "culture"},
                {"time": "20:00", "name": "Rooftop dinner", "type": "food"},
            ],
        },
        {
            "day": 2,
            "title": "Museums, market, and sunset",
            "activities": [
                {"time": "09:30", "name": "City museum", "type": "museum"},
                {"time": "13:00", "name": "Street food market", "type": "food"},
                {"time": "16:00", "name": "Neighborhood exploration", "type": "walk"},
                {"time": "19:30", "name": "Sunset viewpoint", "type": "nature"},
            ],
        },
        {
            "day": 3,
            "title": "Free morning and departure",
            "activities": [
                {"time": "10:00", "name": "Coffee and souvenir shopping", "type": "shopping"},
                {"time": "14:00", "name": "Airport transfer", "type": "transport"},
            ],
        },
    ]

    booking_options = {
        "flights": [
            {"label": "Aegean Airlines", "price": 235, "details": "Round trip · 1 stop"},
            {"label": "Lufthansa", "price": 282, "details": "Round trip · 1 stop"},
        ],
        "hotels": [
            {"label": "CityNest Hotel", "price": 420, "details": "3 nights · 3-star · city center"},
            {"label": "Urban Stay Suites", "price": 560, "details": "3 nights · 4-star · breakfast included"},
        ],
    }

    budget_breakdown = pd.DataFrame(
        {
            "category": ["Flights", "Hotel", "Food", "Transit", "Activities"],
            "amount": [260, 450, 180, 60, 120],
        }
    )

    total_cost = int(budget_breakdown["amount"].sum())
    critique = {
        "overall_score": 8.1,
        "revision_count": 1,
        "issues": [
            "Hotel choice was revised once to improve budget fit.",
            "Day 2 was shortened to keep the pace balanced.",
        ],
        "scores": pd.DataFrame(
            {
                "dimension": [
                    "Budget fit",
                    "Pace",
                    "Preference alignment",
                    "Practicality",
                    "Diversity",
                ],
                "score": [8.5, 7.8, 8.7, 7.9, 7.5],
            }
        ),
    }

    return {
        "request": request,
        "created_at": str(date.today()),
        "summary": {
            "destination": destination,
            "dates": f"{start_date} → {request['end_date']}",
            "budget": budget,
            "estimated_total": total_cost,
            "within_budget": total_cost <= budget,
        },
        "itinerary": itinerary,
        "booking_options": booking_options,
        "budget_breakdown": budget_breakdown,
        "critique": critique,
        # These are placeholder coordinates so we can wire the map UI now.
        "map_points": pd.DataFrame(
            {
                "name": ["Hotel", "Old Town", "Museum", "Market", "Viewpoint"],
                "lat": [41.3854, 41.3879, 41.4036, 41.3821, 41.3809],
                "lon": [2.1734, 2.1699, 2.1744, 2.1715, 2.1228],
                "day": [1, 1, 2, 2, 2],
            }
        ),
    }

#styling helpers
def card(title:str,value:str,help_text:str|None = None) -> None:
    with st.container(border=True):
        st.caption(title)
        st.subheader(value)
        if help_text:
            st.write(help_text)


#sidebar
def render_sidebar()->str:
    st.sidebar.title("TravelAgent")
    
    page = st.sidebar.radio("Pages",
                            ["Plan a Trip","Saved Trips","Settings"],
                            index=["Plan a Trip","Saved Trips","Settings"].index(st.session_state.selected_page))
    
    st.session_state.selected_page = page
    st.sidebar.divider()
    st.sidebar.subheader("UI controls")
    st.session_state.dark_cards = st.sidebar.toggle("Card borders", value=st.session_state.dark_cards)
    st.sidebar.selectbox("Density", ["Comfortable", "Compact"], index=0)
    st.sidebar.selectbox("Map style", ["Default", "Light", "Minimal"], index=0)

    st.sidebar.divider()
    st.sidebar.info("UI Design For now")
    return page

#plan page
def render_trip_form() -> Dict[str,Any] | None:
    st.title("Plan a Trip")
    
    top_left, top_right = st.columns([1.4,1])
    with top_left:
        with st.container(border=True):
            st.subheader("Trip Details")

            with st.form("trip_form"):
                c1,c2= st.columns(2)
                
                with c1:
                    destination = st.text_input("Destination", placeholder="Barcelona, Spain")
                    start_date = st.date_input("Start date", value=date.today() + timedelta(days=14))
                    budget = st.number_input("Budget (€)", min_value=100, value=1500, step=50)
                    interests = st.multiselect("Interests", INTEREST_OPTIONS, default=["food", "culture"])

                with c2:
                    trip_length = st.slider("Trip length (days)", 2, 14, 4)
                    end_date = start_date + timedelta(days=trip_length - 1)
                    st.text_input("End date", value=str(end_date), disabled=True)
                    pace = st.select_slider("Pace", options=PACE_OPTIONS, value="balanced")
                    travelers = st.selectbox("Travelers", ["Solo", "Couple", "Friends", "Family"], index=1)

                constraints = st.text_area(
                    "Preferences or constraints",
                    placeholder="Vegetarian food, central hotel, no early flights, near metro...",
                )

                submitted = st.form_submit_button("Preview Trip Layout",use_container_width=True)
    with top_right:
        with st.container(border=True):
            st.subheader("Quick preview")
            st.write("See how the final result area will look before connecting real backend logic.")
            st.markdown(
                """
                **Sections included**

                - Overview cards
                - Day-by-day itinerary
                - Flights and hotels
                - Budget chart
                - Map preview
                """
            )

        with st.container(border=True):
            st.subheader("Suggested presets")
            for preset in ["Weekend city break", "Food-focused trip", "Relaxed cultural escape"]:
                st.button(preset, use_container_width=True, key=f"preset_{preset}")
    if not submitted:
        return None
    if not destination.strip():
        st.error("Please enter a destination")
        return None 
    return {
        "destination": destination.strip(),
        "start_date": str(start_date),
        "end_date": str(end_date),
        "budget": int(budget),
        "interests": interests,
        "pace": pace,
        "travelers": travelers,
        "constraints": constraints.strip(),
        "trip_length": int(trip_length),
    }


def render_header_summary(plan:Dict[str,Any])-> None:
    summary = plan["summary"]

    st.divider()
    st.subheader("Trip preview")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        card("Destination", summary["destination"])
    with c2:
        card("Dates", summary["dates"])
    with c3:
        card("Budget", f"€{summary['budget']}")
    with c4:
        card("Estimated total", f"€{summary['estimated_total']}")

    st.write("")
    info_col, badge_col = st.columns([3, 1])
    with info_col:
        with st.container(border=True):
            st.subheader("Highlights")
            for item in plan["highlights"]:
                st.write(f"• {item}")
    with badge_col:
        with st.container(border=True):
            st.subheader("Budget status")
            st.success("Within budget" if summary["within_budget"] else "Over budget")


def render_itinerary(plan:Dict[str,Any])->None:
    left ,right= st.columns([1.5,1])
    with left:
        st.subheader("Itinerary")
        for day in plan["itinerary"]:
            with st.expander(f"Day {day['day']} — {day['title']}", expanded=True):
                for activity in day["activities"]:
                    a, b = st.columns([1, 5])
                    a.write(activity["time"])
                    b.write(f"**{activity['name']}**  ")
                    b.caption(activity["tag"])
    with right:
        st.subheader("Map")
        st.map(plan['map_points'],latitude='lat',longitude='lon')

def render_travel_options(plan:Dict[str,Any])->None:
    fcol,hcol = st.columns(2)

    with fcol:
        st.subheader("Flight options")
        for item in plan['flights']:
            with st.container(border=True):
                top,price= st.columns([3,1])
                top.write(f"**{item['label']}")
                price.write(f"€{item['price']}")
                st.caption(item['details'])
                st.button("View Option",key=f"flight_{item['label']}",use_container_width=True)
    with hcol:
        st.subheader("Hotel Options")
        for item in plan['hotels']:
            with st.container(border=True):
                top,price = st.columns([3,1])
                top.write(f"**{item['label']}**")
                price.write(f"€{item['price']}")
                st.caption(item["details"])
                st.button("View option", key=f"hotel_{item['label']}", use_container_width=True)

def render_budget(plan:Dict[str,Any])->None:
    df = plan['budget_breakdown']
    left,right = st.columns([1.1,1])
    
    with left:
        st.subheader("Budget breakdown")
        fig = px.pie(df, names="category", values="amount", hole=0.55)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Cost table")
        st.dataframe(df, use_container_width=True, hide_index=True)



def render_saved_trips()->None:
     st.title("Saved Trips")

     if not st.session_state.trip_history:
         st.info("No saved trips yet. Create one from the main page")
         return 
     
     cols = st.columns(2)
     for idx,trip in enumerate(reversed(st.session_state.trip_history)):
         col = cols[idx%2]
         with col:
             with st.container(border=True):
                st.subheader(trip["summary"]["destination"])
                st.caption(trip["summary"]["dates"])
                st.write(f"Budget: €{trip['summary']['budget']}")
                st.write(f"Estimated total: €{trip['summary']['estimated_total']}")
                if st.button("Open preview", key=f"open_trip_{idx}", use_container_width=True):
                    st.session_state.current_plan = trip
                    st.success("Preview loaded.")
     if st.session_state.current_plan is not None:
         render_results(st.session_state.current_plan)

def render_results(plan:Dict[str,Any])->None:
    render_header_summary(plan)
    tab1, tab2, tab3 = st.tabs(["Itinerary", "Travel options", "Budget"])

    with tab1:
        render_itinerary(plan)
    with tab2:
        render_travel_options(plan)
    with tab3:
        render_budget(plan)

def render_settings()->None:
    st.title("Settings")
    c1,c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("Appearance")
            st.selectbox("Accent style", ["Default", "Minimal", "Travel card"])
            st.selectbox("Layout density", ["Comfortable", "Compact"])
            st.checkbox("Show bordered containers", value=True)
            st.checkbox("Keep map visible next to itinerary", value=True)

    with c2:
        with st.container(border=True):
            st.subheader("Experience")
            st.selectbox("Default landing page", ["Plan a Trip", "Saved Trips", "Settings"])
            st.selectbox("Budget chart style", ["Donut", "Bar"])
            st.selectbox("Trip card style", ["Grid", "List"])
            st.checkbox("Show suggested presets", value=True)

    st.write("")
    with st.container(border=True):
        st.subheader("Design note")
        st.write(
            "This app version is intentionally UI-only. The goal is to design the full travel planning experience "
            "before wiring any backend logic, APIs, or multi-agent orchestration."
        )


def main() -> None:
    init_session_state()
    page = render_sidebar()

    if page == "Plan a Trip":
        request = render_trip_form()
        if request is not None:
            plan = build_mock_plan(request)
            st.session_state.current_plan = plan 
            st.session_state.trip_history.append(plan)
        
        if st.session_state.current_plan is not None:
            render_results(st.session_state.current_plan)
    elif page=="Saved Trips" :
        render_saved_trips()
    else:
        render_settings()


if __name__ == "__main__":
    main()