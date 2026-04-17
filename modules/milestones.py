import streamlit as st


def show_milestones_page(supabase, is_admin):
    if not is_admin:
        st.error("Kein Zugriff auf diese Seite.")
        return

    st.header("Meilensteine verwalten")

    milestones_admin_response = supabase.table("milestones") \
        .select("id, title, description, is_active, created_at") \
        .order("created_at", desc=False) \
        .execute()

    milestones_admin = milestones_admin_response.data or []

    st.subheader("Neuen Meilenstein anlegen")

    with st.form("create_milestone_form"):
        new_id = st.text_input("Meilenstein-ID", placeholder="z. B. MS-001")
        new_title = st.text_input("Titel")
        new_description = st.text_area("Beschreibung")
        create_milestone = st.form_submit_button("Meilenstein anlegen")

    if create_milestone:
        if not new_id.strip():
            st.warning("Bitte eine Meilenstein-ID eingeben.")
        elif not new_title.strip():
            st.warning("Bitte einen Titel eingeben.")
        else:
            try:
                supabase.table("milestones").insert({
                    "id": new_id.strip(),
                    "title": new_title.strip(),
                    "description": new_description.strip(),
                    "is_active": True
                }).execute()

                st.success("Meilenstein angelegt ✅")
                st.rerun()

            except Exception as e:
                st.error(f"Fehler beim Anlegen: {e}")

    st.divider()
    st.subheader("Vorhandene Meilensteine")

    if len(milestones_admin) == 0:
        st.info("Es sind noch keine Meilensteine vorhanden.")
        return

    milestone_options = {
        f'{m["id"]} | {m["title"]} | {"Offen" if m["is_active"] else "Geschlossen"}': m
        for m in milestones_admin
    }

    selected_milestone_label = st.selectbox(
        "Meilenstein auswählen",
        options=list(milestone_options.keys())
    )

    selected_milestone = milestone_options[selected_milestone_label]

    st.markdown("### Meilenstein bearbeiten")

    with st.form("edit_milestone_form"):
        edit_title = st.text_input("Titel bearbeiten", value=selected_milestone["title"])
        edit_description = st.text_area(
            "Beschreibung bearbeiten",
            value=selected_milestone["description"] or ""
        )
        edit_is_active = st.checkbox(
            "Meilenstein offen für Stundeneinträge",
            value=selected_milestone["is_active"]
        )

        save_milestone = st.form_submit_button("Änderungen speichern")

    if save_milestone:
        if not edit_title.strip():
            st.warning("Der Titel darf nicht leer sein.")
        else:
            supabase.table("milestones") \
                .update({
                    "title": edit_title.strip(),
                    "description": edit_description.strip(),
                    "is_active": edit_is_active
                }) \
                .eq("id", selected_milestone["id"]) \
                .execute()

            st.success("Meilenstein aktualisiert ✅")
            st.rerun()

    st.markdown("### Meilenstein löschen")

    milestone_entry_check = supabase.table("time_entries") \
        .select("id", count="exact") \
        .eq("milestone_id", selected_milestone["id"]) \
        .execute()

    entry_count = milestone_entry_check.count if milestone_entry_check.count is not None else 0

    st.write(f"Verknüpfte Einträge: {entry_count}")

    confirm_delete_milestone = st.checkbox(
        "Ich möchte diesen Meilenstein wirklich löschen.",
        key="confirm_delete_milestone"
    )

    if st.button("Meilenstein löschen"):
        if entry_count > 0:
            st.error("Löschen nicht möglich: Dieser Meilenstein hat bereits Stundeneinträge.")
        elif not confirm_delete_milestone:
            st.warning("Bitte Löschung bestätigen.")
        else:
            supabase.table("milestones") \
                .delete() \
                .eq("id", selected_milestone["id"]) \
                .execute()

            st.success("Meilenstein gelöscht ✅")
            st.rerun()