import streamlit as st
import sqlite3
import pandas as pd
import hashlib
import os
import json
import calendar
import gspread
from datetime import datetime, date
from fpdf import FPDF

import streamlit as st
import time # Serve per il timer della transizione
from streamlit_lottie import st_lottie # Per l'animazione di benvenuto
import requests # Per scaricare l'animazione

from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
from google.oauth2 import service_account

# Sostituisci con l'ID della tua cartella Google Drive
ID_CARTELLA_DRIVE = "10A1flQZ5GkwukRSxSvLMl6vPYwJmXW4K" 
ID_FOGLIO_PRESENZE = "1wUBaTESXuKJRIFPDqvPWMgjXLBVcwnlLpEtXrylNfM8"

def inizializza_drive():
    # 1. Prova a leggere dalla variabile d'ambiente di Google Cloud
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    
    if creds_json:
        # Siamo online su Cloud Run: usiamo la variabile che hai incollato prima
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(info)
        gauth = GoogleAuth()
        gauth.credentials = creds
        return GoogleDrive(gauth)
    else:
        # Siamo sul tuo PC: usiamo il file credentials.json come facevi prima
        scope = ['https://www.googleapis.com/auth/drive']
        gauth = GoogleAuth()
        if os.path.exists('credentials.json'):
            gauth.credentials = service_account.Credentials.from_service_account_file(
                'credentials.json', scopes=scope)
        else:
            # Se manca tutto, prova l'autenticazione standard
            gauth.LocalWebserverAuth()
        return GoogleDrive(gauth)
def inizializza_foglio():
    creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json:
        info = json.loads(creds_json)
        creds = service_account.Credentials.from_service_account_info(
            info, 
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
    else:
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json', 
            scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        )
    
    client = gspread.authorize(creds)
    return client.open_by_key(ID_FOGLIO_PRESENZE).sheet1
def salva_presenza_su_google(nome_dipendente, data, stato):
    try:
        salva_presenza_su_google(col_label, data_corrente, stato_db)
        foglio = inizializza_foglio()
        foglio.append_row([
            nome_dipendente, 
            str(data), 
            stato, 
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                  
        ])
    except Exception as e:
        st.error(f"Errore nel salvataggio su Google Sheets: {e}")    
def salva_su_drive(percorso_file_locale, nome_file):
    drive = inizializza_drive()
    file_drive = drive.CreateFile({
        'title': nome_file,
        'parents': [{'id': ID_CARTELLA_DRIVE}]
    })
    file_drive.SetContentFile(percorso_file_locale)
    file_drive.Upload()
    return file_drive['alternateLink'] # Restituisce il link per vederlo online

# pdf 

def calcola_giorni_previsti(giro):
    if giro == "Verona":
        return 26  # Esempio: 6 giorni su 7
    elif giro == "Padova":
        return 21  # Esempio: 5 giorni su 7 (Mar-Sab)
    elif giro == "Segretario":
        return 22  # Standard ufficio, ma sarà modificabile
    return 26

def genera_pdf(df, extra, tot_km, imp, iva_val, finale, mese, anno): # Aggiunto mese e anno qui
    pdf = FPDF()
    pdf.add_page()
    
    # Intestazione Aziendale
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 8, "E.G. TRASPORTI SRLS", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 5, "PARTITA IVA: 04978570234", ln=True)
    pdf.cell(0, 5, "CODICE FISCALE: 04978570234", ln=True)
    pdf.cell(0, 5, "PEC: egtrasporti@pec.cgn.it", ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"DETTAGLIO TRASPORTI - {mese}/{anno}", ln=True, align='C')
    pdf.ln(5)

    # Intestazioni Tabella
    pdf.set_font("Arial", 'B', 10)
    w = [35, 25, 30, 30, 40]
    pdf.set_fill_color(230, 230, 230)
    cols = ["Data", "Giorno", "KM Padova", "KM Verona", "Tot KM"]
    for i in range(len(cols)):
        pdf.cell(w[i], 10, cols[i], 1, 0, 'C', True)
    pdf.ln()

    # Righe con colori richiesti
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        # Calcolo totale riga se non presente nel DF
        tot_riga = row["KM Padova"] + row["KM Verona"]
        
        pdf.cell(w[0], 8, row["Data"], 1)
        pdf.cell(w[1], 8, row["Giorno"], 1)
        
        # Colonna Padova (Azzurro Light)
        pdf.set_fill_color(173, 216, 230) 
        pdf.cell(w[2], 8, str(int(row["KM Padova"])), 1, 0, 'C', True)
        
        # Colonna Verona (Arancione Light)
        pdf.set_fill_color(255, 204, 153) 
        pdf.cell(w[3], 8, str(int(row["KM Verona"])), 1, 0, 'C', True)
        
        # Totale riga (Grigio chiaro)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(w[4], 8, str(int(tot_riga)), 1, 1, 'C', True)

    # Riepilogo economico
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(100, 8, f"Kilometri Extra: {extra:.0f}km", 0, 1)
    pdf.cell(100, 8, f"Totale KM Mensili (incl. Extra): {tot_km:.0f}km", 0, 1)
    pdf.cell(100, 8, f"Imponibile: Euro {imp:.2f}", 0, 1)
    pdf.cell(100, 8, f"IVA (22%): Euro {iva_val:.2f}", 0, 1)
    
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(0, 112, 255) # Blu E.G. Trasporti
    pdf.cell(100, 10, f"TOTALE GENERALE: Euro {finale:.2f}", 0, 1)
    
    return pdf.output(dest='S').encode('latin-1', errors='replace')
    
# --- CONFIGURAZIONE INIZIALE PAGINA ---
st.set_page_config(page_title="E.G. TRASPORTI - Portale HR", page_icon="🚛", layout="wide")

# --- FUNZIONE PER ANIMAZIONE WELCOME ---
def load_lottieurl(url):
    r = requests.get(url)
    if r.status_code != 200:
        return None
    return r.json()

# --- TRANSIZIONE DI BENVENUTO ---
# Usiamo session_state per far apparire il benvenuto solo la prima volta che si apre l'app
if 'intro_fatta' not in st.session_state:
    placeholder = st.empty() # Crea uno spazio temporaneo che poi svuoteremo
    
    with placeholder.container():
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            # Titolo stilizzato
            st.markdown("""
                <h1 style='text-align: center; color: #0070FF; font-family: sans-serif; font-size: 50px;'>
                    Welcome to <br> E.G. TRASPORTI
                </h1>
                <p style='text-align: center; color: gray;'>Loading ...</p>
            """, unsafe_allow_html=True)
            
            # Carichiamo un'animazione di un camion/logistica
            lottie_truck = load_lottieurl("https://assets5.lottiefiles.com/packages/lf20_j9p6u8.json")
            if lottie_truck:
                st_lottie(lottie_truck, height=300, key="coding")
            
            # Barra di caricamento che dura circa 3 secondi
            bar = st.progress(0)
            for i in range(100):
                time.sleep(0.04) # 0.03 * 100 = 3 secondi
                bar.progress(i + 1)
                
    placeholder.empty() # Rimuove tutto il contenuto del benvenuto
    st.session_state['intro_fatta'] = True # Segna che l'intro è stata mostrata
    st.rerun() # Ricarica la pagina per mostrare il login

# --- CREAZIONE CARTELLE LOCALI (VAULT SICURO) ---
# Queste cartelle verranno create sul tuo PC per salvare i file fisicamente
CARTELLA_BASE = "Archivio_Sicuro_EG"
CARTELLA_DOCS = os.path.join(CARTELLA_BASE, "Documenti")
CARTELLA_FOTO = os.path.join(CARTELLA_BASE, "Foto_Profili")

for cartella in [CARTELLA_BASE, CARTELLA_DOCS, CARTELLA_FOTO]:
    if not os.path.exists(cartella):
        os.makedirs(cartella)

# --- FUNZIONI DI SICUREZZA (CRITTOGRAFIA PASSWORD) ---
def crea_hash(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def verifica_hash(password, password_hash_db):
    if crea_hash(password) == password_hash_db:
        return True
    return False

# --- CONFIGURAZIONE DATABASE SQLITE ---
# Il file .db verrà creato automaticamente nella stessa cartella
conn = sqlite3.connect('database_aziendale.db', check_same_thread=False)
cur = conn.cursor()

def inizializza_database():
# --- AGGIORNAMENTO TABELLA UTENTI ---
    cur.execute('''CREATE TABLE IF NOT EXISTS utenti(
        username TEXT PRIMARY KEY, password TEXT, ruolo TEXT, nome TEXT, cognome TEXT, data_nascita DATE, data_assunzione DATE,scadenza_patente DATE,iban TEXT,paga_mensile REAL, giro TEXT
    )''')
    
    try:
        cur.execute("ALTER TABLE utenti ADD COLUMN giro TEXT")
    except:
        pass
    conn.commit()

    # Tabella Presenze
    cur.execute('''CREATE TABLE IF NOT EXISTS presenze(
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT,data DATE,stato TEXT,dettagli TEXT
    )''')
# Tabella Storico Fatture (Anno e Mese sono UNIQUE per permettere la sovrascrittura)
    cur.execute('''CREATE TABLE IF NOT EXISTS archivio_fatture ( anno INTEGER, mese INTEGER, imponibile REAL, totale REAL, data_creazione TEXT, PRIMARY KEY (anno, mese)
    )''')
    conn.commit()
    
    # Creazione automatica del primo Dirigente se il DB è vuoto
    cur.execute("SELECT * FROM utenti WHERE username='admin'")
    if not cur.fetchone():
        cur.execute('INSERT INTO utenti VALUES (?,?,?,?,?,?,?,?,?,?,?)', 
                    ('admin', crea_hash('admin123'), 'Dirigente', 'Admin', 'Principale', #per cambiare il password del dirigente...
                     date(1980, 1, 1), date.today(), date(2030, 1, 1), 'IT0000000000000000000000000', 0.0, None))
        conn.commit()
inizializza_database()
# Demantha --> egport1
# Mudhitha --> egportv 

# --- GESTIONE SESSIONE (LOGIN) ---
if 'loggato' not in st.session_state:
    st.session_state['loggato'] = False
    st.session_state['username_corrente'] = ""
    st.session_state['ruolo_corrente'] = ""
    st.session_state['nome_corrente'] = ""

def login():
    st.markdown("<h1 style='text-align: center; color: #0070FF;'>🚛 Portale Aziendale E.G. TRASPORTI</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.subheader("🔐 Area Riservata")
        utente_input = st.text_input("Nome Utente (Username)")
        password_input = st.text_input("Password", type='password')
        
        if st.button("Accedi al Portale", use_container_width=True):
            cur.execute("SELECT password, ruolo, nome, cognome FROM utenti WHERE username=?", (utente_input,))
            risultato = cur.fetchone()
            
            if risultato and verifica_hash(password_input, risultato[0]):
                st.session_state['loggato'] = True
                st.session_state['username_corrente'] = utente_input
                st.session_state['ruolo_corrente'] = risultato[1]
                st.session_state['nome_corrente'] = f"{risultato[2]} {risultato[3]}"
                st.rerun()
            else:
                st.error("Credenziali errate. Riprova.")

def logout():
    st.session_state['loggato'] = False
    st.session_state['username_corrente'] = ""
    st.session_state['ruolo_corrente'] = ""
    st.rerun()

# Se non sei loggato, mostra solo la schermata di login e ferma lo script
if not st.session_state['loggato']:
    login()
    st.stop()

# --- SIDEBAR DI NAVIGAZIONE ---
st.sidebar.title(f"👤 Ciao, {st.session_state['nome_corrente']}")
st.sidebar.markdown(f"**Ruolo:** {st.session_state['ruolo_corrente']}")
st.sidebar.markdown("---")

if st.session_state['ruolo_corrente'] == "Dirigente":
    menu = st.sidebar.radio("Navigazione", ["Dashboard", "Gestione Dipendenti", "Carica Documenti", "Registro Presenze", "Fatturazione", "Calcolo Paghe"])
else:
    menu = st.sidebar.radio("Navigazione", ["Il Mio Profilo", "I Miei Documenti", "Comunica Presenza"])

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Esci (Logout)"):
    logout()

                                                                # ==========================================
                                                                # ============ AREA DIRIGENTE ==============
                                                                # ==========================================

if st.session_state['ruolo_corrente'] == "Dirigente":

# --- 1. DASHBOARD ---
    if menu == "Dashboard":
        st.title("📊 Analisi Andamento Fatturato")

        # 1. Recupero dati dal database
        df_archivio = pd.read_sql_query("SELECT * FROM archivio_fatture", conn)

        if not df_archivio.empty:
            # Filtro per Anno
            anni_disponibili = sorted(df_archivio['anno'].unique(), reverse=True)
            anno_selezionato = st.selectbox("📅 Seleziona l'anno:", anni_disponibili)
            df_filtrato = df_archivio[df_archivio['anno'] == anno_selezionato]

            # --- 2. LOGICA DI ORDINAMENTO CRONOLOGICO ---
            mesi_nomi = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
            
            # Creiamo una tabella base con i 12 mesi
            df_mesi_base = pd.DataFrame({'mese': range(1, 13), 'Mese': mesi_nomi})

            # Sommiamo i dati reali raggruppati per numero mese
            df_mensile = df_filtrato.groupby('mese')[['imponibile', 'totale']].sum().reset_index()

            # Uniamo i dati reali con i 12 mesi (per non avere buchi)
            df_finale = pd.merge(df_mesi_base, df_mensile, on='mese', how='left').fillna(0)

            # --- IL TRUCCO PER L'ORDINE ---
            # Diciamo a Pandas che la colonna 'Mese' è una categoria con un ordine specifico
            df_finale['Mese'] = pd.Categorical(df_finale['Mese'], categories=mesi_nomi, ordered=True)
            df_finale = df_finale.sort_values('Mese')

            # --- 3. VISUALIZZAZIONE GRAFICO A LINEE ---
            st.subheader(f"📈 Andamento Mensile - Anno {anno_selezionato}")
            
            # Prepariamo i dati per il grafico (usiamo i nomi dei mesi come indice)
            df_grafico = df_finale.set_index('Mese')[['imponibile', 'totale']]
            
            # Disegniamo il grafico a LINEE
            st.line_chart(df_grafico, height=400)

            # Metriche sotto il grafico
            tot_anno = df_finale['totale'].sum()
            media_mensile = tot_anno / 12
            
            c1, c2 = st.columns(2)
            c1.metric(f"Totale Fatturato {anno_selezionato}", f"€ {tot_anno:,.2f}")
            c2.metric("Media Mensile", f"€ {media_mensile:,.2f}")
        else:
            st.info("Non ci sono ancora fatture archiviate per generare il grafico.")


# --- 2. GESTIONE DIPENDENTI  ---
    elif menu == "Gestione Dipendenti":
        st.title("👥 Gestione Anagrafica Dipendenti")
        
        # Carichiamo i dati all'inizio per averli sempre aggiornati
        df_utenti = pd.read_sql_query("SELECT * FROM utenti WHERE ruolo='Dipendente'", conn)
        
        # Creazione dei Tab
        tab_inserisci, tab_lista = st.tabs(["➕ Nuovo Dipendente", "📋 Lista e Modifica"])
        
        # --- TAB 1: INSERIMENTO NUOVO DIPENDENTE ---
        with tab_inserisci:
            with st.form("form_nuovo_dipendente", clear_on_submit=True):
                st.subheader("Inserisci Dati Anagrafici")
                col1, col2 = st.columns(2)
                
                with col1:
                    nuovo_user = st.text_input("Username (es. Mario80)")
                    nuova_pass = st.text_input("Password Iniziale", type='password')
                    nome = st.text_input("Nome")
                    cognome = st.text_input("Cognome")
                    iban = st.text_input("IBAN")
                    paga_mensile = st.number_input("Paga Mensile Lorda (€)", min_value=0.0, step=100.0)
                    nuovo_giro = st.selectbox("Assegna Giro/Ruolo", ["Verona", "Padova", "Segretario"])
                
                with col2:
                    data_nascita = st.date_input("Data di Nascita", min_value=date(1950, 1, 1))
                    data_assunzione = st.date_input("Data di Assunzione")
                    scadenza_patente = st.date_input("Scadenza Patente")
                
                if st.form_submit_button("💾 Salva Nuovo Dipendente", use_container_width=True):
                    if nuovo_user and nuova_pass and nome and cognome:
                        try:
                            cur.execute('''INSERT INTO utenti 
                            (username, password, ruolo, nome, cognome, data_nascita, data_assunzione, scadenza_patente, iban, paga_mensile, giro) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)''', 
                            (nuovo_user, crea_hash(nuova_pass), "Dipendente", nome, cognome, data_nascita, data_assunzione, scadenza_patente, iban, paga_mensile, nuovo_giro))
                            conn.commit()
                            
                            # Creazione cartella documenti automatica
                            cartella_personale = os.path.join(CARTELLA_DOCS, nuovo_user)
                            if not os.path.exists(cartella_personale):
                                os.makedirs(cartella_personale)
                                
                            st.success(f"✅ Dipendente {nome} {cognome} registrato con successo!")
                            time.sleep(1)
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("❌ Errore: L'Username esiste già.")
                    else:
                        st.warning("⚠️ Compila tutti i campi obbligatori (Username, Password, Nome e Cognome).")

        # --- TAB 2: LISTA, MODIFICA ED ELIMINAZIONE ---
        with tab_lista:
            st.subheader("Lista Personale Attivo")
            # Mostriamo la tabella (senza password per sicurezza)
            st.dataframe(df_utenti.drop(columns=['password']), use_container_width=True, hide_index=True)
            
            st.markdown("---")
            col_mod, col_del = st.columns(2)
            
            with col_mod:
                st.subheader("✏️ Modifica Dati")
                lista_u = df_utenti['username'].tolist()
                u_da_mod = st.selectbox("Seleziona chi modificare:", [""] + lista_u)
                
                if u_da_mod:
                    # Recuperiamo i dati correnti del dipendente selezionato
                    cur.execute("SELECT * FROM utenti WHERE username=?", (u_da_mod,))
                    d = cur.fetchone()
                    
                    with st.form("form_modifica_veloce"):
                        m_nome = st.text_input("Nome", value=d[3])
                        m_cognome = st.text_input("Cognome", value=d[4])
                        m_giro = st.selectbox("Giro/Ruolo", ["Verona", "Padova", "Segretario"], 
                                            index=["Verona", "Padova", "Segretario"].index(d[10]) if d[10] in ["Verona", "Padova", "Segretario"] else 0)
                        m_paga = st.number_input("Paga Mensile (€)", value=float(d[9]))
                        m_iban = st.text_input("IBAN", value=d[8])
                        
                        c1, c2 = st.columns(2)
                        m_assunzione = c1.date_input("Data Assunzione", value=pd.to_datetime(d[6]).date())
                        m_patente = c2.date_input("Scadenza Patente", value=pd.to_datetime(d[7]).date())
                        
                        if st.form_submit_button("💾 Aggiorna Dati Dipendente", use_container_width=True):
                            cur.execute('''UPDATE utenti SET nome=?, cognome=?, giro=?, paga_mensile=?, iban=?, 
                                        data_assunzione=?, scadenza_patente=? WHERE username=?''',
                                        (m_nome, m_cognome, m_giro, m_paga, m_iban, m_assunzione, m_patente, u_da_mod))
                            conn.commit()
                            st.success(f"✅ Dati di {u_da_mod} aggiornati!")
                            time.sleep(1)
                            st.rerun()

            with col_del:
                st.subheader("🗑️ Elimina Profilo")
                u_da_del = st.selectbox("Rimuovi utente dal sistema:", [""] + lista_u, key="del_sel_box")
                if st.button("❌ Elimina Definitivamente", type="secondary", use_container_width=True):
                    if u_da_del:
                        cur.execute("DELETE FROM utenti WHERE username=?", (u_da_del,))
                        cur.execute("DELETE FROM presenze WHERE username=?", (u_da_del,))
                        conn.commit()
                        st.warning(f"Profilo {u_da_del} rimosso.")
                        time.sleep(1)
                        st.rerun()
# --- 3. CARICA DOCUMENTI ---
    elif menu == "Carica Documenti":
        st.title("📂 Caricamento Documenti (Buste Paga, Contratti)")
        
        # Recupera lista dipendenti
        cur.execute("SELECT username, nome, cognome FROM utenti WHERE ruolo='Dipendente'")
        lista_dipendenti = cur.fetchall()
        opzioni_dipendenti = {f"{d[1]} {d[2]} ({d[0]})": d[0] for d in lista_dipendenti}
        
        if not opzioni_dipendenti:
            st.warning("Nessun dipendente registrato nel sistema.")
        else:
            dipendente_scelto = st.selectbox("Seleziona il Dipendente:", list(opzioni_dipendenti.keys()))
            username_scelto = opzioni_dipendenti[dipendente_scelto]
            
            tipo_documento = st.selectbox("Tipo di Documento", ["Busta Paga", "Contratto", "UNILAV", "Altro"])
            
            # --- NUOVA PARTE PER SELEZIONE PERIODO ---
            st.markdown("### 📅 Periodo di riferimento")
            c1, c2 = st.columns(2)
            with c1: ann_doc = st.selectbox("Anno Doc", [2025, 2026], index=1)
            with c2: mes_doc = st.selectbox("Mese Doc", list(range(1, 13)), index=date.today().month-1)


            file_caricato = st.file_uploader("Trascina qui il file PDF", type=['pdf'])
            
            if st.button("📤 Salva Documento in Archivio", type="primary"):
                if file_caricato is not None:
                    # 1. Percorso Storico Aziendale: Archivio_Sicuro_EG/2025/Mese_4/
                    cartella_destinazione = os.path.join(CARTELLA_BASE, str(ann_doc), f"Mese_{mes_doc}")
                    os.makedirs(cartella_destinazione, exist_ok=True)
                    
                    nome_file_finale = f"{tipo_documento.replace(' ', '_')}_{username_scelto}.pdf"
                    percorso_salv = os.path.join(cartella_destinazione, nome_file_finale)
                    
                    # Salva nello storico
                    with open(percorso_salv, "wb") as f:
                        f.write(file_caricato.getbuffer())
                    
                    # 2. Copia Personale per il dipendente: Archivio_Sicuro_EG/Documenti/username/
                    percorso_personale = os.path.join(CARTELLA_DOCS, username_scelto, nome_file_finale)
                    os.makedirs(os.path.dirname(percorso_personale), exist_ok=True)
                    
                    with open(percorso_personale, "wb") as f:
                        f.write(file_caricato.getbuffer())

                    st.success(f"✅ Documento salvato con successo!")
                    st.info(f"Archiviato in: {ann_doc}/Mese_{mes_doc} e nel profilo di {username_scelto}")
                else:
                    st.error("Inserisci un file prima di salvare.")

  # --- 4. REGISTRO PRESENZE (INTERATTIVO) ---
    elif menu == "Registro Presenze":
        st.title("📅 Registro Presenze Mensile")

        # 1. Selezione mese/anno
        c1, c2 = st.columns(2)
        with c1:
            mese_sel = st.selectbox("Mese", list(range(1, 13)), index=date.today().month - 1,
                                    format_func=lambda m: calendar.month_name[m])
        with c2:
            anno_sel = st.selectbox("Anno", [2025, 2026], index=1)

        # 2. Recupera dati
        cur.execute("SELECT username, nome, cognome FROM utenti WHERE ruolo='Dipendente' ORDER BY cognome")
        dipendenti = cur.fetchall()
        
        if not dipendenti:
            st.warning("Nessun dipendente registrato.")
            st.stop()

        df_pres_mese = pd.read_sql_query(
            "SELECT username, data, stato FROM presenze WHERE strftime('%m',data)=? AND strftime('%Y',data)=?",
            conn, params=(f"{mese_sel:02d}", str(anno_sel))
        )

        # 3. Costruisci DataFrame per l'editor
        num_days = calendar.monthrange(anno_sel, mese_sel)[1]
        nomi_giorni_it = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
        
        date_list = [date(anno_sel, mese_sel, d) for d in range(1, num_days + 1)]
        df_pivot = pd.DataFrame({
            "Data_Raw": date_list, # Colonna nascosta per i calcoli
            "📅 Data": [d.strftime("%d/%m/%Y") for d in date_list],
            "Giorno": [nomi_giorni_it[d.weekday()] for d in date_list]
        })

        emp_cols = []
        for user, nome, cognome in dipendenti:
            col_name = f"{nome} {cognome}"
            emp_cols.append(col_name)
            valori_colonna = []
            for dt in date_list:
                match = df_pres_mese[(df_pres_mese['username'] == user) & (df_pres_mese['data'] == str(dt))]
                if not match.empty:
                    stato = match.iloc[0]['stato']
                    if stato == "Presente": valori_colonna.append("✅ Presente")
                    elif stato == "Assente": valori_colonna.append("❌ Assente")
                    elif stato == "No Lavoro": valori_colonna.append("⚪ No Lavoro")
                    else: valori_colonna.append("⭕ Non reg.")
                else:
                    if dt.weekday() == 6: # 6 corrisponde a Domenica
                        valori_colonna.append("⚪ No Lavoro")
                    else:
                        valori_colonna.append("⭕ Non reg.")
            df_pivot[col_name] = valori_colonna

        # 4. Visualizzazione con st.data_editor
        st.markdown(f"### 📊 Modifica Registro {calendar.month_name[mese_sel]}")
        st.info("💡 Clicca sulle celle per cambiare lo stato e poi premi il tasto 'Salva Modifiche' in fondo.")

        # Configurazione colonne (Menu a tendina nelle celle)
        config_colonne = {
            "Data_Raw": None, # Nascondi
            "📅 Data": st.column_config.TextColumn(disabled=True),
            "Giorno": st.column_config.TextColumn(disabled=True),
        }
        for col in emp_cols:
            config_colonne[col] = st.column_config.SelectboxColumn(
                options=["✅ Presente", "❌ Assente", "⚪ No Lavoro", "⭕ Non reg."],
                width="medium"
            )

        # Mostra l'editor
        df_editato = st.data_editor(
            df_pivot,
            column_config=config_colonne,
            hide_index=True,
            use_container_width=True,
            height=500,
            key="editor_presenze"
        )

        # 5. Pulsante di salvataggio
        if st.button("💾 Salva Tutte le Modifiche", type="primary", use_container_width=True):
            for index, row in df_editato.iterrows():
                data_corrente = row["Data_Raw"]
                for user, nome, cognome in dipendenti:
                    col_label = f"{nome} {cognome}"
                    nuovo_valore_raw = row[col_label]
                    
                    # Mappatura per il database
                    stato_db = "Non registrato"
                    if "Presente" in nuovo_valore_raw: stato_db = "Presente"
                    elif "Assente" in nuovo_valore_raw: stato_db = "Assente"
                    elif "No Lavoro" in nuovo_valore_raw: stato_db = "No Lavoro"

                    if stato_db != "Non registrato":
                        # 1. SALVATAGGIO SU SQLITE (Locale/Temporaneo)
                        cur.execute("SELECT id FROM presenze WHERE username=? AND data=?", (user, data_corrente))
                        esiste = cur.fetchone()
                        if esiste:
                            cur.execute("UPDATE presenze SET stato=? WHERE id=?", (stato_db, esiste[0]))
                        else:
                            cur.execute("INSERT INTO presenze (username, data, stato, dettagli) VALUES (?,?,?,?)",
                                        (user, data_corrente, stato_db, ""))
                        
                        # 2. SALVATAGGIO SU GOOGLE SHEETS (Permanente)
                        # Questa è la riga che abbiamo aggiunto:
                        salva_presenza_su_google(col_label, data_corrente, stato_db)
                    
            conn.commit()
            st.success("Dati salvati sia nel database che su Google Sheets!")
            time.sleep(1)
            st.rerun()
        # --- 5. FATTURAZIONE (VERSIONE CORRETTA E OTTIMIZZATA) ---
    elif menu == "Fatturazione":
            st.title("🚛 Generatore Fatture Logistica")
            
            # 1. Input principali in colonne
            c1, c2, c3 = st.columns([1, 1, 2])
            with c1:
                anno_f = st.number_input("Anno", value=datetime.now().year)
                mese_f = st.selectbox("Mese", list(range(1, 13)), index=datetime.now().month - 1)
            with c2:
                costo_km = st.number_input("Costo per KM (€)", value=0.63, step=0.01)
                km_extra = st.number_input("Extra KM", value=0)
            with c3:
                # Calcoliamo i giorni del mese per il selettore ferie
                num_days = calendar.monthrange(anno_f, mese_f)[1]
                giorni_del_mese = list(range(1, num_days + 1))
                ferie = st.multiselect(
                    "🌴 Seleziona giorni di Ferie / Festivi",
                    options=giorni_del_mese,
                    help="I giorni selezionati avranno KM azzerati automaticamente"
                )

            # 2. Generazione dati logica
            giorni_sett = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]
            dati_fattura = []
            
            for d in range(1, num_days + 1):
                dt = datetime(anno_f, mese_f, d)
                wd = dt.weekday()
                
                # Se il giorno è tra le ferie, KM = 0, altrimenti usa i tuoi valori standard
                if d in ferie:
                    km_p = 0.0
                    km_v = 0.0
                else:
                    km_p = [0, 397, 320, 394, 306, 446, 0][wd]
                    km_v = [158, 183, 147, 187, 183, 187, 0][wd]
                
                dati_fattura.append({
                    "Data": dt.strftime("%d/%m/%Y"), 
                    "Giorno": giorni_sett[wd], 
                    "KM Padova": float(km_p), 
                    "KM Verona": float(km_v)
                })
            
            df_f = pd.DataFrame(dati_fattura)

            # 3. Visualizzazione Tabella (L'editor crea la variabile 'edited_f')
            st.markdown("### 📝 Revisione KM Mensili")
            edited_f = st.data_editor(
                df_f, 
                hide_index=True, 
                use_container_width=True,
                column_config={
                    "KM Padova": st.column_config.NumberColumn(format="%d km"),
                    "KM Verona": st.column_config.NumberColumn(format="%d km")
                }
            )
            
            # 4. Calcoli Finali (basati sulla tabella modificata)
            tot_km = edited_f["KM Padova"].sum() + edited_f["KM Verona"].sum() + km_extra
            imponibile = tot_km * costo_km
            iva_calc = imponibile * 0.22
            totale_f = imponibile + iva_calc
            
            # UI Risultati
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("TOTALE KM", f"{tot_km:,.0f} km")
            m2.metric("IMPONIBILE", f"€ {imponibile:,.2f}")
            m3.metric("TOTALE FATTURA (IVA)", f"€ {totale_f:,.2f}")
            
            # 5. Generazione PDF e Salvataggio
            if st.button("🚀 Genera PDF e Archivia", use_container_width=True, type="primary"):
                percorso_mese = os.path.join(CARTELLA_BASE, str(anno_f), f"Mese_{mese_f}")
                os.makedirs(percorso_mese, exist_ok=True)
                
                # Richiamo funzione PDF
                pdf_file = genera_pdf(edited_f, km_extra, tot_km, imponibile, iva_calc, totale_f, mese_f, anno_f)
                nome_file_fattura = f"Fattura_EG_{mese_f}_{anno_f}.pdf"
                percorso_completo_pdf = os.path.join(percorso_mese, nome_file_fattura)

                link_drive = salva_su_drive(percorso_completo_pdf, nome_file_fattura)
                st.success(f"✅ Fattura caricata su Drive! [Clicca qui per vederla]({link_drive})")
                
                with open(percorso_completo_pdf, "wb") as f:
                    f.write(pdf_file)
                
                # Database
                cur.execute("""
                    INSERT OR REPLACE INTO archivio_fatture (anno, mese, imponibile, totale, data_creazione)
                    VALUES (?, ?, ?, ?, ?)
                """, (anno_f, mese_f, round(imponibile, 2), round(totale_f, 2), datetime.now().strftime("%Y-%m-%d %H:%M")))
                conn.commit()
                
                st.success(f"✅ Fattura archiviata con successo!")
                st.download_button(
                    "📥 Scarica PDF", 
                    data=pdf_file, 
                    file_name=nome_file_fattura, 
                    mime="application/pdf",
                    use_container_width=True
                
                

                
                )
# --- 6. CALCOLO_PAGHE (AGGIORNATO) ---
    elif menu == "Calcolo Paghe":
        st.title("💰 Calcolo Stipendi Proporzionali")
        
        c1, c2 = st.columns(2)
        with c1: mese_p = st.selectbox("Mese", list(range(1, 13)), index=date.today().month-1)
        with c2: anno_p = st.selectbox("Anno ", [2025, 2026], index=1)
        
        st.info("💡 Calcolo automatico basato sul Giro assegnato in Anagrafica.")

        def conta_lavorativi(anno, mese, tipo_giro):
            num_days = calendar.monthrange(anno, mese)[1]
            giorni_teorici = 0
            for d in range(1, num_days + 1):
                wd = date(anno, mese, d).weekday() # 0=Lun, 6=Dom
                if tipo_giro == "Padova":
                    if wd in [1, 2, 3, 4, 5]: giorni_teorici += 1 # Mar-Sab
                elif tipo_giro == "Verona":
                    if wd in [0, 1, 2, 3, 4, 5]: giorni_teorici += 1 # Lun-Sab
                elif tipo_giro == "Segretario":
                    giorni_teorici = 22 # Standard fisso
                    break 
            return giorni_teorici

        # Recupero dipendenti con il loro GIRO salvato
        cur.execute("SELECT username, nome, cognome, paga_mensile, giro FROM utenti WHERE ruolo='Dipendente'")
        dipendenti = cur.fetchall()
        
        risultati_paghe = []
        for user, nome, cognome, paga_base, giro_db in dipendenti:
            tipo = giro_db if giro_db else "Verona"
            
            # Calcolo Giorni Teorici
            g_teorici = conta_lavorativi(anno_p, mese_p, tipo)
            
            # Calcolo Giorni Effettivi (Presenze)
            cur.execute("""SELECT COUNT(*) FROM presenze WHERE username=? AND 
                        strftime('%m', data)=? AND strftime('%Y', data)=? AND stato='Presente'""", 
                        (user, f"{mese_p:02d}", str(anno_p)))
            g_effettivi = cur.fetchone()[0]
            
            # Se è segretario, permettiamo inserimento manuale o usiamo 22 come base
            if tipo == "Segretario":
                paga_dovuta = (paga_base / 22) * g_effettivi if g_effettivi > 0 else 0
            else:
                paga_dovuta = (paga_base / g_teorici) * g_effettivi if g_teorici > 0 else 0
            
            risultati_paghe.append({
                "Dipendente": f"{nome} {cognome}",
                "Paga Base": f"€ {paga_base:.2f}",
                "Giro Assegnato": tipo,
                "Giorni Dovuti": g_teorici,
                "Giorni Lavorati": g_effettivi,
                "STIPENDIO NETTO": f"€ {paga_dovuta:.2f}"
            })

        st.table(pd.DataFrame(risultati_paghe))
        
        if st.button("🖨️ Esporta Riepilogo Paghe"):
            st.success("Riepilogo generato!")                       # ==========================================
                                                                # =========== AREA DIPENDENTE ==============
                                                                # ==========================================

elif st.session_state['ruolo_corrente'] == "Dipendente":
        username_att = st.session_state['username_corrente']

        # --- 1. PROFILO ---
        if menu == "Il Mio Profilo":
            st.title("👤 Area Personale")
            
            # Recupero dati anagrafici
            cur.execute("SELECT nome, cognome, data_nascita, data_assunzione, scadenza_patente, iban, paga_mensile, giro FROM utenti WHERE username=?", (username_att,))
            dati = cur.fetchone()
            
            if dati:
                nome_c, cogn_c, d_nasc, d_ass, s_pat, iban_c, paga_base, giro_c = dati
                paga_base = paga_base if paga_base is not None else 0.0
                giro_c = giro_c if giro_c else "Verona" # Default se vuoto

                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("Foto Profilo")
                    percorso_foto = os.path.join(CARTELLA_FOTO, f"{username_att}.png")
                    if os.path.exists(percorso_foto):
                        st.image(percorso_foto, width=200)
                    else:
                        st.info("Nessuna foto inserita.")
                    
                    nuova_foto = st.file_uploader("Aggiorna Foto", type=['jpg', 'jpeg', 'png'])
                    if st.button("Salva Foto"):
                        if nuova_foto:
                            with open(percorso_foto, "wb") as f:
                                f.write(nuova_foto.getbuffer())
                            st.success("Foto aggiornata!")
                            st.rerun()

                with col2:
                    st.subheader("I Miei Dati")
                    st.markdown(f"**Nome e Cognome:** {nome_c} {cogn_c}")
                    st.markdown(f"**IBAN:** {iban_c}")
                    st.markdown(f"**Giro Assegnato:** {giro_c}")
                    st.markdown(f"**Paga Base:** € {paga_base:.2f}")
                    
                st.divider()

                # --- NUOVA PARTE: CALCOLO STIPENDIO CORRENTE ---
                st.subheader(f"💰 Situazione Stipendio: {date.today().strftime('%B %Y')}")
                
                # Parametri temporali correnti
                oggi = date.today()
                mese_corrente = oggi.month
                anno_corrente = oggi.year

                # Funzione di calcolo giorni (uguale a quella del dirigente)
                def conta_giorni_teorici(anno, mese, tipo_giro):
                    num_days = calendar.monthrange(anno, mese)[1]
                    g_teorici = 0
                    for d in range(1, num_days + 1):
                        wd = date(anno, mese, d).weekday() # 0=Lun, 6=Dom
                        if tipo_giro == "Padova":
                            if wd in [1, 2, 3, 4, 5]: g_teorici += 1 # Mar-Sab
                        elif tipo_giro == "Verona":
                            if wd in [0, 1, 2, 3, 4, 5]: g_teorici += 1 # Lun-Sab
                        elif tipo_giro == "Segretario":
                            return 22
                    return g_teorici

                # Calcolo giorni dovuti e lavorati
                g_dovuti = conta_giorni_teorici(anno_corrente, mese_corrente, giro_c)
                
                cur.execute("""SELECT COUNT(*) FROM presenze WHERE username=? AND 
                               strftime('%m', data)=? AND strftime('%Y', data)=? AND stato='Presente'""", 
                            (username_att, f"{mese_corrente:02d}", str(anno_corrente)))
                g_lavorati = cur.fetchone()[0]

                # Calcolo paga proporzionale
                if giro_c == "Segretario":
                    stipendio_maturato = (paga_base / 22) * g_lavorati if g_lavorati > 0 else 0
                else:
                    stipendio_maturato = (paga_base / g_dovuti) * g_lavorati if g_dovuti > 0 else 0

                # Visualizzazione Tabella come il Dirigente
                df_riepilogo = pd.DataFrame([{
                    "Mese": f"{mese_corrente}/{anno_corrente}",
                    "Giro": giro_c,
                    "Giorni Dovuti": g_dovuti,
                    "Giorni Lavorati": g_lavorati,
                    "Paga Base": f"€ {paga_base:.2f}",
                    "MATURATO AD OGGI": f"€ {stipendio_maturato:.2f}"
                }])
                
                st.table(df_riepilogo)

                # Grafico andamento (quello che avevi già)
                st.markdown("### 📈 Andamento Storico")
                query_grafico = """
                    SELECT strftime('%m/%Y', data) as Mese, 
                    COUNT(*) as giorni_presenza
                    FROM presenze 
                    WHERE username = ? AND stato = 'Presente'
                    GROUP BY Mese ORDER BY data DESC LIMIT 6
                """
                df_grafico = pd.read_sql_query(query_grafico, conn, params=(username_att,))
                if not df_grafico.empty:
                    df_grafico['Stipendio (€)'] = (paga_base / 26) * df_grafico['giorni_presenza']
                    st.area_chart(df_grafico.set_index('Mese')['Stipendio (€)'])
        # --- 2. I MIEI DOCUMENTI ---
        elif menu == "I Miei Documenti":
            st.title("📄 Archivio Documenti")
            cartella_personale = os.path.join(CARTELLA_DOCS, username_att)
            
            if os.path.exists(cartella_personale):
                file_presenti = os.listdir(cartella_personale)
                if not file_presenti:
                    st.info("Nessun documento disponibile.")
                else:
                    for file in file_presenti:
                        percorso_file = os.path.join(cartella_personale, file)
                        with open(percorso_file, "rb") as f:
                            st.download_button(f"⬇️ Scarica {file}", f.read(), file_name=file, key=file)
            else:
                st.info("Archivio non ancora configurato.")

        # --- 3. COMUNICA PRESENZA ---
        elif menu == "Comunica Presenza":
            st.title("📍 La Mia Presenza")
            st.markdown("Puoi registrare la presenza per **oggi** e i **2 giorni precedenti**.")
            
            oggi = date.today()
            giorni_disponibili = [oggi - pd.Timedelta(days=i) for i in range(3)]
            nomi_giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]

            for giorno in giorni_disponibili:
                cur.execute("SELECT stato, dettagli FROM presenze WHERE username=? AND data=?", (username_att, giorno.isoformat()))
                esistente = cur.fetchone()
                
                # Formattazione etichetta
                label = "📅 OGGI" if giorno == oggi else ("📆 Ieri" if giorno == oggi - pd.Timedelta(days=1) else "📆 2 giorni fa")
                testo_giorno = f"{label} — {nomi_giorni[giorno.weekday()]} {giorno.strftime('%d/%m/%Y')}"
                
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"#### {testo_giorno}")
                        if esistente:
                            simbolo = "✅" if esistente[0] == "Presente" else ("❌" if esistente[0] == "Assente" else "⚪")
                            st.success(f"{simbolo} Stato: **{esistente[0]}**")
                            if esistente[1]: st.caption(f"📝 Nota: {esistente[1]}")
                        else:
                            st.warning("⭕ Non ancora registrato")
                    
                    with c2:
                        if not esistente:
                            with st.form(key=f"form_{giorno}"):
                                scelta = st.radio("Seleziona:", ["✅ Presente", "❌ Assente"], horizontal=True)
                                nota = st.text_input("Nota (opzionale):")
                                if st.form_submit_button("Invia"):
                                    stato_db = "Presente" if "Presente" in scelta else "Assente"
                                    cur.execute("INSERT INTO presenze (username, data, stato, dettagli) VALUES (?,?,?,?)",
                                               (username_att, giorno, stato_db, nota))
                                    conn.commit()
                                    st.rerun()
                        else:
                            st.info("Registrato. Per modifiche contatta l'ufficio.")
