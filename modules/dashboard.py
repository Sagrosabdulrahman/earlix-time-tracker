import streamlit as st
import pandas as pd
import plotly.express as px



def show_dashboard(
    supabase,
    start_date,
    end_date,
    reverse_milestone_map_all
):
    st.header("Dashboard")



    # Daten laden
    response = supabase.table("time_entries") \
        .select("user_id, milestone_id, entry_date, hours") \
        .gte("entry_date", start_date) \
        .lt("entry_date", end_date) \
        .execute()

    data = response.data or []

    if not data:
        st.info("Keine Daten für diesen Zeitraum.")
        return

    df = pd.DataFrame(data)

    # Mitarbeiter laden
    profiles_response = supabase.table("profiles") \
        .select("id, full_name") \
        .execute()

    profiles = profiles_response.data or []
    user_map = {p["id"]: p["full_name"] for p in profiles}

    df["Mitarbeiter"] = df["user_id"].map(user_map)
    df["Meilenstein"] = df["milestone_id"].map(reverse_milestone_map_all)

    # Filter
    st.subheader("Filter")

    filter_col1, filter_col2 = st.columns(2)

    all_employees = sorted(df["Mitarbeiter"].dropna().unique().tolist())
    all_milestones = sorted(df["Meilenstein"].dropna().unique().tolist())

    with filter_col1:
        selected_employee = st.selectbox(
            "Mitarbeiter auswählen",
            options=["Alle"] + all_employees
        )

    with filter_col2:
        selected_milestone = st.selectbox(
            "Meilenstein auswählen",
            options=["Alle"] + all_milestones
        )

    filtered_df = df.copy()

    if selected_employee != "Alle":
        filtered_df = filtered_df[filtered_df["Mitarbeiter"] == selected_employee]

    if selected_milestone != "Alle":
        filtered_df = filtered_df[filtered_df["Meilenstein"] == selected_milestone]

    if filtered_df.empty:
        st.warning("Keine Daten für die gewählte Filterkombination.")
        return

    # KPI-Kacheln
    total_hours = filtered_df["hours"].astype(float).sum()
    total_entries = len(filtered_df)
    total_employees = df["Mitarbeiter"].nunique()
    total_milestones = df["Meilenstein"].nunique()

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    with kpi1:
        st.metric("Gesamtstunden", f"{total_hours:.2f} h")

    with kpi2:
        st.metric("Einträge", total_entries)

    with kpi3:
        st.metric("Mitarbeiter", total_employees)

    with kpi4:
        st.metric("Meilensteine", total_milestones)
    
    # Vergleich mit Vormonat
    current_start = pd.to_datetime(start_date)
    
    if current_start.month == 1:
        prev_month_start = current_start.replace(year=current_start.year - 1, month=12)
    else:
        prev_month_start = current_start.replace(month=current_start.month - 1)
    
    prev_month_end = current_start
    
    prev_response = supabase.table("time_entries") \
        .select("hours") \
        .gte("entry_date", prev_month_start.strftime("%Y-%m-%d")) \
        .lt("entry_date", prev_month_end.strftime("%Y-%m-%d")) \
        .execute()
    
    prev_entries = prev_response.data or []
    prev_total_hours = sum(float(e["hours"]) for e in prev_entries)
    
    delta_hours = total_hours - prev_total_hours
    
    st.metric(
        "Vergleich zum Vormonat",
        f"{total_hours:.2f} h",
        delta=f"{delta_hours:+.2f} h"
    )
    
    
    # ======================
    # 1. Linienchart: Stundenverlauf über Zeit
    # ======================
    st.subheader("Stundenverlauf über Zeit")

    filtered_df["entry_date"] = pd.to_datetime(filtered_df["entry_date"])
    df_time = filtered_df.groupby("entry_date", as_index=False)["hours"].sum()
    
    fig_time = px.line(
        df_time,
        x="entry_date",
        y="hours",
        title="Stunden pro Tag",
        markers=True
    )
    
    fig_time.update_layout(height=350)
    
    st.plotly_chart(fig_time, use_container_width=True)
    
    
    # =====================
    # 2. Stunden pro Mitarbeiter
    # =====================

    
    df_user = filtered_df.groupby("Mitarbeiter", as_index=False)["hours"].sum()
    
    fig_user = px.bar(
        df_user,
        x="Mitarbeiter",
        y="hours",
        title="Stunden je Mitarbeiter"
    )
    fig_user.update_layout(height=350)
    
    # =====================
    # 3. Stunden pro Meilenstein
    # =====================

    df_ms = df.groupby("Meilenstein", as_index=False)["hours"].sum()
    
    fig_ms = px.bar(
        df_ms,
        x="Meilenstein",
        y="hours",
        title="Stunden je Meilenstein"
    )
    fig_ms.update_layout(height=350)
    fig_ms.update_layout(xaxis_tickangle=-30)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(fig_user, use_container_width=True)
    
    with col2:
        st.plotly_chart(fig_ms, use_container_width=True)
        

    # ======================
    # 4. Donut-Chart für Meilenstein-Verteilung
    # ======================   

    st.subheader("Verteilung der Stunden nach Meilenstein")

    fig_pie = px.pie(
        df_ms,
        names="Meilenstein",
        values="hours",
        title="Anteil der Stunden je Meilenstein",
        hole=0.45
    )

    fig_pie.update_layout(height=400)

    st.plotly_chart(fig_pie, use_container_width=True)
    
    
    fig_user.update_layout(height=350)
    fig_ms.update_layout(height=350)
    fig_ms.update_layout(xaxis_tickangle=-30)
    
    
    st.subheader("Rankings")

    rank_col1, rank_col2 = st.columns(2)
    
    with rank_col1:
        st.markdown("#### Top Mitarbeiter")
        top_employees = (
            filtered_df.groupby("Mitarbeiter", as_index=False)["hours"]
            .sum()
            .sort_values("hours", ascending=False)
        )
        top_employees.columns = ["Mitarbeiter", "Stunden"]
        st.dataframe(top_employees, use_container_width=True, hide_index=True)
    
    with rank_col2:
        st.markdown("#### Top Meilensteine")
        top_milestones = (
            filtered_df.groupby("Meilenstein", as_index=False)["hours"]
            .sum()
            .sort_values("hours", ascending=False)
        )
        top_milestones.columns = ["Meilenstein", "Stunden"]
        st.dataframe(top_milestones, use_container_width=True, hide_index=True)
    
    