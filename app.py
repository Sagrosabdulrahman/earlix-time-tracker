import streamlit as st
from supabase import create_client

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
    page_title="+Earlix Zeiterfassung",
    page_icon="assets/logo.png",
    layout="wide"
)


col1, col2 = st.columns([4, 1])

with col1:
    st.title("Stundenkontierung⌚")

with col2:
    st.image("assets/logo.png", width=120)




supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_KEY"]
)

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
    
    st.write("User ID:", st.session_state.user.id)

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
        "Stunden korrigieren",
        "Stunden löschen"
    ]

    if is_admin:
        menu_options.append("Admin-Übersicht")

    menu = st.sidebar.radio("Navigation", menu_options)

    st.sidebar.success(f"Eingeloggt als:\n{st.session_state.user.email}")
    
    

    milestones_response = supabase.table("milestones") \
        .select("id, title") \
        .eq("is_active", True) \
        .execute()

    milestones = milestones_response.data

    if not milestones:
        st.error("Keine aktiven Meilensteine gefunden.")
        st.stop()

    milestone_map = {m["title"]: m["id"] for m in milestones}
    
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
        st.subheader("Meine Stunden")

        entries_response = supabase.table("time_entries") \
            .select("id, entry_date, milestone_id, task_text, hours, comment") \
            .eq("user_id", profile["id"]) \
            .gte("entry_date", start_date) \
            .lt("entry_date", end_date) \
            .order("entry_date", desc=False) \
            .execute()
    
        entries = entries_response.data
        if len(entries) == 0:
            st.info("Für diesen Monat wurden noch keine Stunden erfasst.")
        else:
            df = pd.DataFrame(entries)
    
            reverse_milestone_map = {v: k for k, v in milestone_map.items()}
            df["milestone"] = df["milestone_id"].map(reverse_milestone_map)
            
            df = df[["entry_date", "milestone", "task_text", "hours", "comment"]]
            df.columns = ["Datum", "Meilenstein", "Aufgabe", "Stunden", "Kommentar"]
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            total_hours = df["Stunden"].sum()
            st.metric("Gesamtstunden im Monat", f"{total_hours:.2f} h")
        
    reverse_milestone_map = {v: k for k, v in milestone_map.items()}
    
    entries_response = supabase.table("time_entries") \
        .select("id, entry_date, milestone_id, task_text, hours, comment") \
        .eq("user_id", profile["id"]) \
        .gte("entry_date", start_date) \
        .lt("entry_date", end_date) \
        .order("entry_date", desc=False) \
        .execute()
    
    entries = entries_response.data or []
    
    entry_options = {
        f'{e["id"]} | {e["entry_date"]} | {reverse_milestone_map.get(e["milestone_id"], e["milestone_id"])} | {e["task_text"]}': e
        for e in entries
    }
        
        
    if menu == "Stunden korrigieren":
        st.subheader("Stunden korrigieren")
    

        if len(entries) > 0:
            entry_options = {
                f'{e["id"]} | {e["entry_date"]} | {reverse_milestone_map.get(e["milestone_id"], e["milestone_id"])} | {e["task_text"]}': e
                for e in entries
            }

            selected_entry_label = st.selectbox(
                "Eintrag auswählen",
                options=list(entry_options.keys())
            )
            
            selected_entry = entry_options[selected_entry_label]
            
            milestone_titles = list(milestone_map.keys())
            current_milestone_title = reverse_milestone_map.get(selected_entry["milestone_id"])

            with st.form("edit_entry_form"):
                edit_date = st.date_input("Datum bearbeiten", value=pd.to_datetime(selected_entry["entry_date"]).date())
                edit_milestone = st.selectbox(
                    "Meilenstein bearbeiten",
                    options=milestone_titles,
                    index=milestone_titles.index(current_milestone_title) if current_milestone_title in milestone_titles else 0
                )
                edit_task = st.text_input("Aufgabe bearbeiten", value=selected_entry["task_text"])
                edit_hours = st.number_input("Stunden bearbeiten", min_value=0.5, max_value=12.0, step=0.5, value=float(selected_entry["hours"]))
                edit_comment = st.text_area("Kommentar bearbeiten", value=selected_entry["comment"] or "")

                save_edit = st.form_submit_button("Änderungen speichern")
                
            if save_edit:
                supabase.table("time_entries") \
                    .update({
                        "entry_date": str(edit_date),
                        "milestone_id": milestone_map[edit_milestone],
                        "task_text": edit_task,
                        "hours": edit_hours,
                        "comment": edit_comment
                    }) \
                    .eq("id", selected_entry["id"]) \
                    .execute()

                st.success("Eintrag aktualisiert ✅")
                st.rerun()

    if menu == "Stunden löschen":
        st.subheader("Stunden löschen")
        
        
        if len(entries) > 0:
            delete_entry_label = st.selectbox(
                "Eintrag zum Löschen auswählen",
                options=list(entry_options.keys()),
                key="delete_select"
            )

            delete_entry = entry_options[delete_entry_label]
            
            confirm_delete = st.checkbox("Ich möchte diesen Eintrag wirklich löschen.")
            
            if st.button("Eintrag löschen"):
                if confirm_delete:
                    supabase.table("time_entries") \
                        .delete() \
                        .eq("id", delete_entry["id"]) \
                        .execute()

                    st.success("Eintrag gelöscht ✅")
                    st.rerun()
                else:
                    st.warning("Bitte Löschung bestätigen.")


    if menu == "Stunden eintragen":
        st.subheader("Stunden eintragen")
    
        with st.form("time_form"):
        
            entry_date = st.date_input("Datum")
            milestone_title = st.selectbox("Meilenstein", list(milestone_map.keys()))
            task_text = st.text_input("Aufgabe")
            hours = st.number_input("Stunden", min_value=0.5, max_value=12.0, step=0.5)
            comment = st.text_area("Kommentar")
    
            submit = st.form_submit_button("Speichern")
        
        if submit:
            insert_response = supabase.table("time_entries").insert({
                "user_id": profile["id"],
                "entry_date": str(entry_date),
                "milestone_id": milestone_map[milestone_title],
                "task_text": task_text,
                "hours": hours,
                "comment": comment
            }).execute()
        
            
            st.success("Stunden gespeichert ✅")


    if menu == "Admin-Übersicht" and is_admin:
        st.header("Admin-Übersicht")
        
        admin_entries_response = supabase.table("time_entries") \
            .select("entry_date, user_id, milestone_id, task_text, hours, comment") \
            .gte("entry_date", start_date) \
            .lt("entry_date", end_date) \
            .order("entry_date", desc=False) \
            .execute()

        admin_entries = admin_entries_response.data

        profiles_response = supabase.table("profiles") \
            .select("id, full_name") \
            .execute()

        all_profiles = profiles_response.data
        user_map = {p["id"]: p["full_name"] for p in all_profiles}

        reverse_milestone_map = {v: k for k, v in milestone_map.items()}
    
        if len(admin_entries) == 0:
            st.info("Für diesen Monat liegen noch keine Einträge vor.")
        else:
            admin_df = pd.DataFrame(admin_entries)
            
            admin_df["Mitarbeiter"] = admin_df["user_id"].map(user_map)
            admin_df["Meilenstein"] = admin_df["milestone_id"].map(reverse_milestone_map)
            
            admin_df = admin_df[["entry_date", "Mitarbeiter", "Meilenstein", "task_text", "hours", "comment"]]
            admin_df.columns = ["Datum", "Mitarbeiter", "Meilenstein", "Aufgabe", "Stunden", "Kommentar"]
            
            st.subheader("Alle Einträge")
            st.dataframe(admin_df, use_container_width=True, hide_index=True)

            st.subheader("Stunden nach Mitarbeiter und Meilenstein")
            pivot_df = admin_df.pivot_table(
                index="Mitarbeiter",
                columns="Meilenstein",
                values="Stunden",
                aggfunc="sum",
                fill_value=0
            )

            st.dataframe(pivot_df, use_container_width=True)
    
            total_admin_hours = admin_df["Stunden"].sum()
            st.metric("Gesamtstunden aller Mitarbeiter", f"{total_admin_hours:.2f} h")
            
            csv_data = dataframe_to_csv_bytes(admin_df)
            excel_data = dataframe_to_excel_bytes(admin_df, sheet_name="Alle_Eintraege")
    
            col1, col2 = st.columns(2)
    
            with col1:
                st.download_button(
                    label="CSV herunterladen",
                    data=csv_data,
                    file_name=f"earlix_zeiterfassung_{selected_year}_{selected_month:02d}.csv",
                    mime="text/csv"
                )
    
            with col2:
                st.download_button(
                    label="Excel herunterladen",
                    data=excel_data,
                    file_name=f"earlix_zeiterfassung_{selected_year}_{selected_month:02d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    
            pivot_export_df = pivot_df.reset_index()
    
            pivot_csv_data = dataframe_to_csv_bytes(pivot_export_df)
            pivot_excel_data = dataframe_to_excel_bytes(
                pivot_export_df,
                sheet_name="Pivot_Mitarbeiter_Meilenstein"
            )
    
            col3, col4 = st.columns(2)
    
            with col3:
                st.download_button(
                    label="Pivot als CSV herunterladen",
                    data=pivot_csv_data,
                    file_name=f"earlix_pivot_{selected_year}_{selected_month:02d}.csv",
                    mime="text/csv"
                )
    
            with col4:
                st.download_button(
                    label="Pivot als Excel herunterladen",
                    data=pivot_excel_data,
                    file_name=f"earlix_pivot_{selected_year}_{selected_month:02d}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


    if st.sidebar.button("Logout"):
        try:
            supabase.auth.sign_out()
        except Exception:
            pass

        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.refresh_token = None
        st.rerun()