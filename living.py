import re
from datetime import date, datetime

import pandas as pd
import streamlit as st


LIVING_COLUMNS = ["date", "amount", "category", "method", "memo"]

LIVING_EXPENSE_CATEGORY_OPTIONS = [
    "식비",
    "영양식품",
    "주거비",
    "생활용품",
    "가족용돈",
    "자동차관련",
    "쇼핑",
    "여행관련",
    "카페/간식",
    "선물",
    "문화활동",
    "병원/건강",
    "기타",
]

LIVING_INCOME_CATEGORY_OPTIONS = [
    "정기입금",
    "추가수입",
    "환급",
]

LIVING_TYPE_OPTIONS = ["지출", "입금"]
LIVING_DEFAULT_METHOD = "생활비통장"
LIVING_PAGE_SIZE = 10

@st.cache_data(ttl=60)
def load_living_df(_get_worksheet_func) -> pd.DataFrame:
    try:
        ws = _get_worksheet_func("living")
        values = ws.get_all_records()

        if not values:
            return pd.DataFrame(columns=LIVING_COLUMNS)

        df = pd.DataFrame(values).fillna("")

        rename_map = {
            "날짜": "date",
            "금액": "amount",
            "카테고리": "category",
            "결제수단": "method",
            "메모": "memo",
            "구분": "type",
        }

        df = df.rename(columns=rename_map)

        if "번호" in df.columns:
            df = df.drop(columns=["번호"])

        for c in ["date", "amount", "category", "method", "memo"]:
            if c not in df.columns:
                df[c] = ""

        if "type" not in df.columns:
            df["type"] = ""

        raw_amount = df["amount"].astype(str).str.strip()

        df["amount"] = (
            raw_amount
            .str.replace(",", "", regex=False)
            .str.replace("원", "", regex=False)
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

        df["type"] = df["type"].astype(str).str.strip()
        df["method"] = df["method"].astype(str).str.strip()
        df["memo"] = df["memo"].astype(str).str.strip()

        def restore_amount(row):
            amt = abs(int(row["amount"]))
            typ = row["type"]
            raw = str(row.get("_raw_amount", "")).strip()

            if typ == "입금":
                return amt
            elif typ == "지출":
                return -amt

            if raw.startswith("-"):
                return -amt
            elif raw.startswith("+"):
                return amt
            else:
                return -amt

        df["_raw_amount"] = raw_amount
        df["amount"] = df.apply(restore_amount, axis=1)
        df = df.drop(columns=["_raw_amount"])

        df["date"] = df["date"].astype(str)
        df["category"] = df["category"].astype(str)
        df["method"] = df["method"].astype(str)
        df["memo"] = df["memo"].astype(str)

        return df[LIVING_COLUMNS].copy()

    except Exception:
        return pd.DataFrame(columns=LIVING_COLUMNS)


def save_living_df(df: pd.DataFrame, _get_worksheet_func) -> None:
    ws = _get_worksheet_func("living")

    save_data = df[LIVING_COLUMNS].copy().fillna("")

    save_data["date_dt"] = pd.to_datetime(save_data["date"], errors="coerce")
    save_data = save_data.sort_values(
        by=["date_dt", "date"],
        ascending=[False, False]
    ).drop(columns=["date_dt"])

    save_data["구분"] = save_data["amount"].apply(
        lambda x: "입금" if int(x) > 0 else "지출"
    )

    save_data["금액"] = save_data["amount"].apply(
        lambda x: f"{abs(int(x)):,}원"
    )

    save_data["날짜"] = save_data["date"]
    save_data["카테고리"] = save_data["category"]
    save_data["결제수단"] = save_data["method"]
    save_data["메모"] = save_data["memo"]

    save_data = save_data.reset_index(drop=True)
    save_data.insert(0, "번호", range(1, len(save_data) + 1))

    save_data = save_data[
        ["번호", "날짜", "구분", "카테고리", "메모", "금액", "결제수단"]
    ]

    rows = [save_data.columns.tolist()] + save_data.values.tolist()

    ws.clear()
    ws.update(rows)
    load_living_df.clear()


def render_living_tab(get_worksheet_func, render_budget_card):
    living_df = load_living_df(get_worksheet_func)

    st.subheader("🏦 생활비 통장")

    month_key = datetime.today().strftime("%Y-%m")

    month_df = living_df.copy()
    month_df["date_dt"] = pd.to_datetime(month_df["date"], errors="coerce")
    month_df = month_df[
        month_df["date_dt"].dt.strftime("%Y-%m") == month_key
    ]

    living_spent = abs(int(month_df[month_df["amount"] < 0]["amount"].sum()))
    living_income = int(month_df[month_df["amount"] > 0]["amount"].sum())
    living_net = living_spent - living_income

    c1, c2, c3 = st.columns(3)

    with c1:
        render_budget_card("이번달 지출", f"{living_spent:,}원", "#F8FBF7", "#D9E8D4", "#4D6B50")
    with c2:
        render_budget_card("이번달 입금", f"{living_income:,}원", "#F3F8FF", "#D8E6F8", "#4A6688")
    with c3:
        render_budget_card("순지출", f"{living_net:,}원", "#FFF7F5", "#F2D9D2", "#8A5A4A")

    st.divider()

    st.subheader("✍ 생활비 입력")

    with st.form("living_add_form", clear_on_submit=True):
        f1, f2, f3, f4, f5 = st.columns(5)

        with f1:
            living_date = st.date_input(
                "날짜",
                value=date.today(),
                key="living_date"
            )

        with f2:
            living_type = st.selectbox(
                "구분",
                LIVING_TYPE_OPTIONS,
                index=0,
                key="living_type"
            )

        with f3:
            if living_type == "입금":
                living_category = st.selectbox(
                    "카테고리",
                    LIVING_INCOME_CATEGORY_OPTIONS,
                    index=0,
                    key="living_category"
                )
            else:
                living_category = st.selectbox(
                    "카테고리",
                    LIVING_EXPENSE_CATEGORY_OPTIONS,
                    index=0,
                    key="living_category"
                )

        with f4:
            living_memo = st.text_input(
                "메모",
                value="",
                key="living_memo"
            )

        with f5:
            living_amount_text = st.text_input(
                "금액",
                value="",
                placeholder="금액 입력",
                key="living_amount"
            )

        living_saved = st.form_submit_button("➕ 생활비 저장", use_container_width=True)

    if living_saved:
        amount_clean = living_amount_text.replace(",", "").strip()

        if not amount_clean:
            st.error("금액을 입력해줘.")
        elif not re.fullmatch(r"\d+", amount_clean):
            st.error("금액은 숫자만 입력해줘.")
        else:
            amount_value = int(amount_clean)
            final_amount = amount_value if living_type == "입금" else -amount_value

            new_row = {
                "date": str(living_date),
                "amount": final_amount,
                "category": living_category,
                "method": LIVING_DEFAULT_METHOD,
                "memo": living_memo,
            }

            current_df = load_living_df(get_worksheet_func)
            current_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
            save_living_df(current_df, get_worksheet_func)

            st.success("✅ 생활비 저장 완료!")
            st.rerun()

    st.divider()
    st.subheader("🧾 생활비 내역")

    living_month_df = living_df.copy()
    living_month_df["date_dt"] = pd.to_datetime(living_month_df["date"], errors="coerce")

    living_month_options = sorted(
        {
            m.strftime("%Y-%m")
            for m in living_month_df["date_dt"].dropna().dt.to_period("M").dt.to_timestamp()
        },
        reverse=True
    )

    current_month = datetime.today().strftime("%Y-%m")
    if current_month not in living_month_options:
        living_month_options.insert(0, current_month)

    if not living_month_options:
        living_month_options = [current_month]

    top_left, top_right = st.columns([1, 1])

    with top_left:
        if "living_selected_month" not in st.session_state or st.session_state["living_selected_month"] not in living_month_options:
            st.session_state["living_selected_month"] = current_month

        living_month = st.selectbox(
            "월 선택",
            living_month_options,
            key="living_selected_month"
        )

    with top_right:
        living_q = st.text_input(
            "검색(카테고리/메모/구분)",
            placeholder="예: 식비 / 관리비 / 입금",
            key="living_search_text"
        )

    living_view = living_df.copy()
    living_view["date_dt"] = pd.to_datetime(living_view["date"], errors="coerce")

    try:
        y, m = living_month.split("-")
        living_view = living_view[
            (living_view["date_dt"].dt.year == int(y)) &
            (living_view["date_dt"].dt.month == int(m))
        ]
    except Exception:
        pass

    if living_q.strip():
        qq = living_q.strip().lower()
        row_type_series = living_view["amount"].apply(lambda x: "입금" if int(x) > 0 else "지출")
        mask = (
            living_view["category"].astype(str).str.lower().str.contains(qq, na=False)
            | living_view["memo"].astype(str).str.lower().str.contains(qq, na=False)
            | row_type_series.astype(str).str.lower().str.contains(qq, na=False)
        )
        living_view = living_view[mask]

    living_view = living_view.sort_values(by=["date_dt", "date"], ascending=False)

    living_total = int(living_view["amount"].abs().sum()) if not living_view.empty else 0
    st.markdown(
        f"<div style='text-align:right; font-size:13px; opacity:0.75;'>현재 보기: {living_month} · 총금액: {living_total:,}원</div>",
        unsafe_allow_html=True
    )

    living_view = living_view.reset_index(drop=True)

    if living_view.empty:
        st.write("생활비 내역이 없어요.")
    else:
        total_rows = len(living_view)
        total_pages = (total_rows - 1) // LIVING_PAGE_SIZE + 1

        if "living_record_page" not in st.session_state:
            st.session_state["living_record_page"] = 1

        living_view_key = f"{living_month}|{living_q}"
        if "living_last_view_key" not in st.session_state:
            st.session_state["living_last_view_key"] = living_view_key

        if st.session_state["living_last_view_key"] != living_view_key:
            st.session_state["living_record_page"] = 1
            st.session_state["living_last_view_key"] = living_view_key

        if st.session_state["living_record_page"] > total_pages:
            st.session_state["living_record_page"] = total_pages
        if st.session_state["living_record_page"] < 1:
            st.session_state["living_record_page"] = 1

        start_idx = (st.session_state["living_record_page"] - 1) * LIVING_PAGE_SIZE
        end_idx = start_idx + LIVING_PAGE_SIZE

        page_view = living_view.iloc[start_idx:end_idx].copy()
        page_view["번호"] = range(start_idx + 1, min(end_idx, total_rows) + 1)

        st.markdown(
            f"<div style='text-align:right; font-size:13px; opacity:0.75;'>총 {total_rows}건</div>",
            unsafe_allow_html=True
        )

        h1, h2, h3, h4, h5, h6 = st.columns([0.7, 1.2, 1.0, 1.2, 2.8, 1.2])
        h1.markdown("<div class='table-head'>번호</div>", unsafe_allow_html=True)
        h2.markdown("<div class='table-head'>날짜</div>", unsafe_allow_html=True)
        h3.markdown("<div class='table-head'>구분</div>", unsafe_allow_html=True)
        h4.markdown("<div class='table-head'>카테고리</div>", unsafe_allow_html=True)
        h5.markdown("<div class='table-head'>메모</div>", unsafe_allow_html=True)
        h6.markdown("<div class='table-head'>금액</div>", unsafe_allow_html=True)

        for _, r in page_view.iterrows():
            c1, c2, c3, c4, c5, c6 = st.columns([0.7, 1.2, 1.0, 1.2, 2.8, 1.2])

            row_type = "입금" if int(r["amount"]) > 0 else "지출"
            amount_display = f"{abs(int(r['amount'])):,}원"
            amount_html = (
                f"<div class='row-box amount-text'>➕ {amount_display}</div>"
                if int(r["amount"]) > 0
                else f"<div class='row-box amount-text'>💸 {amount_display}</div>"
            )

            c1.markdown(f"<div class='row-box'>{r['번호']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='row-box'>{r['date']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='row-box'>{row_type}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='row-box'><span class='cat-tag'>{r['category']}</span></div>", unsafe_allow_html=True)
            c5.markdown(f"<div class='row-box'>{r['memo']}</div>", unsafe_allow_html=True)
            c6.markdown(amount_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        p1, p2, p3 = st.columns([1.2, 5, 1.2])

        current_page = st.session_state["living_record_page"]

        pages_to_show = []
        if total_pages <= 10:
            pages_to_show = list(range(1, total_pages + 1))
        else:
            if current_page <= 4:
                pages_to_show = [1, 2, 3, 4, 5, "...", total_pages]
            elif current_page >= total_pages - 3:
                pages_to_show = [1, "...", total_pages - 4, total_pages - 3, total_pages - 2, total_pages - 1, total_pages]
            else:
                pages_to_show = [1, "...", current_page - 1, current_page, current_page + 1, "...", total_pages]

        with p1:
            prev_disabled = current_page <= 1
            if st.button(
                "◀ 이전",
                use_container_width=True,
                key="living_prev_page",
                disabled=prev_disabled
            ):
                st.session_state["living_record_page"] -= 1
                st.rerun()

        with p2:
            page_cols = st.columns(len(pages_to_show))
            for i, page_item in enumerate(pages_to_show):
                with page_cols[i]:
                    if page_item == "...":
                        st.markdown(
                            "<div style='text-align:center; padding-top:8px; font-weight:700;'>...</div>",
                            unsafe_allow_html=True
                        )
                    else:
                        if st.button(
                            str(page_item),
                            use_container_width=True,
                            key=f"living_page_{page_item}",
                            type="primary" if current_page == page_item else "secondary"
                        ):
                            st.session_state["living_record_page"] = page_item
                            st.rerun()

        with p3:
            next_disabled = current_page >= total_pages
            if st.button(
                "다음 ▶",
                use_container_width=True,
                key="living_next_page",
                disabled=next_disabled
            ):
                st.session_state["living_record_page"] += 1
                st.rerun()

    st.divider()
    st.subheader("🏠 최근 1년 관리비 내역")

    today_dt = pd.Timestamp.today()
    one_year_ago = today_dt - pd.DateOffset(months=12)

    management_df = living_df.copy()
    management_df["date_dt"] = pd.to_datetime(management_df["date"], errors="coerce")

    management_df = management_df[
        (management_df["date_dt"] >= one_year_ago) &
        (management_df["category"] == "주거비") &
        (management_df["memo"].astype(str).str.contains("관리비", na=False))
    ].copy()

    management_df = management_df.sort_values(by="date_dt", ascending=False)

    management_spent = abs(int(management_df[management_df["amount"] < 0]["amount"].sum())) if not management_df.empty else 0

    st.markdown(
        f"<div style='text-align:right; font-size:13px; opacity:0.75;'>최근 1년 관리비 합계: {management_spent:,}원</div>",
        unsafe_allow_html=True
    )

    if management_df.empty:
        st.write("최근 1년 관리비 내역이 없어요.")
    else:
        management_df = management_df.reset_index(drop=True)
        management_df["번호"] = range(1, len(management_df) + 1)

        h1, h2, h3, h4, h5 = st.columns([0.7, 1.2, 1.2, 2.8, 1.2])
        h1.markdown("<div class='table-head'>번호</div>", unsafe_allow_html=True)
        h2.markdown("<div class='table-head'>날짜</div>", unsafe_allow_html=True)
        h3.markdown("<div class='table-head'>구분</div>", unsafe_allow_html=True)
        h4.markdown("<div class='table-head'>메모</div>", unsafe_allow_html=True)
        h5.markdown("<div class='table-head'>금액</div>", unsafe_allow_html=True)

        for _, r in management_df.iterrows():
            c1, c2, c3, c4, c5 = st.columns([0.7, 1.2, 1.2, 2.8, 1.2])

            row_type = "입금" if int(r["amount"]) > 0 else "지출"
            amount_display = f"{abs(int(r['amount'])):,}원"
            amount_html = (
                f"<div class='row-box amount-text'>➕ {amount_display}</div>"
                if int(r["amount"]) > 0
                else f"<div class='row-box amount-text'>💸 {amount_display}</div>"
            )

            c1.markdown(f"<div class='row-box'>{r['번호']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='row-box'>{r['date']}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='row-box'>{row_type}</div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='row-box'>{r['memo']}</div>", unsafe_allow_html=True)
            c5.markdown(amount_html, unsafe_allow_html=True)
