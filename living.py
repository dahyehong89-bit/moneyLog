import re
from datetime import date, datetime

import pandas as pd
import streamlit as st


LIVING_COLUMNS = ["date", "amount", "category", "method", "memo", "type"]

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

LIVING_EMERGENCY_CATEGORY_OPTIONS = [
    "비상금 넣기",
    "비상금 빼기",
]

LIVING_TYPE_OPTIONS = ["지출", "입금", "비상금"]
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

        for c in LIVING_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        raw_amount = df["amount"].astype(str).str.strip()

        df["amount"] = (
            raw_amount
            .str.replace(",", "", regex=False)
            .str.replace("원", "", regex=False)
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

        df["date"] = df["date"].astype(str).str.strip()
        df["category"] = df["category"].astype(str).str.strip()
        df["method"] = df["method"].astype(str).str.strip()
        df["memo"] = df["memo"].astype(str).str.strip()
        df["type"] = df["type"].astype(str).str.strip()

        df["_raw_amount"] = raw_amount

        def restore_amount(row):
            amt = abs(int(row["amount"]))
            typ = str(row.get("type", "")).strip()
            category = str(row.get("category", "")).strip()
            raw = str(row.get("_raw_amount", "")).strip()

            if typ == "입금":
                return amt
            if typ == "지출":
                return -amt
            if typ == "비상금":
                if category == "비상금 넣기":
                    return -amt
                if category == "비상금 빼기":
                    return amt

            if raw.startswith("-"):
                return -amt
            if raw.startswith("+"):
                return amt

            if category == "비상금 넣기":
                return -amt
            if category == "비상금 빼기":
                return amt

            return -amt

        df["amount"] = df.apply(restore_amount, axis=1)
        df = df.drop(columns=["_raw_amount"])

        return df[LIVING_COLUMNS].copy()

    except Exception as e:
        st.error(f"load_living_df 에러: {e}")
        return pd.DataFrame(columns=LIVING_COLUMNS)


def save_living_df(df: pd.DataFrame, _get_worksheet_func) -> None:
    ws = _get_worksheet_func("living")

    save_data = df[LIVING_COLUMNS].copy().fillna("")

    save_data["date_dt"] = pd.to_datetime(save_data["date"], errors="coerce")
    save_data = save_data.sort_values(
        by=["date_dt", "date"],
        ascending=[False, False]
    ).drop(columns=["date_dt"])

    save_data["구분"] = save_data["type"].astype(str).str.strip()
    save_data["구분"] = save_data["구분"].replace("", pd.NA)
    save_data["구분"] = save_data["구분"].fillna(
        save_data["amount"].apply(lambda x: "입금" if int(x) > 0 else "지출")
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


def get_living_month_options(df: pd.DataFrame):
    current_month = datetime.today().strftime("%Y-%m")

    if df.empty:
        return [current_month]

    temp = df.copy()
    temp["date_dt"] = pd.to_datetime(temp["date"], errors="coerce")

    months = sorted(
        {
            m.strftime("%Y-%m")
            for m in temp["date_dt"].dropna().dt.to_period("M").dt.to_timestamp()
        },
        reverse=True
    )

    if current_month not in months:
        months.insert(0, current_month)

    return months or [current_month]


def calc_living_summary(df: pd.DataFrame, month_key: str):
    temp = df.copy()
    temp["date_dt"] = pd.to_datetime(temp["date"], errors="coerce")

    if "type" not in temp.columns:
        temp["type"] = ""

    temp["type"] = temp["type"].astype(str).str.strip()
    temp["category"] = temp["category"].astype(str).str.strip()

    month_start = pd.to_datetime(f"{month_key}-01")
    month_end = month_start + pd.offsets.MonthEnd(1)
    prev_end = month_start - pd.Timedelta(days=1)

    def is_emergency(dataframe):
        return (
            dataframe["type"].eq("비상금")
            | dataframe["category"].isin(LIVING_EMERGENCY_CATEGORY_OPTIONS)
        )

    prev_df = temp[temp["date_dt"] <= prev_end].copy()
    prev_normal_df = prev_df[~is_emergency(prev_df)].copy()
    prev_total_balance = int(prev_normal_df["amount"].sum())

    prev_emergency_put = abs(int(
        prev_df[prev_df["category"] == "비상금 넣기"]["amount"].sum()
    ))
    prev_emergency_take = int(
        prev_df[prev_df["category"] == "비상금 빼기"]["amount"].sum()
    )
    prev_emergency_balance = prev_emergency_put - prev_emergency_take

    carryover = prev_total_balance - prev_emergency_balance

    month_df = temp[
        (temp["date_dt"] >= month_start) &
        (temp["date_dt"] <= month_end)
    ].copy()
    month_normal_df = month_df[~is_emergency(month_df)].copy()

    month_income = int(month_normal_df[month_normal_df["amount"] > 0]["amount"].sum())
    month_expense = abs(int(month_normal_df[month_normal_df["amount"] < 0]["amount"].sum()))

    current_df = temp[temp["date_dt"] <= month_end].copy()
    current_normal_df = current_df[~is_emergency(current_df)].copy()
    total_balance = int(current_normal_df["amount"].sum())

    emergency_put = abs(int(
        current_df[current_df["category"] == "비상금 넣기"]["amount"].sum()
    ))
    emergency_take = int(
        current_df[current_df["category"] == "비상금 빼기"]["amount"].sum()
    )
    emergency_balance = emergency_put - emergency_take

    available_balance = total_balance - emergency_balance

    return {
        "carryover": carryover,
        "income": month_income,
        "expense": month_expense,
        "emergency": emergency_balance,
        "available": available_balance,
    }


def render_living_tab(get_worksheet_func, render_budget_card):
    living_df = load_living_df(get_worksheet_func)

    st.subheader("🏦 생활비 통장")

    month_options = get_living_month_options(living_df)
    current_month = datetime.today().strftime("%Y-%m")

    top_left, top_right = st.columns([1, 1])

    with top_left:
        if (
            "living_selected_month" not in st.session_state
            or st.session_state["living_selected_month"] not in month_options
        ):
            st.session_state["living_selected_month"] = current_month

        living_month = st.selectbox(
            "월 선택",
            month_options,
            key="living_selected_month"
        )

    with top_right:
        living_q = st.text_input(
            "검색(카테고리/메모/구분)",
            placeholder="예: 식비 / 관리비 / 입금 / 비상금",
            key="living_search_text"
        )

    summary = calc_living_summary(living_df, living_month)

    c1, c2, c3, c4, c5 = st.columns(5)

    with c1:
        render_budget_card("이월금액", f"{summary['carryover']:,}원", "#F8FBF7", "#D9E8D4", "#4D6B50")
    with c2:
        render_budget_card("입금", f"{summary['income']:,}원", "#F3F8FF", "#D8E6F8", "#4A6688")
    with c3:
        render_budget_card("지출", f"{summary['expense']:,}원", "#FFF7F5", "#F2D9D2", "#8A5A4A")
    with c4:
        render_budget_card("비상금", f"{summary['emergency']:,}원", "#FFF9E9", "#F2E1A8", "#8A6A00")
    with c5:
        render_budget_card("가용생활비", f"{summary['available']:,}원", "#F7F3FF", "#DCCBFA", "#6C48A6")

    st.divider()
    st.subheader("✍ 생활비 입력")

    if "living_date" not in st.session_state:
        st.session_state["living_date"] = date.today()
    if "living_type" not in st.session_state:
        st.session_state["living_type"] = "지출"
    if "living_category" not in st.session_state:
        st.session_state["living_category"] = LIVING_EXPENSE_CATEGORY_OPTIONS[0]
    if "living_memo" not in st.session_state:
        st.session_state["living_memo"] = ""
    if "living_amount" not in st.session_state:
        st.session_state["living_amount"] = ""

    if st.session_state.get("living_form_reset"):
        st.session_state["living_date"] = date.today()
        st.session_state["living_type"] = "지출"
        st.session_state["living_category"] = LIVING_EXPENSE_CATEGORY_OPTIONS[0]
        st.session_state["living_memo"] = ""
        st.session_state["living_amount"] = ""
        st.session_state["living_form_reset"] = False

    f1, f2, f3, f4, f5 = st.columns(5)

    with f1:
        living_date = st.date_input(
            "날짜",
            key="living_date"
        )

    with f2:
        living_type = st.selectbox(
            "구분",
            LIVING_TYPE_OPTIONS,
            key="living_type"
        )

    with f3:
        if living_type == "입금":
            category_options = LIVING_INCOME_CATEGORY_OPTIONS
        elif living_type == "비상금":
            category_options = LIVING_EMERGENCY_CATEGORY_OPTIONS
        else:
            category_options = LIVING_EXPENSE_CATEGORY_OPTIONS

        if st.session_state.get("living_category") not in category_options:
            st.session_state["living_category"] = category_options[0]

        living_category = st.selectbox(
            "카테고리",
            category_options,
            key="living_category"
        )

    with f4:
        living_memo = st.text_input(
            "메모",
            key="living_memo"
        )

    with f5:
        living_amount_text = st.text_input(
            "금액",
            placeholder="금액 입력",
            key="living_amount"
        )

    living_saved = st.button("➕ 생활비 저장", use_container_width=True)

    if living_saved:
        amount_clean = living_amount_text.replace(",", "").strip()

        if not amount_clean:
            st.error("금액을 입력해줘.")
        elif not re.fullmatch(r"\d+", amount_clean):
            st.error("금액은 숫자만 입력해줘.")
        else:
            amount_value = int(amount_clean)

            if living_type == "입금":
                final_amount = amount_value
            elif living_type == "비상금":
                final_amount = -amount_value if living_category == "비상금 넣기" else amount_value
            else:
                final_amount = -amount_value

            new_row = {
                "date": str(living_date),
                "amount": final_amount,
                "category": living_category,
                "method": LIVING_DEFAULT_METHOD,
                "memo": living_memo,
                "type": living_type,
            }

            current_df = load_living_df(get_worksheet_func)
            current_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
            save_living_df(current_df, get_worksheet_func)

            st.success("✅ 생활비 저장 완료!")
            st.session_state["living_form_reset"] = True
            st.rerun()

    @st.dialog("✏ 생활비 기록 수정")
    def edit_living_dialog(rid: int):
        current_df = load_living_df(get_worksheet_func)

        if rid >= len(current_df):
            st.error("수정할 데이터를 찾지 못했어요.")
            return

        row = current_df.iloc[rid]
        row_category = str(row["category"]).strip()
        row_amount = int(row["amount"])
        row_type = str(row.get("type", "")).strip()

        if not row_type:
            if row_category in LIVING_EMERGENCY_CATEGORY_OPTIONS:
                row_type = "비상금"
            elif row_amount > 0:
                row_type = "입금"
            else:
                row_type = "지출"

        if row_type == "입금":
            category_options = LIVING_INCOME_CATEGORY_OPTIONS
        elif row_type == "비상금":
            category_options = LIVING_EMERGENCY_CATEGORY_OPTIONS
        else:
            category_options = LIVING_EXPENSE_CATEGORY_OPTIONS

        type_index = LIVING_TYPE_OPTIONS.index(row_type) if row_type in LIVING_TYPE_OPTIONS else 0
        category_index = category_options.index(row_category) if row_category in category_options else 0

        with st.form(f"living_edit_form_{rid}"):
            q1, q2 = st.columns(2)

            with q1:
                d = st.date_input(
                    "날짜",
                    value=pd.to_datetime(row["date"], errors="coerce"),
                    key=f"living_edit_date_{rid}"
                )
                edit_type = st.selectbox(
                    "구분",
                    LIVING_TYPE_OPTIONS,
                    index=type_index,
                    key=f"living_edit_type_{rid}"
                )

            with q2:
                if edit_type == "입금":
                    edit_category_options = LIVING_INCOME_CATEGORY_OPTIONS
                elif edit_type == "비상금":
                    edit_category_options = LIVING_EMERGENCY_CATEGORY_OPTIONS
                else:
                    edit_category_options = LIVING_EXPENSE_CATEGORY_OPTIONS

                if row_category not in edit_category_options:
                    edit_category_index = 0
                else:
                    edit_category_index = edit_category_options.index(row_category)

                edit_category = st.selectbox(
                    "카테고리",
                    edit_category_options,
                    index=edit_category_index,
                    key=f"living_edit_category_{rid}"
                )

            q3, q4 = st.columns(2)

            with q3:
                memo = st.text_input(
                    "메모",
                    value=str(row["memo"]),
                    key=f"living_edit_memo_{rid}"
                )

            with q4:
                amount_text = st.text_input(
                    "금액",
                    value=f"{abs(row_amount):,}",
                    key=f"living_edit_amount_{rid}"
                )

            col_cancel, col_save = st.columns(2)

            with col_cancel:
                canceled = st.form_submit_button("취소", use_container_width=True)

            with col_save:
                saved = st.form_submit_button("💾 저장", use_container_width=True)

        if saved:
            amount_clean = amount_text.replace(",", "").strip()

            if not amount_clean or not re.fullmatch(r"\d+", amount_clean):
                st.error("금액은 숫자만 입력해줘.")
            else:
                amount_value = int(amount_clean)

                if edit_type == "입금":
                    final_amount = amount_value
                elif edit_type == "비상금":
                    final_amount = -amount_value if edit_category == "비상금 넣기" else amount_value
                else:
                    final_amount = -amount_value

                current_df.iloc[rid] = [
                    str(d),
                    final_amount,
                    edit_category,
                    LIVING_DEFAULT_METHOD,
                    memo,
                    edit_type,
                ]

                save_living_df(current_df, get_worksheet_func)
                st.success("수정 완료!")
                st.rerun()

        if canceled:
            st.rerun()

    st.divider()
    st.subheader("🧾 생활비 내역")

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

        def get_row_type(r):
            row_type = str(r.get("type", "")).strip()
            if row_type:
                return row_type
            if r["category"] in LIVING_EMERGENCY_CATEGORY_OPTIONS:
                return "비상금"
            return "입금" if int(r["amount"]) > 0 else "지출"

        row_type_series = living_view.apply(get_row_type, axis=1)

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

    if living_view.empty:
        st.write("생활비 내역이 없어요.")
    else:
        living_view_with_idx = living_view.copy()
        living_view_with_idx["row_id"] = living_view_with_idx.index
        living_view_with_idx = living_view_with_idx.reset_index(drop=True)

        total_rows = len(living_view_with_idx)
        total_pages = (total_rows - 1) // LIVING_PAGE_SIZE + 1

        living_view_key = f"{living_month}|{living_q}"
        if "living_last_view_key" not in st.session_state:
            st.session_state["living_last_view_key"] = living_view_key

        if "living_record_page" not in st.session_state:
            st.session_state["living_record_page"] = 1

        if st.session_state["living_last_view_key"] != living_view_key:
            st.session_state["living_record_page"] = 1
            st.session_state["living_last_view_key"] = living_view_key

        if st.session_state["living_record_page"] > total_pages:
            st.session_state["living_record_page"] = total_pages
        if st.session_state["living_record_page"] < 1:
            st.session_state["living_record_page"] = 1

        start_idx = (st.session_state["living_record_page"] - 1) * LIVING_PAGE_SIZE
        end_idx = start_idx + LIVING_PAGE_SIZE

        page_view = living_view_with_idx.iloc[start_idx:end_idx].copy()
        page_view["번호"] = range(start_idx + 1, min(end_idx, total_rows) + 1)

        st.markdown(
            f"<div style='text-align:right; font-size:13px; opacity:0.75;'>총 {total_rows}건</div>",
            unsafe_allow_html=True
        )

        h1, h2, h3, h4, h5, h6, h7, h8 = st.columns([0.7, 1.2, 1.0, 1.2, 2.6, 1.2, 0.8, 0.8])
        h1.markdown("<div class='table-head'>번호</div>", unsafe_allow_html=True)
        h2.markdown("<div class='table-head'>날짜</div>", unsafe_allow_html=True)
        h3.markdown("<div class='table-head'>구분</div>", unsafe_allow_html=True)
        h4.markdown("<div class='table-head'>카테고리</div>", unsafe_allow_html=True)
        h5.markdown("<div class='table-head'>메모</div>", unsafe_allow_html=True)
        h6.markdown("<div class='table-head'>금액</div>", unsafe_allow_html=True)
        h7.markdown("<div class='table-head'>삭제</div>", unsafe_allow_html=True)
        h8.markdown("<div class='table-head'>수정</div>", unsafe_allow_html=True)

        for _, r in page_view.iterrows():
            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns([0.7, 1.2, 1.0, 1.2, 2.6, 1.2, 0.8, 0.8])

            row_type = str(r.get("type", "")).strip()
            if not row_type:
                if r["category"] in LIVING_EMERGENCY_CATEGORY_OPTIONS:
                    row_type = "비상금"
                else:
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

            rid = int(r["row_id"])

            with c7:
                if st.button("🗑", key=f"living_del_{rid}", use_container_width=True):
                    current_df = load_living_df(get_worksheet_func)
                    current_df = current_df.drop(index=rid).reset_index(drop=True)
                    save_living_df(current_df, get_worksheet_func)
                    st.success("삭제 완료!")
                    st.rerun()

            with c8:
                if st.button("✏", key=f"living_edit_{rid}", use_container_width=True):
                    edit_living_dialog(rid)

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

            row_type = str(r.get("type", "")).strip()
            if not row_type:
                if r["category"] in LIVING_EMERGENCY_CATEGORY_OPTIONS:
                    row_type = "비상금"
                else:
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
