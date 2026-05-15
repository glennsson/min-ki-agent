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

load_dotenv()

# ========================================
# KONFIGURASJON
# ========================================
# Prioriter: 1) st.secrets (Streamlit Cloud), 2) os.environ (lokal .env)
API_KEY = st.secrets.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "google/gemini-2.5-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ========================================
# SIDEOppsett
# ========================================
st.set_page_config(
    page_title="Min KI-Agent 🤖",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========================================
# CSS-STYLING
# ========================================
st.markdown("""
<style>
    /* Hovedbakgrunn */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
    }
    
    /* Chat-meldinger */
    .stChatMessage {
        border-radius: 15px !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
    }
    
    /* Brukerens meldinger */
    [data-testid="stChatMessage"][aria-label="user"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-left: 5px solid #ffd700 !important;
        margin-left: 20px !important;
    }
    
    /* Agentens meldinger */
    [data-testid="stChatMessage"][aria-label="assistant"] {
        background: rgba(255,255,255,0.1) !important;
        backdrop-filter: blur(10px) !important;
        color: white !important;
        border-left: 5px solid #00ff88 !important;
        margin-right: 20px !important;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
        border-right: 1px solid rgba(255,255,255,0.1) !important;
    }
    
    /* Knapper */
    .stButton button {
        border-radius: 25px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: bold !important;
        border: none !important;
        transition: transform 0.3s ease !important;
    }
    
    .stButton button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Input-felt */
    .stTextInput input, .stChatInput input {
        background: rgba(255,255,255,0.1) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        color: white !important;
        border-radius: 25px !important;
    }
    
    /* Hovedtittel */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
    }
    
    /* Nedlastingsknapp */
    .stDownloadButton button {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%) !important;
        border-radius: 25px !important;
    }
    
    /* Statuskort */
    .status-card {
        background: rgba(255,255,255,0.1);
        backdrop-filter: blur(10px);
        border-radius: 15px;
        padding: 15px;
        text-align: center;
        color: white;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* Velkomstboks */
    .welcome-box {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(20px);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        border: 1px solid rgba(255,255,255,0.1);
        margin-bottom: 20px;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 20px;
        color: rgba(255,255,255,0.5);
    }
</style>
""", unsafe_allow_html=True)

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

Reply ONLY with one TOOL: line if you need a tool."""

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center; color: white;'>⚙️ Kontrollpanel</h2>", unsafe_allow_html=True)
    
    # Statuskort
    st.markdown("""
    <div class="status-card">
        <h3>🟢 Agent Online</h3>
        <p>7 verktøy aktive</p>
        <p style='font-size: 0.8em;'>Drevet av Gemini 2.5 Flash</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("<h3 style='color: white;'>📧 E-post (valgfritt)</h3>", unsafe_allow_html=True)
    bruker_email = st.text_input("Din Gmail", placeholder="deg@gmail.com", key="email_input")
    bruker_passord = st.text_input("App-passord", placeholder="16 tegn", type="password", key="pass_input")
    st.caption("[Lage app-passord](https://myaccount.google.com/apppasswords)")
    
    if bruker_email and bruker_passord:
        st.success("✅ E-post klar!")
    
    st.divider()
    
    st.markdown("<h3 style='color: white;'>📅 Kalender</h3>", unsafe_allow_html=True)
    st.caption("Lager ICS-fil for alle kalendere")
    st.success("✅ Kalender klar!")
    
    st.divider()
    
    st.markdown("<p style='color: rgba(255,255,255,0.7); font-size: 0.9em;'>🛠️ Verktøy:</p>", unsafe_allow_html=True)
    st.markdown("<p style='color: rgba(255,255,255,0.5); font-size: 0.8em;'>Kalkulator · Dato · Vær · Wikipedia · Lagring · E-post · Kalender</p>", unsafe_allow_html=True)

# ========================================
# HOVEDVINDU
# ========================================
st.title("🤖 Min KI-Agent")
st.caption("En intelligent assistent med 7 verktøy")

# Velkomstmelding
if "meldinger" not in st.session_state:
    st.session_state.meldinger = [{"role": "system", "content": SYSTEM_MELDING}]
    st.markdown("""
    <div class="welcome-box">
        <h2>👋 Velkommen til din personlige KI-Agent!</h2>
        <p style='color: rgba(255,255,255,0.8);'>Jeg kan hjelpe deg med:</p>
        <p style='color: rgba(255,255,255,0.9); font-size: 1.1em;'>
            🧮 <b>Matematikk</b> · 🌤️ <b>Vær</b> · 📚 <b>Wikipedia</b> · 📧 <b>E-post</b> · 📅 <b>Kalender</b> · 💾 <b>Lagring</b>
        </p>
        <p style='color: rgba(255,255,255,0.6);'><i>Skriv et spørsmål i chatten for å starte...</i></p>
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

# Håndter ny brukerinput
if sporsmal := st.chat_input("💬 Skriv en melding..."):
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
    "<p class='footer'>Bygget med ❤️ | Drevet av Gemini 2.5 Flash via OpenRouter | Streamlit Cloud</p>",
    unsafe_allow_html=True
)
