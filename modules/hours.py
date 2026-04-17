import streamlit as st
import pandas as pd


def show_hours(
    supabase,
    profile,
    start_date,
    end_date,
    reverse_milestone_map_all,
    milestone_map_active
):
    st.subheader("Meine Stunden")

    # Monats-Einträge laden
    entries_response = supabase.table("time_entries") \
        .select("id, entry_date, milestone_id, task_text, hours, comment") \
        .eq("user_id", profile["id"]) \
        .gte("entry_date", start_date) \
        .lt("entry_date", end_date) \
        .order("entry_date", desc=False) \
        .execute()

    entries = entries_response.data or []

    # Alle Einträge laden für Gesamtstunden insgesamt
    all_entries_response = supabase.table("time_entries") \
        .select("hours") \
        .eq("user_id", profile["id"]) \
        .execute()

    all_entries = all_entries_response.data or []
    all_time_total_hours = sum(float(e["hours"]) for e in all_entries)

    if "edit_entry_id" not in st.session_state:
        st.session_state.edit_entry_id = None

    if "delete_entry_id" not in st.session_state:
        st.session_state.delete_entry_id = None

    if not entries:
        st.info("Für diesen Monat wurden noch keine Stunden erfasst.")
        st.metric("Gesamtstunden insgesamt", f"{all_time_total_hours:.2f} h")
        return

    df = pd.DataFrame(entries)
    df["Meilenstein"] = df["milestone_id"].map(reverse_milestone_map_all)

    total_hours = df["hours"].astype(float).sum()
    total_entries = len(df)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Gesamtstunden im Monat", f"{total_hours:.2f} h")
    with col2:
        st.metric("Anzahl Einträge", total_entries)
    with col3:
        st.metric("Gesamtstunden insgesamt", f"{all_time_total_hours:.2f} h")

    st.subheader("Meine Stunden nach Meilenstein")
    milestone_summary = (
        df.groupby("Meilenstein", as_index=False)["hours"]
        .sum()
        .sort_values("hours", ascending=False)
    )
    milestone_summary.columns = ["Meilenstein", "Stunden"]
    st.dataframe(milestone_summary, use_container_width=True, hide_index=True)

    st.subheader("Einträge")

    milestone_titles = list(milestone_map_active.keys())

    for entry in entries:
        milestone_name = reverse_milestone_map_all.get(entry["milestone_id"], entry["milestone_id"])

        with st.container():
            info_col, edit_col, delete_col = st.columns([8, 1, 1])

            with info_col:
                st.markdown(
                    f"""
**Datum:** {entry['entry_date']}  
**Meilenstein:** {milestone_name}  
**Aufgabe:** {entry['task_text'] or '-'}  
**Stunden:** {entry['hours']}  
**Kommentar:** {entry['comment'] or '-'}
"""
                )

            with edit_col:
                if st.button("✏️", key=f"edit_btn_{entry['id']}", help="Bearbeiten"):
                    st.session_state.edit_entry_id = entry["id"]
                    st.session_state.delete_entry_id = None

            with delete_col:
                if st.button("🗑️", key=f"delete_btn_{entry['id']}", help="Löschen"):
                    st.session_state.delete_entry_id = entry["id"]
                    st.session_state.edit_entry_id = None

            # Bearbeiten
            if st.session_state.edit_entry_id == entry["id"]:
                st.markdown("#### Eintrag bearbeiten")

                current_milestone_title = reverse_milestone_map_all.get(entry["milestone_id"])
                default_index = (
                    milestone_titles.index(current_milestone_title)
                    if current_milestone_title in milestone_titles
                    else 0
                )

                with st.form(f"edit_form_{entry['id']}"):
                    edit_date = st.date_input(
                        "Datum bearbeiten",
                        value=pd.to_datetime(entry["entry_date"]).date(),
                        key=f"edit_date_{entry['id']}"
                    )

                    edit_milestone = st.selectbox(
                        "Meilenstein bearbeiten",
                        options=milestone_titles,
                        index=default_index,
                        key=f"edit_milestone_{entry['id']}"
                    )

                    edit_task = st.text_input(
                        "Aufgabe bearbeiten",
                        value=entry["task_text"] or "",
                        key=f"edit_task_{entry['id']}"
                    )

                    edit_hours = st.number_input(
                        "Stunden bearbeiten",
                        min_value=0.5,
                        max_value=24.0,
                        step=0.5,
                        value=float(entry["hours"]),
                        key=f"edit_hours_{entry['id']}"
                    )

                    edit_comment = st.text_area(
                        "Kommentar bearbeiten",
                        value=entry["comment"] or "",
                        key=f"edit_comment_{entry['id']}"
                    )

                    save_col, cancel_col = st.columns(2)
                    with save_col:
                        save_edit = st.form_submit_button("Speichern")
                    with cancel_col:
                        cancel_dummy = st.form_submit_button("Abbrechen")

                if save_edit:
                    supabase.table("time_entries") \
                        .update({
                            "entry_date": str(edit_date),
                            "milestone_id": milestone_map_active[edit_milestone],
                            "task_text": edit_task,
                            "hours": edit_hours,
                            "comment": edit_comment
                        }) \
                        .eq("id", entry["id"]) \
                        .execute()

                    st.session_state.edit_entry_id = None
                    st.success("Eintrag aktualisiert ✅")
                    st.rerun()

                if cancel_dummy:
                    st.session_state.edit_entry_id = None
                    st.rerun()

            # Löschen
            if st.session_state.delete_entry_id == entry["id"]:
                st.warning("Diesen Eintrag wirklich löschen?")

                del_col1, del_col2 = st.columns(2)

                with del_col1:
                    if st.button("Ja, löschen", key=f"confirm_delete_{entry['id']}"):
                        supabase.table("time_entries") \
                            .delete() \
                            .eq("id", entry["id"]) \
                            .execute()

                        st.session_state.delete_entry_id = None
                        st.success("Eintrag gelöscht ✅")
                        st.rerun()

                with del_col2:
                    if st.button("Abbrechen", key=f"cancel_delete_{entry['id']}"):
                        st.session_state.delete_entry_id = None
                        st.rerun()

            st.divider()