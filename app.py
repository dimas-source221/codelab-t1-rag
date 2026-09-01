import streamlit as st
from google import genai
from google.genai import types
import PyPDF2
from PIL import Image
import uuid
import json
import datetime
import io
import time
import firebase_admin
from firebase_admin import credentials, firestore

# 1. Konfigurasi Halaman & Routing
st.set_page_config(page_title="DIMA-X | AI Agent", page_icon="🚀", layout="centered", initial_sidebar_state="expanded")

if "current_page" not in st.session_state:
    st.session_state.current_page = "💬 AI Workspace"
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "last_latency" not in st.session_state:
    st.session_state.last_latency = None

# 2. Desain CSS Custom (Full Original Design)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@700;800;900&family=Roboto:wght@400;500&display=swap');
    html, body, [class*=\"css\"] { font-family: 'Roboto', sans-serif; }
    .stApp { background-color: #000000; color: #e3e3e3; }
    .brand-sidebar { font-family: 'Nunito', sans-serif; font-size: 1.8rem; font-weight: 900; text-align: left; margin-bottom: 20px; }
    .brand-text { background: linear-gradient(135deg, #ffffff 40%, #87CEEB 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .stButton>button { border-radius: 8px; border: 1px solid #333; background-color: #1e1e1e; color: white; }
    .status-badge { font-size: 0.8rem; color: #a3a3a3; background-color: #141414; border: 1px solid #2a2a2a; padding: 4px 12px; border-radius: 999px; }
    .stChatInput div[data-baseweb=\"input\"] { border-radius: 999px !important; }
    </style>
""", unsafe_allow_html=True)

api_key = st.secrets["GEMINI_API_KEY"]

# 3. Inisialisasi Firebase & Koleksi
if not firebase_admin._apps:
    try:
        firebase_secrets = st.secrets["firebase"]["firebase_json"]
        cred_dict = json.loads(firebase_secrets)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e: st.error(f"Firebase Error: {e}")

db = firestore.client()
collection_name, notebook_collection = "dimax_history", "dimax_notebooks"
memory_collection, cache_collection = "dimax_long_term_memory", "dimax_response_cache"

# --- HELPER FUNCTIONS ---
def get_long_term_memory():
    doc = db.collection(memory_collection).document("core_identity").get()
    return doc.to_dict().get("context", "") if doc.exists else "Fakta Pengguna: Mahasiswa SI UT."

def create_new_session():
    new_id = str(uuid.uuid4())
    db.collection(collection_name).document(new_id).set({"title": "Obrolan Baru", "messages": [], "updated_at": datetime.datetime.now().isoformat(), "is_pinned": False})
    return new_id

def save_message(session_id, messages, title=None):
    update_data = {"messages": messages, "updated_at": datetime.datetime.now().isoformat()}
    if title: update_data["title"] = title
    db.collection(collection_name).document(session_id).set(update_data, merge=True)

def get_all_sessions():
    docs = db.collection(collection_name).stream()
    sessions = {doc.id: doc.to_dict() for doc in docs}
    return dict(sorted(sessions.items(), key=lambda x: (x[1].get('is_pinned', False), x[1].get('updated_at', '')), reverse=True))

# --- MODEL CONFIG & FALLBACK (SOLUSI 404) ---
MODELS_MAPPING = {
    "⚡ DIMX 3.5 plus-lite": "gemini-2.0-flash",
    "🚀 DIMX 3.6 pro": "gemini-2.0-flash",
    "🧠 DIMX 3.1 pro-max": "gemini-2.0-pro-exp-02-05"
}
FALLBACK_MODELS = ['gemini-2.0-flash', 'gemini-1.5-flash']

def generate_with_fallback(client, primary_model, contents, config):
    candidates = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]
    last_err = None
    for model_id in candidates:
        try:
            return client.models.generate_content(model=model_id, contents=contents, config=config), model_id
        except Exception as e:
            last_err = e
            if "404" in str(e) or "NOT_FOUND" in str(e).upper(): continue
            raise e
    raise last_err

# --- SIDEBAR ---
chat_sessions = get_all_sessions()
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = create_new_session()

with st.sidebar:
    st.markdown('<div class=\"brand-sidebar\"><span class=\"rocket-icon\">🚀</span> <span class=\"brand-text\">DIMA-X</span></div>', unsafe_allow_html=True)
    st.session_state.demo_mode = st.toggle("🎬 Demo Mode", value=st.session_state.demo_mode)
    
    if not st.session_state.demo_mode:
        nav = st.radio("MENU", ["💬 AI Workspace", "📓 Notebook Dashboard", "☁️ Drive Integration"])
        st.session_state.current_page = nav
        if st.button("➕ Obrolan Baru", use_container_width=True): 
            st.session_state.current_session_id = create_new_session()
            st.rerun()
        
        # Versi Engine: Default Lite (index=0)
        model_label = st.selectbox("Versi Engine", list(MODELS_MAPPING.keys()), index=0)
        active_model = MODELS_MAPPING[model_label]
        mode_dima = st.selectbox("Mode AI", ["🤖 AI Chat", "🎓 STUDY-X", "💼 WORK-X", "✍️ WRITE-X"])

# --- MAIN UI ---
long_term_context = get_long_term_memory()
system_instruction = f"Kamu adalah DIMA-X, Personal AI Thinking Partner. Konteks: {long_term_context}"

if st.session_state.current_page == "💬 AI Workspace":
    curr_session = chat_sessions.get(st.session_state.current_session_id, {"messages": [], "title": "Obrolan Baru"})
    messages = curr_session.get("messages", [])

    for msg in messages:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    # Multimedia Inputs
    with st.popover("➕ Media"):
        up_file = st.file_uploader("Upload PDF/Image", type=['pdf', 'png', 'jpg', 'jpeg'])
        cam_photo = st.camera_input("Ambil Foto")

    prompt = st.chat_input("Tanyakan DIMA-X...")
    if prompt:
        messages.append({"role": "user", "content": prompt})
        save_message(st.session_state.current_session_id, messages, title=prompt[:20])
        st.chat_message("user").write(prompt)

        client = genai.Client(api_key=api_key)
        parts = [{"text": prompt}]

        # Logic File/Image Processing
        if up_file:
            if up_file.name.endswith('.pdf'):
                pdf_text = "".join([p.extract_text() for p in PyPDF2.PdfReader(up_file).pages])
                parts.insert(0, {"text": f"PDF Content: {pdf_text}\n"})
            else:
                img = Image.open(up_file)
                parts.append(img)
        if cam_photo: parts.append(Image.open(cam_photo))

        try:
            with st.spinner("DIMA-X Thinking..."):
                config = types.GenerateContentConfig(system_instruction=system_instruction)
                res, used_m = generate_with_fallback(client, active_model, [{"role": "user", "parts": parts}], config)
                st.chat_message("assistant").write(res.text)
                st.caption(f"Engine: {used_m}")
                messages.append({"role": "assistant", "content": res.text})
                save_message(st.session_state.current_session_id, messages)
        except Exception as e: st.error(f"Error: {e}")

elif st.session_state.current_page == "📓 Notebook Dashboard":
    st.title("📓 Notebook")
    notes = db.collection(notebook_collection).stream()
    for n in notes: st.expander(n.to_dict()['title']).write(n.to_dict()['content'])
