import sqlite3
import pandas as pd
import streamlit as st
from chat_store import DB_PATH

TABLE = "messages"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

@st.cache_data(show_spinner=False)
def load_users():
    with get_conn() as conn:
        return pd.read_sql(f"SELECT DISTINCT user FROM {TABLE} ORDER BY user;", conn)["user"].tolist()

def load_rows(user, sort_desc=True, hide_reviewed=False):
    order = "DESC" if sort_desc else "ASC"
    where = "WHERE user = ?" + (" AND reviewed = 0" if hide_reviewed else "")
    with get_conn() as conn:
        return pd.read_sql(
            f"""
            SELECT id, user, timestamp AS ts, message, reviewed
            FROM {TABLE}
            {where}
            ORDER BY ts {order};
            """,
            conn, params=(user,)
        )

def update_reviewed(ids, value):
    if not ids: return
    q = f"UPDATE {TABLE} SET reviewed = ? WHERE id IN ({','.join(['?']*len(ids))})"
    with get_conn() as conn:
        conn.execute("BEGIN")
        conn.execute(q, (1 if value else 0, *ids))
        conn.commit()

st.title("Review Queue")

if st.sidebar.button("Refresh users"):
    st.cache_data.clear()

users = load_users()
if not users:
    st.write("No users found.")
    st.stop()

st.sidebar.header("Filters")
cur_idx = st.session_state.get("cur_user_idx", 0)
user = st.sidebar.selectbox("User", users, index=min(cur_idx, len(users)-1))
sort_desc = st.sidebar.checkbox("Newest first", value=True)
hide_reviewed = st.sidebar.checkbox("Hide reviewed", value=False)

df = load_rows(user, sort_desc, hide_reviewed)
st.subheader(f"User: {user}")
st.caption(f"{len(df)} message(s)")

if df.empty:
    st.write("No rows match your filters.")
else:
    # python
    # Reorder columns so "reviewed" is first, then "message", then the rest
    df = df[["reviewed", "message", "id", "user", "ts"]]

    selected = st.data_editor(
        df[["reviewed", "message"]],  # Only visible columns
        key="grid",
        use_container_width=True,
        disabled=["message"],
        column_config={
            "message": st.column_config.TextColumn(width="large"),
            "reviewed": st.column_config.CheckboxColumn("reviewed", width=0)
        },
        hide_index=True
    )

    select_ids = st.multiselect(
        "Select rows to mark reviewed/unreviewed:",
        options=df["id"].tolist(),
        default=[]
    )

    col1, col2, col3 = st.columns([1,1,2])
    with col1:
        if st.button("Mark as reviewed"):
            update_reviewed(select_ids, True)
            st.cache_data.clear()
    with col2:
        if st.button("Mark as unreviewed"):
            update_reviewed(select_ids, False)
    with col3:
        if st.button("Mark all shown as reviewed"):
            update_reviewed(df["id"].tolist(), True)

nav1, nav2 = st.columns(2)
with nav1:
    if st.button("◀ Prev user"):
        st.session_state["cur_user_idx"] = max(0, users.index(user)-1)
with nav2:
    if st.button("Next user ▶"):
        st.session_state["cur_user_idx"] = min(len(users)-1, users.index(user)+1)

