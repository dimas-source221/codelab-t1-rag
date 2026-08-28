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

# 2. Desain CSS Custom (Visual Effect, Glow, & Font)
st.markdown("""
    <style>
    /* Mengimpor font modern berkarakter (Nunito untuk Brand, Roboto untuk Teks) */
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Roboto:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    .stApp { background-color: #000000; color: #e3e3e3; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stSidebar"] { background-color: #141414; }
    
    /* Branding Sidebar - Posisi pas di pojok kanan */
    .brand-sidebar {
        font-family: 'Nunito', sans-serif;
        background: linear-gradient(90deg, #4A90E2, #001f3f);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1.8rem;
        font-weight: 900;
        text-align: right;
        padding-right: 5px; 
        margin-bottom: 20px;
    }
    
    /* Branding Utama di Tengah - Putih dengan hint Navy */
    .brand-main {
        font-family: 'Nunito', sans-serif;
        background: linear-gradient(135deg, #ffffff 50%, #87CEEB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        letter-spacing: -1.5px;
    }
    
    /* Tombol Utama */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #333;
        background-color: #1e1e1e;
        color: white;
        transition: all 0.2s;
        text-align: left;
    }
    .stButton>button:hover { background-color: #333; border-color: #4A90E2; }
    
    /* Mengubah Glow Merah menjadi Navy pada Kolom Chat */
    .stChatInput div[data-baseweb="input"]:focus-within, 
    .stChatInput div[data-baseweb="textarea"] > div:focus-within {
        border-color: #1e3a8a !important;
        box-shadow: 0 0 10px 1px rgba(30, 58, 138, 0.7) !important;
    }
    
    /* Trik CSS: Memaksa Popover Ikon + masuk ke dalam kolom Chat Input */
    [data-testid="stPopover"] {
        position: fixed !important;
        bottom: 31px; /* Jarak dari bawah layar */
        left: 50%;
        transform: translateX(-340px); /* Geser ke ujung kiri dalam kolom input */
        z-index: 1000;
    }
    
    /* Desain ikon + agar menyatu tanpa background tebal */
    [data-testid="stPopover"] button {
        border: none;
        background: transparent !important;
        padding: 5px !important;
        color: #a3a3a3;
        font-size: 1.2rem;
    }
    [data-testid="stPopover"] button:hover { color: #ffffff; }
    
    /* Memberi jarak ketikan teks agar tidak tertimpa ikon + */
    div[data-testid="stChatInput"] textarea {
        padding-left: 45px !important;
    }
    
    /* Responsif ikon + di layar HP */
    @media (max-width: 768px) {
        [data-testid="stPopover"] {
            transform: translateX(-42vw);
            bottom: 25px;
        }
    }
    
    /* Action Bar (Copy, Redo, dll) */
    .action-btn button {
        font-size: 0.8rem;
        padding: 2px 8px;
        background-color: transparent;
        border: none;
        color: #888;
    }
    .action-btn button:hover { color: #4A90E2; background-color: #1e1e1e; }
    </style>
""", unsafe_allow_html=True)

api_key = st.secrets["GEMINI_API_KEY"]

# 3. Inisialisasi Firebase
if not firebase_admin._apps:
    firebase_secrets = st.secrets["firebase"]["firebase_json"]
    cred_dict = json.loads(firebase_secrets)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()
collection_name = "dimax_history"

def get_all_sessions():
    sessions = {}
    docs = db.collection(collection_name).order_by("updated_at", direction=firestore.Query.DESCENDING).stream()
    for doc in docs:
        sessions[doc.id] = doc.to_dict()
    return sessions

def create_new_session():
    new_id = str(uuid.uuid4())
    new_data = {
        "title": "Obrolan Baru", 
        "messages": [], 
        "updated_at": datetime.datetime.now().isoformat(),
        "is_pinned": False
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

chat_sessions = get_all_sessions()

if "current_session_id" not in st.session_state:
    if len(chat_sessions) > 0:
        st.session_state.current_session_id = list(chat_sessions.keys())[0]
    else:
        st.session_state.current_session_id = create_new_session()
        chat_sessions = get_all_sessions() 

if st.session_state.current_session_id not in chat_sessions:
    if len(chat_sessions) > 0:
        st.session_state.current_session_id = list(chat_sessions.keys())[0]
    else:
        st.session_state.current_session_id = create_new_session()
        chat_sessions = get_all_sessions()

current_session_id = st.session_state.current_session_id
current_data = chat_sessions[current_session_id]
current_messages = current_data.get("messages", [])

# 4. Sidebar 
with st.sidebar:
    st.markdown('<div class="brand-sidebar">🚀 DIMA-X</div>', unsafe_allow_html=True)
    
    if st.button("➕ Obrolan Baru", use_container_width=True):
        st.session_state.current_session_id = create_new_session()
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("RIWAYAT OBROLAN")
    
    for s_id, s_data in chat_sessions.items():
        col_title, col_menu = st.columns([8, 2])
        with col_title:
            if st.button(f"💬 {s_data['title']}", key=f"btn_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                st.rerun()
        with col_menu:
            with st.popover("⋮"):
                st.caption("Opsi Obrolan")
                if st.button("📌 Pin", key=f"pin_{s_id}", use_container_width=True):
                    st.toast("Fitur Pin segera hadir!", icon="📌")
                if st.button("✏️ Rename", key=f"ren_{s_id}", use_container_width=True):
                    st.toast("Ketik prompt baru untuk otomatis ganti judul.", icon="✏️")
                st.download_button("⬇️ Download PDF", data="Ekspor PDF", file_name=f"{s_data['title']}.pdf", key=f"dl_{s_id}", use_container_width=True)
                if st.button("📓 Add to Notebook", key=f"note_{s_id}", use_container_width=True):
                    st.toast("Disimpan ke Notebook", icon="📓")
                if st.button("🗑️ Delete", key=f"del_{s_id}", use_container_width=True):
                    delete_session(s_id)
                    st.rerun()
                
    st.divider()
    st.caption("WORKSPACE & SETTINGS")
    mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])

# 5. Logika Memori 
base_memory = "Kamu adalah DIMA-X, asisten AI pribadi cerdas. Jawab dengan gaya natural, bersahabat, profesional, dan langsung ke inti. Jangan menyebut nama spesifik pengguna kecuali pengguna memperkenalkan dirinya."
if "STUDY-X" in mode_dima:
    system_instruction = f"Mode STUDY-X. {base_memory} Fokus membantu pembelajaran dan merangkum modul edukasi."
elif "WORK-X" in mode_dima:
    system_instruction = f"Mode WORK-X. {base_memory} Fokus menyusun laporan, administrasi, dan surat resmi."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Mode WRITE-X. {base_memory} Fokus pada perbaikan tata bahasa dan struktur penulisan."
else:
    system_instruction = base_memory

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

# 6. Layar Selamat Datang (Main Brand)
if len(current_messages) == 0:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div class='brand-main'>🚀 DIMA-X</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 1.1rem; margin-top: 10px;'>Halo! Apa yang bisa saya bantu hari ini?</p>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎓 Ringkas materi pembelajaran", use_container_width=True):
            current_messages.append({"role": "user", "content": "Bantu saya meringkas materi utama hari ini."})
            save_message(current_session_id, current_messages, title="Ringkasan Materi")
            st.rerun()
    with col2:
        if st.button("💼 Susun draf laporan", use_container_width=True):
            current_messages.append({"role": "user", "content": "Bantu saya menyusun kerangka laporan kerja."})
            save_message(current_session_id, current_messages, title="Laporan Kerja")
            st.rerun()

# 7. Riwayat Pesan & Action Bar
for idx, message in enumerate(current_messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        if message["role"] == "assistant":
            st.markdown('<div class="action-btn">', unsafe_allow_html=True)
            a_col1, a_col2, a_col3, a_col4 = st.columns([1.5, 1.5, 1.5, 5])
            with a_col1:
                if st.button("📋 Copy", key=f"cp_{idx}"):
                    st.toast("Teks disalin!", icon="📋")
            with a_col2:
                if st.button("🔄 Redo", key=f"rd_{idx}"):
                    current_messages = current_messages[:-1]
                    save_message(current_session_id, current_messages)
                    st.rerun()
            with a_col3:
                st.download_button("📄 Export", data=message["content"], file_name=f"DIMAX_Response_{idx}.txt", key=f"ex_{idx}")
            st.markdown('</div>', unsafe_allow_html=True)

# 8. Ikon Plus (+) Akses File (Melayang di atas input lewat CSS)
with st.popover("➕"):
    uploaded_file = st.file_uploader("Upload Files", type=['pdf', 'txt'])
    if st.button("☁️ Add from Drive", use_container_width=True):
        st.toast("Integrasi Drive segera hadir.", icon="☁️")
    if st.button("📓 Notebooks", use_container_width=True):
        st.toast("Akses Notebook terbuka.", icon="📓")

# 9. Input AI Utama
if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
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
        save_message(current_session_id, current_messages)
        st.rerun()

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
