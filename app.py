import streamlit as st
from google import genai
from google.genai import types
import PyPDF2

# 1. Konfigurasi Halaman (Lebih Clean & Terpusat)
st.set_page_config(page_title="DIMA-X | AI Agent", page_icon="🚀", layout="centered")

# Custom CSS ala ChatGPT Dark Mode
st.markdown("""
    <style>
    /* Warna background solid dark abu-abu tua ala ChatGPT */
    .stApp { background-color: #212121; color: #ececec; }
    
    /* Menyembunyikan elemen bawaan Streamlit (footer) */
    /* Header dibiarkan agar tombol sidebar kiri tetap bisa diklik */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Mempercantik tombol Obrolan Baru */
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

# Ambil API Key dari brankas rahasia
api_key = st.secrets["GEMINI_API_KEY"]

# Inisialisasi Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Sidebar - Navigasi ala ChatGPT
with st.sidebar:
    # Tombol Reset Obrolan
    if st.button("➕ Obrolan Baru", use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Desain UI Riwayat (Tampilan Visual)
    st.caption("Hari Ini")
    st.markdown("💬 Diskusi Sistem Informasi")
    st.markdown("💬 Laporan Pekerjaan")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("Kemarin")
    st.markdown("💬 Belajar Python Dasar")
    st.markdown("💬 Rencana UI/UX Aplikasi")
    
    st.divider()
    
    # Menu Mode & Upload dipindah ke bawah agar rapi
    st.caption("WORKSPACE")
    mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])
    uploaded_file = st.file_uploader("📄 Upload Dokumen", type=['pdf', 'txt'])

# 3. Logika Memori Umum (Netral)
base_memory = "Kamu adalah DIMA-X, asisten AI yang cerdas dan profesional. Tugasmu membantu pengguna dengan cepat dan akurat. Gunakan bahasa yang natural dan bersahabat. Jangan menebak nama pengguna, sapa secara umum kecuali pengguna telah memperkenalkan namanya."

if "STUDY-X" in mode_dima:
    system_instruction = f"Mode STUDY-X. {base_memory} Fokusmu membantu pengguna belajar, merangkum materi kampus, dan menjelaskan konsep edukasi."
elif "WORK-X" in mode_dima:
    system_instruction = f"Mode WORK-X. {base_memory} Fokusmu membantu pengguna mengurus pekerjaan profesional, menyusun laporan, dan surat resmi."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Mode WRITE-X. {base_memory} Fokusmu memperbaiki tata bahasa dan merapikan tulisan pengguna."
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

# 4. Layar Selamat Datang (Tanpa Nama Spesifik)
if len(st.session_state.messages) == 0:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; color: white; font-size: 2.5rem;'>🚀 DIMA-X</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 1.1rem;'>Apa yang bisa saya bantu hari ini?</p>", unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Pintasan Cepat di tengah layar
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🎓 Ringkas materi", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Bantu saya meringkas materi atau dokumen hari ini."})
            st.rerun()
    with col2:
        if st.button("💼 Buat laporan kerja", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "Bantu saya menyusun kerangka laporan pekerjaan."})
            st.rerun()

# 5. Menampilkan Riwayat Pesan di Layar
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Input dan Pemrosesan AI
if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
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
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
