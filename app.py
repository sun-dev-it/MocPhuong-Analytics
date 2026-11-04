import streamlit as st
import psycopg2
import pandas as pd

st.set_page_config(
    page_title="MocPhuong Analytics",
    page_icon="🪑",
    layout="wide"
)

st.title("Mộc Phương Analytics")

try:
    conn = psycopg2.connect(
        st.secrets["database"]["url"],
        sslmode="require"
    )

    st.success("Kết nối PostgreSQL Render thành công!")

    # Lấy danh sách bảng
    query = """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """

    tables = pd.read_sql_query(query, conn)

    st.subheader("Danh sách bảng trong database")
    st.dataframe(tables, use_container_width=True)

    conn.close()

except Exception as e:
    st.error(f"Kết nối thất bại: {e}")
