import os
import re
import base64
import socket
from io import BytesIO
from datetime import date, datetime

import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

FILE = "money.csv"
CHECKLIST_FILE = "checklist.csv"
COLUMNS = ["date", "amount", "category", "method", "memo"]

CATEGORY_OPTIONS = ["쇼핑", "외식", "배달", "커피", "고정비", "사건비"]
METHOD_OPTIONS = ["현대카드", "신한카드", "사건비통장"]
DEFAULT_METHOD = "현대카드"
MONTHLY_BUDGET = 600000
BUDGET_METHOD = "현대카드"
PAGE_SIZE = 10

AUTO_CATEGORY = {
    "스타벅스": "커피",
    "커피": "커피",
    "카페": "커피",
    "배민": "배달",
    "요기요": "배달",
    "쿠팡이츠": "배달",
    "쿠팡": "쇼핑",
    "다이소": "쇼핑",
    "올리브영": "쇼핑",
    "편의점": "쇼핑",
    "마트": "쇼핑",
    "우유": "쇼핑",
}

AUTO_SHINHAN = [
    "주유",
    "통신비",
    "쿠팡와우",
    "이모티콘",
    "톨게이트",
]

INCIDENT_INCOME_KEYWORDS = ["환급", "입금", "수입", "보험금"]

CHECKLIST_ITEMS = [
    "공용 생활비 : 100만",
    "사건비 통장 : 20만",
    "수원 지역화폐 충전 : 10만",
    "모임비 : 19만",
    "정기 주차비 : 8만",
    "적금 : 30만",
    "청약 : 2만",
    "보험료1 : 23,226원",
    "보험료2 : 60,712원",
]

# -----------------------
# 테마 설정
# -----------------------
THEMES = {
    "strawberry": {
        "app_bg_1": "#FFF7FB",
        "app_bg_2": "#FFF1F6",
        "container_bg": "rgba(255, 250, 253, 0.55)",
        "input_border": "rgba(255,143,177,0.35)",
        "input_bg": "rgba(255,255,255,0.78)",
        "button_bg_1": "#FFD1E1",
        "button_bg_2": "#FFB6CF",
        "button_border": "rgba(255,143,177,0.35)",
        "button_text": "#2E2A2B",
        "button_shadow": "rgba(255,143,177,0.18)",
        "line": "rgba(255,143,177,0.25)",
        "metric_border": "rgba(255,143,177,0.25)",
        "expander_border": "rgba(255,143,177,0.18)",
        "form_border": "rgba(255,143,177,0.15)",
        "table_head_bg": "rgba(255,209,225,0.65)",
        "table_head_border": "rgba(255,143,177,0.25)",
        "table_head_text": "#7A4B5A",
        "row_hover": "rgba(255,143,177,0.08)",
        "amount_text": "#C33B5E",
        "cat_bg": "rgba(255,182,207,0.35)",
        "cat_text": "#7A4B5A",
        "filter_bg": "rgba(255,255,255,0.80)",
        "filter_border": "rgba(255,143,177,0.35)",
        "filter_hover": "rgba(255,209,225,0.25)",
        "filter_active_1": "#FFD1E1",
        "filter_active_2": "#FFB6CF",
        "filter_active_border": "rgba(255,143,177,0.55)",
        "filter_shadow": "rgba(255,143,177,0.18)",
        "date_text": "#A85E74"
    },
    "latte": {
        "app_bg_1": "#FCF8F3",
        "app_bg_2": "#F7F0E8",
        "container_bg": "rgba(255, 252, 247, 0.65)",
        "input_border": "rgba(181,153,120,0.30)",
        "input_bg": "rgba(255,255,255,0.82)",
        "button_bg_1": "#F7E7D2",
        "button_bg_2": "#EFD6B6",
        "button_border": "rgba(181,153,120,0.30)",
        "button_text": "#4E3F33",
        "button_shadow": "rgba(180,150,120,0.14)",
        "line": "rgba(181,153,120,0.22)",
        "metric_border": "rgba(181,153,120,0.22)",
        "expander_border": "rgba(181,153,120,0.18)",
        "form_border": "rgba(181,153,120,0.15)",
        "table_head_bg": "rgba(239,214,182,0.65)",
        "table_head_border": "rgba(181,153,120,0.20)",
        "table_head_text": "#6B5443",
        "row_hover": "rgba(239,214,182,0.18)",
        "amount_text": "#A75A2A",
        "cat_bg": "rgba(239,214,182,0.45)",
        "cat_text": "#6B5443",
        "filter_bg": "rgba(255,255,255,0.82)",
        "filter_border": "rgba(181,153,120,0.30)",
        "filter_hover": "rgba(239,214,182,0.22)",
        "filter_active_1": "#F7E7D2",
        "filter_active_2": "#EFD6B6",
        "filter_active_border": "rgba(181,153,120,0.45)",
        "filter_shadow": "rgba(180,150,120,0.16)",
        "date_text": "#8B6B4A"
    },
    "modern": {
        "app_bg_1": "#F7F7F8",
        "app_bg_2": "#EFEFF2",
        "container_bg": "rgba(255,255,255,0.62)",
        "input_border": "rgba(160,160,170,0.28)",
        "input_bg": "rgba(255,255,255,0.88)",
        "button_bg_1": "#EAEAEA",
        "button_bg_2": "#D8D8DD",
        "button_border": "rgba(160,160,170,0.30)",
        "button_text": "#2E2E33",
        "button_shadow": "rgba(120,120,130,0.10)",
        "line": "rgba(160,160,170,0.20)",
        "metric_border": "rgba(160,160,170,0.20)",
        "expander_border": "rgba(160,160,170,0.18)",
        "form_border": "rgba(160,160,170,0.14)",
        "table_head_bg": "rgba(225,225,232,0.75)",
        "table_head_border": "rgba(160,160,170,0.18)",
        "table_head_text": "#555763",
        "row_hover": "rgba(200,200,210,0.14)",
        "amount_text": "#4E5968",
        "cat_bg": "rgba(225,225,232,0.55)",
        "cat_text": "#555763",
        "filter_bg": "rgba(255,255,255,0.86)",
        "filter_border": "rgba(160,160,170,0.28)",
        "filter_hover": "rgba(225,225,232,0.30)",
        "filter_active_1": "#EAEAEA",
        "filter_active_2": "#D8D8DD",
        "filter_active_border": "rgba(160,160,170,0.42)",
        "filter_shadow": "rgba(120,120,130,0.12)",
        "date_text": "#5B5E68"
    },
    "green": {
        "app_bg_1": "#F5FFF8",
        "app_bg_2": "#EAF7EE",
        "container_bg": "rgba(250,255,251,0.68)",
        "input_border": "rgba(124,181,139,0.30)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#D7F2DD",
        "button_bg_2": "#BDE8C7",
        "button_border": "rgba(124,181,139,0.32)",
        "button_text": "#2D5C38",
        "button_shadow": "rgba(124,181,139,0.14)",
        "line": "rgba(124,181,139,0.20)",
        "metric_border": "rgba(124,181,139,0.20)",
        "expander_border": "rgba(124,181,139,0.18)",
        "form_border": "rgba(124,181,139,0.15)",
        "table_head_bg": "rgba(189,232,199,0.65)",
        "table_head_border": "rgba(124,181,139,0.20)",
        "table_head_text": "#3D6E49",
        "row_hover": "rgba(189,232,199,0.18)",
        "amount_text": "#2F8A4B",
        "cat_bg": "rgba(189,232,199,0.45)",
        "cat_text": "#3D6E49",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(124,181,139,0.30)",
        "filter_hover": "rgba(189,232,199,0.22)",
        "filter_active_1": "#D7F2DD",
        "filter_active_2": "#BDE8C7",
        "filter_active_border": "rgba(124,181,139,0.45)",
        "filter_shadow": "rgba(124,181,139,0.16)",
        "date_text": "#3D7A57"
    },
    "blue": {
        "app_bg_1": "#F5FAFF",
        "app_bg_2": "#EAF3FF",
        "container_bg": "rgba(250,252,255,0.68)",
        "input_border": "rgba(126,170,220,0.30)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#D9EBFF",
        "button_bg_2": "#BCD8F8",
        "button_border": "rgba(126,170,220,0.32)",
        "button_text": "#2C527A",
        "button_shadow": "rgba(126,170,220,0.14)",
        "line": "rgba(126,170,220,0.20)",
        "metric_border": "rgba(126,170,220,0.20)",
        "expander_border": "rgba(126,170,220,0.18)",
        "form_border": "rgba(126,170,220,0.15)",
        "table_head_bg": "rgba(188,216,248,0.65)",
        "table_head_border": "rgba(126,170,220,0.20)",
        "table_head_text": "#416B96",
        "row_hover": "rgba(188,216,248,0.18)",
        "amount_text": "#2F6FAD",
        "cat_bg": "rgba(188,216,248,0.45)",
        "cat_text": "#416B96",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(126,170,220,0.30)",
        "filter_hover": "rgba(188,216,248,0.22)",
        "filter_active_1": "#D9EBFF",
        "filter_active_2": "#BCD8F8",
        "filter_active_border": "rgba(126,170,220,0.45)",
        "filter_shadow": "rgba(126,170,220,0.16)",
        "date_text": "#416B96"
    },
    "violet": {
        "app_bg_1": "#FAF7FF",
        "app_bg_2": "#F1EBFB",
        "container_bg": "rgba(252,250,255,0.68)",
        "input_border": "rgba(167,145,206,0.30)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#E6D9FA",
        "button_bg_2": "#D3C0F3",
        "button_border": "rgba(167,145,206,0.32)",
        "button_text": "#503A73",
        "button_shadow": "rgba(167,145,206,0.14)",
        "line": "rgba(167,145,206,0.20)",
        "metric_border": "rgba(167,145,206,0.20)",
        "expander_border": "rgba(167,145,206,0.18)",
        "form_border": "rgba(167,145,206,0.15)",
        "table_head_bg": "rgba(211,192,243,0.65)",
        "table_head_border": "rgba(167,145,206,0.20)",
        "table_head_text": "#6A548C",
        "row_hover": "rgba(211,192,243,0.18)",
        "amount_text": "#7B4FC9",
        "cat_bg": "rgba(211,192,243,0.45)",
        "cat_text": "#6A548C",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(167,145,206,0.30)",
        "filter_hover": "rgba(211,192,243,0.22)",
        "filter_active_1": "#E6D9FA",
        "filter_active_2": "#D3C0F3",
        "filter_active_border": "rgba(167,145,206,0.45)",
        "filter_shadow": "rgba(167,145,206,0.16)",
        "date_text": "#6A548C"
    },
    "mint": {
        "app_bg_1": "#F3FFFD",
        "app_bg_2": "#E6F9F6",
        "container_bg": "rgba(245,255,253,0.70)",
        "input_border": "rgba(130,210,195,0.30)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#CFF5EE",
        "button_bg_2": "#AEEDE2",
        "button_border": "rgba(130,210,195,0.30)",
        "button_text": "#285A53",
        "button_shadow": "rgba(130,210,195,0.14)",
        "line": "rgba(130,210,195,0.20)",
        "metric_border": "rgba(130,210,195,0.20)",
        "expander_border": "rgba(130,210,195,0.18)",
        "form_border": "rgba(130,210,195,0.15)",
        "table_head_bg": "rgba(174,237,226,0.62)",
        "table_head_border": "rgba(130,210,195,0.20)",
        "table_head_text": "#2B6B63",
        "row_hover": "rgba(174,237,226,0.18)",
        "amount_text": "#2B8F82",
        "cat_bg": "rgba(174,237,226,0.45)",
        "cat_text": "#2B6B63",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(130,210,195,0.30)",
        "filter_hover": "rgba(174,237,226,0.22)",
        "filter_active_1": "#CFF5EE",
        "filter_active_2": "#AEEDE2",
        "filter_active_border": "rgba(130,210,195,0.45)",
        "filter_shadow": "rgba(130,210,195,0.16)",
        "date_text": "#2B8F82"
    },
    "lemon": {
        "app_bg_1": "#FFFDEB",
        "app_bg_2": "#FFF8CC",
        "container_bg": "rgba(255,255,240,0.70)",
        "input_border": "rgba(230,210,120,0.35)",
        "input_bg": "rgba(255,255,255,0.86)",
        "button_bg_1": "#FFF3A3",
        "button_bg_2": "#FFE777",
        "button_border": "rgba(230,210,120,0.35)",
        "button_text": "#6D6200",
        "button_shadow": "rgba(230,210,120,0.14)",
        "line": "rgba(230,210,120,0.20)",
        "metric_border": "rgba(230,210,120,0.20)",
        "expander_border": "rgba(230,210,120,0.18)",
        "form_border": "rgba(230,210,120,0.15)",
        "table_head_bg": "rgba(255,231,119,0.50)",
        "table_head_border": "rgba(230,210,120,0.20)",
        "table_head_text": "#8A7A00",
        "row_hover": "rgba(255,231,119,0.18)",
        "amount_text": "#9A8B00",
        "cat_bg": "rgba(255,231,119,0.35)",
        "cat_text": "#8A7A00",
        "filter_bg": "rgba(255,255,255,0.86)",
        "filter_border": "rgba(230,210,120,0.35)",
        "filter_hover": "rgba(255,231,119,0.22)",
        "filter_active_1": "#FFF3A3",
        "filter_active_2": "#FFE777",
        "filter_active_border": "rgba(230,210,120,0.45)",
        "filter_shadow": "rgba(230,210,120,0.16)",
        "date_text": "#9A8B00"
    },
    "peach": {
        "app_bg_1": "#FFF6F1",
        "app_bg_2": "#FFEDE4",
        "container_bg": "rgba(255,250,247,0.70)",
        "input_border": "rgba(255,170,150,0.35)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#FFD6C6",
        "button_bg_2": "#FFBEA8",
        "button_border": "rgba(255,170,150,0.35)",
        "button_text": "#7A4A3A",
        "button_shadow": "rgba(255,170,150,0.14)",
        "line": "rgba(255,170,150,0.20)",
        "metric_border": "rgba(255,170,150,0.20)",
        "expander_border": "rgba(255,170,150,0.18)",
        "form_border": "rgba(255,170,150,0.15)",
        "table_head_bg": "rgba(255,190,168,0.50)",
        "table_head_border": "rgba(255,170,150,0.20)",
        "table_head_text": "#A45B49",
        "row_hover": "rgba(255,190,168,0.18)",
        "amount_text": "#C7654E",
        "cat_bg": "rgba(255,190,168,0.35)",
        "cat_text": "#A45B49",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(255,170,150,0.35)",
        "filter_hover": "rgba(255,190,168,0.22)",
        "filter_active_1": "#FFD6C6",
        "filter_active_2": "#FFBEA8",
        "filter_active_border": "rgba(255,170,150,0.45)",
        "filter_shadow": "rgba(255,170,150,0.16)",
        "date_text": "#C7654E"
    },
    "navy": {
        "app_bg_1": "#F4F6FA",
        "app_bg_2": "#E6EBF5",
        "container_bg": "rgba(250,252,255,0.70)",
        "input_border": "rgba(120,140,200,0.35)",
        "input_bg": "rgba(255,255,255,0.86)",
        "button_bg_1": "#B9C7E8",
        "button_bg_2": "#9FB2DE",
        "button_border": "rgba(120,140,200,0.35)",
        "button_text": "#31466E",
        "button_shadow": "rgba(120,140,200,0.14)",
        "line": "rgba(120,140,200,0.20)",
        "metric_border": "rgba(120,140,200,0.20)",
        "expander_border": "rgba(120,140,200,0.18)",
        "form_border": "rgba(120,140,200,0.15)",
        "table_head_bg": "rgba(159,178,222,0.50)",
        "table_head_border": "rgba(120,140,200,0.20)",
        "table_head_text": "#48608F",
        "row_hover": "rgba(159,178,222,0.18)",
        "amount_text": "#3A4F8A",
        "cat_bg": "rgba(159,178,222,0.35)",
        "cat_text": "#48608F",
        "filter_bg": "rgba(255,255,255,0.86)",
        "filter_border": "rgba(120,140,200,0.35)",
        "filter_hover": "rgba(159,178,222,0.22)",
        "filter_active_1": "#B9C7E8",
        "filter_active_2": "#9FB2DE",
        "filter_active_border": "rgba(120,140,200,0.45)",
        "filter_shadow": "rgba(120,140,200,0.16)",
        "date_text": "#3A4F8A"
    },
    "blackberry": {
        "app_bg_1": "#FBF7FF",
        "app_bg_2": "#EFE7FB",
        "container_bg": "rgba(250,245,255,0.70)",
        "input_border": "rgba(170,140,220,0.35)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#DCCBFA",
        "button_bg_2": "#C6AFF2",
        "button_border": "rgba(170,140,220,0.35)",
        "button_text": "#4E3B74",
        "button_shadow": "rgba(170,140,220,0.14)",
        "line": "rgba(170,140,220,0.20)",
        "metric_border": "rgba(170,140,220,0.20)",
        "expander_border": "rgba(170,140,220,0.18)",
        "form_border": "rgba(170,140,220,0.15)",
        "table_head_bg": "rgba(198,175,242,0.50)",
        "table_head_border": "rgba(170,140,220,0.20)",
        "table_head_text": "#6C48A6",
        "row_hover": "rgba(198,175,242,0.18)",
        "amount_text": "#6C48A6",
        "cat_bg": "rgba(198,175,242,0.35)",
        "cat_text": "#6C48A6",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(170,140,220,0.35)",
        "filter_hover": "rgba(198,175,242,0.22)",
        "filter_active_1": "#DCCBFA",
        "filter_active_2": "#C6AFF2",
        "filter_active_border": "rgba(170,140,220,0.45)",
        "filter_shadow": "rgba(170,140,220,0.16)",
        "date_text": "#6C48A6"
    },
    "rose_gold": {
        "app_bg_1": "#FFF7F5",
        "app_bg_2": "#FFEDEA",
        "container_bg": "rgba(255,248,246,0.70)",
        "input_border": "rgba(230,150,130,0.35)",
        "input_bg": "rgba(255,255,255,0.84)",
        "button_bg_1": "#FFD5CC",
        "button_bg_2": "#FFC1B6",
        "button_border": "rgba(230,150,130,0.35)",
        "button_text": "#7A4F45",
        "button_shadow": "rgba(230,150,130,0.14)",
        "line": "rgba(230,150,130,0.20)",
        "metric_border": "rgba(230,150,130,0.20)",
        "expander_border": "rgba(230,150,130,0.18)",
        "form_border": "rgba(230,150,130,0.15)",
        "table_head_bg": "rgba(255,193,182,0.50)",
        "table_head_border": "rgba(230,150,130,0.20)",
        "table_head_text": "#B96A5C",
        "row_hover": "rgba(255,193,182,0.18)",
        "amount_text": "#B96A5C",
        "cat_bg": "rgba(255,193,182,0.35)",
        "cat_text": "#B96A5C",
        "filter_bg": "rgba(255,255,255,0.84)",
        "filter_border": "rgba(230,150,130,0.35)",
        "filter_hover": "rgba(255,193,182,0.22)",
        "filter_active_1": "#FFD5CC",
        "filter_active_2": "#FFC1B6",
        "filter_active_border": "rgba(230,150,130,0.45)",
        "filter_shadow": "rgba(230,150,130,0.16)",
        "date_text": "#B96A5C"
    },
}

@st.cache_resource
def get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scopes,
    )
    return gspread.authorize(credentials)


def get_worksheet(sheet_name: str):
    client = get_gspread_client()
    spreadsheet = client.open(st.secrets["sheets"]["spreadsheet_name"])
    return spreadsheet.worksheet(sheet_name)

@st.cache_data(ttl=60)
def load_df() -> pd.DataFrame:
    try:
        ws = get_worksheet("money")
        values = ws.get_all_records()

        if not values:
            return pd.DataFrame(columns=COLUMNS)

        df = pd.DataFrame(values).fillna("")

        for c in COLUMNS:
            if c not in df.columns:
                df[c] = ""

        df = df[COLUMNS].copy()

        df["amount"] = (
            df["amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
        )
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

        df["date"] = df["date"].astype(str)
        df["category"] = df["category"].astype(str)
        df["method"] = df["method"].astype(str)
        df["memo"] = df["memo"].astype(str)

        return df

    except Exception:
        return pd.DataFrame(columns=COLUMNS)

def save_df(df: pd.DataFrame) -> None:
    ws = get_worksheet("money")

    save_data = df[COLUMNS].copy().fillna("")
    rows = [COLUMNS] + save_data.values.tolist()

    ws.clear()
    ws.update(rows)
    load_df.clear()

def get_month_sheet(gc, month_key):
    sh = gc.open("moneyLog")

    try:
        worksheet = sh.worksheet(month_key)
    except:
        worksheet = sh.add_worksheet(title=month_key, rows="1000", cols="20")

    return worksheet

def get_worksheet(sheet_name: str):
    client = get_gspread_client()
    spreadsheet = client.open(st.secrets["sheets"]["spreadsheet_name"])
    return spreadsheet.worksheet(sheet_name)

@st.cache_data(ttl=60)
def load_checklist_df() -> pd.DataFrame:
    try:
        ws = get_worksheet("checklist")
        values = ws.get_all_records()

        if not values:
            return pd.DataFrame(columns=["month", "item", "checked"])

        df = pd.DataFrame(values).fillna("")

        for c in ["month", "item", "checked"]:
            if c not in df.columns:
                df[c] = ""

        df = df[["month", "item", "checked"]].copy()
        df["month"] = df["month"].astype(str)
        df["item"] = df["item"].astype(str)
        df["checked"] = df["checked"].astype(str).map(
            lambda x: str(x).lower() in ["true", "1", "yes"]
        )

        return df

    except Exception:
        return pd.DataFrame(columns=["month", "item", "checked"])

def save_checklist_df(df: pd.DataFrame) -> None:
    ws = get_worksheet("checklist")

    save_data = df[["month", "item", "checked"]].copy().fillna("")
    rows = [["month", "item", "checked"]] + save_data.values.tolist()

    ws.clear()
    ws.update(rows)
    load_checklist_df.clear()

def get_month_checklist(month_key: str) -> pd.DataFrame:
    checklist_df = load_checklist_df()
    month_df = checklist_df[checklist_df["month"] == month_key].copy()

    if month_df.empty:
        month_df = pd.DataFrame({
            "month": [month_key] * len(CHECKLIST_ITEMS),
            "item": CHECKLIST_ITEMS,
            "checked": [False] * len(CHECKLIST_ITEMS),
        })
        checklist_df = pd.concat([checklist_df, month_df], ignore_index=True)
        save_checklist_df(checklist_df)
    else:
        existing_items = set(month_df["item"].tolist())
        missing_items = [x for x in CHECKLIST_ITEMS if x not in existing_items]

        if missing_items:
            add_df = pd.DataFrame({
                "month": [month_key] * len(missing_items),
                "item": missing_items,
                "checked": [False] * len(missing_items),
            })
            checklist_df = pd.concat([checklist_df, add_df], ignore_index=True)
            save_checklist_df(checklist_df)
            month_df = checklist_df[checklist_df["month"] == month_key].copy()

    return month_df


def update_checklist_item(month_key: str, item_name: str, checked_value: bool) -> None:
    checklist_df = load_checklist_df()
    mask = (checklist_df["month"] == month_key) & (checklist_df["item"] == item_name)

    if mask.any():
        checklist_df.loc[mask, "checked"] = checked_value
    else:
        add_row = pd.DataFrame([{
            "month": month_key,
            "item": item_name,
            "checked": checked_value,
        }])
        checklist_df = pd.concat([checklist_df, add_row], ignore_index=True)

    save_checklist_df(checklist_df)


def auto_category_from_text(text: str, fallback: str = "쇼핑") -> str:
    t = (text or "").strip()

    for k, v in AUTO_CATEGORY.items():
        if k and k in t:
            return v

    return fallback


def auto_card_and_category(text: str, default_category: str, default_method: str):
    t = (text or "").strip()

    for k in AUTO_SHINHAN:
        if k in t:
            return "고정비", "신한카드"

    category = auto_category_from_text(t, default_category)
    return category, default_method


def split_fuel_memo(memo: str):
    memo = (memo or "").strip()
    m = re.search(r"리터당\s*([\d,]+)원", memo)

    fuel_price = ""
    clean_memo = memo

    if m:
        fuel_price = m.group(1).replace(",", "")
        clean_memo = re.sub(r"\s*/?\s*리터당\s*[\d,]+원", "", memo).strip()
        clean_memo = re.sub(r"\s*/?\s*[\d.]+L", "", clean_memo).strip()

    return clean_memo, fuel_price


def is_incident_income(method: str, memo: str) -> bool:
    if method != "사건비통장":
        return False

    memo_text = (memo or "").strip()
    return any(k in memo_text for k in INCIDENT_INCOME_KEYWORDS)


def build_fuel_memo(memo: str, fuel_price_clean: str, amount_clean: str) -> str:
    final_memo = (memo or "").strip()

    if fuel_price_clean:
        fuel_price_int = int(fuel_price_clean)
        amount_int = int(amount_clean)
        liters = abs(amount_int) / fuel_price_int
        liters_str = f"{liters:.2f}L"

        if final_memo:
            return f"{final_memo} / 리터당 {fuel_price_int:,}원 / {liters_str}"
        return f"주유 / 리터당 {fuel_price_int:,}원 / {liters_str}"

    return final_memo


def parse_quick_input(text: str, default_category: str, default_method: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("빈 입력이에요.")

    tokens = text.split()
    if not tokens:
        raise ValueError("입력값이 없어요.")

    d = str(date.today())
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", tokens[0]):
        d = tokens[0]
        tokens = tokens[1:]
        if not tokens:
            raise ValueError("날짜만 있고 금액이 없어요. 예: 2026-03-01 우유 4500")

    method = default_method or DEFAULT_METHOD
    filtered_tokens = []

    for t in tokens:
        if t.startswith("@") and len(t) > 1:
            method = t[1:]
        else:
            filtered_tokens.append(t)

    amount = None
    memo_tokens = []

    for t in filtered_tokens:
        t_clean = t.replace(",", "")
        if amount is None and re.fullmatch(r"[+-]?\d+", t_clean):
            amount = int(t_clean)
        else:
            memo_tokens.append(t)

    if amount is None:
        raise ValueError("금액이 없어요. 예: 4500 우유 / 우유 4500")

    memo = " ".join(memo_tokens).strip()
    category, method = auto_card_and_category(memo, default_category, method)

    # 사건비통장 + 환급/입금/수입/보험금 => 수입(+)
    if method == "사건비통장" and any(k in memo for k in INCIDENT_INCOME_KEYWORDS):
        final_amount = abs(amount)
    else:
        final_amount = -abs(amount)

    return {
        "date": d,
        "amount": final_amount,
        "category": category,
        "method": method or DEFAULT_METHOD,
        "memo": memo,
    }


def get_month_options(df: pd.DataFrame):
    current_month = datetime.today().strftime("%Y-%m")

    if df.empty:
        return [current_month]

    dts = pd.to_datetime(df["date"], errors="coerce")
    months = sorted(
        {m.strftime("%Y-%m") for m in dts.dropna().dt.to_period("M").dt.to_timestamp()},
        reverse=True
    )

    if current_month not in months:
        months.insert(0, current_month)

    return months or [current_month]


def load_font():
    if not os.path.exists("leejieun.ttf"):
        return

    with open("leejieun.ttf", "rb") as f:
        font_bytes = f.read()

    encoded = base64.b64encode(font_bytes).decode()

    st.markdown(
        f"""
        <style>
        @font-face {{
            font-family: 'LeeJieun';
            src: url(data:font/ttf;base64,{encoded}) format('truetype');
            font-weight: normal;
            font-style: normal;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None


def budget_status(spent: int):
    ratio = spent / MONTHLY_BUDGET if MONTHLY_BUDGET > 0 else 0

    if ratio >= 1:
        return {
            "label": "초과",
            "bg": "#FFE3E8",
            "border": "#FF7A9A",
            "text": "#C33B5E",
        }
    elif ratio >= 0.8:
        return {
            "label": "거의 다 씀",
            "bg": "#FFF1E0",
            "border": "#FFB85C",
            "text": "#C97A00",
        }
    elif ratio >= 0.5:
        return {
            "label": "주의",
            "bg": "#FFF8D9",
            "border": "#E7C84C",
            "text": "#9A7A00",
        }
    else:
        return {
            "label": "여유",
            "bg": "#E9F9EF",
            "border": "#72D69B",
            "text": "#257A45",
        }


def render_budget_card(title: str, value: str, bg: str, border: str, text: str):
    st.markdown(
        f"""
        <div style="
            background:{bg};
            border:1px solid {border};
            border-radius:18px;
            padding:16px;
            min-height:105px;
            box-shadow:0 6px 18px rgba(0,0,0,0.04);
        ">
            <div style="font-size:14px; color:{text}; margin-bottom:8px;">{title}</div>
            <div style="font-size:28px; font-weight:800; color:{text};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# -----------------------------
# App
# -----------------------------
st.set_page_config(page_title="빠른 가계부", layout="wide")
df = load_df()
load_font()

theme_name = st.sidebar.selectbox(
    "🎨 테마 선택",
    list(THEMES.keys()),
    index=0,
    key="theme_select"
)

theme = THEMES[theme_name]

st.markdown(f"""
<style>
/* ===== 폰트 ===== */
html, body, [data-testid="stApp"], [data-testid="stAppViewContainer"],
[data-testid="stSidebar"], div, p, span, label, li {{
    font-family: "LeeJieun", "Segoe UI Emoji", "Apple Color Emoji", sans-serif;
}}

input,
textarea,
button,
label,
select,
input[type="text"],
input[type="number"],
input[type="date"] {{
    font-family: "LeeJieun", "Segoe UI Emoji", "Apple Color Emoji", sans-serif !important;
}}

div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input,
div[data-testid="stTextArea"] textarea,
[data-baseweb="select"] *,
div[data-testid="stSelectbox"] * {{
    font-family: "LeeJieun", "Segoe UI Emoji", "Apple Color Emoji", sans-serif !important;
}}

html, body, [data-testid="stAppViewContainer"] {{
    background: linear-gradient(180deg, {theme["app_bg_1"]} 0%, {theme["app_bg_2"]} 100%) !important;
}}

[data-testid="stAppViewContainer"] > .main {{
    background: transparent !important;
}}

.block-container {{
    padding-top: 1.2rem;
    max-width: 1400px;
    background: {theme["container_bg"]};
    border-radius: 24px;
}}

h1, h2, h3 {{
    font-weight: 800;
    letter-spacing: -1px;
}}

input, textarea {{
    border-radius: 14px !important;
    border: 1px solid {theme["input_border"]} !important;
    background: {theme["input_bg"]} !important;
}}

[data-baseweb="select"] > div {{
    border-radius: 14px !important;
    border: 1px solid {theme["input_border"]} !important;
    background: {theme["input_bg"]} !important;
    cursor: pointer !important;
}}

button:not([kind="primary"]) {
    border-radius: 16px !important;
    border: 1px solid {theme["button_border"]} !important;
    background: linear-gradient(180deg, {theme["button_bg_1"]}, {theme["button_bg_2"]}) !important;
    color: {theme["button_text"]} !important;
    font-weight: 700 !important;
    box-shadow: 0 10px 18px {theme["button_shadow"]} !important;
    transition: all 0.15s ease !important;
}}

button:hover {{
    transform: translateY(-1px);
}}

button[kind="secondary"] {{
    background: {theme["filter_bg"]} !important;
    border: 1px solid {theme["filter_border"]} !important;
    color: {theme["button_text"]} !important;
    box-shadow: none !important;
}}

button[kind="secondary"]:hover {{
    background: {theme["filter_hover"]} !important;
    border: 1px solid {theme["filter_active_border"]} !important;
    transform: translateY(-1px);
}}

button[kind="primary"] {{
    background: linear-gradient(180deg, {theme["filter_active_1"]}, {theme["filter_active_2"]}) !important;
    border: 1px solid {theme["filter_active_border"]} !important;
    color: {theme["button_text"]} !important;
    box-shadow: 0 8px 16px {theme["filter_shadow"]} !important;
    font-weight: 800 !important;
}}

button[kind="primary"]:hover {{
    background: linear-gradient(180deg, {theme["filter_active_1"]}, {theme["filter_active_2"]}) !important;
    border: 1px solid {theme["filter_active_border"]} !important;
}}

hr {{
    border: none;
    height: 1px;
    background: {theme["line"]};
    margin: 1.1rem 0;
}}

[data-testid="stMetric"] {{
    background: rgba(255,255,255,0.60);
    border-radius: 16px;
    padding: 10px;
    border: 1px solid {theme["metric_border"]};
}}

[data-testid="stForm"] {{
    background: rgba(255,255,255,0.45);
    border: 1px solid {theme["form_border"]};
    border-radius: 18px;
    padding: 14px;
}}

.table-head {{
    font-weight: 800;
    background: {theme["table_head_bg"]};
    border: 1px solid {theme["table_head_border"]};
    border-radius: 12px;
    padding: 8px 10px;
    text-align: center;
    color: {theme["table_head_text"]};
    margin-bottom: 4px;
}}

.row-box {{
    padding: 6px;
    border-radius: 10px;
    text-align: center;
}}

.row-box:hover {{
    background: {theme["row_hover"]};
}}

.amount-text {{
    font-weight: 800;
    color: {theme["amount_text"]};
}}

.cat-tag {{
    background: {theme["cat_bg"]};
    color: {theme["cat_text"]};
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    display: inline-block;
}}

.method-hyundai {{
    background: rgba(200,200,200,0.35);
    color: #4A4A4A;
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    display: inline-block;
}}

.method-shinhan {{
    background: rgba(180,220,255,0.45);
    color: #2F6F8F;
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    display: inline-block;
}}

.method-incident {{
    background: rgba(255,225,120,0.45);
    color: #8A6A00;
    padding: 4px 10px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 15px;
    display: inline-block;
}}

div[data-testid="stButton"] {{
    margin-top: 0 !important;
    margin-bottom: 0 !important;
}}

div[data-testid="stButton"] button {{
    padding: 2px 6px !important;
    min-height: 26px !important;
}}

label:has(input[type="checkbox"]) {{
    font-weight: 700;
}}

div[role="radiogroup"] {{
    gap: 8px !important;
    padding-left: 0px !important;
    margin-left: 0px !important;
}}

div[role="radiogroup"] * {{
    box-shadow: none !important;
}}

div[role="radiogroup"] label {{
    background: {theme["filter_bg"]} !important;
    border: 1px solid {theme["filter_border"]} !important;
    border-radius: 14px !important;
    padding: 8px 14px !important;
    min-height: 42px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
    transition: all 0.15s ease !important;
    margin-left: 0px !important;
}}

div[role="radiogroup"] label:hover {{
    background: {theme["filter_hover"]} !important;
    transform: translateY(-1px);
}}

div[role="radiogroup"] label:has(input:checked) {{
    background: linear-gradient(180deg, {theme["filter_active_1"]}, {theme["filter_active_2"]}) !important;
    border: 1px solid {theme["filter_active_border"]} !important;
    box-shadow: 0 8px 16px {theme["filter_shadow"]} !important;
    color: {theme["button_text"]} !important;
}}

div[role="radiogroup"] label > div:first-child {{
    display: none !important;
}}

div[role="radiogroup"] input[type="radio"] {{
    display: none !important;
}}

div[role="radiogroup"] input[type="radio"],
div[role="radiogroup"] input[type="radio"] + div,
div[role="radiogroup"] [data-testid="stMarkdownContainer"] + div {{
    accent-color: transparent !important;
}}

/* 탭 아래 border 라인 */
div[data-baseweb="tab-border"] {{
    background: {theme["table_head_border"]} !important;
}}

/* 탭 밑줄 */
div[data-baseweb="tab-highlight"] {{
    background: linear-gradient(90deg, {theme["button_bg_1"]}, {theme["button_bg_2"]}) !important;
    border-radius: 999px !important;
    height: 4px !important;
}}

/* 진행바 바깥 트랙 */
[data-testid="stProgress"] [data-baseweb="progress-bar"] > div {{
    background: rgba(255,255,255,0.55) !important;
    border: 1px solid {theme["metric_border"]} !important;
    border-radius: 999px !important;
    overflow: hidden !important;
}}

/* 진행바 채워지는 부분 */
[data-testid="stProgress"] [role="progressbar"] div[style*="width"],
[data-testid="stProgress"] [data-baseweb="progress-bar"] div div div {{
    background: linear-gradient(90deg, {theme["button_bg_1"]}, {theme["button_bg_2"]}) !important;
    border-radius: 999px !important;
}}
</style>
""", unsafe_allow_html=True)

# -------------------
# 상단 제목 + 오늘 날짜
# -------------------
weekday = ["월", "화", "수", "목", "금", "토", "일"]
today = datetime.today()
today_str = f"{today.strftime('%Y.%m.%d')} ({weekday[today.weekday()]})"

title_left, title_right = st.columns([3, 1])

with title_left:
    st.title("💸 빠른 가계부")

with title_right:
    st.markdown(
        f"""
        <div style="text-align:right;margin-top:10px;">
            <div style="font-size:14px;color:{theme["date_text"]};font-weight:700;">
                오늘
            </div>
            <div style="font-size:20px;font-weight:800;color:{theme["date_text"]};">
                {today_str}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# 공통 월 데이터
month_key = datetime.today().strftime("%Y-%m")
month_df = df.copy()
month_df["date_dt"] = pd.to_datetime(month_df["date"], errors="coerce")
month_df = month_df[month_df["date_dt"].dt.strftime("%Y-%m") == month_key]

# 예산은 현대카드만
spent = int(
    month_df[month_df["method"] == BUDGET_METHOD]["amount"]
    .abs()
    .sum()
)
remaining = MONTHLY_BUDGET - spent
percent = min(spent / MONTHLY_BUDGET, 1.0) if MONTHLY_BUDGET > 0 else 0
status = budget_status(spent)

# 카드별 월 합계
card_raw_sum = month_df.groupby("method")["amount"].sum()

hyundai_amount = abs(int(card_raw_sum.get("현대카드", 0)))
shinhan_amount = abs(int(card_raw_sum.get("신한카드", 0)))

# 사건비통장: 지출 / 환급 / 순금액 분리
incident_df = month_df[month_df["method"] == "사건비통장"].copy()

incident_spent = abs(int(incident_df[incident_df["amount"] < 0]["amount"].sum()))   # 쓴 금액
incident_refund = int(incident_df[incident_df["amount"] > 0]["amount"].sum())       # 환급 금액
incident_amount = incident_spent - incident_refund                                    # 총금액(순지출)

total_amount = hyundai_amount + shinhan_amount + incident_amount

# 탭
tab1, tab2 = st.tabs(["🏠 메인", "📊 내역"])
st.write("")

# -------------------
# 수정 모달
# -------------------
@st.dialog("✏ 기록 수정")
def edit_dialog(rid: int):
    current_df = load_df()

    if rid >= len(current_df):
        st.error("수정할 데이터를 찾지 못했어요.")
        return

    row = current_df.iloc[rid]
    current_cat = str(row["category"])
    cat_index = CATEGORY_OPTIONS.index(current_cat) if current_cat in CATEGORY_OPTIONS else 0

    with st.form(f"edit_form_{rid}"):
        d = st.date_input("날짜", value=pd.to_datetime(row["date"], errors="coerce"), key=f"edit_date_{rid}")
        category = st.selectbox("카테고리", CATEGORY_OPTIONS, index=cat_index, key=f"edit_cat_{rid}")

        base_memo, base_fuel_price = split_fuel_memo(str(row["memo"]))
        memo = st.text_input("메모", value=base_memo, key=f"edit_memo_{rid}")
        amount = st.text_input("금액", value=f"{abs(int(row['amount'])):,}", key=f"edit_amount_{rid}")
        fuel_price = st.text_input(
            "리터당 가격",
            value=base_fuel_price,
            placeholder="주유일 때만 입력",
            key=f"edit_fuel_price_{rid}"
        )

        current_method = str(row["method"]).strip() if str(row["method"]).strip() else DEFAULT_METHOD
        method_index = METHOD_OPTIONS.index(current_method) if current_method in METHOD_OPTIONS else 0
        method = st.selectbox("결제수단", METHOD_OPTIONS, index=method_index, key=f"edit_method_{rid}")

        col_a, col_b = st.columns(2)
        saved = col_a.form_submit_button("저장")
        canceled = col_b.form_submit_button("취소")

    if saved:
        amount_clean = amount.replace(",", "").strip()
        fuel_price_clean = fuel_price.replace(",", "").strip()

        if not amount_clean or not re.fullmatch(r"\d+", amount_clean):
            st.error("금액은 숫자만 입력해줘.")
        elif fuel_price_clean and not re.fullmatch(r"\d+", fuel_price_clean):
            st.error("리터당 가격은 숫자만 입력해줘.")
        else:
            final_memo = build_fuel_memo(memo, fuel_price_clean, amount_clean)
            final_category, final_method = auto_card_and_category(
                final_memo,
                category,
                method or DEFAULT_METHOD
            )

            amount_value = int(amount_clean)
            if is_incident_income(final_method, final_memo):
                final_amount = amount_value
            else:
                final_amount = -amount_value

            current_df.iloc[rid] = [
                str(d),
                final_amount,
                final_category,
                final_method,
                final_memo
            ]
            save_df(current_df)
            st.success("수정 완료!")
            st.rerun()

    if canceled:
        st.rerun()


if "pending_quick_entry" not in st.session_state:
    st.session_state.pending_quick_entry = None


def add_quick(amount: int, category: str, memo: str = "", method: str = DEFAULT_METHOD):
    global df

    amount = abs(int(amount))
    final_category, final_method = auto_card_and_category(memo, category, method)

    if is_incident_income(final_method, memo):
        final_amount = amount
    else:
        final_amount = -amount

    row = {
        "date": str(date.today()),
        "amount": final_amount,
        "category": final_category,
        "method": final_method,
        "memo": memo,
    }

    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_df(df)
    st.success("✅ 저장 완료!")
    st.rerun()


def open_quick_edit(amount: int, category: str, memo: str = "", method: str = DEFAULT_METHOD):
    st.session_state.pending_quick_entry = {
        "date": date.today(),
        "amount": abs(int(amount)),
        "category": category,
        "method": method,
        "memo": memo,
    }
    quick_add_dialog()


@st.dialog("📝 빠른 입력 수정")
def quick_add_dialog():
    item = st.session_state.get("pending_quick_entry")

    if not item:
        st.warning("등록할 항목이 없어요.")
        return

    current_cat = str(item["category"])
    cat_index = CATEGORY_OPTIONS.index(current_cat) if current_cat in CATEGORY_OPTIONS else 0

    current_method = str(item["method"]).strip() if str(item["method"]).strip() else DEFAULT_METHOD
    method_index = METHOD_OPTIONS.index(current_method) if current_method in METHOD_OPTIONS else 0

    base_memo, base_fuel_price = split_fuel_memo(str(item["memo"]))

    with st.form("quick_add_edit_form"):
        q1, q2 = st.columns(2)
    
        with q1:
            category = st.selectbox("카테고리", CATEGORY_OPTIONS, index=cat_index, key="quick_edit_cat")
            method = st.selectbox("결제수단", METHOD_OPTIONS, index=method_index, key="quick_edit_method")
            d = st.date_input("날짜", value=item["date"], key="quick_edit_date")
    
        with q2:
            memo = st.text_input("메모", value=base_memo, key="quick_edit_memo")
            amount_text = st.text_input("금액", value=f"{abs(int(item['amount'])):,}", key="quick_edit_amount")
            fuel_price = st.text_input(
                "리터당 가격",
                value=base_fuel_price,
                placeholder="주유일 때만 입력",
                key="quick_edit_fuel_price"
            )

        col_cancel, col_save = st.columns(2)

        with col_cancel:
            canceled = st.form_submit_button("취소", use_container_width=True)
        
        with col_save:
            saved = st.form_submit_button("💾 저장", use_container_width=True)

    if saved:
        amount_clean = amount_text.replace(",", "").strip()
        fuel_price_clean = fuel_price.replace(",", "").strip()

        if not amount_clean:
            st.error("금액을 입력해줘.")
        elif not re.fullmatch(r"\d+", amount_clean):
            st.error("금액은 숫자만 입력해줘.")
        elif fuel_price_clean and not re.fullmatch(r"\d+", fuel_price_clean):
            st.error("리터당 가격은 숫자만 입력해줘.")
        else:
            final_memo = build_fuel_memo(memo, fuel_price_clean, amount_clean)
            final_category, final_method = auto_card_and_category(
                final_memo,
                category,
                method or DEFAULT_METHOD
            )

            amount_value = int(amount_clean)
            if is_incident_income(final_method, final_memo):
                final_amount = amount_value
            else:
                final_amount = -amount_value

            row = {
                "date": str(d),
                "amount": final_amount,
                "category": final_category,
                "method": final_method,
                "memo": final_memo,
            }

            current_df = load_df()
            current_df = pd.concat([current_df, pd.DataFrame([row])], ignore_index=True)
            save_df(current_df)

            st.session_state.pending_quick_entry = None
            st.success("✅ 저장 완료!")
            st.rerun()

    if canceled:
        st.session_state.pending_quick_entry = None
        st.rerun()

with tab1:
    # -------------------
    # 상단 예산 현황
    # -------------------
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_budget_card(
            "이번달 예산",
            f"{MONTHLY_BUDGET:,}원",
            theme["container_bg"],
            theme["metric_border"],
            theme["button_text"]
        )
    
    with c2:
        render_budget_card(
            "지금까지 사용",
            f"{spent:,}원",
            theme["container_bg"],
            theme["metric_border"],
            theme["button_text"]
        )
    
    with c3:
        render_budget_card(
            "남은 금액",
            f"{remaining:,}원",
            theme["container_bg"],
            theme["metric_border"],
            theme["button_text"]
        )
    
    with c4:
        render_budget_card(
            "예산 상태",
            status["label"],
            status["bg"],
            status["border"],
            status["text"]
        )

    st.progress(percent)

    if spent > MONTHLY_BUDGET:
        st.warning(f"예산을 {spent - MONTHLY_BUDGET:,}원 초과했어요.")
    else:
        st.caption(f"{month_key} 예산 사용률: {percent * 100:.1f}%")

    # -------------------
    # 체크리스트
    # -------------------
    checklist_month_df = get_month_checklist(month_key)

    checked_count = int(checklist_month_df["checked"].sum())
    total_count = len(checklist_month_df)
    all_checked = total_count > 0 and checked_count == total_count

    expander_title = f"✅ 이번달 체크리스트 ({checked_count}/{total_count})"

    with st.expander(expander_title, expanded=not all_checked):
        check_cols = st.columns(2)

        checklist_df_reset = checklist_month_df.reset_index(drop=True)
        half = (len(checklist_df_reset) + 1) // 2

        left_items = checklist_df_reset.iloc[:half]
        right_items = checklist_df_reset.iloc[half:]

        with check_cols[0]:
            for _, row in left_items.iterrows():
                checked_now = st.checkbox(
                    row["item"],
                    value=bool(row["checked"]),
                    key=f"check_{month_key}_{row['item']}"
                )
                if checked_now != bool(row["checked"]):
                    update_checklist_item(month_key, row["item"], checked_now)
                    st.rerun()

        with check_cols[1]:
            for _, row in right_items.iterrows():
                checked_now = st.checkbox(
                    row["item"],
                    value=bool(row["checked"]),
                    key=f"check_{month_key}_{row['item']}"
                )
                if checked_now != bool(row["checked"]):
                    update_checklist_item(month_key, row["item"], checked_now)
                    st.rerun()

    st.divider()

    # -------------------
    # 카드별 이번달 사용
    # -------------------
    st.subheader("💳 카드별 이번달 사용")

    card_col1, card_col2, card_col3, card_col4 = st.columns(4)

    with card_col1:
        render_budget_card("현대카드", f"{hyundai_amount:,}원", "#F4F4F4", "#D6D6D6", "#4A4A4A")

    with card_col2:
        render_budget_card("신한카드", f"{shinhan_amount:,}원", "#F2FBFF", "#BFE8F7", "#3E7C91")

    with card_col3:
        render_budget_card("사건비통장", f"{incident_amount:,}원", "#FFF8CC", "#F2E18B", "#8A6A00")
        st.write("")
        st.caption(f"지출 {incident_spent:,}원 - 환급 {incident_refund:,}원 = 총 {incident_amount:,}원")

    with card_col4:
        render_budget_card("이번달 총 지출", f"{total_amount:,}원", "#FFEFF6", "#FFC4D6", "#A85E74")

    st.divider()

    # =========================
    # 날짜 선택 입력
    # =========================
    st.subheader("🗓 날짜 선택해서 입력")

    with st.form("manual_add", clear_on_submit=True):
        m1, m2, m3 = st.columns(3)

        with m1:
            d = st.date_input("날짜", value=date.today(), key="manual_date")
            category = st.selectbox(
                "카테고리",
                CATEGORY_OPTIONS,
                index=CATEGORY_OPTIONS.index("쇼핑"),
                key="manual_cat"
            )

        with m2:
            memo = st.text_input("메모", value="", key="manual_memo")
            amount_text = st.text_input("금액", value="", placeholder="금액 입력", key="manual_amount")

        with m3:
            fuel_price = st.text_input("리터당 가격", value="", placeholder="주유일 때만 입력", key="manual_fuel_price")
            method = st.selectbox(
                "결제수단",
                METHOD_OPTIONS,
                index=METHOD_OPTIONS.index(DEFAULT_METHOD),
                key="manual_method"
            )

        submitted_manual = st.form_submit_button("추가", use_container_width=True)

    if submitted_manual:
        amount_clean = amount_text.replace(",", "").strip()
        fuel_price_clean = fuel_price.replace(",", "").strip()

        if not amount_clean:
            st.error("금액을 입력해줘.")
        elif not re.fullmatch(r"\d+", amount_clean):
            st.error("금액은 숫자만 입력해줘. 예: 4500 또는 4,500")
        elif fuel_price_clean and not re.fullmatch(r"\d+", fuel_price_clean):
            st.error("리터당 가격은 숫자만 입력해줘.")
        else:
            final_memo = build_fuel_memo(memo, fuel_price_clean, amount_clean)
            final_category, final_method = auto_card_and_category(
                final_memo,
                category,
                method or DEFAULT_METHOD
            )

            amount_value = int(amount_clean)
            if is_incident_income(final_method, final_memo):
                final_amount = amount_value
            else:
                final_amount = -amount_value

            row = {
                "date": str(d),
                "amount": final_amount,
                "category": final_category,
                "method": final_method,
                "memo": final_memo,
            }
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
            save_df(df)
            st.success("✅ 저장 완료!")
            st.rerun()

    st.divider()

    # =========================
    # 입력예시 | 빠른입력
    # =========================
    left_col, right_col = st.columns([1, 1])

    with left_col:
        st.subheader("📝 입력 예시 / 규칙")
        st.markdown("""
- 빠른 입력: `금액 메모 @결제수단`
- 예: `12000 점심 @현대카드`
- `우유 1000` / `1000 우유` 둘 다 가능
- 날짜 지정: `YYYY-MM-DD`를 맨 앞에
- 예: `2026-03-01 4500 스타벅스 @현금`
- 사건비통장에서 `환급`, `입금`, `수입`, `보험금` 단어가 들어가면 자동 수입 처리
- 지정 키워드가 없으면 카테고리는 기본 `쇼핑`
""")

    with right_col:
        st.subheader("⚡ 빠른 입력")
        with st.form("quick_add", clear_on_submit=True):
            quick_category = st.selectbox(
                "카테고리",
                CATEGORY_OPTIONS,
                index=CATEGORY_OPTIONS.index("쇼핑"),
                key="quick_category_select"
            )
        
            quick = st.text_input(
                "입력",
                placeholder="4500 스타벅스 @현대카드",
                key="quick_input_text"
            )
        
            submitted_quick = st.form_submit_button("저장 (Enter)", use_container_width=True)        

        if submitted_quick:
            try:
                row = parse_quick_input(
                    quick,
                    default_category=quick_category,
                    default_method=DEFAULT_METHOD
                )
                df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                save_df(df)
                st.success("✅ 저장 완료!")
                st.rerun()
            except Exception as e:
                st.error(f"저장 실패: {e}")

    st.divider()

    # =========================
    # 빠른 입력 보조
    # =========================
    with st.expander("⚡ 빠른 입력 보조", expanded=False):
        top_left, top_right = st.columns([1, 1])

        with top_left:
            st.subheader("⚡ 자주 쓰는 버튼")

            b1, b2 = st.columns(2)
            b3, b4 = st.columns(2)

            with b1:
                if st.button("☕ 커피 4,500", use_container_width=True, key="btn_coffee"):
                    open_quick_edit(4500, "커피")

            with b2:
                if st.button("🍚 외식 12,000", use_container_width=True, key="btn_eatout"):
                    open_quick_edit(12000, "외식")

            with b3:
                if st.button("🛵 배달 18,000", use_container_width=True, key="btn_delivery"):
                    open_quick_edit(18000, "배달")

            with b4:
                if st.button("🛒 쇼핑 30,000", use_container_width=True, key="btn_shopping"):
                    open_quick_edit(30000, "쇼핑")

        with top_right:
            st.subheader("📌 신한카드 고정비")

            fix1, fix2 = st.columns(2)
            fix3, fix4 = st.columns(2)


            with fix1:
                if st.button("📱 통신비", use_container_width=True, key="btn_phone"):
                    open_quick_edit(129890, "고정비", "통신비", "신한카드")

            with fix2:
                if st.button("📦 쿠팡와우", use_container_width=True, key="btn_wow"):
                    open_quick_edit(7890, "고정비", "쿠팡와우", "신한카드")

            with fix3:
                if st.button("💬 이모티콘", use_container_width=True, key="btn_emoji"):
                    open_quick_edit(3900, "고정비", "이모티콘", "신한카드")
            with fix4:
                if st.button("⛽ 주유", use_container_width=True, key="btn_fuel"):
                    open_quick_edit(65000, "고정비", "주유", "신한카드")

    # -------------------
    # 폰에서도 쓰기 안내
    # -------------------
    local_ip = get_local_ip()
    with st.expander("📱 폰에서도 쓰기", expanded=False):
        if local_ip:
            st.markdown(
                f"""
같은 와이파이에서 폰 브라우저로 아래 주소 열면 돼:

`http://{local_ip}:8501`

`run.bat`은 아래처럼 쓰면 더 안정적이야:

`python -m streamlit run app.py --server.address 0.0.0.0`
"""
            )
        else:
            st.write("로컬 IP를 찾지 못했어요.")

with tab2:
    # =========================
    # 검색 / 월선택 / 다운로드
    # =========================
    top_filter_left, top_filter_right = st.columns([1, 1])

    with top_filter_left:
        month_options = get_month_options(df)
        current_month = datetime.today().strftime("%Y-%m")

        if "selected_month" not in st.session_state or st.session_state["selected_month"] not in month_options:
            st.session_state["selected_month"] = current_month

        month = st.selectbox("월 선택", month_options, key="selected_month")
        q = st.text_input(
            "검색(카테고리/메모/결제수단)",
            placeholder="예: 스타벅스 / 배달 / 현대카드 / 환급",
            key="search_text"
        )

        with top_filter_right:
            download_month = st.selectbox(
                "다운로드할 월 선택",
                month_options,
                key="download_month"
            )    
        
            # 다운로드용 데이터
            download_view = df.copy()
            download_view["date_dt"] = pd.to_datetime(download_view["date"], errors="coerce")
        
            try:
                dy, dm = download_month.split("-")
                download_view = download_view[
                    (download_view["date_dt"].dt.year == int(dy)) &
                    (download_view["date_dt"].dt.month == int(dm))
                ]
            except Exception:
                download_view = download_view.iloc[0:0]
        
            if download_view.empty:
                st.caption("선택한 월의 다운로드할 내역이 없어요.")
            else:
                download_df = download_view.drop(columns=["date_dt"], errors="ignore").copy()
                download_df = download_df.sort_values(by="date")
                download_df["amount_num"] = download_df["amount"].abs()
                download_df["amount"] = download_df["amount_num"].apply(lambda x: f"{x:,}원")
        
                download_df = download_df.rename(columns={
                    "date": "날짜",
                    "amount": "금액",
                    "category": "카테고리",
                    "method": "결제수단",
                    "memo": "메모"
                })
        
                download_df = download_df[["날짜", "카테고리", "메모", "금액", "결제수단", "amount_num"]]
        
                buffer = BytesIO()
        
                with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                    download_df.drop(columns=["amount_num"]).to_excel(
                        writer,
                        index=False,
                        sheet_name="가계부"
                    )
        
                    worksheet = writer.sheets["가계부"]
                    from openpyxl.styles import Font, Alignment
        
                    header_font = Font(bold=True)
        
                    for cell in worksheet[1]:
                        cell.font = header_font
        
                    column_widths = [12, 12, 25, 12, 12]
                    for i, width in enumerate(column_widths, start=1):
                        worksheet.column_dimensions[chr(64 + i)].width = width
        
                    for row in worksheet.iter_rows(min_row=2, min_col=4, max_col=4):
                        for cell in row:
                            cell.alignment = Alignment(horizontal="right")
        
                    total_row = len(download_df) + 2
                    worksheet[f"C{total_row}"] = "총합"
                    worksheet[f"D{total_row}"] = f"{download_df['amount_num'].sum():,}원"
        
                    category_sum = (
                        download_df
                        .groupby("카테고리")["amount_num"]
                        .sum()
                        .reset_index()
                    )
        
                    category_sum["합계"] = category_sum["amount_num"].apply(lambda x: f"{x:,}원")
                    category_sum = category_sum[["카테고리", "합계"]]
        
                    category_sum.to_excel(
                        writer,
                        index=False,
                        sheet_name="카테고리합계"
                    )
        
                    sheet2 = writer.sheets["카테고리합계"]
        
                    for cell in sheet2[1]:
                        cell.font = header_font
        
                    sheet2.column_dimensions["A"].width = 15
                    sheet2.column_dimensions["B"].width = 15
        
                excel_data = buffer.getvalue()
        
                st.download_button(
                    label=f"📥 {download_month} 가계부 다운로드",
                    data=excel_data,
                    file_name=f"{download_month}_가계부.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    st.divider()

    current_view_key = f"{month}|{q}|{st.session_state.get('record_filter', '전체')}"
    if "last_view_key" not in st.session_state:
        st.session_state["last_view_key"] = current_view_key

    if st.session_state["last_view_key"] != current_view_key:
        st.session_state["record_page"] = 1
        st.session_state["last_view_key"] = current_view_key

    # =========================
    # 기록 보기 필터
    # =========================
    st.subheader("🧾 기록 보기 / 필터")
    
    if "record_filter" not in st.session_state:
        st.session_state["record_filter"] = "전체"
    
    filter_items = [
        ("전체", "전체"),
        ("💳현대", "현대"),
        ("💳신한", "신한"),
        ("⛽주유", "주유"),
        ("📂사건비", "사건비"),
        ("💰환급", "환급"),
    ]
    
    cols = st.columns(len(filter_items))
    
    for i, (label, value) in enumerate(filter_items):
        with cols[i]:
            if st.button(
                label,
                use_container_width=True,
                key=f"filter_{value}",
                type="primary" if st.session_state["record_filter"] == value else "secondary"
            ):
                st.session_state["record_filter"] = value
                st.session_state["record_page"] = 1
                st.rerun()
    
    record_filter = st.session_state["record_filter"]
    
    # 보기용 데이터
    view = df.copy()
    view["date_dt"] = pd.to_datetime(view["date"], errors="coerce")
    
    try:
        y, m = month.split("-")
        view = view[
            (view["date_dt"].dt.year == int(y)) &
            (view["date_dt"].dt.month == int(m))
        ]
    except Exception:
        pass
    
    if q.strip():
        qq = q.strip().lower()
        mask = (
            view["category"].astype(str).str.lower().str.contains(qq, na=False)
            | view["memo"].astype(str).str.lower().str.contains(qq, na=False)
            | view["method"].astype(str).str.lower().str.contains(qq, na=False)
        )
        view = view[mask]
    
    view = view.sort_values(by=["date_dt"], ascending=False)
    
    if record_filter == "현대":
        view = view[view["method"] == "현대카드"]
    
    elif record_filter == "신한":
        view = view[view["method"] == "신한카드"]
    
    elif record_filter == "주유":
        view = view[view["memo"].astype(str).str.contains("주유", na=False)]
    
    elif record_filter == "사건비":
        view = view[view["category"] == "사건비"]
    
    elif record_filter == "환급":
        view = view[(view["method"] == "사건비통장") & (view["amount"] > 0)]
    
    filtered_total = int(view["amount"].abs().sum()) if not view.empty else 0
    st.caption(f"현재 보기: {record_filter} · 총금액: {filtered_total:,}원")
    
    if view.empty:
        st.write("표시할 기록이 없어요.")
    else:
        view_with_idx = view.copy()
        view_with_idx["row_id"] = view_with_idx.index
        view_with_idx = view_with_idx.reset_index(drop=True)
    
        total_rows = len(view_with_idx)
        total_pages = (total_rows - 1) // PAGE_SIZE + 1
    
        if "record_page" not in st.session_state:
            st.session_state["record_page"] = 1
    
        # 페이지 범위 보정
        if st.session_state["record_page"] > total_pages:
            st.session_state["record_page"] = total_pages
        if st.session_state["record_page"] < 1:
            st.session_state["record_page"] = 1
    
        start_idx = (st.session_state["record_page"] - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
    
        page_view = view_with_idx.iloc[start_idx:end_idx].copy()
        page_view["no"] = range(start_idx + 1, min(end_idx, total_rows) + 1)
    
        st.caption(f"총 {total_rows}건")
    
        h0, h1, h2, h3, h4, h5, h6, h7 = st.columns([0.6, 1.1, 1.2, 2.2, 1.2, 1.1, 0.8, 0.8])
        h0.markdown("<div class='table-head'>번호</div>", unsafe_allow_html=True)
        h1.markdown("<div class='table-head'>날짜</div>", unsafe_allow_html=True)
        h2.markdown("<div class='table-head'>카테고리</div>", unsafe_allow_html=True)
        h3.markdown("<div class='table-head'>메모</div>", unsafe_allow_html=True)
        h4.markdown("<div class='table-head'>금액</div>", unsafe_allow_html=True)
        h5.markdown("<div class='table-head'>결제수단</div>", unsafe_allow_html=True)
        h6.markdown("<div class='table-head'>삭제</div>", unsafe_allow_html=True)
        h7.markdown("<div class='table-head'>수정</div>", unsafe_allow_html=True)
    
        for _, r in page_view.iterrows():
            c0, c1, c2, c3, c4, c5, c6, c7 = st.columns([0.6, 1.1, 1.2, 2.2, 1.2, 1.1, 0.8, 0.8])
    
            c0.markdown(f"<div class='row-box'>{r['no']}</div>", unsafe_allow_html=True)
            c1.markdown(f"<div class='row-box'>{r['date']}</div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='row-box'><span class='cat-tag'>{r['category']}</span></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='row-box'>{r['memo']}</div>", unsafe_allow_html=True)
    
            amount_display = f"{abs(int(r['amount'])):,}원"
            if int(r["amount"]) > 0:
                amount_html = f"<div class='row-box amount-text'>➕ {amount_display}</div>"
            else:
                amount_html = f"<div class='row-box amount-text'>💸 {amount_display}</div>"
    
            c4.markdown(amount_html, unsafe_allow_html=True)
    
            method = str(r["method"])
            if method == "신한카드":
                method_html = f"<span class='method-shinhan'>{method}</span>"
            elif method == "사건비통장":
                method_html = f"<span class='method-incident'>{method}</span>"
            else:
                method_html = f"<span class='method-hyundai'>{method}</span>"
    
            c5.markdown(f"<div class='row-box'>{method_html}</div>", unsafe_allow_html=True)
    
            rid = int(r["row_id"])
    
            with c6:
                if st.button("🗑", key=f"del_{rid}", use_container_width=True):
                    df = df.drop(index=rid).reset_index(drop=True)
                    save_df(df)
                    st.success("삭제 완료!")
                    st.rerun()
    
            with c7:
                if st.button("✏", key=f"edit_{rid}", use_container_width=True):
                    edit_dialog(rid)
    
        st.markdown("<br>", unsafe_allow_html=True)
    
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
    
        with page_col1:
            if st.button("◀ 이전", use_container_width=True, key="prev_page"):
                if st.session_state["record_page"] > 1:
                    st.session_state["record_page"] -= 1
                    st.rerun()
    
        with page_col2:
            st.markdown(
                f"<div style='text-align:center;font-weight:700;padding-top:8px;'>"
                f"{st.session_state['record_page']} / {total_pages} 페이지"
                f"</div>",
                unsafe_allow_html=True
            )
    
        with page_col3:
            if st.button("다음 ▶", use_container_width=True, key="next_page"):
                if st.session_state["record_page"] < total_pages:
                    st.session_state["record_page"] += 1
                    st.rerun()
                
    st.divider()

    # =========================
    # 그래프
    # =========================
    st.subheader("📊 요약 그래프")

    expense_view = view[view["amount"] < 0]

    if not expense_view.empty:
        top_cat = (
            expense_view.groupby("category")["amount"]
            .sum()
            .abs()
            .sort_values(ascending=False)
        )

        st.subheader("🔥 이번달 지출 TOP")
        top3 = top_cat.head(3)
        cols = st.columns(len(top3))

        for i, (cat, val) in enumerate(top3.items()):
            cols[i].metric(cat, f"{int(val):,} 원")

    if not view.empty:
        st.caption("카테고리별 지출")
        if not expense_view.empty:
            st.bar_chart(
                expense_view.groupby("category")["amount"]
                .sum()
                .abs()
                .sort_values(ascending=False)
            )

        st.caption("결제수단별 순금액")
        method_sum = view.groupby("method")["amount"].sum().abs().sort_values(ascending=False)

        if not method_sum.empty:
            st.bar_chart(method_sum)

    st.caption(f"데이터 파일: {FILE} / {CHECKLIST_FILE}")































