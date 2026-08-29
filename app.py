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

# 2. Desain CSS Custom
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Roboto:wght@400;500&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Roboto', sans-serif;
    }
    .stApp { background-color: #000000; color: #e3e3e3; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stSidebar"] { background-color: #141414; }
    
    /* Branding Sidebar - Rata Kiri & Sejajar dengan Tombol */
    .brand-sidebar {
        font-family: 'Nunito', sans-serif;
        font-size: 1.8rem;
        font-weight: 900;
        text-align: left;
        margin-bottom: 20px;
        padding-left: 2px;
    }
    
    /* Branding Utama di Tengah */
    .brand-main {
        font-family: 'Nunito', sans-serif;
        font-size: 3.5rem;
        font-weight: 900;
        text-align: center;
        letter-spacing: -1.5px;
    }
    
    /* Gradasi Teks Putih ke Biru Muda (Navy/Cyan) */
    .brand-text {
        background: linear-gradient(135deg, #ffffff 40%, #87CEEB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Memastikan emoji roket tidak kehilangan warnanya */
    .rocket-icon {
        -webkit-text-fill-color: initial;
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
    
    /* Navy Glow saat Kolom Chat Diklik */
    .stChatInput div[data-baseweb="input"]:focus-within, 
    .stChatInput div[data-baseweb="textarea"] > div:focus-within {
        border-color: #1e3a8a !important;
        box-shadow: 0 0 10px 1px rgba(30, 58, 138, 0.7) !important;
    }
    
    /* Tombol Popover (+ dan Titik 3) agar tidak memiliki background tebal */
    [data-testid="stPopover"] button {
        border: 1px solid #333;
        background-color: #141414;
        color: #a3a3a3;
        border-radius: 8px;
    }
    [data-testid="stPopover"] button:hover { 
        color: #ffffff; 
        border-color: #4A90E2; 
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
    # Branding Sidebar
    st.markdown('<div class="brand-sidebar"><span class="rocket-icon">🚀</span> <span class="brand-text">DIMA-X</span></div>', unsafe_allow_html=True)
    
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

# 5. Logika Memori (Fase 2.1: Context Engine, System Analyst Mindset & Anti-Overconfidence)
base_memory = """Kamu adalah DIMA-X, Personal AI Thinking Partner dan Asisten Pribadi khusus untuk Dimas. Dimas adalah mahasiswa Sistem Informasi dan staf administrasi di Disbudporapar Kabupaten Landak.

Prinsip Utama (System Analyst Mindset):
1. "Think deeply, but don't overbuild." 
2. Evaluasi setiap permintaan. Jika requirement sederhana, berikan solusi yang efisien, ringkas, dan to-the-point.
3. Dilarang keras over-engineering. Jangan sarankan arsitektur kompleks, microservices, atau framework berat kecuali Dimas memintanya.
4. Berani bilang "tidak perlu" jika sebuah teknologi berlebihan.
5. ANTI-HALUSINASI METRIK & KLAIM ABSOLUT: Dilarang keras mengarang estimasi waktu pengerjaan (misal: "selesai 1-3 hari") atau metrik performa (misal: "<2ms") tanpa data benchmark yang diuji. Jika data tidak ada, katakan "Belum dapat dipastikan".
6. AKURASI TEKNIS TINGKAT TINGGI: Jangan pernah mengklaim kode atau sistem "100% aman" dari bug atau race condition. Jelaskan trade-off atau syarat teknisnya (misalnya perlunya Isolation Level, Row Locking, atau Constraint di database).
7. KRITIS PADA LOGIKA BISNIS: Jangan berasumsi pada alur kerja krusial yang tidak disebutkan. Tanyakan edge-cases (misal: apakah status 'pending' sudah memblokir jadwal/ruangan?).
8. Untuk analisis dokumen/data, wajib merujuk pada teks asli (no hallucination).
9. Jawab dengan gaya natural, bersahabat, profesional, dan langsung ke inti."""

if "STUDY-X" in mode_dima:
    system_instruction = f"Mode STUDY-X.\n\n{base_memory}\n\nFokus membantu pembelajaran, menyusun alur belajar, dan merangkum modul edukasi Sistem Informasi."
elif "WORK-X" in mode_dima:
    system_instruction = f"Mode WORK-X.\n\n{base_memory}\n\nFokus menyusun laporan, administrasi dinas, dan surat resmi."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Mode WRITE-X.\n\n{base_memory}\n\nFokus pada perbaikan tata bahasa, penyesuaian gaya penulisan (formal/akademik/kasual), dan struktur dokumen."
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

# 6. Layar Selamat Datang
if len(current_messages) == 0:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div class='brand-main'><span class='rocket-icon'>🚀</span> <span class='brand-text'>DIMA-X</span></div>", unsafe_allow_html=True)
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

# 8. Menu Ekstra
st.markdown("<br>", unsafe_allow_html=True)
menu_col1, menu_col2, menu_col3 = st.columns([1, 8, 1])

with menu_col1:
    with st.popover("⋮"):
        st.caption("Opsi Tambahan")
        if st.button("⚙️ Pengaturan", use_container_width=True):
            st.toast("Pengaturan AI", icon="⚙️")
        if st.button("🧹 Bersihkan Konteks", use_container_width=True):
            st.toast("Konteks dibersihkan", icon="🧹")

with menu_col3:
    with st.popover("➕"):
        uploaded_file = st.file_uploader("Upload Files", type=['pdf', 'txt'])
        if st.button("☁️ Add from Drive", use_container_width=True):
            st.toast("Integrasi Drive segera hadir.", icon="☁️")
        if st.button("📓 Notebooks", use_container_width=True):
            st.toast("Akses Notebook terbuka.", icon="📓")

# 9. Input AI Utama & Eksekusi Context Engine
if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
    new_title = current_data["title"]
    if len(current_messages) == 0:
        new_title = prompt[:25] + "..." if len(prompt) > 25 else prompt

    # Simpan pesan user ke list
    current_messages.append({"role": "user", "content": prompt})
    save_message(current_session_id, current_messages, title=new_title)
    
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        client = genai.Client(api_key=api_key)
        
        # Susun riwayat percakapan untuk Context Engine (Format dictionary baru)
        formatted_contents = []
        for msg in current_messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_contents.append({
                "role": role, 
                "parts": [{"text": msg["content"]}]
            })
        
        # Siapkan teks untuk pesan terakhir (gabung dengan dokumen jika ada)
        context = ""
        if uploaded_file:
            context = f"\n\n--- KONTEKS DOKUMEN ---\n{get_document_text(uploaded_file)}\n\nBerdasarkan dokumen di atas:\n"
        
        final_prompt_text = context + prompt
        formatted_contents.append({
            "role": "user", 
            "parts": [{"text": final_prompt_text}]
        })

        with st.chat_message("assistant"):
            with st.spinner("DIMA-X sedang memproses..."):
                response = client.models.generate_content(
                    model='gemini-3.6-flash', 
                    contents=formatted_contents, 
                    config=types.GenerateContentConfig(system_instruction=system_instruction)
                )
                st.markdown(response.text)
        
        current_messages.append({"role": "assistant", "content": response.text})
        save_message(current_session_id, current_messages)
        st.rerun()

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
