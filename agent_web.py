import streamlit as st
import requests
import re
from datetime import datetime
import wikipedia
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import speech_recognition as sr
import tempfile

load_dotenv()

# ========================================
# KONFIGURASJON
# ========================================
API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "google/gemini-2.5-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ========================================
# SIDEOppsett + Streamlit Mørkt Tema
# ========================================
st.set_page_config(
    page_title="Min KI-Agent 🤖",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={sted}&count=1&language=en"
        geo_res = requests.get(geo_url).json()
        if "results" not in geo_res or not geo_res["results"]:
            return f"Fant ikke stedet '{sted}'."
        pos = geo_res["results"][0]
        lat, lon = pos["latitude"], pos["longitude"]
        navn = pos.get("name", sted)
        vaer_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
        vaer_res = requests.get(vaer_url).json()
        naa = vaer_res["current_weather"]
        temp = naa["temperature"]
        vind = naa["windspeed"]
        forhold = {0: "klart", 1: "delvis skyet", 2: "skyet", 3: "overskyet", 45: "tåke", 51: "lett yr", 61: "regn", 71: "snø", 95: "torden"}
        vaertype = forhold.get(naa["weathercode"], "ukjent")
        return f"I {navn} er det nå {temp}°C, {vaertype}, vind {vind} m/s."
    except:
        return "Kunne ikke hente værvarsel."

def sok_wikipedia(emne):
    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(emne, sentences=3)
    except:
        return "Kunne ikke hente informasjon fra Wikipedia."

def lagre_fil(filnavn, innhold):
    try:
        with open(filnavn, "w", encoding="utf-8") as f:
            f.write(innhold)
        return f"Fil '{filnavn}' er lagret."
    except:
        return "Kunne ikke lagre filen."

def send_epost(mottaker, emne, innhold, avsender=None, passord=None):
    if not avsender or not passord:
        return "E-post ikke satt opp. Fyll inn din Gmail i sidepanelet."
    try:
        melding = MIMEMultipart()
        melding["From"] = avsender
        melding["To"] = mottaker
        melding["Subject"] = emne
        melding.attach(MIMEText(innhold, "plain"))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(avsender, passord)
            server.sendmail(avsender, mottaker, melding.as_string())
        return f"E-post sendt til {mottaker}!"
    except Exception as e:
        return f"Kunne ikke sende e-post: {str(e)}"

def legg_til_kalender(tittel, dato, tid):
    try:
        time_delt = tid.split(":")
        slutt_time = int(time_delt[0]) + 1
        slutt_tid = f"{slutt_time:02d}:{time_delt[1]}"
        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:{dato.replace('-','')}T{tid.replace(':','')}00
DTEND:{dato.replace('-','')}T{slutt_tid.replace(':','')}00
SUMMARY:{tittel}
END:VEVENT
END:VCALENDAR"""
        st.session_state.ics_data = ics
        st.session_state.ics_filnavn = f"{tittel.replace(' ','_')}.ics"
        return f"✅ Kalenderfil '{st.session_state.ics_filnavn}' klar for nedlasting!"
    except Exception as e:
        return f"Kunne ikke lage kalenderfil: {str(e)}"

# ========================================
# SYSTEMBESKJED
# ========================================
SYSTEM_MELDING = """You are a helpful assistant. Answer SHORT (max 3 sentences).

You MUST use tools for:
- Math: TOOL: kalkulator(expression)
- Date/time: TOOL: dato()
- Weather: TOOL: vaer(city)
- Wikipedia: TOOL: wikipedia(topic)
- Save file: TOOL: lagre(filename, content)
- Send email: TOOL: send_epost(recipient, subject, message)
- Calendar event: TOOL: kalender(title, date, time) - date YYYY-MM-DD, time HH:MM

Reply ONLY with one TOOL: line if you need a tool. Otherwise answer directly."""

# ========================================
# TALEGJENKJENNING (for web-app)
# ========================================
def speech_to_text(audio_bytes):
    """Konverterer lydopptak til tekst via Google Speech Recognition"""
    try:
        # Lagre lydopptak midlertidig
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        recognizer = sr.Recognizer()
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        
        # Slett midlertidig fil
        os.unlink(tmp_path)
        
        # Send til Google for talegjenkjenning
        tekst = recognizer.recognize_google(audio, language="en-US")
        return tekst
    except sr.UnknownValueError:
        return None
    except Exception as e:
        st.error(f"Kunne ikke gjenkjenne tale: {e}")
        return None

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>⚙️ Kontrollpanel</h2>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="status-card">
        <h3>🟢 Agent Online</h3>
        <p>7 verktøy aktive</p>
        <p style='font-size: 0.8em;'>Drevet av Gemini 2.5 Flash</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("<h3>📧 E-post (valgfritt)</h3>", unsafe_allow_html=True)
    bruker_email = st.text_input("Din Gmail", placeholder="deg@gmail.com", key="email_input")
    bruker_passord = st.text_input("App-passord", placeholder="16 tegn", type="password", key="pass_input")
    st.caption("[Lage app-passord](https://myaccount.google.com/apppasswords)")
    
    if bruker_email and bruker_passord:
        st.success("✅ E-post klar!")
    
    st.divider()
    
    st.markdown("<h3>📅 Kalender</h3>", unsafe_allow_html=True)
    st.caption("Lager ICS-fil for alle kalendere")
    st.success("✅ Kalender klar!")
    
    st.divider()
    
    st.markdown("<p style='font-size: 0.9em;'>🛠️ Verktøy:</p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 0.8em;'>Kalkulator · Dato · Vær · Wikipedia · Lagring · E-post · Kalender</p>", unsafe_allow_html=True)

# ========================================
# HOVEDVINDU
# ========================================
st.title("🤖 Min KI-Agent")
st.caption("En intelligent assistent med 7 verktøy • fra gzorn til deg 🚀")

# Velkomstmelding
if "meldinger" not in st.session_state:
    st.session_state.meldinger = [{"role": "system", "content": SYSTEM_MELDING}]
    st.markdown("""
    <div class="welcome-box">
        <h2>👋 Velkommen til din personlige KI-Agent!</h2>
        <p style='font-size: 1.1em;'>
            🧮 <b>Matematikk</b> · 🌤️ <b>Vær</b> · 📚 <b>Wikipedia</b> · 📧 <b>E-post</b> · 📅 <b>Kalender</b> · 💾 <b>Lagring</b>
        </p>
        <p><i>Skriv et spørsmål eller bruk 🎤 for å snakke...</i></p>
    </div>
    """, unsafe_allow_html=True)

# Vis meldinger
for melding in st.session_state.meldinger:
    if melding["role"] == "user":
        with st.chat_message("user"):
            st.markdown(melding["content"])
    elif melding["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(melding["content"])

# ========================================
# TO INPUT-METODER: Skriv ELLER Snakk
# ========================================
col1, col2 = st.columns([5, 1])

with col1:
    sporsmal = st.chat_input("💬 Skriv en melding...")

with col2:
    lydopptak = st.audio_input("🎤")

# Håndter lydopptak
if lydopptak is not None:
    with st.spinner("🎤 Lytter..."):
        tekst = speech_to_text(lydopptak)
    
    if tekst:
        sporsmal = tekst
        st.success(f"Oppfattet: {tekst}")
    else:
        st.warning("Kunne ikke oppfatte tale. Prøv igjen.")

# Håndter spørsmål (fra tekst eller tale)
if sporsmal:
    with st.chat_message("user"):
        st.markdown(sporsmal)
    st.session_state.meldinger.append({"role": "user", "content": sporsmal})

    with st.spinner("🤔 Tenker..."):
        r = requests.post(URL, headers=HEADERS, json={
            "model": MODEL,
            "messages": st.session_state.meldinger,
            "max_tokens": 1000
        })
        data = r.json()

    if "choices" in data:
        svar = data["choices"][0]["message"]["content"]

        if "TOOL:" in svar:
            for linje in svar.split("\n"):
                if "TOOL:" in linje:
                    kall = linje.replace("TOOL:", "").strip()
                    with st.chat_message("assistant"):
                        st.markdown(f"🔧 Bruker verktøy: `{kall}`")

                    if "(" in kall and ")" in kall:
                        navn_v = kall.split("(")[0].strip()
                        arg = kall.split("(")[1].split(")")[0].strip().strip('\'"')
                    else:
                        navn_v = kall.strip()
                        arg = ""

                    if navn_v == "kalkulator":
                        resultat = kalkulator(arg)
                    elif navn_v == "dato":
                        resultat = dato_og_tid()
                    elif navn_v == "vaer":
                        resultat = vaer(arg)
                    elif navn_v == "wikipedia":
                        resultat = sok_wikipedia(arg)
                    elif navn_v == "lagre":
                        deler = arg.split(",", 1)
                        if len(deler) == 2:
                            resultat = lagre_fil(deler[0].strip().strip('"'), deler[1].strip().strip('"'))
                        else:
                            resultat = "Feil format."
                    elif navn_v == "send_epost":
                        deler = arg.split(",", 2)
                        if len(deler) == 3:
                            resultat = send_epost(
                                deler[0].strip().strip('"'),
                                deler[1].strip().strip('"'),
                                deler[2].strip().strip('"'),
                                avsender=bruker_email,
                                passord=bruker_passord
                            )
                        else:
                            resultat = "Feil format."
                    elif navn_v == "kalender":
                        deler = arg.split(",", 2)
                        if len(deler) == 3:
                            resultat = legg_til_kalender(deler[0].strip(), deler[1].strip(), deler[2].strip())
                        else:
                            resultat = "Feil format. Bruk: kalender(tittel, YYYY-MM-DD, HH:MM)"
                    else:
                        resultat = f"Ukjent verktøy: {navn_v}"

                    with st.chat_message("assistant"):
                        st.markdown(f"📊 Resultat: `{resultat}`")

                    st.session_state.meldinger.append({"role": "assistant", "content": svar})
                    st.session_state.meldinger.append({"role": "user", "content": f"Verktøy-resultat: {resultat}\nSvar brukeren."})

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
                        st.session_state.meldinger.append({"role": "assistant", "content": resultat})
        else:
            with st.chat_message("assistant"):
                st.markdown(svar)
            st.session_state.meldinger.append({"role": "assistant", "content": svar})
    else:
        with st.chat_message("assistant"):
            st.error(f"Feil: {data}")

# Nedlastingsknapp for kalender
if "ics_data" in st.session_state and st.session_state.ics_data:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label=f"📥 Last ned {st.session_state.ics_filnavn}",
            data=st.session_state.ics_data,
            file_name=st.session_state.ics_filnavn,
            mime="text/calendar",
            use_container_width=True
        )

# Footer
st.markdown("---")
st.markdown(
    "<p class='footer'>fra gzorn til deg 🚀</p>",
    unsafe_allow_html=True
)