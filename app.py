import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import uuid
import json
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Konfigurasi Halaman 
st.set_page_config(page_title="DIMA-X | AI Agent", page_icon="🚀", layout="centered", initial_sidebar_state="expanded")

# Custom CSS ala ChatGPT
st.markdown("""
    <style>
    .stApp { background-color: #212121; color: #ececec; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #424242;
        background-color: #2f2f2f;
        color: white;
        transition: all 0.2s;
        text-align: left;
    }
    .stButton>button:hover {
        background-color: #424242;
        border-color: #565656;
    }
    </style>
""", unsafe_allow_html=True)

# Ambil API Key Gemini
api_key = st.secrets["GEMINI_API_KEY"]

# 2. Inisialisasi Firebase (Hanya berjalan satu kali)
if not firebase_admin._apps:
    # Membaca rahasia Firebase dari Streamlit Secrets
    firebase_secrets = st.secrets["firebase"]["firebase_json"]
    cred_dict = json.loads(firebase_secrets)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()
collection_name = "dimax_history"

# Fungsi Firebase
def get_all_sessions():
    sessions = {}
    # Mengambil obrolan dari yang paling baru
    docs = db.collection(collection_name).order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
    for doc in docs:
        sessions[doc.id] = doc.to_dict()
    return sessions

def create_new_session():
    new_id = str(uuid.uuid4())
    new_data = {
        "title": "Obrolan Baru", 
        "messages": [], 
        "updated_at": datetime.datetime.now().isoformat()
    }
    db.collection(collection_name).document(new_id).set(new_data)
    return new_id

def delete_session(session_id):
    db.collection(collection_name).document(session_id).delete()

def save_message(session_id, messages, title=None):
    update_data = {
        "messages": messages,
        "updated_at": datetime.datetime.now().isoformat()
    }
    if title:
        update_data["title"] = title
    db.collection(collection_name).document(session_id).update(update_data)

# 3. Manajemen Sesi Aktif
chat_sessions = get_all_sessions()

if "current_session_id" not in st.session_state:
    if len(chat_sessions) > 0:
        # Buka obrolan terakhir yang ada di database
        st.session_state.current_session_id = list(chat_sessions.keys())[0]
    else:
        st.session_state.current_session_id = create_new_session()
        chat_sessions = get_all_sessions() # Refresh data

# Cek jika sesi aktif terhapus
if st.session_state.current_session_id not in chat_sessions:
    if len(chat_sessions) > 0:
        st.session_state.current_session_id = list(chat_sessions.keys())[0]
    else:
        st.session_state.current_session_id = create_new_session()
        chat_sessions = get_all_sessions()

current_session_id = st.session_state.current_session_id
current_data = chat_sessions[current_session_id]
current_messages = current_data.get("messages", [])

# 4. Sidebar - Navigasi Riwayat Firebase
with st.sidebar:
    if st.button("➕ Obrolan Baru", use_container_width=True):
        st.session_state.current_session_id = create_new_session()
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("RIWAYAT OBROLAN")
    
    for s_id, s_data in chat_sessions.items():
        col1, col2 = st.columns([8, 2])
        with col1:
            if st.button(f"💬 {s_data['title']}", key=f"btn_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{s_id}"):
                delete_session(s_id)
                st.rerun()
                
    st.divider()
    st.caption("WORKSPACE")
    mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])
    uploaded_file = st.file_uploader("📄 Upload Dokumen", type=['pdf', 'txt'])

# 5. Logika Memori Asisten Pribadi
base_memory = "Penggunamu bernama Dimas, mahasiswa Sistem Informasi dan staf administrasi di Disbudporapar Kabupaten Landak."
if "STUDY-X" in mode_dima:
    system_instruction = f"Mode STUDY-X. {base_memory} Bantu Dimas belajar dan merangkum modul."
elif "WORK-X" in mode_dima:
    system_instruction = f"Mode WORK-X. {base_memory} Bantu menyusun laporan dinas dan surat resmi."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Mode WRITE-X. {base_memory} Perbaiki tata bahasa dan struktur tulisan."
else:
    system_instruction = f"Kamu adalah DIMA-X, asisten AI pribadi yang cerdas. {base_memory} Jawab natural dan langsung ke inti."

def get_document_text(file):
    text = ""
    if file.name.endswith('.txt'):
        text = file.read().decode('utf-8')
    elif file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text

# 6. Layar Selamat Datang
if len(current_messages) == 0:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white; font-size: 2.5rem;'>🚀 DIMA-X</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 1.1rem;'>Apa yang bisa saya bantu hari ini, Mas Dimas?</p>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎓 Ringkas materi kuliah", use_container_width=True):
            current_messages.append({"role": "user", "content": "Bantu saya meringkas materi kuliah Sistem Informasi."})
            save_message(current_session_id, current_messages, title="Ringkasan Materi")
            st.rerun()
    with col2:
        if st.button("💼 Buat laporan dinas", use_container_width=True):
            current_messages.append({"role": "user", "content": "Bantu saya menyusun kerangka laporan dinas."})
            save_message(current_session_id, current_messages, title="Laporan Dinas")
            st.rerun()

# Menampilkan Pesan
for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. Input AI dan Simpan ke Firebase
if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
    # Generate judul otomatis untuk obrolan baru
    new_title = current_data["title"]
    if len(current_messages) == 0:
        new_title = prompt[:25] + "..." if len(prompt) > 25 else prompt

    current_messages.append({"role": "user", "content": prompt})
    save_message(current_session_id, current_messages, title=new_title)
    
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        client = genai.Client(api_key=api_key)
        context = ""
        if uploaded_file:
            context = f"\n\n--- KONTEKS DOKUMEN ---\n{get_document_text(uploaded_file)}\n\nBerdasarkan dokumen di atas:\n"

        final_prompt = context + prompt

        with st.chat_message("assistant"):
            with st.spinner("DIMA-X sedang mengetik..."):
                response = client.models.generate_content(
                    model='gemini-3.6-flash', 
                    contents=final_prompt,
                    config=types.GenerateContentConfig(system_instruction=system_instruction)
                )
                st.markdown(response.text)
        
        current_messages.append({"role": "assistant", "content": response.text})
        save_message(current_session_id, current_messages) # Simpan balasan AI ke database

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
