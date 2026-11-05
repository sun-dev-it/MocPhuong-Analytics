
import streamlit as st
import pandas as pd
import plotly.express as px
import psycopg2


# =========================================================
# 1. CẤU HÌNH TRANG
# =========================================================

st.set_page_config(
    page_title="MocPhuong Analytics",
    page_icon="🪑",
    layout="wide"
)

st.title("Mộc Phương Analytics", icon=":material/analytics:")
st.caption("Dashboard thống kê dữ liệu cửa hàng nội thất Mộc Phương")


# =========================================================
# 2. KẾT NỐI DATABASE
# =========================================================

conn = None

try:
    conn = psycopg2.connect(
        st.secrets["database"]["url"],
        sslmode="require"
    )

    st.badge(
        "Đã kết nối PostgreSQL",
        icon=":material/check_circle:",
        color="green"
    )

    # =====================================================
    # 3. TỔNG QUAN DỮ LIỆU
    # =====================================================

    st.header("1. Tổng quan dữ liệu")

    overview_query = """
        SELECT
            (SELECT COUNT(*) FROM products) AS total_products,
            (SELECT COUNT(*) FROM categories) AS total_categories,
            (SELECT COUNT(*) FROM project_informations) AS total_projects,
            (SELECT COUNT(*) FROM accessories) AS total_accessories,
            (SELECT COUNT(*) FROM decorations) AS total_decorations,
            (SELECT COUNT(*) FROM orders) AS total_orders,
            (SELECT COUNT(*) FROM users) AS total_users;
    """

    overview = pd.read_sql_query(overview_query, conn)
    data = overview.iloc[0]

    metrics = [
        ("Sản phẩm", data["total_products"]),
        ("Danh mục", data["total_categories"]),
        ("Dự án", data["total_projects"]),
        ("Phụ kiện", data["total_accessories"]),
        ("Đồ trang trí", data["total_decorations"]),
        ("Đơn hàng", data["total_orders"]),
        ("Người dùng", data["total_users"])
    ]

    columns = st.columns(7)

    for column, (label, value) in zip(columns, metrics):
        with column:
            st.container(border=True).metric(
                label=label,
                value=f"{value:,}"
            )

    st.divider()

    # =====================================================
    # 4. DANH SÁCH ĐƠN HÀNG
    # =====================================================

    st.header("2. Danh sách đơn hàng")

    orders_query = """
        SELECT
            o.id AS order_id,
            u.name AS customer_name,
            u.email AS customer_email,
            o.phone,
            o.address,
            o.total_price,
            o.status,
            o.created_at
        FROM orders o
        LEFT JOIN users u ON o.user_id = u.id
        ORDER BY o.created_at DESC;
    """

    order_data = pd.read_sql_query(orders_query, conn)

    if order_data.empty:
        st.info(
            "Chưa có đơn hàng nào.",
            title="Chưa có dữ liệu"
        )
    else:
        # Bộ lọc trạng thái
        status_options = ["Tất cả"] + sorted(
            order_data["status"]
            .dropna()
            .unique()
            .tolist()
        )

        selected_status = st.selectbox(
            "Lọc theo trạng thái",
            status_options,
            key="order_status_filter"
        )

        # Tìm kiếm đơn hàng
        search_order = st.text_input(
            "Tìm kiếm đơn hàng",
            placeholder="Nhập mã đơn, tên khách hàng, email, số điện thoại hoặc địa chỉ..."
        )

        filtered_orders = order_data.copy()

        if selected_status != "Tất cả":
            filtered_orders = filtered_orders[
                filtered_orders["status"] == selected_status
            ]

        if search_order.strip():
            keyword = search_order.strip()

            search_columns = [
                "order_id",
                "customer_name",
                "customer_email",
                "phone",
                "address"
            ]

            mask = pd.Series(
                False,
                index=filtered_orders.index
            )

            for column in search_columns:
                mask |= (
                    filtered_orders[column]
                    .fillna("")
                    .astype(str)
                    .str.casefold()
                    .str.contains(
                        keyword.casefold(),
                        regex=False
                    )
                )

            filtered_orders = filtered_orders[mask]

        st.metric(
            "Số đơn hàng tìm thấy",
            f"{len(filtered_orders):,}"
        )

        st.dataframe(
            filtered_orders,
            width="stretch",
            hide_index=True,
            column_config={
                "order_id": st.column_config.NumberColumn(
                    "Mã đơn hàng",
                    format="%d"
                ),
                "customer_name": "Tên khách hàng",
                "customer_email": "Email",
                "phone": "Số điện thoại",
                "address": "Địa chỉ",
                "total_price": st.column_config.NumberColumn(
                    "Tổng tiền",
                    format="%,d đ"
                ),
                "status": "Trạng thái",
                "created_at": st.column_config.DatetimeColumn(
                    "Ngày đặt hàng",
                    format="DD/MM/YYYY HH:mm"
                )
            }
        )

    st.divider()

    # =====================================================
    # 5. THỐNG KÊ SẢN PHẨM THEO DANH MỤC
    # =====================================================

    st.header("3. Thống kê sản phẩm theo danh mục")

    category_query = """
        SELECT
            c.name AS category_name,
            COUNT(p.id) AS total_products
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id, c.name;
    """

    category_data = pd.read_sql_query(
        category_query,
        conn
    )

    if category_data.empty:
        st.info(
            "Chưa có danh mục sản phẩm.",
            title="Chưa có dữ liệu"
        )
    else:
        # Sắp xếp tên danh mục theo thứ tự chữ cái
        category_data = category_data.sort_values(
            "category_name",
            ascending=False,
            key=lambda names: (
                names.str.casefold()
                .str.replace("đ", "d", regex=False)
                .str.normalize("NFD")
                .str.replace(
                    r"[\u0300-\u036f]",
                    "",
                    regex=True
                )
            ),
            kind="stable",
            ignore_index=True
        )

        with st.container(border=True):
            st.subheader("Số lượng sản phẩm")

            fig = px.bar(
                category_data,
                x="total_products",
                y="category_name",
                orientation="h",
                text="total_products",
                category_orders={
                    "category_name": (
                        category_data["category_name"].tolist()
                    )
                },
                labels={
                    "category_name": "Danh mục",
                    "total_products": "Số lượng sản phẩm"
                }
            )

            fig.update_traces(
                textposition="outside",
                cliponaxis=False
            )

            fig.update_layout(
                xaxis_title="Số lượng sản phẩm",
                yaxis_title=None,
                template="plotly_white",
                showlegend=False,
                margin=dict(
                    l=12,
                    r=24,
                    t=16,
                    b=12
                ),
                bargap=0.3
            )

            fig.update_xaxes(
                rangemode="tozero",
                showgrid=True
            )

            fig.update_yaxes(
                autorange="reversed"
            )

            st.plotly_chart(
                fig,
                width="stretch",
                alt="Số lượng sản phẩm ở từng danh mục"
            )

    st.divider()

    # =====================================================
    # 6. DANH SÁCH NGƯỜI DÙNG
    # =====================================================

    st.header("4. Danh sách người dùng")

    users_query = """
        SELECT
            name AS user_name,
            email,
            role,
            provider,
            created_at
        FROM users
        ORDER BY created_at DESC;
    """

    user_data = pd.read_sql_query(
        users_query,
        conn
    )

    if user_data.empty:
        st.info(
            "Chưa có người dùng nào.",
            title="Chưa có dữ liệu"
        )
    else:
        # Chuyển mã quyền thành tên hiển thị
        role_labels = {
            "super_admin": "Admin tổng",
            "admin_manager": "Admin quản lý",
            "staff": "Staff"
        }

        # Bộ lọc quyền tài khoản
        role_codes = sorted(
            user_data["role"]
            .dropna()
            .unique()
            .tolist()
        )

        role_options = ["Tất cả"] + [
            role_labels.get(role, role)
            for role in role_codes
        ]

        selected_role = st.selectbox(
            "Lọc theo quyền",
            role_options,
            key="user_role_filter"
        )

        # Tìm kiếm người dùng
        search_user = st.text_input(
            "Tìm kiếm người dùng",
            placeholder="Nhập tên hoặc email..."
        )

        filtered_users = user_data.copy()

        # Lọc theo quyền bằng mã role trong database
        if selected_role != "Tất cả":
            selected_role_code = next(
                (
                    code
                    for code, label in role_labels.items()
                    if label == selected_role
                ),
                selected_role
            )

            filtered_users = filtered_users[
                filtered_users["role"] == selected_role_code
            ]

        # Tìm kiếm theo tên hoặc email
        if search_user.strip():
            keyword = search_user.strip().casefold()

            name_match = (
                filtered_users["user_name"]
                .fillna("")
                .astype(str)
                .str.casefold()
                .str.contains(keyword, regex=False)
            )

            email_match = (
                filtered_users["email"]
                .fillna("")
                .astype(str)
                .str.casefold()
                .str.contains(keyword, regex=False)
            )

            filtered_users = filtered_users[
                name_match | email_match
            ]

        # Đổi mã quyền thành tên hiển thị
        filtered_users["role"] = (
            filtered_users["role"].map(
                lambda role: role_labels.get(role, role)
            )
        )

        st.metric(
            "Số người dùng tìm thấy",
            f"{len(filtered_users):,}"
        )

        # Không hiển thị ID tài khoản hoặc OAuth UID
        display_users = filtered_users[
            [
                "user_name",
                "email",
                "role",
                "provider",
                "created_at"
            ]
        ].rename(
            columns={
                "user_name": "Tên người dùng",
                "email": "Email",
                "role": "Quyền tài khoản",
                "provider": "Phương thức đăng nhập",
                "created_at": "Ngày tạo tài khoản"
            }
        )

        st.dataframe(
            display_users,
            width="stretch",
            hide_index=True,
            column_config={
                "Tên người dùng": "Tên người dùng",
                "Email": "Email",
                "Quyền tài khoản": "Quyền tài khoản",
                "Phương thức đăng nhập": "Phương thức đăng nhập",
                "Ngày tạo tài khoản": st.column_config.DatetimeColumn(
                    "Ngày tạo tài khoản",
                    format="DD/MM/YYYY HH:mm"
                )
            }
        )


except Exception as e:
    st.error(
        f"Đã xảy ra lỗi: {e}",
        icon="🚨"
    )

finally:
    if conn is not None and not conn.closed:
        conn.close()
