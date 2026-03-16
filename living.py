import re
from datetime import date, datetime

import pandas as pd
import streamlit as st


LIVING_COLUMNS = ["date", "amount", "category", "method", "memo"]

LIVING_CATEGORY_OPTIONS = [
    "식비",
    "장보기",
    "생활용품",
    "공과금",
    "주거/관리비",
    "교통",
    "경조사",
    "기타",
]

LIVING_METHOD_OPTIONS = [
    "생활비통장",
    "현대카드",
    "신한카드",
    "현금",
]

LIVING_DEFAULT_METHOD = "생활비통장"


@st.cache_data(ttl=60)
def load_living_df(get_worksheet_func) -> pd.DataFrame:
    try:
        ws = get_worksheet_func("living")
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

            if typ == "환급":
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


def save_living_df(df: pd.DataFrame, get_worksheet_func) -> None:
    ws = get_worksheet_func("living")

    save_data = df[LIVING_COLUMNS].copy().fillna("")

    save_data["date_dt"] = pd.to_datetime(save_data["date"], errors="coerce")
    save_data = save_data.sort_values(
        by=["date_dt", "date"],
        ascending=[False, False]
    ).drop(columns=["date_dt"])

    save_data["구분"] = save_data["amount"].apply(
        lambda x: "환급" if int(x) > 0 else "지출"
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
    living_refund = int(month_df[month_df["amount"] > 0]["amount"].sum())
    living_net = living_spent - living_refund

    c1, c2, c3 = st.columns(3)

    with c1:
        render_budget_card("이번달 지출", f"{living_spent:,}원", "#F8FBF7", "#D9E8D4", "#4D6B50")
    with c2:
        render_budget_card("이번달 환급", f"{living_refund:,}원", "#F3F8FF", "#D8E6F8", "#4A6688")
    with c3:
        render_budget_card("순지출", f"{living_net:,}원", "#FFF7F5", "#F2D9D2", "#8A5A4A")

    st.divider()

    st.subheader("✍ 생활비 입력")

    with st.form("living_add_form", clear_on_submit=True):
        f1, f2, f3 = st.columns(3)

        with f1:
            living_date = st.date_input("날짜", value=date.today(), key="living_date")
            living_category = st.selectbox(
                "카테고리",
                LIVING_CATEGORY_OPTIONS,
                index=0,
                key="living_category"
            )

        with f2:
            living_memo = st.text_input("메모", value="", key="living_memo")
            living_amount_text = st.text_input(
                "금액",
                value="",
                placeholder="금액 입력",
                key="living_amount"
            )

        with f3:
            living_method = st.selectbox(
                "결제수단",
                LIVING_METHOD_OPTIONS,
                index=LIVING_METHOD_OPTIONS.index(LIVING_DEFAULT_METHOD),
                key="living_method"
            )
            living_type = st.selectbox(
                "구분",
                ["지출", "환급"],
                index=0,
                key="living_type"
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
            final_amount = amount_value if living_type == "환급" else -amount_value

            new_row = {
                "date": str(living_date),
                "amount": final_amount,
                "category": living_category,
                "method": living_method,
                "memo": living_memo,
            }

            current_df = load_living_df(get_worksheet_func)
            current_df = pd.concat([current_df, pd.DataFrame([new_row])], ignore_index=True)
            save_living_df(current_df, get_worksheet_func)

            st.success("✅ 생활비 저장 완료!")
            st.rerun()

    st.divider()

    st.subheader("🧾 생활비 내역")

    living_view = living_df.copy()
    living_view["date_dt"] = pd.to_datetime(living_view["date"], errors="coerce")
    living_view = living_view.sort_values(by=["date_dt"], ascending=False)

    if living_view.empty:
        st.write("생활비 내역이 없어요.")
        return

    living_view = living_view.reset_index(drop=True)
    living_view["번호"] = range(1, len(living_view) + 1)

    h1, h2, h3, h4, h5, h6, h7 = st.columns([0.7, 1.1, 1.0, 1.2, 2.4, 1.2, 1.2])
    h1.markdown("<div class='table-head'>번호</div>", unsafe_allow_html=True)
    h2.markdown("<div class='table-head'>날짜</div>", unsafe_allow_html=True)
    h3.markdown("<div class='table-head'>구분</div>", unsafe_allow_html=True)
    h4.markdown("<div class='table-head'>카테고리</div>", unsafe_allow_html=True)
    h5.markdown("<div class='table-head'>메모</div>", unsafe_allow_html=True)
    h6.markdown("<div class='table-head'>금액</div>", unsafe_allow_html=True)
    h7.markdown("<div class='table-head'>결제수단</div>", unsafe_allow_html=True)

    for _, r in living_view.iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([0.7, 1.1, 1.0, 1.2, 2.4, 1.2, 1.2])

        row_type = "환급" if int(r["amount"]) > 0 else "지출"

        c1.markdown(f"<div class='row-box'>{r['번호']}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='row-box'>{r['date']}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='row-box'>{row_type}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='row-box'><span class='cat-tag'>{r['category']}</span></div>", unsafe_allow_html=True)
        c5.markdown(f"<div class='row-box'>{r['memo']}</div>", unsafe_allow_html=True)

        amount_display = f"{abs(int(r['amount'])):,}원"
        if int(r["amount"]) > 0:
            amount_html = f"<div class='row-box amount-text'>➕ {amount_display}</div>"
        else:
            amount_html = f"<div class='row-box amount-text'>💸 {amount_display}</div>"

        c6.markdown(amount_html, unsafe_allow_html=True)
        c7.markdown(f"<div class='row-box'>{r['method']}</div>", unsafe_allow_html=True)