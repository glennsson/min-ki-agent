import streamlit as st
import requests
import re
from datetime import datetime
import wikipedia
import json
import streamlit as st
import requests
import re
from datetime import datetime
import wikipedia
import os
from dotenv import load_dotenv

load_dotenv()
# ========================================
# KONFIGURASJON
# ========================================
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")  # ✅ Hentes fra .env
MODEL = "google/gemini-2.5-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ========================================
# VERKTØY
# ========================================
def kalkulator(uttrykk):
    try:
        rent = re.sub(r'[^0-9+\-*/.() ]', '', uttrykk)
        return str(eval(rent))
    except:
        return "Feil i utregning"

def dato_og_tid():
    return datetime.now().strftime("%d. %B %Y, klokken %H:%M")

def vaer(sted):
    """Henter værvarsel fra Open-Meteo (gratis, ingen API-nøkkel)"""
    try:
        # 1. Finn koordinater for stedet
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={sted}&count=1&language=no"
        geo_res = requests.get(geo_url).json()
        if "results" not in geo_res or not geo_res["results"]:
            return f"Fant ikke stedet '{sted}'."

        pos = geo_res["results"][0]
        lat, lon = pos["latitude"], pos["longitude"]
        navn = pos.get("name", sted)

        # 2. Hent værvarsel
        vær_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto&language=no"
        vær_res = requests.get(vær_url).json()
        nå = vær_res["current_weather"]
        temp = nå["temperature"]
        vind = nå["windspeed"]
        forhold = {
            0: "klart",
            1: "delvis skyet",
            2: "skyet",
            3: "overskyet",
            45: "tåke",
            51: "lett yr",
            61: "regn",
            71: "snø",
            95: "torden"
        }
        værtype = forhold.get(nå["weathercode"], "ukjent")
        return f"I {navn} er det nå {temp}°C, {værtype}, vind {vind} m/s."
    except:
        return "Kunne ikke hente værvarsel."

def sok_wikipedia(emne):
    """Henter sammendrag fra Wikipedia (norsk)"""
    try:
        wikipedia.set_lang("no")
        sammendrag = wikipedia.summary(emne, sentences=3)
        return sammendrag
    except wikipedia.exceptions.DisambiguationError as e:
        # Hvis flere treff, velg det første
        try:
            wikipedia.set_lang("no")
            sammendrag = wikipedia.summary(e.options[0], sentences=3)
            return f"Fant flere alternativer. Viser '{e.options[0]}':\n{sammendrag}"
        except:
            return "Kunne ikke finne informasjon."
    except:
        return "Kunne ikke hente informasjon fra Wikipedia."

def lagre_fil(filnavn, innhold):
    """Lagrer tekst til en fil"""
    try:
        with open(filnavn, "w", encoding="utf-8") as f:
            f.write(innhold)
        return f"Fil '{filnavn}' er lagret."
    except:
        return "Kunne ikke lagre filen."

# ========================================
# SYSTEMBESKJED (utvidet)
# ========================================
SYSTEM_MELDING = """Du er en norsk assistent. Svar KORT.

Du MÅ bruke verktøy for følgende:
- Matte: VERKTOY: kalkulator(uttrykk)
- Dato/tid: VERKTOY: dato()
- Vær: VERKTOY: vaer(sted)
- Wikipedia: VERKTOY: wikipedia(emne)
- Lagre notat: VERKTOY: lagre(filnavn, innhold)

Når du trenger et verktøy, svar KUN med én linje som begynner med VERKTOY: etterfulgt av navn(argumenter).
Aldri gjett svar på disse områdene. Ellers svar direkte."""

# ========================================
# STREAMLIT APP
# ========================================
st.set_page_config(page_title="Min KI-Agent", page_icon="🤖")
st.title("🤖 Min KI-Agent")
st.caption("med kalkulator, dato, vær, Wikipedia og lagring")

# Initialiser chat-historikk
if "meldinger" not in st.session_state:
    st.session_state.meldinger = [{"role": "system", "content": SYSTEM_MELDING}]

# Vis meldinger
for melding in st.session_state.meldinger:
    if melding["role"] == "user":
        with st.chat_message("user"):
            st.markdown(melding["content"])
    elif melding["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(melding["content"])

# Håndter ny brukerinput
if sporsmal := st.chat_input("Skriv melding..."):
    with st.chat_message("user"):
        st.markdown(sporsmal)
    st.session_state.meldinger.append({"role": "user", "content": sporsmal})

    with st.spinner("Tenker..."):
        # Første kall
        r = requests.post(URL, headers=HEADERS, json={
            "model": MODEL,
            "messages": st.session_state.meldinger,
            "max_tokens": 1000
        })
        data = r.json()

        if "choices" in data:
            svar = data["choices"][0]["message"]["content"]

            if "VERKTOY:" in svar:
                for linje in svar.split("\n"):
                    if "VERKTOY:" in linje:
                        kall = linje.replace("VERKTOY:", "").strip()
                        with st.chat_message("assistant"):
                            st.markdown(f"🔧 Bruker verktøy: `{kall}`")

                        # Tolk verktøy og argumenter
                        if "(" in kall and ")" in kall:
                            navn_v = kall.split("(")[0].strip()
                            arg = kall.split("(")[1].split(")")[0].strip()
                            # Fjern eventuelle anførselstegn rundt argumentet
                            arg = arg.strip('\'"')
                        else:
                            navn_v = kall.strip()
                            arg = ""

                        # Utfør verktøy
                        if navn_v == "kalkulator":
                            resultat = kalkulator(arg)
                        elif navn_v == "dato":
                            resultat = dato_og_tid()
                        elif navn_v == "vaer":
                            resultat = vaer(arg)
                        elif navn_v == "wikipedia":
                            resultat = sok_wikipedia(arg)
                        elif navn_v == "lagre":
                            # Forventer format: lagre(filnavn, innhold)
                            # Vi splitter på komma og håndterer enkelt
                            deler = arg.split(",", 1)
                            if len(deler) == 2:
                                filnavn = deler[0].strip().strip('"')
                                innhold = deler[1].strip().strip('"')
                                resultat = lagre_fil(filnavn, innhold)
                            else:
                                resultat = "Feil format. Bruk: lagre(filnavn, innhold)"
                        else:
                            resultat = f"Ukjent verktøy: {navn_v}"

                        with st.chat_message("assistant"):
                            st.markdown(f"📊 Resultat: `{resultat}`")

                        # Legg til historikk
                        st.session_state.meldinger.append({"role": "assistant", "content": svar})
                        st.session_state.meldinger.append({"role": "user", "content": f"Verktøy-resultat: {resultat}\nSvar brukeren på norsk."})

                        # Andre kall for å formulere svar
                        r2 = requests.post(URL, headers=HEADERS, json={
                            "model": MODEL,
                            "messages": st.session_state.meldinger,
                            "max_tokens": 500
                        })
                        data2 = r2.json()
                        if "choices" in data2:
                            svar2 = data2["choices"][0]["message"]["content"]
                            with st.chat_message("assistant"):
                                st.markdown(svar2)
                            st.session_state.meldinger.append({"role": "assistant", "content": svar2})
                        else:
                            with st.chat_message("assistant"):
                                st.markdown(resultat)
                            st.session_state.meldinger.append({"role": "assistant", "content": resultat})
            else:
                with st.chat_message("assistant"):
                    st.markdown(svar)
                st.session_state.meldinger.append({"role": "assistant", "content": svar})
        else:
            with st.chat_message("assistant"):
                st.error(f"Feil: {data}")