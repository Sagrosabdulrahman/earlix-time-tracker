import streamlit as st

#Hochladen der UnterCodes
from supabase import create_client
from modules.admin_overview import show_admin_overview_page
from modules.milestones import show_milestones_page
from modules.hours import show_hours
from modules.dashboard import show_dashboard

import pandas as pd
from datetime import date

def dataframe_to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def dataframe_to_excel_bytes(df, sheet_name="Report"):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    output.seek(0)
    return output.getvalue()

from datetime import date
from io import BytesIO

st.set_page_config(
    page_title="Earlix Zeiterfassung V2",
    page_icon="assets/logo.png",
    layout="wide"
)


col1, col2 = st.columns([4, 1])


st.sidebar.markdown(
    "<div style='background-color: #54A4F5; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold;'>Produktiv</div>",
    unsafe_allow_html=True
)

###st.sidebar.markdown(
###    "<div style='background-color: #287233; color: white; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold;'>Entwicklung</div>",
###    unsafe_allow_html=True
###)



with col1:
    st.title("Earlix Zeiterfassung V2")

with col2:
    st.image("assets/logo.png", width=120)




from services.supabase_client import get_supabase

supabase = get_supabase()


# Session-State vorbereiten
if "user" not in st.session_state:
    st.session_state.user = None

if "access_token" not in st.session_state:
    st.session_state.access_token = None

if "refresh_token" not in st.session_state:
    st.session_state.refresh_token = None

# Wenn Tokens vorhanden sind, Session im Supabase-Client wiederherstellen
if st.session_state.access_token and st.session_state.refresh_token:
    try:
        supabase.auth.set_session(
            st.session_state.access_token,
            st.session_state.refresh_token
        )
    except Exception as e:
        st.warning(f"Session konnte nicht wiederhergestellt werden: {e}")
        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None

# LOGIN -----------------------------------------------
if st.session_state.user is None:
    st.subheader("Login")

    email = st.text_input("E-Mail")
    password = st.text_input("Passwort", type="password")

    if st.button("Einloggen"):
        try:
            result = supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            # Ganz wichtig: komplette Session speichern
            st.session_state.user = result.user
            st.session_state.access_token = result.session.access_token
            st.session_state.refresh_token = result.session.refresh_token

            st.success("Login erfolgreich")
            st.rerun()

        except Exception as e:
            st.error(f"Login fehlgeschlagen: {e}")

else:
    #Einloggenbereich---------------------------------------------------------
    st.success(f"Eingeloggt als: {st.session_state.user.email}")
    

    profile_response = supabase.table("profiles") \
        .select("*") \
        .eq("auth_user_id", st.session_state.user.id) \
        .execute()


    if not profile_response.data:
        st.error("Kein Profil gefunden oder RLS blockiert den Zugriff.")
        st.stop()

    profile = profile_response.data[0]
    role_value = str(profile.get("role", "")).strip().lower()
    is_admin = role_value == "admin"

    menu_options = [
        "Stunden eintragen",
        "Meine Stunden",
        "Dashboard"
    ]

    if is_admin:
        menu_options.append("Admin-Übersicht")
        menu_options.append("Meilensteine verwalten")

    menu = st.sidebar.radio("Navigation", menu_options)


    
    

    all_milestones_response = supabase.table("milestones") \
        .select("id, title, is_active") \
        .execute()
    
    all_milestones = all_milestones_response.data or []
    
    if not all_milestones:
        st.error("Keine Meilensteine gefunden.")
        st.stop()

    # Nur offene Meilensteine für neue Stundeneinträge
    active_milestones = [m for m in all_milestones if m["is_active"]]
    
    # Dropdown für neue Einträge
    milestone_map_active = {m["title"]: m["id"] for m in active_milestones}
    
    # Mapping für Historie / Anzeige / Admin
    reverse_milestone_map_all = {m["id"]: m["title"] for m in all_milestones}

    
    today = date.today()
    selected_month = st.sidebar.selectbox(
        "Monat wählen",
        options=list(range(1, 13)),
        index=today.month - 1
    )
    
    selected_year = st.sidebar.number_input(
        "Jahr",
        min_value=2025,
        max_value=2035,
        value=today.year,
        step=1
    )
    
    start_date = f"{selected_year}-{selected_month:02d}-01"
    
    if selected_month == 12:
        end_date = f"{selected_year + 1}-01-01"
    else:
        end_date = f"{selected_year}-{selected_month + 1:02d}-01"
    
    


    if menu == "Meine Stunden":
        show_hours(
            supabase=supabase,
            profile=profile,
            start_date=start_date,
            end_date=end_date,
            reverse_milestone_map_all=reverse_milestone_map_all,
            milestone_map_active=milestone_map_active
        )
    
    entries_response = supabase.table("time_entries") \
        .select("id, entry_date, milestone_id, task_text, hours, comment") \
        .eq("user_id", profile["id"]) \
        .gte("entry_date", start_date) \
        .lt("entry_date", end_date) \
        .order("entry_date", desc=False) \
        .execute()
    
    entries = entries_response.data or []
    
    entry_options = {
        f'{e["id"]} | {e["entry_date"]} | {reverse_milestone_map_all.get(e["milestone_id"], e["milestone_id"])} | {e["task_text"]}': e
        for e in entries
    }
        



    if menu == "Stunden eintragen":
        st.subheader("Stunden eintragen")
    
        with st.form("time_form"):
        
            entry_date = st.date_input("Datum")
            milestone_title = st.selectbox("Meilenstein", list(milestone_map_active.keys()))
            task_text = st.text_input("Aufgabe")
            hours = st.number_input("Stunden", min_value=0.5, max_value=12.0, step=0.5)
            comment = st.text_area("Kommentar")
    
            submit = st.form_submit_button("Speichern")
        
        if submit:
            insert_response = supabase.table("time_entries").insert({
                "user_id": profile["id"],
                "entry_date": str(entry_date),
                "milestone_id": milestone_map_active[milestone_title],
                "task_text": task_text,
                "hours": hours,
                "comment": comment
            }).execute()
        
            
            st.success("Stunden gespeichert ✅")


    if menu == "Admin-Übersicht" and is_admin:
        show_admin_overview_page(
            supabase=supabase,
            is_admin=is_admin,
            start_date=start_date,
            end_date=end_date,
            reverse_milestone_map_all=reverse_milestone_map_all,
            selected_year=selected_year,
            selected_month=selected_month,
            dataframe_to_csv_bytes=dataframe_to_csv_bytes,
            dataframe_to_excel_bytes=dataframe_to_excel_bytes
        )
        
    if menu == "Dashboard":
        show_dashboard(
            supabase=supabase,
            start_date=start_date,
            end_date=end_date,
            reverse_milestone_map_all=reverse_milestone_map_all
        )

    
    if menu == "Meilensteine verwalten" and is_admin:
        show_milestones_page(supabase, is_admin)

    if st.sidebar.button("Logout"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.rerun()