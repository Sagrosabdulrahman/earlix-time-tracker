import streamlit as st
import pandas as pd


def show_admin_overview_page(
    supabase,
    is_admin,
    start_date,
    end_date,
    reverse_milestone_map_all,
    selected_year,
    selected_month,
    dataframe_to_csv_bytes,
    dataframe_to_excel_bytes
):
    if not is_admin:
        st.error("Kein Zugriff auf diese Seite.")
        return

    st.header("Admin-Übersicht")

    admin_entries_response = supabase.table("time_entries") \
        .select("entry_date, user_id, milestone_id, task_text, hours, comment") \
        .gte("entry_date", start_date) \
        .lt("entry_date", end_date) \
        .order("entry_date", desc=False) \
        .execute()

    admin_entries = admin_entries_response.data or []

    profiles_response = supabase.table("profiles") \
        .select("id, full_name") \
        .execute()

    all_profiles = profiles_response.data or []
    user_map = {p["id"]: p["full_name"] for p in all_profiles}

    if len(admin_entries) == 0:
        st.info("Für diesen Monat liegen noch keine Einträge vor.")
        return

    admin_df = pd.DataFrame(admin_entries)

    admin_df["Mitarbeiter"] = admin_df["user_id"].map(user_map)
    admin_df["Meilenstein"] = admin_df["milestone_id"].map(reverse_milestone_map_all)

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