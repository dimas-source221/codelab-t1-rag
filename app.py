import streamlit as st
from google import genai
from google.genai import types
import PyPDF2

# 1. Konfigurasi Halaman
st.set_page_config(page_title="DIMA-X | Personal Agent", page_icon="🚀", layout="wide")

# Custom CSS untuk mendekati desain gambar (Dark Dashboard)
st.markdown("""
    <style>
    /* Tema Dasar */
    .stApp { background-color: #0b0f19; color: #ffffff; }
    
    /* Banner Header */
    .main-banner {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
        padding: 2.5rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        border: 1px solid #334155;
    }
    
    /* Kartu Quick Actions */
    .stButton>button {
        width: 100%;
        height: 65px;
        background-color: #1e293b;
        color: #f8fafc;
        border: 1px solid #334155;
        border-radius: 10px;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background-color: #3b82f6;
        border-color: #60a5fa;
    }
    </style>
""", unsafe_allow_html=True)

# 2. Sidebar - Navigasi ala Dashboard
with st.sidebar:
    st.markdown("### 🚀 DIMA-X")
    st.caption("Personal AI Work & Study Agent")
    
    api_key = st.text_input("🔑 API Key Gemini", type="password")
    
    st.divider()
    st.markdown("#### WORKSPACE")
    mode_dima = st.radio(
        "Mode Agent Aktif:",
        ["🤖 AI Chat (Umum)", "🎓 STUDY-X (Mahasiswa)", "💼 WORK-X (Kantoran)", "✍️ WRITE-X (Menulis)"]
    )
    
    st.divider()
    st.markdown("#### 📄 DOC-X")
    uploaded_file = st.file_uploader("Upload PDF/TXT", type=['pdf', 'txt'])
    
    st.divider()
    st.markdown("👨‍💼 **Dimas**\n\n*Sistem Informasi & Profesional*")

# 3. Main Area - Banner
st.markdown("""
<div class="main-banner">
    <h2 style="margin-top:0;">🚀 DIMA-X</h2>
    <h1 style="font-size: 2.5rem; font-weight: bold;">Good morning, Dimas! 👋</h1>
    <p style="font-size: 1.1rem;">What would you like to accomplish today?</p>
    <p style="color: #94a3b8; font-size: 0.95rem;">DIMA-X siap membantu kamu dalam belajar, bekerja, coding, menulis, research, dan produktivitas sehari-hari.</p>
</div>
""", unsafe_allow_html=True)

# 4. Quick Actions Grid
st.markdown("### ⚡ Quick Actions")
st.caption("Pilih salah satu pintasan untuk memulai")
col1, col2, col3 = st.columns(3)
with col1:
    st.button("🎓 Study Assistant")
    st.button("📄 Summarize Document")
with col2:
    st.button("💼 Work Assistant")
    st.button("✍️ Write an Email")
with col3:
    st.button("</> Coding Assistant")
    st.button("🔍 Research Topic")

st.divider()

# 5. Logika AI 
base_memory = "Penggunamu bernama Dimas, seorang mahasiswa Sistem Informasi dan staf administrasi di Dinas Kebudayaan, Pariwisata, Pemuda dan Olahraga (Disbudporapar) Kabupaten Landak."

if "STUDY-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode STUDY-X. {base_memory} Tugasmu membantu Dimas belajar perkuliahan, merangkum modul Sistem Informasi, membuat contoh soal, dan menjelaskan konsep IT."
elif "WORK-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode WORK-X. {base_memory} Tugasmu membantu Dimas mengurus pekerjaan administratif dinas pemerintahan, menyusun laporan kegiatan, surat resmi, dan notulen."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode WRITE-X. {base_memory} Tugasmu menjadi asisten penulis. Perbaiki tata bahasa, buat outline, dan sesuaikan nada tulisan Dimas."
else:
    system_instruction = f"Kamu adalah DIMA-X. {base_memory} Berikan jawaban yang relevan dan praktis."

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

# Inisialisasi Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": f"🤖 **Your AI workspace is ready.** Ask DIMA-X anything."}]

if "current_mode" not in st.session_state or st.session_state.current_mode != mode_dima:
    st.session_state.current_mode = mode_dima
    st.session_state.messages = [{"role": "assistant", "content": f"Mode diubah ke **{mode_dima}**. DIMA-X siap!"}]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input dan Pemrosesan
if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
    if not api_key:
        st.warning("⚠️ DIMA-X belum aktif. Masukkan API Key di sidebar!")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        client = genai.Client(api_key=api_key)
        context = ""
        if uploaded_file:
            context = f"\n\n--- KONTEKS DOKUMEN ---\n{get_document_text(uploaded_file)}\n\nBerdasarkan dokumen di atas, penuhi perintah berikut:\n"

        final_prompt = context + prompt

        with st.chat_message("assistant"):
            with st.spinner(f"DIMA-X memproses ({mode_dima})..."):
                response = client.models.generate_content(
                    model='gemini-3.6-flash',  # <-- PASTIKAN HANYA ADA SATU KATA 'model='
                    contents=final_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                    )
                )
                st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Terjadi kesalahan: {e}")
