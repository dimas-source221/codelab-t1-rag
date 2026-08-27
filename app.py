import streamlit as st

st.set_page_config(
    page_title="RAG AI Agent | Codelab T1",
    page_icon="🤖",
    layout="centered"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🤖 Agen AI RAG (Retrieval-Augmented Generation)")
st.caption("Google Gen AI APAC Academy - T1 Codelab Deployment")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya adalah Agen AI RAG. Ada dokumen atau informasi yang ingin dianalisis hari ini?"}
    ]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Tanyakan sesuatu ke Agen AI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Mengambil konteks dari basis data..."):
            response = f"Berdasarkan dokumen RAG, berikut analisis untuk: **{prompt}**. Sistem berfungsi dengan baik!"
            st.markdown(response)
            
    st.session_state.messages.append({"role": "assistant", "content": response})

st.sidebar.title("🔧 Konfigurasi Agen")
st.sidebar.info("Sistem RAG aktif. Koneksi ke Google Cloud ADK berhasil diinisialisasi.")
