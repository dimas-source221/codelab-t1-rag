import streamlit as st
import google.generativeai as genai
import PyPDF2
import os

# 1. Konfigurasi Halaman & Identitas
st.set_page_config(
    page_title="DIMA-X | Personal Agent",
    page_icon="🚀",
    layout="wide"
)

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 DIMA-X")
st.caption("Your Personal AI Work & Study Agent")
st.divider()

# 2. Sidebar - Konfigurasi & Modul DIMA-X
st.sidebar.title("🔧 Konfigurasi DIMA-X")
api_key = st.sidebar.text_input("🔑 Masukkan Gemini API Key", type="password", help="Dapatkan di Google AI Studio")

mode_dima = st.sidebar.selectbox(
    "🧠 Pilih Mode Agent (Role Mode)",
    ["🤖 AI Chat (Umum)", "🎓 STUDY-X (Mahasiswa)", "💼 WORK-X (Kantoran)", "✍️ WRITE-X (Menulis)"]
)

st.sidebar.divider()
st.sidebar.subheader("📄 DOC-X (Analisis Dokumen)")
uploaded_file = st.sidebar.file_uploader("Upload Modul / Laporan (PDF/TXT)", type=['pdf', 'txt'])

# 3. Logika Memori & System Prompt (Kepribadian AI)
# DIMA-X sudah disuntikkan memori tentang identitasmu
base_memory = "Penggunamu bernama Dimas, seorang mahasiswa Sistem Informasi dan staf administrasi di Dinas Kebudayaan, Pariwisata, Pemuda dan Olahraga (Disbudporapar) Kabupaten Landak."

if "STUDY-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode STUDY-X. {base_memory} Tugasmu membantu Dimas belajar perkuliahan, merangkum modul Sistem Informasi, membuat contoh soal, dan menjelaskan konsep IT dengan bahasa yang mudah dipahami."
elif "WORK-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode WORK-X. {base_memory} Tugasmu membantu Dimas mengurus pekerjaan administratif dinas pemerintahan, menyusun laporan kegiatan, surat resmi, dan notulen dengan bahasa profesional pemerintahan."
elif "WRITE-X" in mode_dima:
    system_instruction = f"Kamu adalah DIMA-X mode WRITE-X. {base_memory} Tugasmu menjadi asisten penulis. Perbaiki tata bahasa, buat outline, dan sesuaikan nada tulisan Dimas menjadi lebih terstruktur baik untuk keperluan kampus maupun dinas."
else:
    system_instruction = f"Kamu adalah DIMA-X, asisten AI pribadi yang cerdas, cepat, dan proaktif. {base_memory} Berikan jawaban yang relevan dan praktis."

# 4. Fungsi Membaca Dokumen (DOC-X)
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

# 5. Inisialisasi Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": f"Halo Dimas! **DIMA-X** siap membantu. Saat ini saya berada di mode **{mode_dima}**. Ada modul kuliah atau tugas dinas yang ingin diselesaikan hari ini?"}
    ]

# Hapus history jika ganti mode agar AI fokus pada peran barunya
if "current_mode" not in st.session_state or st.session_state.current_mode != mode_dima:
    st.session_state.current_mode = mode_dima
    st.session_state.messages = [
        {"role": "assistant", "content": f"Mode diubah ke **{mode_dima}**. DIMA-X siap menerima perintah!"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 6. Logika Utama Agen AI
if prompt := st.chat_input("Berikan perintah ke DIMA-X..."):
    if not api_key:
        st.warning("⚠️ DIMA-X belum aktif. Masukkan Gemini API Key di sidebar sebelah kiri!")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        # Menghubungkan ke Gemini API
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction
        )

        # Proses DOC-X: Sisipkan teks dokumen ke dalam ingatan Gemini jika ada file yang diupload
        context = ""
        if uploaded_file:
            doc_text = get_document_text(uploaded_file)
            context = f"\n\n--- KONTEKS DOKUMEN YANG DIUNGGAH ---\n{doc_text}\n\nBerdasarkan dokumen di atas, tolong penuhi perintah berikut:\n"

        final_prompt = context + prompt

        with st.chat_message("assistant"):
            with st.spinner(f"DIMA-X sedang menganalisis ({mode_dima})..."):
                response = model.generate_content(final_prompt)
                st.markdown(response.text)
        
        st.session_state.messages.append({"role": "assistant", "content": response.text})

    except Exception as e:
        st.error(f"Terjadi kesalahan sistem: {e}")
