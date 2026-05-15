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
API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "google/gemini-2.5-flash"
URL = "https://openrouter.ai/api/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ========================================
# VERKTOY
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
        forhold = {0: "klart", 1: "delvis skyet", 2: "skyet", 3: "overskyet",
                   45: "tåke", 51: "lett yr", 61: "regn", 71: "snø", 95: "torden"}
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
    """Lager ICS-fil og gir nedlastingsknapp"""
    try:
        time_delt = tid.split(":")
        slutt_time = int(time_delt[0]) + 1
        slutt_tid = f"{slutt_time:02d}:{time_delt[1]}"

        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
DTSTART:{dato.replace('-', '')}T{tid.replace(':', '')}00
DTEND:{dato.replace('-', '')}T{slutt_tid.replace(':', '')}00
SUMMARY:{tittel}
END:VEVENT
END:VCALENDAR"""

        st.session_state.ics_data = ics
        st.session_state.ics_filnavn = f"{tittel.replace(' ', '_')}.ics"

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
- Calendar event: TOOL: kalender(title, date, time) - date as YYYY-MM-DD, time as HH:MM

Reply ONLY with one TOOL: line if you need a tool. Otherwise answer directly."""

# ========================================
# STREAMLIT APP
# ========================================
st.set_page_config(page_title="Min KI-Agent", page_icon="🤖")

# ========================================
# SIDEBAR
# ========================================
with st.sidebar:
    st.header("📧 E-post (valgfritt)")
    bruker_email = st.text_input("Din Gmail", placeholder="deg@gmail.com", key="email_input")
    bruker_passord = st.text_input("App-passord", placeholder="16 tegn", type="password", key="pass_input")
    st.caption("[Lage app-passord](https://myaccount.google.com/apppasswords)")

    if bruker_email and bruker_passord:
        st.success("✅ E-post klar!")

    st.divider()

    st.header("📅 Kalender")
    st.caption("Lager ICS-fil som kan åpnes i alle kalendere")
    st.success("✅ Kalender klar!")

    st.divider()
    st.caption("🛠️ Verktøy: Kalkulator, Dato, Vær, Wikipedia, Lagre, E-post, Kalender")

# ========================================
# HOVEDVINDU
# ========================================
st.title("🤖 Min KI-Agent")
st.caption("En assistent med kalkulator, dato, vær, Wikipedia, lagring, e-post og kalender")

if "meldinger" not in st.session_state:
    st.session_state.meldinger = [{"role": "system", "content": SYSTEM_MELDING}]

for melding in st.session_state.meldinger:
    if melding["role"] == "user":
        with st.chat_message("user"):
            st.markdown(melding["content"])
    elif melding["role"] == "assistant":
        with st.chat_message("assistant"):
            st.markdown(melding["content"])

if sporsmal := st.chat_input("Skriv melding..."):
    with st.chat_message("user"):
        st.markdown(sporsmal)
    st.session_state.meldinger.append({"role": "user", "content": sporsmal})

    with st.spinner("Tenker..."):
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
                            st.markdown(f"🔧 Verktøy: `{kall}`")

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
                            import re as re2
                            arg_clean = arg.replace("'", "").replace('"', "")
                            tittel_match = re2.search(r"title=(.+?),", arg_clean)
                            dato_match = re2.search(r"date=(.+?),", arg_clean)
                            tid_match = re2.search(r"time=(.+)", arg_clean)
                            if tittel_match and dato_match and tid_match:
                                resultat = legg_til_kalender(
                                    tittel_match.group(1).strip(),
                                    dato_match.group(1).strip(),
                                    tid_match.group(1).strip()
                                )
                            else:
                                deler = arg_clean.split(",")
                                if len(deler) == 3:
                                    resultat = legg_til_kalender(
                                        deler[0].strip(), deler[1].strip(), deler[2].strip()
                                    )
                                else:
                                    resultat = "Kunne ikke tolke kalender-format."
                        else:
                            resultat = f"Ukjent verktøy: {navn_v}"

                        with st.chat_message("assistant"):
                            st.markdown(f"📊 Resultat: `{resultat}`")

                        st.session_state.meldinger.append({"role": "assistant", "content": svar})
                        st.session_state.meldinger.append(
                            {"role": "user", "content": f"Verktøy-resultat: {resultat}\nSvar brukeren."}
                        )

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

# Vis nedlastingsknapp for ICS-fil
if "ics_data" in st.session_state and st.session_state.ics_data:
    st.download_button(
        label=f"📥 Last ned {st.session_state.ics_filnavn}",
        data=st.session_state.ics_data,
        file_name=st.session_state.ics_filnavn,
        mime="text/calendar"
    )