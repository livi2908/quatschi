"""Quatschi als Web-App (Streamlit): Chat, Themes und Morgen-News von bild.de."""
import requests
import streamlit as st
from bs4 import BeautifulSoup
from google import genai
from google.genai import types

MODEL = "gemini-2.5-flash"  # Falls Google den Namen ändert, hier anpassen
NEWS_URL = "https://www.bild.de"
PERSONA = (
    "Du bist Quatschi, ein lockerer, witziger Chat-Kumpel nur zum Quatschen "
    "und für Spaß. Du duzt, schreibst kurz (höchstens 80 Wörter), nutzt ein "
    "paar Emojis und stellst gern eine Rückfrage. Du bist freundschaftlich, "
    "nie romantisch, und jugendfrei. Bei ernsten Sorgen wirst du einfühlsam "
    "und empfiehlst, mit einer vertrauten Person zu reden. "
    "Nachrichten fasst du immer in eigenen Worten zusammen."
)
THEMES = {
    "🟠 Sonne": ("#fff7ed", "#2a1f14"),
    "🔵 Ozean": ("#eaf4ff", "#10243a"),
    "🟢 Wald": ("#eef7ee", "#14281a"),
    "🩷 Pink": ("#fff0f6", "#2d1420"),
    "🌙 Nacht": ("#0f1220", "#eceffd"),
}

st.set_page_config(page_title="Quatschi", page_icon="🎉")
wahl = st.sidebar.selectbox("Theme", list(THEMES))
bg, fg = THEMES[wahl]
st.markdown(
    f"<style>.stApp{{background:{bg}}} .stApp h1,.stApp p,.stApp li,"
    f".stApp span{{color:{fg}}}</style>",
    unsafe_allow_html=True,
)


@st.cache_resource
def get_client():
    return genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


@st.cache_data(ttl=3600)
def hole_schlagzeilen(limit=12):
    antwort = requests.get(
        NEWS_URL,
        headers={"User-Agent": "Mozilla/5.0 (Quatschi, privat)"},
        timeout=15,
    )
    antwort.raise_for_status()
    soup = BeautifulSoup(antwort.text, "html.parser")
    zeilen = []
    for tag in soup.find_all(["h2", "h3"]):
        text = " ".join(tag.get_text(" ", strip=True).split())
        if len(text) > 25 and text not in zeilen:
            zeilen.append(text)
        if len(zeilen) >= limit:
            break
    return zeilen


def antworte():
    inhalt = [
        types.Content(role=r, parts=[types.Part(text=api)])
        for r, _anzeige, api in st.session_state.verlauf
    ]
    return (
        get_client()
        .models.generate_content(
            model=MODEL,
            contents=inhalt,
            config=types.GenerateContentConfig(system_instruction=PERSONA),
        )
        .text
    )


def sende(anzeige, api_text=None):
    st.session_state.verlauf.append(("user", anzeige, api_text or anzeige))
    try:
        text = antworte()
    except Exception as fehler:
        st.session_state.verlauf.pop()
        st.error(f"Da ist was schiefgelaufen ({fehler}).")
        return
    st.session_state.verlauf.append(("model", text, text))


if "verlauf" not in st.session_state:
    st.session_state.verlauf = []

st.title("🎉 Quatschi")
if st.button("☀️ Morgen-News"):
    try:
        zeilen = hole_schlagzeilen()
        if not zeilen:
            raise RuntimeError("keine Schlagzeilen gefunden")
        sende(
            "☀️ Was gibt’s Neues?",
            "Hier sind die heutigen Schlagzeilen von bild.de. Fass die 5 "
            "wichtigsten locker in eigenen Worten zusammen:\n- "
            + "\n- ".join(zeilen),
        )
    except Exception as fehler:
        st.warning(f"News gerade nicht erreichbar ({fehler}). Quatschen geht trotzdem!")

for rolle, anzeige, _api in st.session_state.verlauf:
    with st.chat_message("user" if rolle == "user" else "assistant"):
        st.write(anzeige)

frage = st.chat_input("Schreib irgendwas …")
if frage:
    sende(frage)
    st.rerun()
