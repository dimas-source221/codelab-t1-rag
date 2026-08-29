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

# 2. Desain CSS Custom (Pembaruan Tombol Tipis ala Gemini)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Roboto:wght@400;500&display=swap');
    
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .stApp { background-color: #000000; color: #e3e3e3; }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    [data-testid="stSidebar"] { background-color: #141414; }
    
    .brand-sidebar { font-family: 'Nunito', sans-serif; font-size: 1.8rem; font-weight: 900; text-align: left; margin-bottom: 20px; padding-left: 2px; }
    .brand-main { font-family: 'Nunito', sans-serif; font-size: 3.5rem; font-weight: 900; text-align: center; letter-spacing: -1.5px; }
    .brand-text { background: linear-gradient(135deg, #ffffff 40%, #87CEEB 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .rocket-icon { -webkit-text-fill-color: initial; }
    
    .stButton>button { border-radius: 8px; border: 1px solid #333; background-color: #1e1e1e; color: white; transition: all 0.2s; text-align: left; }
    .stButton>button:hover { background-color: #333; border-color: #4A90E2; }
    
    .stChatInput div[data-baseweb="input"]:focus-within, 
    .stChatInput div[data-baseweb="textarea"] > div:focus-within { border-color: #1e3a8a !important; box-shadow: 0 0 10px 1px rgba(30, 58, 138, 0.7) !important; }
    
    [data-testid="stPopover"] button { border: 1px solid #333; background-color: #141414; color: #a3a3a3; border-radius: 8px; }
    [data-testid="stPopover"] button:hover { color: #ffffff; border-color: #4A90E2; }
    
    /* CSS BARU: Membuat tombol Copy/Redo di bawah chat menjadi tipis ala Gemini */
    .stChatMessage [data-testid="stHorizontalBlock"] button {
        background-color: transparent !important;
        border: 1px solid transparent !important;
        color: #a3a3a3 !important;
        font-size: 13px !important;
        padding: 2px 8px !important;
        border-radius: 6px !important;
        box-shadow: none !important;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .stChatMessage [data-testid="stHorizontalBlock"] button:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
        color: #ffffff !important;
    }
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
    docs = db.collection(collection_name).stream()
    for doc in docs:
        sessions[doc.id] = doc.to_dict()
    # Urutkan: Pinned di atas, lalu berdasarkan waktu terbaru
    sorted_sessions = dict(sorted(sessions.items(), key=lambda x: (x[1].get('is_pinned', False), x[1].get('updated_at', '')), reverse=True))
    return sorted_sessions

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
    if title: update_data["title"] = title
    db.collection(collection_name).document(session_id).update(update_data)

chat_sessions = get_all_sessions()

# PEMBARUAN: Langsung buat sesi baru saat pertama kali buka web
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = create_new_session()
    chat_sessions = get_all_sessions()

current_session_id = st.session_state.current_session_id
current_data = chat_sessions.get(current_session_id, {"messages": [], "title": "Obrolan Baru"})
current_messages = current_data.get("messages", [])

# 4. Sidebar 
with st.sidebar:
    st.markdown('<div class="brand-sidebar"><span class="rocket-icon">🚀</span> <span class="brand-text">DIMA-X</span></div>', unsafe_allow_html=True)
    
    if st.button("➕ Obrolan Baru", use_container_width=True):
        st.session_state.current_session_id = create_new_session()
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("RIWAYAT OBROLAN")
    
    for s_id, s_data in chat_sessions.items():
        col_title, col_menu = st.columns([8, 2])
        pin_icon = "📌 " if s_data.get('is_pinned', False) else "💬 "
        
        with col_title:
            if st.button(f"{pin_icon}{s_data['title']}", key=f"btn_{s_id}", use_container_width=True):
                st.session_state.current_session_id = s_id
                st.rerun()
        with col_menu:
            with st.popover("⋮"):
                st.caption("Opsi Obrolan")
                # Fitur Pin Aktif
                pin_label = "Unpin" if s_data.get('is_pinned', False) else "📌 Pin"
                if st.button(pin_label, key=f"pin_{s_id}", use_container_width=True):
                    new_status = not s_data.get('is_pinned', False)
                    db.collection(collection_name).document(s_id).update({"is_pinned": new_status})
                    st.rerun()
                
                # Fitur Rename Aktif
                new_title = st.text_input("Ganti Nama", value=s_data['title'], key=f"ren_input_{s_id}")
                if st.button("💾 Simpan Nama", key=f"save_ren_{s_id}", use_container_width=True):
                    db.collection(collection_name).document(s_id).update({"title": new_title})
                    st.rerun()
                
                st.download_button("⬇️ Download PDF", data="Ekspor PDF (Fitur Text)", file_name=f"{s_data['title']}.pdf", key=f"dl_{s_id}", use_container_width=True)
                
                # Fitur Add to Notebook Aktif
                if st.button("📓 Add to Notebook", key=f"note_{s_id}", use_container_width=True):
                    db.collection("dimax_notebooks").add({"session_id": s_id, "title": s_data['title'], "content": s_data['messages']})
                    st.toast("Berhasil disimpan ke Notebook Database!", icon="📓")
                
                if st.button("🗑️ Delete", key=f"del_{s_id}", use_container_width=True):
                    delete_session(s_id)
                    st.rerun()
                
    st.divider()
    st.caption("WORKSPACE & SETTINGS")
    mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])

# 5. Logika Memori (Fase 2.2: Persiapan Ujian Brutal Level 3)
base_memory = """Kamu adalah DIMA-X, Personal AI Thinking Partner dan Asisten Pribadi khusus untuk Dimas. Dimas adalah mahasiswa Sistem Informasi dan staf administrasi di Disbudporapar Kabupaten Landak.

Prinsip Utama (Senior System Analyst & Level 3 Defense):
1. "Think deeply, but don't overbuild." Evaluasi setiap permintaan, hindari over-engineering kecuali skala sistem menuntutnya dengan bukti data.
2. INTEROGASI PREMIS (ANTI-JEBAKAN): Jangan langsung percaya pada informasi/requirement yang diberikan. Jika ada konflik logika, data palsu, atau premis yang mustahil digabungkan, BONGKAR dan tolak membuat solusi sampai konflik diklarifikasi.
3. AKURASI CONCURRENCY MUTLAK: Jika membahas sistem booking, jangan klaim `SELECT ... FOR UPDATE` aman 100% dari "Phantom Read". Wajib menyarankan proteksi di level schema database (misal: EXCLUDE CONSTRAINT di PostgreSQL).
4. ZERO ESTIMATION: Dilarang keras menebak waktu pengerjaan, biaya, atau performa tanpa spesifikasi server final.
5. Untuk analisis dokumen/data, wajib merujuk pada teks asli (no hallucination).
6. Jawab dengan gaya natural, tajam, profesional, dan langsung ke inti."""

if "STUDY-X" in mode_dima:
    system_instruction = f"Mode STUDY-X.\n\n{base_memory}\n\nFokus membantu pembelajaran, menyusun alur belajar, dan merangkum modul edukasi Sistem Informasi."
elif "WORK-X" in mode_dima:
    system_instruction = f"Mode WORK-X.\n\n{base_memory}\n\nFokus menyusun laporan, administrasi dinas, dan surat resmi."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Mode WRITE-X.\n\n{base_memory}\n\nFokus pada perbaikan tata bahasa, penyesuaian gaya penulisan, dan struktur dokumen."
else:
    system_instruction = base_memory

def get_document_text(file):
    text = ""
    if file.name.endswith('.txt'): text = file.read().decode('utf-8')
    elif file.name.endswith('.pdf'):
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            if page.extract_text(): text += page.extract_text() + "\n"
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
            st.session_state.force_run = "Bantu saya meringkas materi utama hari ini."
            st.rerun()
    with col2:
        if st.button("💼 Susun draf laporan", use_container_width=True):
            st.session_state.force_run = "Bantu saya menyusun kerangka laporan kerja."
            st.rerun()

# 7. Riwayat Pesan & Action Bar (Fitur Redo & Copy ala Gemini)
for idx, message in enumerate(current_messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # Kolom pembungkus tipis di bawah pesan
        st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
        act_cols = st.columns([1, 1, 1, 7]) 
        
        if message["role"] == "user":
            with act_cols[0]:
                if st.button("✏️ Edit", key=f"edit_{idx}"):
                    # Hapus pesan ini dan seterusnya agar user bisa ketik ulang
                    current_messages = current_messages[:idx]
                    save_message(current_session_id, current_messages)
                    st.rerun()
            with act_cols[1]:
                if st.button("↻ Redo", key=f"redo_u_{idx}"):
                    # Jalankan ulang prompt ini (hapus jawaban AI di bawahnya jika ada)
                    current_messages = current_messages[:idx+1]
                    save_message(current_session_id, current_messages)
                    st.session_state.force_run = message["content"]
                    st.rerun()
                    
        elif message["role"] == "assistant":
            with act_cols[0]:
                if st.button("📋 Copy", key=f"cp_{idx}"):
                    st.toast("Teks disalin ke clipboard!", icon="📋")
            with act_cols[1]:
                if st.button("↻ Redo", key=f"redo_a_{idx}"):
                    # Hapus jawaban AI ini, lalu tembak ulang pertanyaan terakhir user
                    current_messages = current_messages[:idx]
                    save_message(current_session_id, current_messages)
                    if len(current_messages) > 0:
                        st.session_state.force_run = current_messages[-1]["content"]
                    st.rerun()
            with act_cols[2]:
                st.download_button("⬇️ Export", data=message["content"], file_name=f"DIMAX_Response_{idx}.txt", key=f"ex_{idx}")

# 8. Menu Ekstra
st.markdown("<br>", unsafe_allow_html=True)
menu_col1, menu_col2, menu_col3 = st.columns([1, 8, 1])

with menu_col1:
    with st.popover("⋮"):
        st.caption("Opsi Tambahan")
        if st.button("⚙️ Pengaturan", use_container_width=True): st.toast("Pengaturan AI", icon="⚙️")
        if st.button("🧹 Bersihkan Konteks", use_container_width=True): st.toast("Konteks dibersihkan", icon="🧹")

with menu_col3:
    with st.popover("➕"):
        uploaded_file = st.file_uploader("Upload Files", type=['pdf', 'txt'])
        if st.button("📓 Notebooks", use_container_width=True): st.toast("Akses Notebook terbuka.", icon="📓")

# 9. Input AI Utama & Logika Eksekusi
trigger_generate = False
prompt_text = ""

if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
    prompt_text = prompt
    current_messages.append({"role": "user", "content": prompt_text})
    
    new_title = current_data["title"]
    if len(current_messages) == 1 or new_title == "Obrolan Baru":
        new_title = prompt_text[:25] + "..." if len(prompt_text) > 25 else prompt_text
    
    save_message(current_session_id, current_messages, title=new_title)
    trigger_generate = True

# Tangkap perintah Force Run dari tombol Redo
if "force_run" in st.session_state:
    prompt_text = st.session_state.force_run
    del st.session_state.force_run
    # Jika force_run dari tombol, prompt sudah ada di array current_messages (tidak perlu di-append lagi)
    trigger_generate = True

if trigger_generate:
    # Tampilkan prompt di layar (jika dari chat_input)
    if not any(msg["content"] == prompt_text for msg in current_messages[-1:]):
        with st.chat_message("user"): st.markdown(prompt_text)

    try:
        client = genai.Client(api_key=api_key)
        
        formatted_contents = []
        # Masukkan history kecuali pesan terakhir (yang akan dikirim)
        for msg in current_messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            formatted_contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        
        context = ""
        if uploaded_file:
            context = f"\n\n--- KONTEKS DOKUMEN ---\n{get_document_text(uploaded_file)}\n\nBerdasarkan dokumen di atas:\n"
        
        final_prompt_text = context + prompt_text
        formatted_contents.append({"role": "user", "parts": [{"text": final_prompt_text}]})

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
