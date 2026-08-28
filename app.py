import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
import uuid  # Library tambahan untuk membuat ID unik tiap obrolan

# 1. Konfigurasi Halaman 
st.set_page_config(page_title="DIMA-X | AI Agent", page_icon="🚀", layout="centered")

# Custom CSS ala ChatGPT
st.markdown("""
    <style>
    .stApp { background-color: #212121; color: #ececec; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Tombol Utama */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #424242;
        background-color: #2f2f2f;
        color: white;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        background-color: #424242;
        border-color: #565656;
    }
    </style>
""", unsafe_allow_html=True)

# Ambil API Key dari Streamlit Secrets
api_key = st.secrets["GEMINI_API_KEY"]

# 2. Inisialisasi Sistem Multi-Sesi Obrolan
if "chat_sessions" not in st.session_state:
    st.session_state.chat_sessions = {}
if "current_session_id" not in st.session_state:
    new_id = str(uuid.uuid4())
    st.session_state.current_session_id = new_id
    st.session_state.chat_sessions[new_id] = {"title": "Obrolan Baru", "messages": []}

def switch_session(session_id):
    st.session_state.current_session_id = session_id

def delete_session(session_id):
    del st.session_state.chat_sessions[session_id]
    # Jika semua dihapus, buat sesi kosong baru
    if len(st.session_state.chat_sessions) == 0:
        new_session_id = str(uuid.uuid4())
        st.session_state.chat_sessions[new_session_id] = {"title": "Obrolan Baru", "messages": []}
        st.session_state.current_session_id = new_session_id
    # Jika sesi yang aktif dihapus, pindah ke sesi pertama yang tersisa
    elif st.session_state.current_session_id == session_id:
        st.session_state.current_session_id = list(st.session_state.chat_sessions.keys())[0]

# 3. Sidebar - Navigasi Riwayat Asli
with st.sidebar:
    if st.button("➕ Obrolan Baru", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.chat_sessions[new_id] = {"title": "Obrolan Baru", "messages": []}
        st.session_state.current_session_id = new_id
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("RIWAYAT OBROLAN")
    
    # Menampilkan daftar obrolan yang aktif
    for s_id, session_data in reversed(list(st.session_state.chat_sessions.items())):
        col1, col2 = st.columns([8, 2])
        with col1:
            if st.button(f"💬 {session_data['title']}", key=f"btn_{s_id}", use_container_width=True):
                switch_session(s_id)
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{s_id}"):
                delete_session(s_id)
                st.rerun()
                
    st.divider()
    
    st.caption("WORKSPACE")
    mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])
    uploaded_file = st.file_uploader("📄 Upload Dokumen", type=['pdf', 'txt'])

# 4. Logika Memori Asisten Pribadi (Dimas)
base_memory = "Penggunamu bernama Dimas, seorang mahasiswa Sistem Informasi Universitas Terbuka dan staf administrasi di Disbudporapar Kabupaten Landak."
if "STUDY-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode STUDY-X. {base_memory} Bantu Dimas belajar perkuliahan, merangkum modul Sistem Informasi, dan menjelaskan konsep IT secara ringkas."
elif "WORK-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode WORK-X. {base_memory} Bantu Dimas mengurus pekerjaan administratif dinas, laporan, dan surat resmi pemerintahan."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode WRITE-X. {base_memory} Perbaiki tata bahasa dan buat tulisan Dimas menjadi lebih terstruktur dan profesional."
else:
    system_instruction = f"Kamu adalah DIMA-X, asisten AI pribadi yang cerdas. {base_memory} Berikan jawaban yang natural, praktis, dan langsung ke inti."

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

# Mengambil data obrolan pada sesi yang sedang aktif
current_messages = st.session_state.chat_sessions[st.session_state.current_session_id]["messages"]

# 5. Layar Selamat Datang (Jika obrolan masih kosong)
if len(current_messages) == 0:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white; font-size: 2.5rem;'>🚀 DIMA-X</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 1.1rem;'>Apa yang bisa saya bantu hari ini, Mas Dimas?</p>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎓 Ringkas materi kuliah", use_container_width=True):
            current_messages.append({"role": "user", "content": "Bantu saya meringkas materi kuliah Sistem Informasi hari ini."})
            st.session_state.chat_sessions[st.session_state.current_session_id]["title"] = "Ringkasan Materi"
            st.rerun()
    with col2:
        if st.button("💼 Buat laporan dinas", use_container_width=True):
            current_messages.append({"role": "user", "content": "Bantu saya menyusun kerangka laporan kegiatan Disbudporapar."})
            st.session_state.chat_sessions[st.session_state.current_session_id]["title"] = "Laporan Dinas"
            st.rerun()

# 6. Menampilkan Riwayat Pesan
for message in current_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 7. Input dan Pemrosesan AI
if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
    # Ganti judul sesi secara otomatis berdasarkan pesan pertama
    if len(current_messages) == 0:
        new_title = prompt[:20] + "..." if len(prompt) > 20 else prompt
        st.session_state.chat_sessions[st.session_state.current_session_id]["title"] = new_title

    current_messages.append({"role": "user", "content": prompt})
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
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    )
                )
                st.markdown(response.text)
        
        current_messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
