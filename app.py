# Cadas Resonance Studio — app.py
# Streamlit app for CLICK -> STAY -> RETURN content planning.
# ClarioHub OpenAI-compatible API integration. Without an API key, the app runs in demo mode.
# Run: pip install streamlit requests && streamlit run app.py

import json
import random
import re
import textwrap
import os
import shutil
import subprocess
import tempfile
from datetime import datetime

import requests
import streamlit as st

APP_NAME = "CADAS RESONANCE STUDIO"
DEFAULT_MODEL = "clario/deepseek-v4-flash"
CLARIOHUB_BASE_URL = "https://clariohub.id/v1"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="💀",
    layout="wide",
    initial_sidebar_state="expanded",
)

def extract_last_video_frame(video_bytes, original_name="scene.mp4"):
    """Extract the final decodable frame using ffmpeg, with a short retry window."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        try:
            import imageio_ffmpeg
            ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:
            ffmpeg = None
    if not ffmpeg:
        raise RuntimeError("FFmpeg tidak tersedia. Tambahkan ffmpeg ke environment Streamlit atau install imageio-ffmpeg.")
    suffix = os.path.splitext(original_name)[1] or ".mp4"
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "input" + suffix)
        out = os.path.join(tmp, "last_frame.png")
        with open(src, "wb") as f:
            f.write(video_bytes)
        # Seek close to the end; if that timestamp falls between decodable frames,
        # retry with a wider tail window. This avoids accidentally returning frame 1.
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-sseof", "-0.5", "-i", src,
               "-frames:v", "1", "-update", "1", "-y", out]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            if os.path.exists(out):
                os.remove(out)
            cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-sseof", "-2", "-i", src,
                   "-frames:v", "1", "-update", "1", "-y", out]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if proc.returncode != 0 or not os.path.exists(out) or os.path.getsize(out) == 0:
            raise RuntimeError("Frame tidak berhasil diekstrak. Pastikan video bisa diputar dan formatnya MP4/MOV/WebM.")
        with open(out, "rb") as f:
            return f.read()


def render_copy_prompt(prompt, button_label="📋 Salin prompt ke clipboard", height=76, key="copy_prompt"):
    """Render a reliable in-page copy control so mobile users don't need to download a TXT file."""
    import base64
    import streamlit.components.v1 as components
    encoded = base64.b64encode(str(prompt).encode("utf-8")).decode("ascii")
    safe_key = re.sub(r"[^a-zA-Z0-9_-]", "_", str(key))
    html = f"""
    <div id="wrap_{safe_key}" style="font-family:system-ui,sans-serif;display:flex;gap:8px;align-items:center;flex-wrap:wrap;">
      <button id="btn_{safe_key}" style="background:linear-gradient(115deg,#315ee8,#7751d8);color:white;border:0;border-radius:10px;padding:11px 16px;font-size:14px;font-weight:700;cursor:pointer;min-height:42px;">{button_label}</button>
      <span id="status_{safe_key}" style="font-size:13px;color:#405078;">Tekan tombol untuk menyalin; tidak perlu download.</span>
      <textarea id="fallback_{safe_key}" aria-label="Prompt untuk disalin" style="position:fixed;left:-9999px;top:0;width:2px;height:2px;opacity:0;"></textarea>
    </div>
    <script>
    (function(){{
      const raw = atob('{encoded}');
      const bytes = Uint8Array.from(raw, c => c.charCodeAt(0));
      const promptText = new TextDecoder('utf-8').decode(bytes);
      const btn = document.getElementById('btn_{safe_key}');
      const status = document.getElementById('status_{safe_key}');
      const fallback = document.getElementById('fallback_{safe_key}');
      btn.addEventListener('click', async function() {{
        try {{
          if (navigator.clipboard && window.isSecureContext) {{
            await navigator.clipboard.writeText(promptText);
          }} else {{
            fallback.value = promptText; fallback.style.position='fixed'; fallback.style.left='0'; fallback.style.top='0'; fallback.style.opacity='1';
            fallback.focus(); fallback.select();
            const ok = document.execCommand('copy');
            fallback.style.position='fixed'; fallback.style.left='-9999px'; fallback.style.opacity='0';
            if (!ok) throw new Error('clipboard unavailable');
          }}
          status.textContent = '✅ Prompt berhasil disalin. Tempel langsung di Google Flow.';
          btn.textContent = '✅ Tersalin!';
        }} catch (e) {{
          fallback.value = promptText; fallback.style.position='static'; fallback.style.left='auto'; fallback.style.width='100%'; fallback.style.height='100px'; fallback.style.opacity='1';
          fallback.focus(); fallback.select();
          status.textContent = 'Pilih teks yang muncul lalu tekan Salin/Copy di HP.';
        }}
      }});
    }})();
    </script>
    """
    components.html(html, height=height, scrolling=False)

# ----------------------------- UI STYLE -----------------------------
st.markdown("""
<style>
    :root {
        --ink: #18223d;
        --muted: #586681;
        --line: rgba(117, 137, 190, .28);
        --blue: #315ee8;
        --violet: #7751d8;
    }
    .stApp {
        background:
            radial-gradient(ellipse at 8% 4%, rgba(105, 145, 255, .23), transparent 32%),
            radial-gradient(ellipse at 94% 12%, rgba(177, 119, 255, .20), transparent 29%),
            radial-gradient(ellipse at 72% 90%, rgba(91, 211, 221, .16), transparent 32%),
            linear-gradient(135deg, #edf2ff 0%, #f5f0ff 48%, #eaf8fb 100%);
        color: var(--ink);
        background-attachment: fixed;
    }
    [data-testid="stHeader"] { background: rgba(239,243,255,.72); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #e5ebff 0%, #f0eaff 52%, #e4f6fb 100%);
        border-right: 1px solid rgba(115, 130, 190, .24);
    }
    [data-testid="stSidebar"] * { color: #202b4b; }
    .block-container { max-width: 1200px; padding-top: 1.25rem; padding-bottom: 3rem; }
    .hero {
        position: relative; overflow: hidden;
        padding: 1.55rem 1.65rem; border-radius: 22px;
        background: linear-gradient(115deg, rgba(255,255,255,.92), rgba(229,235,255,.88) 48%, rgba(238,226,255,.91));
        border: 1px solid rgba(129, 143, 207, .32); margin-bottom: 1.1rem;
        box-shadow: 0 14px 34px rgba(64, 74, 145, .12);
    }
    .hero:after {
        content: ""; position: absolute; width: 190px; height: 190px; right: -48px; top: -78px;
        border-radius: 50%; border: 28px solid rgba(116, 91, 225, .09);
        box-shadow: 0 0 0 22px rgba(75, 137, 232, .05), 0 0 0 48px rgba(75, 137, 232, .035);
        pointer-events: none;
    }
    .hero h1 { margin: 0; font-size: 2rem; color: #26366e; letter-spacing: -.035em; }
    .hero p { margin: .5rem 0 0; color: #52617f; }
    .pill {
        display: inline-block; padding: .25rem .65rem; margin: .15rem;
        border: 1px solid rgba(105, 117, 197, .25); border-radius: 999px;
        color: #38458c; background: linear-gradient(135deg, #fff, #edf0ff); font-size: .82rem;
        box-shadow: 0 3px 8px rgba(80, 91, 165, .06);
    }
    .stage {
        border: 1px solid rgba(117, 137, 190, .25);
        background: linear-gradient(145deg, rgba(255,255,255,.91), rgba(244,246,255,.86));
        border-radius: 16px; padding: 1rem 1.05rem; min-height: 100px;
        box-shadow: 0 7px 20px rgba(62, 75, 140, .07);
    }
    .stage h4 { margin: 0 0 .35rem; color: #3d4da0; }
    .muted { color: var(--muted); font-size: .9rem; }
    div[data-testid="stExpander"] {
        border: 1px solid rgba(117, 137, 190, .25);
        border-radius: 14px; background: rgba(255,255,255,.56);
    }
    div[data-testid="stTextInput"] input, div[data-testid="stTextArea"] textarea,
    div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
    div[data-testid="stNumberInput"] input {
        border-radius: 10px; border-color: rgba(117, 137, 190, .36);
        background: rgba(255,255,255,.86);
    }
    div.stButton > button {
        border-radius: 11px; font-weight: 700; min-height: 2.75rem;
        border: 1px solid rgba(89, 105, 193, .28);
        box-shadow: 0 4px 10px rgba(65, 76, 151, .08);
        transition: transform .15s ease, box-shadow .15s ease;
    }
    div.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 7px 16px rgba(65, 76, 151, .15); }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(115deg, #315ee8, #7751d8); color: white; border: none;
    }
    div[data-testid="stAlert"] { border-radius: 12px; }
    hr { border-color: rgba(117, 137, 190, .22); }
    @media (max-width:700px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .hero { padding: 1.15rem; }
        .hero h1 { font-size: 1.55rem; }
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------- STATE -----------------------------
def init_state():
    defaults = {
        "ideas": [],
        "selected_title": "",
        "selected_idea": {},
        "hooks": [],
        "selected_hook": "",
        "story": {},
        "flow_prompts": [],
        "broll": [],
        "last_signature": "",
        "notice": "",
        "continuity_frame_bytes": None,
        "continuity_frame_name": "scene1_last_frame.png",
        "continuity_video_name": "",
        "continuity_prompt_ready": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_state()

def clear_from(stage):
    """Invalidate downstream results when upstream choices change."""
    order = ["ideas", "hooks", "story", "flow_prompts", "broll"]
    if stage in order:
        idx = order.index(stage)
        for key in order[idx:]:
            if key == "ideas":
                st.session_state.ideas = []
                st.session_state.selected_title = ""
                st.session_state.selected_idea = {}
                st.session_state.chosen_idea_title = ""
            elif key == "hooks":
                st.session_state.hooks = []
                st.session_state.selected_hook = ""
            elif key == "story":
                st.session_state.story = {}
            elif key == "flow_prompts":
                st.session_state.flow_prompts = []
            elif key == "broll":
                st.session_state.broll = []

def invalidate_downstream(stage):
    order = ["hooks", "story", "flow_prompts", "broll"]
    idx = order.index(stage)
    for key in order[idx:]:
        if key == "hooks":
            st.session_state.hooks = []
            st.session_state.selected_hook = ""
        elif key == "story":
            st.session_state.story = {}
        elif key == "flow_prompts":
            st.session_state.flow_prompts = []
        elif key == "broll":
            st.session_state.broll = []

# ----------------------------- GEMINI -----------------------------
def extract_json(text):
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        start = text.find("[")
        end = text.rfind("]")
        if start >= 0 and end > start:
            return json.loads(text[start:end+1])
        raise

def clariohub_generate(prompt, api_key, model, temperature=0.85):
    """Call ClarioHub's OpenAI-compatible chat completions endpoint."""
    if not api_key:
        raise RuntimeError("API key ClarioHub belum diisi. Isi key di panel pengaturan atau gunakan mode demo.")
    url = f"{CLARIOHUB_BASE_URL}/chat/completions"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key.strip()}",
            "Content-Type": "application/json",
        },
        json={
            "model": model.strip() or DEFAULT_MODEL,
            "messages": [
                {"role": "system", "content": (
                    "You are a precise short-video creative producer. Follow the requested JSON schema exactly. "
                    "Return valid JSON only, without markdown fences. "
                    "LANGUAGE LOCK: If the user selects 'Indonesia Lokal' or requests Bahasa Indonesia, ALL audience-facing text MUST be natural Bahasa Indonesia: titles, premises, hooks, story beats, dialogue, punchlines, CTAs, summaries, and series ideas. "
                    "Do not write audience-facing content in English. Do not translate Indonesian dialogue into English. "
                    "Technical visual instructions may be English only when useful, but every spoken line must remain exactly in natural Bahasa Indonesia. "
                    "If the user selects 'Global Skeleton', use English. If the user selects 'Lokal + Global', keep Indonesian and English versions clearly separate; never mix languages in a single dialogue or version."
                )},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        },
        timeout=120,
    )
    if response.status_code != 200:
        try:
            data = response.json()
            detail = data.get("error", {}).get("message", response.text)
        except Exception:
            detail = response.text
        raise RuntimeError(f"ClarioHub API error ({response.status_code}): {detail}")
    data = response.json()
    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "\n".join(str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content)
        return extract_json(str(content))
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Respons ClarioHub kosong atau bukan JSON yang valid.") from exc

def ai_or_demo(prompt, api_key, model, demo_fn, temperature=0.85):
    if api_key:
        return clariohub_generate(prompt, api_key, model, temperature)
    return demo_fn()

# ----------------------------- PROMPT HELPERS -----------------------------
def mode_language(mode):
    if mode == "Global Skeleton":
        return "LANGUAGE LOCK: English only for titles, premises, hooks, story, dialogue, punchlines, CTA, and series ideas."
    if mode == "Indonesia Lokal":
        return "KUNCI BAHASA WAJIB: Semua judul, premis, hook, konflik, twist, seluruh dialog yang diucapkan, punchline, CTA, potensi serial, dan deskripsi cerita WAJIB Bahasa Indonesia natural. DILARANG memakai bahasa Inggris untuk isi cerita atau dialog. Istilah teknis visual boleh bahasa Inggris, tetapi dialog yang diucapkan harus tetap Bahasa Indonesia dan jangan diterjemahkan. Gunakan humor dan ungkapan Indonesia yang alami."
    return "Buat versi Bahasa Indonesia dan versi English secara TERPISAH. Jangan mencampur bahasa dalam satu judul, satu versi cerita, atau satu dialog."

def realism_rules(mode):
    return """
VISUAL RULES — MANDATORY:
- Photorealistic live-action look or highly realistic cinematic CGI with believable materials.
- NOT cartoon, NOT Pixar, NOT anime, NOT illustration, NOT toy-like plastic, NOT flat 2D.
- Realistic anatomy/materials, detailed textures, physically plausible lighting, cinematic lensing.
- For skeleton stories, use a detailed realistic anatomical skeleton with natural bone texture;
  it must not look like a cartoon mascot or a plastic toy.
- Keep the same character identity, clothing/accessories, proportions, and location across shots.
- Vertical 9:16 by default, sharp focus on the subject, no blur unless motivated by camera movement.
- Do not generate subtitles, logos, watermarks, or extra text inside the video.
"""

def current_config():
    return {
        "mode": st.session_state.get("mode", "Global Skeleton"),
        "theme": st.session_state.get("theme", "Absurd Comedy"),
        "subtheme": st.session_state.get("subtheme", "Everyday disaster"),
        "duration": st.session_state.get("duration", 20),
        "audience": st.session_state.get("audience", "General audience"),
        "style": st.session_state.get("style", "Realistic cinematic"),
        "goal": st.session_state.get("goal", "Subscriber growth"),
        "character": st.session_state.get("character", "Overconfident Skeleton"),
        "setting": st.session_state.get("setting", "Everyday location"),
        "humor": st.session_state.get("humor", "Absurd, fast-paced, visual"),
        "language": mode_language(st.session_state.get("mode", "Global Skeleton")),
    }

def config_signature(cfg):
    return json.dumps(cfg, sort_keys=True, ensure_ascii=False)

def ensure_current():
    cfg = current_config()
    sig = config_signature(cfg)
    if st.session_state.last_signature and sig != st.session_state.last_signature:
        clear_from("ideas")
    st.session_state.last_signature = sig

def make_ideas_prompt(cfg, count):
    return f"""
You are the creative strategist for {APP_NAME}.
Generate exactly {count} genuinely different short-video concepts.
Return valid JSON only with this schema:
{{
 "ideas":[
  {{
   "title":"specific clickable title",
   "premise":"one-sentence premise",
   "hook":"what viewers see/hear in the first 1 second",
   "conflict":"central problem",
   "twist":"payoff/reversal",
   "series_potential":"a concrete way this could become an episode series",
   "primary_goal":"{cfg['goal']}"
  }}
 ]
}}
CHANNEL: {cfg['mode']}
THEME: {cfg['theme']} / {cfg['subtheme']}
CHARACTER: {cfg['character']}
SETTING: {cfg['setting']}
AUDIENCE: {cfg['audience']}
HUMOR: {cfg['humor']}
LANGUAGE: {cfg['language']}
STRICT VARIETY RULES:
- Each of the {count} ideas must have a DIFFERENT concrete story mechanism and different payoff, not merely a synonym title.
- Do NOT repeat the same phrase from the subtheme in every title. Use the subtheme as the world/topic, then invent distinct episode events.
- Titles must be distinct enough that each could produce a visibly different video. Vary the object, obstacle, mistaken assumption, stakes, and twist.
- Avoid title templates repeated across the list (for example, repeated “ketika X malah kacau”).
- Before returning JSON, internally compare all titles and premises; rewrite any that feel like duplicates.
Create distinct concepts, not the same premise with different titles. Avoid generic clickbait.
Each hook must be immediately understandable and visually filmable. Every concept needs a clear payoff. For subscriber-growth goals, optimize for an instant visual stop, escalating curiosity, a memorable payoff, and a natural explicit subscribe/like invitation in the final beat.
{realism_rules(cfg['mode'])}
"""

def demo_ideas(cfg, count):
    """Settings-aware fallback when no API key is supplied; never return a fixed unrelated title pool."""
    subtheme = re.sub(r"\s+", " ", str(cfg.get("subtheme", "kejadian absurd")).strip()).strip(" .,!?:;")
    if not subtheme:
        subtheme = str(cfg.get("theme", "kejadian absurd"))
    character = str(cfg.get("character", "karakter utama"))
    setting = str(cfg.get("setting", "lokasi sesuai subtema"))
    theme = str(cfg.get("theme", "Komedi"))
    goal = str(cfg.get("goal", "Subscriber growth"))
    local = cfg.get("mode") == "Indonesia Lokal"

    # Demo concepts must vary the STORY ANGLE, not just rearrange the same subtheme words.
    short_topic = subtheme[:76].strip()
    low_topic = subtheme.lower()
    ghost_subscribe = any(k in low_topic for k in ["hantu", "pocong", "kuntilanak"
