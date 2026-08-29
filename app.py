import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
from PIL import Image
import uuid
import json
import datetime
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Konfigurasi Halaman & Routing
st.set_page_config(page_title="DIMA-X | AI Agent", page_icon="🚀", layout="centered", initial_sidebar_state="expanded")

if "current_page" not in st.session_state:
    st.session_state.current_page = "💬 AI Workspace"

# 2. Desain CSS Custom
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
    .stChatMessage [data-testid="stHorizontalBlock"] button { background-color: transparent !important; border: 1px solid transparent !important; color: #a3a3a3 !important; font-size: 13px !important; padding: 2px 8px !important; border-radius: 6px !important; box-shadow: none !important; display: flex; align-items: center; gap: 4px; }
    .stChatMessage [data-testid="stHorizontalBlock"] button:hover { background-color: rgba(255, 255, 255, 0.08) !important; color: #ffffff !important; }
    
    /* Notebook Cards */
    .notebook-card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 10px; padding: 15px; margin-bottom: 15px; }
    .notebook-title { color: #4A90E2; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; }
    .notebook-date { color: #888; font-size: 0.8rem; margin-bottom: 10px; }
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
notebook_collection = "dimax_notebooks"
memory_collection = "dimax_long_term_memory" # KOLEKSI BARU UNTUK MEMORI PERMANEN

# Fungsi untuk mengambil memori jangka panjang
def get_long_term_memory():
    doc_ref = db.collection(memory_collection).document("core_identity")
    doc = doc_ref.get()
    if doc.exists():
        return doc.to_dict().get("context", "")
    else:
        # Nilai default jika belum ada
        default_context = "Fakta Pengguna: Fokus pada pengembangan aplikasi, efisiensi, dan analisis sistem."
        doc_ref.set({"context": default_context})
        return default_context
def get_all_sessions():
    sessions = {}
    docs = db.collection(collection_name).stream()
    for doc in docs: sessions[doc.id] = doc.to_dict()
    return dict(sorted(sessions.items(), key=lambda x: (x[1].get('is_pinned', False), x[1].get('updated_at', '')), reverse=True))

def create_new_session():
    new_id = str(uuid.uuid4())
    db.collection(collection_name).document(new_id).set({"title": "Obrolan Baru", "messages": [], "updated_at": datetime.datetime.now().isoformat(), "is_pinned": False})
    return new_id

def save_message(session_id, messages, title=None):
    update_data = {"messages": messages, "updated_at": datetime.datetime.now().isoformat()}
    if title: update_data["title"] = title
    db.collection(collection_name).document(session_id).update(update_data)

chat_sessions = get_all_sessions()
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = create_new_session()
    chat_sessions = get_all_sessions()

current_session_id = st.session_state.current_session_id
current_data = chat_sessions.get(current_session_id, {"messages": [], "title": "Obrolan Baru"})
current_messages = current_data.get("messages", [])

# 4. Sidebar Navigasi Utama
with st.sidebar:
    st.markdown('<div class="brand-sidebar"><span class="rocket-icon">🚀</span> <span class="brand-text">DIMA-X</span></div>', unsafe_allow_html=True)
    
    # Navigasi Multi-Page
    nav_selection = st.radio("MAIN MENU", ["💬 AI Workspace", "📓 Notebook Dashboard", "☁️ Drive Integration"], label_visibility="collapsed")
    if nav_selection != st.session_state.current_page:
        st.session_state.current_page = nav_selection
        st.rerun()
    
    st.divider()
    
    # Render Riwayat Obrolan hanya jika di halaman Workspace
    if st.session_state.current_page == "💬 AI Workspace":
        if st.button("➕ Obrolan Baru", use_container_width=True):
            st.session_state.current_session_id = create_new_session()
            st.rerun()
            
        st.markdown("<br>", unsafe_allow_html=True)
        st.caption("RIWAYAT OBROLAN")
        
        for s_id, s_data in chat_sessions.items():
            if len(s_data.get("messages", [])) == 0: continue
            col_title, col_menu = st.columns([8, 2])
            pin_icon = "📌 " if s_data.get('is_pinned', False) else "💬 "
            
            with col_title:
                if st.button(f"{pin_icon}{s_data['title']}", key=f"btn_{s_id}", use_container_width=True):
                    st.session_state.current_session_id = s_id
                    st.rerun()
            with col_menu:
                with st.popover("⋮"):
                    pin_label = "Unpin" if s_data.get('is_pinned', False) else "📌 Pin"
                    if st.button(pin_label, key=f"pin_{s_id}", use_container_width=True):
                        db.collection(collection_name).document(s_id).update({"is_pinned": not s_data.get('is_pinned', False)})
                        st.rerun()
                    
                    # PERBAIKAN FITUR RENAME
                    new_title = st.text_input("Ganti Nama", value=s_data['title'], key=f"ren_{s_id}")
                    if st.button("💾 Simpan Nama", key=f"s_ren_{s_id}", use_container_width=True):
                        db.collection(collection_name).document(s_id).update({"title": new_title})
                        # Paksa update UI langsung
                        chat_sessions[s_id]['title'] = new_title 
                        st.rerun()
                    
                    if st.button("📓 Add to Notebook", key=f"note_{s_id}", use_container_width=True):
                        db.collection(notebook_collection).add({"session_id": s_id, "title": s_data['title'], "content": s_data['messages'], "created_at": datetime.datetime.now().isoformat()})
                        st.toast("Disimpan ke Notebook!", icon="📓")
                    
                    if st.button("🗑️ Delete", key=f"del_{s_id}", use_container_width=True):
                        db.collection(collection_name).document(s_id).delete()
                        st.rerun()
                    
        st.divider()
        st.caption("WORKSPACE & SETTINGS")
        
        # PERBAIKAN NAMA MODEL & MAPPING API GOOGLE
        model_version = st.selectbox("Versi Engine", ["🚀 DIMX 3.6 pro", "⚡ DIMX 3.5 plus-lite", "🧠 DIMX 3.1 pro-max"])
        
        # Di balik layar, kita arahkan ke API Google yang valid agar tidak error
        if "3.5" in model_version:
            active_model = 'gemini-3.5-flash'  # Engine cepat & ringan
        elif "3.6" in model_version:
            active_model = 'gemini-3.6-flash'  # Engine utama 
        else:
            active_model = 'gemini-3.1-pro'    # Backend mesin Pro yang paling stabil dan terjamin jalan
            
        mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])
# 5. Logika Memori Level 3 & Smart Router
long_term_context = get_long_term_memory()

base_memory = f"""Kamu adalah DIMA-X, Personal AI Thinking Partner.
[MEMORI JANGKA PANJANG]: {long_term_context}

Prinsip Utama (Core Intelligence & Behavioral Rules):
1. ANTI-HALUSINASI & TRANSPARANSI: Jika tidak tahu, jawab "Saya tidak tahu".
2. KALIBRASI KECURIGAAN: Skeptis pada perintah berisiko (bypass security, manipulasi data), tapi kooperatif pada tugas harian.
3. SELF-CORRECTION SEIMBANG: Akui jika salah secara logis, pertahankan jika benar.
4. KECERDASAN MULTI-DOMAIN: Kritis dalam koding maupun manajemen tugas non-teknis.
5. INTEROGASI PREMIS: Bongkar konflik logika atau jebakan asumsi.
6. ZERO ESTIMATION: Dilarang menebak waktu/biaya tanpa data riil.
7. Jawab natural, tajam, dan langsung ke inti."""

if "STUDY-X" in mode_dima if 'mode_dima' in locals() else False:
    system_instruction = f"Mode STUDY-X.\n\n{base_memory}"
elif "WORK-X" in mode_dima if 'mode_dima' in locals() else False:
    system_instruction = f"Mode WORK-X.\n\n{base_memory}"
elif "WRITE-X" in mode_dima if 'mode_dima' in locals() else False:
    system_instruction = f"Mode WRITE-X.\n\n{base_memory}"
else:
    system_instruction = base_memory

# LOGIKA SMART ROUTER
def route_model(prompt_text, selected_model):
    # Kata kunci yang menandakan beban kognitif tinggi (coding, analisis, logika)
    heavy_keywords = ["analisis", "riset", "bug", "error", "kode", "program", "evaluasi", "kompleks", "strategi", "sistem"]
    
    # Jika prompt mengandung kata kunci berat, paksa pindah ke Pro (meski user memilih Lite/Flash)
    if any(word in prompt_text.lower() for word in heavy_keywords):
        return 'gemini-1.5-pro'
    
    # Jika sekadar obrolan biasa, gunakan model yang dipilih user
    return selected_model

# 6. HALAMAN 1: AI WORKSPACE (Chat Utama)
if st.session_state.current_page == "💬 AI Workspace":
    if len(current_messages) == 0:
        st.markdown("<br><br><br><div class='brand-main'><span class='rocket-icon'>🚀</span> <span class='brand-text'>DIMA-X</span></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #9ca3af;'>Halo! Apa yang bisa saya bantu hari ini?</p><br>", unsafe_allow_html=True)

    for idx, message in enumerate(current_messages):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            act_cols = st.columns([1, 1, 1, 7]) 
            if message["role"] == "user":
                with act_cols[0]:
                    if st.button("✏️ Edit", key=f"edit_{idx}"):
                        current_messages = current_messages[:idx]
                        save_message(current_session_id, current_messages)
                        st.rerun()
                with act_cols[1]:
                    if st.button("↻ Redo", key=f"ru_{idx}"):
                        current_messages = current_messages[:idx+1]
                        save_message(current_session_id, current_messages)
                        st.session_state.force_run = message["content"]
                        st.rerun()
            elif message["role"] == "assistant":
                with act_cols[0]:
                    if st.button("📋 Copy", key=f"cp_{idx}"): st.toast("Disalin!", icon="📋")
                with act_cols[1]:
                    if st.button("↻ Redo", key=f"ra_{idx}"):
                        current_messages = current_messages[:idx]
                        save_message(current_session_id, current_messages)
                        if len(current_messages) > 0: st.session_state.force_run = current_messages[-1]["content"]
                        st.rerun()

    # Menu Ekstra + Kamera + File Uploader
    menu_col1, menu_col2, menu_col3 = st.columns([1, 8, 1])
    with menu_col1:
        with st.popover("⋮"): st.button("🧹 Bersihkan Konteks", use_container_width=True)
    with menu_col3:
        with st.popover("➕"):
            uploaded_file = st.file_uploader("Upload File (PDF/TXT/Gambar)", type=['pdf', 'txt', 'png', 'jpg', 'jpeg'])
            camera_photo = st.camera_input("📸 Ambil Foto Dokumen")

    trigger_generate = False
    prompt_text = ""
    if prompt := st.chat_input("Tanyakan apa saja kepada DIMA-X..."):
        prompt_text = prompt
        current_messages.append({"role": "user", "content": prompt_text})
        new_title = prompt_text[:25] + "..." if len(current_messages) == 1 else current_data["title"]
        save_message(current_session_id, current_messages, title=new_title)
        trigger_generate = True

    if "force_run" in st.session_state:
        prompt_text = st.session_state.force_run
        del st.session_state.force_run
        trigger_generate = True

    if trigger_generate:
        if not any(msg["content"] == prompt_text for msg in current_messages[-1:]):
            with st.chat_message("user"): st.markdown(prompt_text)

        try:
            client = genai.Client(api_key=api_key)
            formatted_contents = [{"role": "user" if m["role"] == "user" else "model", "parts": [{"text": m["content"]}]} for m in current_messages[:-1]]
            
            parts_payload = [{"text": prompt_text}]
            
            # Penanganan Input Visual & Dokumen (Tetap sama)
            if camera_photo:
                img = Image.open(camera_photo)
                parts_payload.insert(0, img)
                parts_payload.insert(0, {"text": "Tolong analisis foto dari kamera ini:\n"})
            elif uploaded_file:
                if uploaded_file.name.endswith(('.png', '.jpg', '.jpeg')):
                    img = Image.open(uploaded_file)
                    parts_payload.insert(0, img)
                    parts_payload.insert(0, {"text": "Tolong analisis gambar ini:\n"})
                else:
                    doc_text = ""
                    if uploaded_file.name.endswith('.txt'): doc_text = uploaded_file.read().decode('utf-8')
                    elif uploaded_file.name.endswith('.pdf'):
                        reader = PyPDF2.PdfReader(uploaded_file)
                        for p in reader.pages: doc_text += (p.extract_text() or "") + "\n"
                    parts_payload.insert(0, {"text": f"\n--- KONTEKS DOKUMEN ---\n{doc_text}\nBerdasarkan dokumen di atas:\n"})

            formatted_contents.append({"role": "user", "parts": parts_payload})
            
            # Tentukan Final Model menggunakan Smart Router
            final_model_to_use = route_model(prompt_text, active_model)
            model_badge = "⚡ Mode Hemat" if final_model_to_use != 'gemini-1.5-pro' else "🧠 Mode Analisis Dalam"

            with st.chat_message("assistant"):
                with st.spinner(f"DIMA-X sedang menulis... ({model_badge})"):
                    response = client.models.generate_content(
                        model=final_model_to_use, 
                        contents=formatted_contents, 
                        config=types.GenerateContentConfig(system_instruction=system_instruction)
                    )
                    st.markdown(response.text)
            
            current_messages.append({"role": "assistant", "content": response.text})
            save_message(current_session_id, current_messages)
            st.rerun()
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")
# 7. HALAMAN 2: NOTEBOOK DASHBOARD
elif st.session_state.current_page == "📓 Notebook Dashboard":
    st.title("📓 Notebook Dashboard")
    st.markdown("Kumpulan catatan, ringkasan, dan draf penting yang sudah kamu simpan dari obrolan DIMA-X.")
    st.divider()
    
    notes = db.collection(notebook_collection).order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    has_notes = False
    
    for note in notes:
        has_notes = True
        n_data = note.to_dict()
        with st.expander(f"📌 {n_data['title']} (Disimpan: {n_data.get('created_at', '')[:10]})"):
            for msg in n_data['content']:
                role_icon = "🧑‍💻" if msg["role"] == "user" else "🤖"
                st.markdown(f"**{role_icon}**: {msg['content']}")
            if st.button("🗑️ Hapus Catatan", key=f"del_note_{note.id}"):
                db.collection(notebook_collection).document(note.id).delete()
                st.rerun()
                
    if not has_notes:
        st.info("Belum ada catatan. Gunakan fitur 'Add to Notebook' dari menu titik tiga di obrolan untuk menyimpan teks penting ke sini.")

# 8. HALAMAN 3: GOOGLE DRIVE INTEGRATION
elif st.session_state.current_page == "☁️ Drive Integration":
    st.title("☁️ Google Drive Workspace")
    st.markdown("Integrasikan dokumen dari Google Drive langsung ke otak DIMA-X.")
    st.warning("⚠️ Karena ini adalah aplikasi Streamlit personal, cara paling aman dan efisien mengimpor dokumen tanpa ribet setup OAuth/Credentials.json adalah menggunakan tautan folder publik atau link file langsung.")
    
    drive_link = st.text_input("🔗 Paste Link File/Folder Google Drive di sini:")
    if st.button("🔄 Sinkronkan Data", type="primary"):
        if "drive.google.com" in drive_link:
            st.success("Tautan terdeteksi! (Script API akan mengekstrak ID dan mengunduh teks ke memori DIMA-X). Fitur ekstraksi URL ini akan aktif sepenuhnya saat deploy final.")
        else:
            st.error("Masukkan tautan Google Drive yang valid.")
