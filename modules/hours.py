import streamlit as st
import pandas as pd


def show_hours(supabase, profile, start_date, end_date, reverse_milestone_map_all):
    st.subheader("Meine Stunden")

    # Einträge für den gewählten Monat laden
    entries_response = supabase.table("time_entries") \
        .select("id, entry_date, milestone_id, task_text, hours, comment") \
        .eq("user_id", profile["id"]) \
        .gte("entry_date", start_date) \
        .lt("entry_date", end_date) \
        .execute()

    entries = entries_response.data or []

    # Alle Einträge laden für Gesamtstunden insgesamt
    all_entries_response = supabase.table("time_entries") \
        .select("hours") \
        .eq("user_id", profile["id"]) \
        .execute()

    all_entries = all_entries_response.data or []
    all_time_total_hours = sum(float(e["hours"]) for e in all_entries)

    if not entries:
        st.info("Für diesen Monat wurden noch keine Stunden erfasst.")
        st.metric("Gesamtstunden insgesamt", f"{all_time_total_hours:.2f} h")
        return

    df = pd.DataFrame(entries)
    df["Meilenstein"] = df["milestone_id"].map(reverse_milestone_map_all)

    df = df[["entry_date", "Meilenstein", "task_text", "hours", "comment"]]
    df.columns = ["Datum", "Meilenstein", "Aufgabe", "Stunden", "Kommentar"]
    
    df["Stunden"] = df["Stunden"].astype(float)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Kennzahlen
    total_hours = df["Stunden"].sum()
    total_entries = len(df)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Gesamtstunden im Monat", f"{total_hours:.2f} h")

    with col2:
        st.metric("Anzahl Einträge", total_entries)

    with col3:
        st.metric("Gesamtstunden insgesamt", f"{all_time_total_hours:.2f} h")

    # Auswertung nach Meilenstein
    st.subheader("Meine Stunden nach Meilenstein")

    milestone_summary = df.groupby("Meilenstein", as_index=False)["Stunden"].sum()
    milestone_summary = milestone_summary.sort_values("Stunden", ascending=False)

    st.dataframe(milestone_summary, use_container_width=True, hide_index=True)