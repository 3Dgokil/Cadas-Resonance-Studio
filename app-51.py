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
    ghost_terms = ("hantu", "pocong", "kuntilanak", "tuyul", "makhluk halus")
    subscribe_terms = ("subscribe", "subscriber", "channel", "youtube", "nonton")
    ghost_subscribe = any(term in low_topic for term in ghost_terms) and any(
        term in low_topic for term in subscribe_terms
    )
    if ghost_subscribe and local:
        title_patterns = (
            "SUBSCRIBER NOL, HANTU MALAH BUKA POS PENGADUAN",
            "POCONG SALAH PENCET: YANG MINTA SUBSCRIBE MALAH KENA BLOKIR",
            "HANTU NGADAIN AUDISI DEMI 1 SUBSCRIBER",
            "PENJUAL WARUNG JADI MANAJER CHANNEL HANTU",
            "HANTU MENGHANTUI ORANG YANG BELUM SUBSCRIBE—TAPI ADA BALASANNYA",
            "LIVE PERTAMA SI HANTU BERAKHIR BENCANA",
            "TANTANGAN 10 DETIK: BIKIN HANTU DAPAT SUBSCRIBER",
            "HANTU SALAH SASARAN SAAT PROMOSI CHANNEL",
            "ANGKA SUBSCRIBER HANTU NAIK, TAPI ADA YANG ANEH",
            "HANTU MINTA LIKE KE ORANG YANG LAGI KETAKUTAN",
        )
    else:
        title_patterns = (
            f"{short_topic.upper()}: RENCANA YANG MALAH MEMPERMALUKAN {character.upper()}",
            f"{character.upper()} MENEMUKAN SATU PETUNJUK YANG SEMUA ORANG LEWATKAN",
            f"{short_topic.upper()} BERUBAH GARA-GARA SATU BENDA KECIL",
            f"{character.upper()} PUNYA 10 DETIK UNTUK MEMPERBAIKI {short_topic.upper()}",
            f"SEMUA MENYALAHKAN {character.upper()}, TAPI BUKTINYA BERBEDA",
            f"{short_topic.upper()}: SOLUSI PERTAMA JUSTRU BIKIN KACAU",
            f"RAHASIA DI {setting.upper()} TERBONGKAR DI DETIK TERAKHIR",
            f"{character.upper()} MENANG DENGAN CARA YANG SALAH TOTAL",
            f"SATU KESALAHPAHAMAN MENGACAUKAN {short_topic.upper()}",
            f"AKHIRNYA TERUNGKAP: YANG HILANG TERNYATA ADA DI DEPAN MATA",
        )
    conflict_templates = [
        f"Rencana {subtheme} terganggu oleh masalah tak terduga di {setting}.",
        f"{character} tidak bisa menyelesaikan {subtheme} semudah yang dibayangkan.",
        f"Satu keputusan konyol membuat situasi {subtheme} makin kacau.",
        f"Ada aturan/halangan di {setting} yang merusak rencana {subtheme}.",
        f"Saat {subtheme} hampir berhasil, muncul masalah yang mempermalukan {character}.",
        f"Semua karakter salah paham tentang tujuan {subtheme}.",
        f"Sebuah benda penting hilang ketika {subtheme} sedang berlangsung.",
        f"{character} mencoba menutupi kesalahan, tetapi justru memperbesar masalah.",
        f"Orang di sekitar salah mengira kejadian {subtheme} sebagai sesuatu yang lain.",
        f"Rencana sederhana di {setting} berubah menjadi kekacauan berantai.",
    ]
    twist_templates = [
        f"Ternyata masalahnya berasal dari hal kecil yang sejak awal terlihat di {setting}.",
        f"{character} justru menjadi penyebab utama kekacauan yang ingin ia hentikan.",
        f"Rencana itu berhasil, tetapi hasil akhirnya malah berlawanan dengan tujuan awal.",
        f"Orang yang dianggap mengganggu ternyata satu-satunya yang paham situasi.",
        f"Benda yang dicari ternyata sudah dibawa karakter sejak awal.",
        f"Semua orang panik, padahal pemicunya adalah kesalahpahaman konyol.",
        f"Akhirnya {character} harus mengulang kejadian dari awal untuk memperbaiki kesalahan.",
        f"Petunjuk twist terlihat di detik pertama dan baru masuk akal saat ditonton ulang.",
        f"Yang dikira kegagalan ternyata justru membuka masalah yang lebih lucu.",
        f"Karakter paling percaya diri malah meminta bantuan penonton untuk menyelesaikannya.",
    ]
    ideas = []
    indices = list(range(len(title_patterns)))
    random.shuffle(indices)
    for i in indices[:max(1, min(count, len(title_patterns)))]:
        title = title_patterns[i]
        conflict = conflict_templates[i]
        twist = twist_templates[i]
        if local:
            if ghost_subscribe:
                ghost_premises = [
                    f"Hantu membuka pos pengaduan di {setting} karena sudah menakut-nakuti banyak orang tetapi tidak mendapat subscriber; ia malah harus menjawab komplain manusia.",
                    f"Hantu salah menekan tombol blokir saat mempromosikan channel kepada {character}; sekarang ia harus membujuk satu-satunya penonton yang tersisa.",
                    f"Hantu mengadakan audisi seram di {setting} demi mendapat subscriber, tetapi semua peserta justru mengajari hantu cara bikin konten.",
                    f"Pemilik {setting} terpaksa menjadi manajer channel hantu dan membuat strategi promosi yang berakhir dengan kekacauan langsung.",
                    f"Hantu mengancam akan menghantui orang yang tidak subscribe, tetapi orang itu justru meminta hantu membuktikan kemampuan seramnya.",
                    f"Siaran langsung pertama hantu di {setting} kacau ketika efek seramnya membuat dirinya sendiri ketakutan.",
                    f"Hantu memberi tantangan 10 detik kepada {character} untuk menaikkan subscriber, tetapi angka di layar malah berubah karena salah pencet.",
                    f"Hantu menawarkan promosi channel ke orang yang salah dan tanpa sadar meminta bantuan pemburu hantu.",
                    f"Subscriber hantu tiba-tiba bertambah satu, tetapi ia curiga akun itu miliknya sendiri yang tidak sengaja berlangganan.",
                    f"Hantu meminta like kepada pelanggan yang ketakutan, tetapi pelanggan itu menekan tombol yang salah dan memicu kejadian baru.",
                ]
                ghost_hooks = [
                    "Hantu: Bang, saya mau lapor! Saya sudah nakut-nakuti 20 orang, subscriber tetap nol!",
                    "Hantu: Jangan blokir saya, Bang! Saya belum sempat minta subscribe!",
                    "Hantu: Audisi dimulai! Siapa yang bisa bikin saya seram dapat hadiah... satu subscribe!",
                    "Manusia: Jadi saya bukan penjaga warung lagi, tapi manajer channel hantu?!",
                    "Hantu: Subscribe sekarang, atau saya—eh, kok kamu malah minta bukti?!",
                    "Hantu: Selamat datang di live pertama saya! AAAAA! Siapa yang berdiri di belakang saya?!",
                    "Hantu: Bang, cuma punya sepuluh detik buat bikin subscriber saya naik!",
                    "Hantu: Saya mau promosi channel! Manusia: Sebentar, saya panggil pemburu hantu dulu.",
                    "Hantu: Akhirnya subscriber saya satu! Tunggu... ini akun saya sendiri?!",
                    "Hantu: Pencet like, Bang! Manusia: Yang mana? Hantu: BUKAN TOMBOL ALARM ITU!",
                ]
                premise = ghost_premises[i]
                hook = ghost_hooks[i]
                conflict = [
                    "Orang-orang datang bukan untuk subscribe, tetapi untuk mengadukan suara hantu yang terlalu berisik.",
                    "Hantu salah memblokir satu-satunya calon subscriber dan harus meminta maaf.",
                    "Semua peserta audisi lebih jago membuat konten daripada menakut-nakuti.",
                    "Manajer baru menyuruh hantu membuat konten ramah keluarga, padahal hantu hanya bisa mengagetkan orang.",
                    "Manusia tidak takut dan malah meminta hantu menunjukkan bukti kemampuan seramnya.",
                    "Efek suara live membuat hantu mengira ada hantu lain yang mengikutinya.",
                    "Hantu salah menekan tombol dan angka subscriber tidak berubah, sementara waktu terus berjalan.",
                    "Orang yang ditawari promosi ternyata datang membawa alat pemburu hantu.",
                    "Akun yang subscribe ternyata akun hantu sendiri yang masih login.",
                    "Manusia salah menekan tombol alarm sehingga seluruh warung panik.",
                ][i]
                twist = [
                    "Para pengadu akhirnya subscribe hanya agar bisa memberi rating buruk pada layanan hantu.",
                    "Akun yang diblokir ternyata satu-satunya subscriber hantu.",
                    "Pemenang audisi adalah tuyul yang hanya muncul untuk mengambil ponsel.",
                    "Konten paling sukses justru video hantu sedang belajar jadi manajer.",
                    "Hantu kabur lebih dulu ketika manusia pura-pura memanggil pemburu hantu.",
                    "Hantu ternyata takut pada pantulan dirinya sendiri di layar ponsel.",
                    "Subscriber naik satu karena hantu tanpa sengaja menekan subscribe sendiri.",
                    "Pemburu hantu malah meminta link channel sebelum mulai bekerja.",
                    "Subscriber turun lagi saat hantu sadar lalu menekan unsubscribe.",
                    "Alarm warung berbunyi dan hantu yang paling ketakutan lari meninggalkan ponsel.",
                ][i]
                series = f"Episode berikutnya mengikuti upaya hantu memperbaiki channel dengan masalah baru di {setting}."
            else:
                premise = f"{subtheme}. Cerita berlangsung di {setting}, dengan {character} sebagai karakter utama; kejadian berkembang menjadi komedi sesuai tema {theme}."
                hook = f"{character.upper()} LANGSUNG MENGHADAPI MASALAH: {subtheme.upper()}!"
                series = f"Episode lanjutan mengeksplorasi masalah baru dari dunia cerita '{subtheme}', tetap memakai karakter dan lokasi yang sama."
        else:
            premise = f"{subtheme}. The story takes place at {setting}, starring {character}, with a {theme} payoff."
            hook = f"{character.upper()} FACES THIS PROBLEM RIGHT NOW: {subtheme.upper()}!"
            series = f"A follow-up episode explores another problem from the same '{subtheme}' premise, keeping the selected character and setting."
        ideas.append({
            "title": title,
            "premise": premise,
            "hook": hook,
            "conflict": conflict,
            "twist": twist,
            "series_potential": series,
            "primary_goal": goal,
        })
    return {"ideas": ideas}

def make_hooks_prompt(cfg, idea):
    return f"""
Generate exactly 3 alternative first-second hooks for this short-video concept, ranked strongest first. The FIRST hook must be the strongest and will be selected automatically; the user will not choose from a list.
Return JSON only: {{"hooks":[{{"hook":"...","visual":"...","curiosity":"...","strength":"..."}},...]}}
SELECTED CONCEPT — SOURCE OF TRUTH (do not replace it with another idea):
Title: {idea.get('title')}
Premise: {idea.get('premise')}
Opening event: {idea.get('hook')}
Conflict: {idea.get('conflict')}
Twist/payoff: {idea.get('twist')}
Channel: {cfg['mode']}; theme: {cfg['theme']}/{cfg['subtheme']}; character: {cfg['character']}; setting: {cfg['setting']}.
Language: {cfg['language']}
Create 3 different hooks for THIS EXACT concept. Every hook's dialogue and visual must match its premise, characters, conflict, and setting. Never introduce a pocong, kos, warung, skeleton, or any other motif unless it is explicitly in the selected idea.
Hooks must be immediately understandable, filmable, and not rely only on shouting. Do not reveal the whole punchline in the hook.
{realism_rules(cfg['mode'])}
"""

def demo_hooks(cfg, idea):
    """Build fallback hooks from the selected idea; never use an unrelated hard-coded story."""
    title = str(idea.get("title", "Ide pilihan")).strip()
    premise = str(idea.get("premise", "")).strip()
    seed_visual = str(idea.get("hook", "")).strip()
    conflict = str(idea.get("conflict", "")).strip()
    twist = str(idea.get("twist", "")).strip()
    is_local = cfg.get("mode") == "Indonesia Lokal"

    if is_local:
        hooks = [
            {"hook": seed_visual or f"LAH, KOK BISA?! {title.upper()}!", "visual": seed_visual or premise,
             "curiosity": f"Apa akibat dari kejadian ini dalam cerita {title.lower()}?", "strength": "Hook mengambil kejadian spesifik dari ide terpilih, bukan judul acak."},
            {"hook": conflict or f"ADA MASALAH DI {title.upper()}!", "visual": conflict or seed_visual or premise,
             "curiosity": f"Bagaimana karakter menyelesaikan masalah ini?", "strength": "Konflik spesifik dari ide terpilih langsung terlihat."},
            {"hook": f"TUNGGU—AKHIRNYA MALAH BEGINI?!", "visual": twist or premise,
             "curiosity": f"Twist apa yang muncul dari {title.lower()}?", "strength": "Menjanjikan kejutan yang berasal dari payoff ide ini."}
        ]
    else:
        hooks = [
            {"hook": f"WAIT—{title.upper()}?!", "visual": seed_visual or premise,
             "curiosity": f"What happens in {title.lower()}?", "strength": "Starts directly with the selected concept."},
            {"hook": conflict or f"THIS WAS NOT SUPPOSED TO HAPPEN!", "visual": conflict or seed_visual or premise,
             "curiosity": "How will the character solve this specific problem?", "strength": "Uses the conflict from the selected idea."},
            {"hook": "THE ENDING MAKES NO SENSE… UNTIL YOU SEE IT!", "visual": twist or premise,
             "curiosity": f"What is the twist in {title.lower()}?", "strength": "Teases the selected concept's actual payoff."}
        ]
    return {"hooks": hooks}

def make_story_prompt(cfg, idea, hook):
    duration = int(cfg.get("duration", 20))
    return f"""
You are a professional short-form comedy screenwriter and director. Write a FILMABLE, SPECIFIC scene—not an outline and not generic instructions.
Return valid JSON only with this schema:
{{
 "title":"{idea.get('title','')}",
 "logline":"one concise sentence",
 "hook":{{"visual":"specific visible action in the first second","dialogue":"one exact spoken line","duration_seconds":2}},
 "beats":[
  {{"start":0,"end":2,"purpose":"HOOK","visual":"specific physical action, character position, facial expression and props","action":"what the character physically does","dialogue":"exact spoken line(s), with character names","sound":"specific ambience/SFX"}},
  {{"start":2,"end":5,"purpose":"CONTEXT","visual":"specific continuation of the same scene","action":"specific action","dialogue":"exact spoken line(s), with character names","sound":"specific sound"}},
  {{"start":5,"end":8,"purpose":"CONFLICT","visual":"specific escalation","action":"specific action","dialogue":"exact spoken line(s), with character names","sound":"specific sound"}},
  {{"start":8,"end":10,"purpose":"PAYOFF + CTA","visual":"specific punchline, reaction and loopable final pose","action":"exact physical payoff and loop action","dialogue":"exact punchline and CTA spoken naturally by a character","sound":"specific sound"}}
 ],
 "punchline":"specific payoff",
 "cta":"custom spoken CTA with explicit subscribe + like + story-specific rewatch reason",
 "return_potential":"specific replay cue",
 "continuity_notes":["specific continuity rule"]
}}

SELECTED IDEA (single source of truth): {json.dumps(idea, ensure_ascii=False)}
SELECTED HOOK: {json.dumps(hook, ensure_ascii=False)}
CHANNEL MODE: {cfg['mode']}
THEME: {cfg['theme']}
SUBTHEME: {cfg['subtheme']}
CHARACTER: {cfg['character']}
LOCATION: {cfg['setting']}
DURATION: exactly {duration} seconds
AUDIENCE: {cfg['audience']}
HUMOR: {cfg['humor']}
GOAL: {cfg['goal']}
LANGUAGE: {cfg['language']}

CHARACTER ROLE MAP — DO NOT SWAP ROLES:
- Hantu/Pocong = supernatural character; speaks about haunting houses, being a ghost, their own channel/subscribers, supernatural experiences, and ghost-specific embarrassment.
- Manusia/Penjual = human character; asks questions, reacts, jokes back, and responds to the ghost. The human must NEVER say the ghost's first-person experience as if it happened to them.
- When a configured character name is more specific, map it to the correct role but preserve the role ownership above.

NON-NEGOTIABLE WRITING RULES:
- Write actual screen action and dialogue. NEVER output placeholders like "character reacts to the situation", "the conflict becomes harder", "show the main problem", "character says the premise", or repeat the title/premise as dialogue.
- Every dialogue field must contain actual spoken words and explicitly prefix each line with the speaker's exact role/name: "Hantu/Pocong: ..." or "Manusia/Penjual: ...". No narration inside dialogue.
- ROLE LOGIC IS MANDATORY: the supernatural character owns supernatural motivations and actions. If the line says it has haunted ten houses, is asking for subscribers, is scared of its own ghostly reflection, or is complaining about zero subscribers, that line MUST be spoken by Hantu/Pocong, NEVER by the human. The human can question, react, tease, or respond, but must not inherit the ghost's first-person experience.
- Never use ambiguous labels like "Karakter", "Manusia + Hantu Lokal", "Mereka", or "Voice" as a speaker. Use one exact role per spoken line.
- Speaker identity is strict: the named character is the only character who speaks that line. Keep one speaker per beat where possible. If two lines occur, place them in separate timed shots and never overlap them.
- In the visual field, explicitly name the active speaker, camera framing, mouth movement, and silent listener with mouth CLOSED. Prefer a separate single-character shot for every line to improve lip-sync reliability.
- Make a short, coherent mini-story: opening incident → specific reaction → escalating physical complication → surprising punchline → CTA that belongs to the joke → loop cue.
- Derive the hook, props, conflict, twist, dialogue, and CTA from the selected title and premise. Do not switch concepts or inject unrelated characters/locations.
- Include concrete props and movements, not just emotions. Avoid abstract statements.
- Fit all beats within 0–{duration}s with no gaps or overlaps. Use enough beats to cover the complete duration; for durations over 10 seconds, add new escalating actions, not stretched empty beats. Never let a beat end after {duration}.
- The last beat must include an explicit, natural invitation to SUBSCRIBE to the channel and press LIKE, with a funny reason tied to this exact story. Also make the last visual/action connect to the opening so replay feels natural. Do not threaten, guilt-trip, or promise rewards.
- CTA structure: story callback → funny punch → explicit subscribe + like → specific replay/loop cue. Do not use the same generic CTA for every title.
- For Indonesia Lokal, all titles, premises, descriptions, and dialogue must be natural Bahasa Indonesia. Spoken dialogue must be entirely Indonesian, except proper names. Never turn visual instructions into dialogue. For Global Skeleton, use English. For Lokal + Global, return distinct Indonesian and English versions, not mixed dialogue.
- Keep spoken lines short enough to fit their beat naturally. Do not cram several sentences into a 1-second beat.
- Preserve selected title exactly: {idea.get('title','')}.
{realism_rules(cfg['mode'])}
"""

def demo_story(cfg, idea, hook):
    """Coherent settings-aware fallback with real dialogue, not abstract placeholder text."""
    title = str(idea.get("title", "Ide pilihan")).strip()
    premise = str(idea.get("premise", "")).strip()
    conflict = str(idea.get("conflict", "")).strip()
    twist = str(idea.get("twist", "")).strip()
    series = str(idea.get("series_potential", "Cerita ini bisa berlanjut di episode berikutnya.")).strip()
    selected_hook_text = str(hook.get("hook", idea.get("hook", "Lho, kok bisa begini?!"))).strip()
    selected_hook_visual = str(hook.get("visual", idea.get("hook", premise))).strip()
    is_local = cfg.get("mode") == "Indonesia Lokal"
    total = max(10, int(cfg.get("duration", 20)))
    character = str(cfg.get("character", "Karakter utama"))
    setting = str(cfg.get("setting", "lokasi cerita"))
    topic = str(cfg.get("subtheme", premise or title)).strip()
    low = (title + " " + topic + " " + premise).lower()

    # A concrete example pattern for the common ghost/subscriber comedy concept.
    ghost_subscribe = is_local and any(k in low for k in ["hantu", "pocong", "kuntilanak", "tuyul", "makhluk halus"]) and any(k in low for k in ["subscribe", "subscriber", "channel", "youtube", "nonton"])
    if ghost_subscribe:
        scene = f"Di {setting}, malam hari. {character} berdiri di dekat meja/etalase. Hantu menyodorkan ponsel yang menampilkan halaman channel tanpa tulisan tambahan yang terbaca."
        hook_dialogue = "Hantu: Bang, subscribe channel saya sekarang!"
        context_visual = f"Penjaga {setting} mundur setengah langkah; hantu tetap menyodorkan ponsel dengan wajah sangat serius."
        context_action = "Hantu mengetuk layar ponsel tiga kali; penjaga melihat ponsel lalu menatap hantu dari kepala sampai kaki."
        context_dialogue = "Manusia: Lho, kamu hantu apa YouTuber?"
        conflict_visual = "Hantu menunjukkan ponselnya dengan angka subscriber nol; kain kafannya tersangkut di sudut meja saat ia berusaha mendekat."
        conflict_action = "Hantu menarik kainnya, membuat sendok dan gelas di meja bergetar; ia tetap berusaha menyodorkan ponsel."
        conflict_dialogue = "Hantu: Saya sudah menghantui sepuluh rumah, Bang. Yang nonton banyak, yang subscribe nggak ada!"
        escalation_visual = "Penjaga menunjuk tombol ponsel, tetapi hantu salah menekan tombol senter dan wajahnya sendiri tersorot dari bawah."
        escalation_action = "Senter menyala ke wajah hantu; ia kaget melihat bayangannya sendiri di kaca etalase lalu menjerit kecil."
        escalation_dialogue = "Manusia: Pantesan gagal, Bang. Kamu sendiri aja kaget lihat muka sendiri!"
        payoff_visual = "Hantu menatap kamera dengan muka tersinggung, mengangkat ponsel lagi persis seperti posisi pada pembukaan."
        payoff_action = "Hantu mengulang pose menyodorkan ponsel; potong tepat saat ponsel mendekati kamera agar loop kembali ke hook."
        payoff_dialogue = "Hantu: Ya sudah, pencet LIKE dan SUBSCRIBE! Tonton ulang—siapa tahu angka nolnya berubah karena kamu!"
        cta = "Pencet LIKE dan SUBSCRIBE biar channel si hantu nggak sepi. Tonton ulang—cek apakah angka nolnya berubah!"
        punchline = "Hantu lebih takut melihat bayangannya sendiri daripada ditolak subscribe."
    else:
        # Keep the selected idea as the source of truth while using actual spoken dialogue.
        hook_dialogue = selected_hook_text or f"{character}: Lho, kok {topic.lower()} malah begini?!"
        scene = f"Di {setting}, {character} sedang melakukan kejadian inti dari ide '{title}'. Tampilkan properti yang paling relevan dengan premis: {premise}."
        context_visual = f"{character} menyadari masalah dari '{title}' dan buru-buru mencoba memperbaikinya di {setting}."
        context_action = f"Karakter memegang/menunjuk benda yang relevan dengan {topic}, lalu mencoba solusi pertama tetapi gagal secara terlihat."
        context_dialogue = f"{character}: Waduh, ini bukan bagian dari rencana!"
        conflict_visual = f"Masalah utama '{conflict}' terlihat jelas: karakter mencoba menyelesaikannya, tetapi satu tindakan justru membuat situasi lebih kacau."
        conflict_action = f"Karakter mencoba satu solusi konkret terhadap masalah: {conflict}; solusi itu memicu akibat langsung yang terlihat."
        conflict_dialogue = f"{character}: Tenang, aku bisa bereskan—eh, kok malah tambah kacau?!"
        escalation_visual = f"Akibat dari tindakan sebelumnya memperlihatkan twist '{twist}' melalui benda/reaksi yang sudah ada di adegan."
        escalation_action = f"Karakter menyadari petunjuk yang mengarah ke twist '{twist}', lalu berhenti sejenak dengan ekspresi tidak percaya."
        escalation_dialogue = f"{character}: Tunggu dulu... jadi selama ini penyebabnya itu?!"
        payoff_visual = f"Close-up reaksi karakter setelah twist; karakter mengulang gerakan pembuka sehingga adegan bisa berulang secara mulus."
        payoff_action = "Karakter menoleh ke kamera, menyelesaikan lelucon, lalu kembali ke pose/gerakan pertama untuk menciptakan loop."
        payoff_dialogue = f"{character}: Kalau ending ini bikin kamu ketawa, pencet LIKE dan SUBSCRIBE! Tonton ulang—petunjuknya tadi sudah kelihatan!"
        cta = f"Pencet LIKE dan SUBSCRIBE kalau twist '{title}' bikin kamu ketawa. Tonton ulang—petunjuknya sudah muncul dari awal!"
        punchline = twist or f"Karakter sadar bahwa masalah dalam '{title}' berasal dari hal yang paling tidak disangka."

    # Build beats over the entire requested duration; no beat is stretched by changing timestamps only.
    cuts = [0, round(total*0.16), round(total*0.38), round(total*0.62), round(total*0.82), total]
    # Ensure strictly increasing timestamps for all supported durations.
    for i in range(1, len(cuts)):
        cuts[i] = max(cuts[i], cuts[i-1] + 1)
    cuts[-1] = total
    if cuts[-2] >= total:
        cuts = [0, 2, 4, 6, 8, 10] if total == 10 else [0, round(total*.15), round(total*.35), round(total*.60), round(total*.82), total]

    beats = [
        {"start":cuts[0],"end":cuts[1],"purpose":"HOOK","visual":f"{scene} {selected_hook_visual}","action":"Mulai langsung dari kejadian ganjil; tidak ada intro atau establishing shot sebelum hook.","dialogue":hook_dialogue,"sound":"SFX pendek tepat pada aksi awal, lalu suara ambience lokasi."},
        {"start":cuts[1],"end":cuts[2],"purpose":"CONTEXT","visual":context_visual,"action":context_action,"dialogue":context_dialogue,"sound":f"Ambience {setting}; dialog jelas di depan."},
        {"start":cuts[2],"end":cuts[3],"purpose":"CONFLICT","visual":conflict_visual,"action":conflict_action,"dialogue":conflict_dialogue,"sound":"SFX mengikuti benda/aksi yang menyebabkan masalah membesar."},
        {"start":cuts[3],"end":cuts[4],"purpose":"ESCALATION","visual":escalation_visual,"action":escalation_action,"dialogue":escalation_dialogue,"sound":"Musik/ketegangan singkat, berhenti sejenak sebelum punchline."},
        {"start":cuts[4],"end":cuts[5],"purpose":"PAYOFF + CTA + LOOP","visual":payoff_visual,"action":payoff_action,"dialogue":payoff_dialogue,"sound":"Sting komedi singkat; tahan reaksi lalu potong ke pose pembuka."}
    ]
    return {
        "title": title,
        "logline": premise,
        "hook": {"visual": selected_hook_visual, "dialogue": hook_dialogue, "duration_seconds": max(1, cuts[1])},
        "beats": beats,
        "punchline": punchline,
        "cta": cta,
        "return_potential": series + " Loop visual: gerakan terakhir kembali ke pose pembuka sehingga penonton dapat langsung menonton ulang.",
        "continuity_notes": [
            f"Karakter tetap sama: {character}; jangan menambah karakter baru.",
            f"Lokasi tetap: {setting}; properti hanya yang relevan dengan ide '{title}'.",
            f"Semua adegan harus menunjukkan kejadian dari '{title}' dan premis: {premise}.",
            "Aksi dan dialog harus konkret; jangan mengubah deskripsi visual menjadi dialog.",
            "Akhiri dengan pose yang menyambung ke adegan pembuka."
        ]
    }

def enforce_cta_requirements(story, cfg):
    """Ensure generated package explicitly asks for subscribe + like and invites replay."""
    title = str(story.get("title", "cerita ini"))
    cta = str(story.get("cta", "")).strip()
    text_blob = cta.lower()
    has_sub = any(term in text_blob for term in ["subscribe", "berlangganan", "subscribe channel", "ikuti channel"])
    has_like = any(term in text_blob for term in ["like", "suka", "tombol jempol"])
    has_replay = any(term in text_blob for term in ["tonton ulang", "ulang", "rewatch", "replay", "watch again"])
    is_local = cfg.get("mode") == "Indonesia Lokal"
    if not (has_sub and has_like and has_replay):
        if is_local:
            fallback = f"Kalau twist {title.lower()} bikin kamu ketawa, pencet LIKE dan SUBSCRIBE channel ini. Tonton ulang—petunjuknya muncul dari awal!"
        else:
            fallback = f"If the twist in {title} got you, hit LIKE and SUBSCRIBE to this channel. Rewatch it—the clue was there from the start!"
        cta = (cta + " " + fallback).strip() if cta else fallback
        story["cta"] = cta
    beats = story.get("beats", [])
    if beats:
        last = beats[-1]
        dialogue = str(last.get("dialogue", ""))
        low_dialogue = dialogue.lower()
        dialogue_has_sub = any(term in low_dialogue for term in ["subscribe", "berlangganan", "ikuti channel"])
        dialogue_has_like = any(term in low_dialogue for term in ["like", "suka", "tombol jempol"])
        dialogue_has_replay = any(term in low_dialogue for term in ["tonton ulang", "ulang", "rewatch", "replay", "watch again"])
        if not (dialogue_has_sub and dialogue_has_like and dialogue_has_replay):
            last["dialogue"] = (dialogue + " " + cta).strip()
        last["purpose"] = "PAYOFF + CTA WAJIB + LOOP"
    story.setdefault("return_potential", "Tonton ulang untuk menangkap petunjuk yang muncul pada adegan pembuka.")
    return story


def build_flow_prompts(cfg, story):
    """Build consecutive, timed Flow prompts directly from concrete story beats."""
    beats = story.get("beats", [])
    total = int(cfg.get("duration", 10))
    chunks = []
    for start in range(0, total, 10):
        end = min(start + 10, total)
        segment_beats = []
        for b in beats:
            try:
                bs, be = int(b.get("start", 0)), int(b.get("end", 0))
            except (TypeError, ValueError):
                continue
            if bs < end and be > start:
                # Clamp displayed beat window to this segment while retaining its actual action.
                segment_beats.append((max(bs, start), min(be, end), b))
        beat_text = []
        speaker_names = []
        for bs, be, b in segment_beats:
            dialogue = str(b.get('dialogue', '')).strip()
            # Extract explicit speaker labels such as "Pocong: ... | Penjual: ...".
            for match in re.finditer(r"(?:^|[|\n])\s*([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 _-]{0,35})\s*:", dialogue):
                name = match.group(1).strip()
                if name and name.lower() not in {n.lower() for n in speaker_names}:
                    speaker_names.append(name)
            beat_text.append(
                f"{bs}–{be}s | {b.get('purpose', 'STORY ACTION')}\n"
                f"VISUAL: {b.get('visual', '')}\n"
                f"PHYSICAL ACTION: {b.get('action', '')}\n"
                f"EXACT SPOKEN DIALOGUE (speaker label is binding): {dialogue}\n"
                f"SOUND: {b.get('sound', '')}"
            )
        speaker_lock = "\n".join(f"- {name}: only this character may speak the line(s) labeled '{name}:'." for name in speaker_names)
        if not speaker_lock:
            speaker_lock = "- Follow the speaker name explicitly written before every spoken line. If no speaker is named, do not invent dialogue; use silent acting only."
        prompt = f"""GOOGLE FLOW VIDEO PROMPT — SEGMENT {len(chunks)+1}
TOTAL VIDEO TITLE: {story.get('title', '')}
SEGMENT DURATION: exactly {end-start} seconds
OVERALL TIMELINE: {start}–{end} seconds of a {total}-second video
FORMAT: vertical 9:16, cinematic photorealistic live-action / highly realistic CGI.

VISUAL RULES — MANDATORY:
- Photorealistic live-action or highly realistic cinematic CGI with believable natural materials and anatomy.
- NOT cartoon, NOT Pixar, NOT anime, NOT illustration, NOT plastic toy, NOT flat 2D.
- Use specific camera framing, visible physical actions, facial reactions, props and spatial positions.
- Maintain identical character identity, face/body, clothing, props, location, lighting and screen direction throughout.
- No subtitles, captions, logos, watermarks, or extra text in the image.

STORY CONTINUITY:
Title: {story.get('title', '')}
Premise: {story.get('logline', '')}
Characters: {cfg.get('character', '')}
Location: {cfg.get('setting', '')}
Selected subtheme: {cfg.get('subtheme', '')}

EXACT TIMED SCENES — FILM THESE ACTIONS, DO NOT SUMMARIZE THEM:
{chr(10).join(beat_text) if beat_text else 'Continue the selected story with a concrete physical action consistent with the established plot.'}

AUDIO / LANGUAGE / SPEAKER LOCK — CRITICAL:
SPEAKER OWNERSHIP OVERRIDES CAMERA CONVENIENCE. Do not assign dialogue to whoever is closest to camera. The role label before each line determines the speaker absolutely.
Use only the exact spoken lines written under EXACT SPOKEN DIALOGUE. Speak them naturally with the selected channel language: {cfg['mode']}.
For Indonesia Lokal, all audible dialogue MUST be natural Bahasa Indonesia. Do not translate, paraphrase, invent extra dialogue, or speak any English. Visual direction may be English, but speech stays Indonesian.
SPEAKER ASSIGNMENTS FOR THIS SEGMENT:
{speaker_lock}
- The name before the colon is the ONLY speaker for that line. Never transfer a line to another character.
- When HANTU/POCONG speaks, show the ghost as the active speaker; animate only the ghost's mouth. Human characters keep their mouths closed and react silently.
- When MANUSIA/PENJUAL speaks, show the human as the active speaker; animate only the human's mouth. Ghost characters keep their mouths closed and react silently.
- Never let two characters speak simultaneously. One line/one speaker at a time.
- EACH DIALOGUE LINE MUST BE ITS OWN SINGLE-SPEAKER SHOT: show only the named speaker's face/mouth while the line is spoken, or show the named speaker clearly foregrounded with the listener silent and mouth fully closed. Do not frame both faces equally during dialogue.
- For a line labeled Hantu/Pocong, camera must show the Hantu/Pocong speaking; the human is silent. For a line labeled Manusia/Penjual, camera must show the human speaking; the ghost is silent.
- Match voice identity to the character consistently across every scene. The ghost has its own distinct voice; the human has a different voice. No off-screen voice assigned to the wrong visible character.
- If correct lip-sync cannot be maintained in a two-character shot, use a separate single-speaker shot for each line while preserving geography and continuity.
- Do not add voice-over, narrator, extra dialogue, or vocal sounds that could be mistaken for another character speaking.
- If a line's assigned speaker cannot be shown clearly, keep the listener off-screen rather than showing the listener's mouth moving.
- NEVER make the human say a ghost's first-person line such as "Saya sudah menghantui sepuluh rumah" or "subscriber saya nol". Those lines belong to Hantu/Pocong only.

SEGMENT RULES:
- Show only events occurring from {start} to {end} seconds. Never exceed the segment duration.
- Segment 2 onward continues the previous segment at the exact physical pose, props, location, lighting, and camera direction; do not restart the story.
- No vague filler such as “the conflict gets harder”; show the concrete actions above.
- Keep the hook/dialogue unobstructed. Any cutaway must be brief and return to the same action.
- End on the specified action/pose so the next segment can continue seamlessly."
"""
        chunks.append({"segment": len(chunks)+1, "start": start, "end": end, "prompt": prompt})
    return chunks

def embed_broll_into_flow(flow_prompts, broll, story):
    """Insert each story-specific cutaway at its requested timestamp inside the matching Flow segment."""
    if not flow_prompts or not broll:
        return flow_prompts
    total = max(1, max(int(seg.get("end", 0)) for seg in flow_prompts))
    for seg in flow_prompts:
        start, end = int(seg.get("start", 0)), int(seg.get("end", 0))
        lines, included = [], []
        for idx, shot in enumerate(broll):
            try:
                shot_start = int(shot.get("start", round((idx + 0.5) * total / max(1, len(broll)))))
                shot_duration = max(1, min(2, int(shot.get("duration_seconds", 2))))
            except (TypeError, ValueError):
                shot_start, shot_duration = round((idx + 0.5) * total / max(1, len(broll))), 2
            shot_end = min(total, shot_start + shot_duration)
            # Include only cutaways belonging to this segment; clip at segment boundary.
            if shot_start >= end or shot_end <= start:
                continue
            clip_start, clip_end = max(start, shot_start), min(end, shot_end)
            lines.append(
                f"CUTAWAY {clip_start}–{clip_end}s ({shot.get('type', 'B-roll')}): "
                f"{shot.get('prompt', '')} Purpose: {shot.get('purpose', '')}."
            )
            included.append(shot)
        if not lines:
            continue
        seg["prompt"] = seg.get("prompt", "") + (
            "\n\nINTEGRATED B-ROLL / CUTAWAYS — insert these brief shots inside the same continuous story, "
            "not as an unrelated montage:\n" + "\n".join("- " + line for line in lines) +
            "\nEDITING: use each cutaway only at its specified time for 1–2 seconds, then return to the exact main action. "
            "Do not cover key dialogue. Preserve character, prop, location, lighting and screen direction. Do not add text."
        )
        seg["integrated_broll"] = included
    return flow_prompts


def make_broll_prompt(cfg, story):
    return f"""
Create exactly 5 brief B-roll/cutaway instructions that can be INSERTED INTO the same short video, not a separate unrelated montage.
Return valid JSON only: {{"broll":[{{"type":"...","start":0,"duration_seconds":1,"prompt":"...","purpose":"..."}},...]}}
TITLE: {story.get('title', '')}
LOGLINE: {story.get('logline', '')}
STORY BEATS: {json.dumps(story.get('beats', []), ensure_ascii=False)}
CHARACTERS: {cfg['character']}; LOCATION: {cfg['setting']}; SUBTHEME: {cfg['subtheme']}; TOTAL DURATION: {cfg['duration']} seconds.

Rules:
- Every cutaway must refer to a real character, prop, or action explicitly present in the story beats. Never invent a new plot or unrelated visual.
- Use: (1) establishing detail that directly matches the location/action, (2) key prop close-up, (3) reaction close-up, (4) escalating action detail, (5) punchline reaction/loop detail.
- Assign each shot a valid start time inside 0–{max(1, int(cfg['duration'])-1)} seconds; keep duration 1–2 seconds. Do not overlap the most important spoken dialogue.
- Describe exactly what the camera sees; avoid generic wording like “character reacting to the problem”.
- Same character identity, clothing, props, location, lighting and photorealistic style. Vertical 9:16, no text/logos/watermarks.
- Keep visual direction concise and filmable. {cfg['language']}
"""


def demo_broll(cfg, story):
    """Produce story-specific cutaways from the actual beat descriptions, with deterministic timing."""
    beats = story.get("beats", []) or []
    total = max(1, int(cfg.get("duration", 10)))
    selected = []
    # Choose concrete beat moments, prioritizing hook, conflict, escalation, and payoff.
    priorities = ["HOOK", "CONFLICT", "ESCALATION", "PAYOFF", "CTA"]
    used = set()
    for priority in priorities:
        match = next((b for b in beats if priority in str(b.get("purpose", "")).upper() and id(b) not in used), None)
        if match:
            used.add(id(match))
            selected.append(match)
    for b in beats:
        if len(selected) >= 5:
            break
        if id(b) not in used:
            selected.append(b)
            used.add(id(b))
    selected = selected[:5]
    types = ["Opening action detail", "Key prop close-up", "Conflict escalation", "Character reaction", "Punchline / loop detail"]
    result = []
    for i, beat in enumerate(selected):
        try:
            start = int(beat.get("start", round(i * total / max(1, len(selected)))))
        except (TypeError, ValueError):
            start = round(i * total / max(1, len(selected)))
        start = max(0, min(total - 1, start))
        visual = str(beat.get("visual", "")).strip()
        action = str(beat.get("action", "")).strip()
        dialogue = str(beat.get("dialogue", "")).strip()
        result.append({
            "type": types[i], "start": start, "duration_seconds": 1 if total <= 15 else 2,
            "purpose": f"Mendukung beat {beat.get('purpose', 'cerita')} pada {start}s; tidak menutupi dialog penting.",
            "prompt": f"At {start}s, insert a brief photorealistic vertical cutaway from the SAME scene: {visual} Show this concrete action/detail: {action}. Preserve exact characters, props and location. Return to the main action immediately; no new plot, no text. Spoken dialogue remains unchanged: {dialogue}"
        })
    return {"broll": result}

# ----------------------------- SIDEBAR -----------------------------
with st.sidebar:
    st.header("⚙️ Pengaturan Studio")
    api_key = st.text_input("ClarioHub API Key", type="password", help="Masukkan API key ClarioHub (format biasanya sk-clario-...). Jangan bagikan key.")
    model_options = ["clario/deepseek-v4-flash", "clario/deepseek-v4-pro", "clario/deepseek-v4.1-flash", "clario/glm-5.3-flash", "clario/glm-5.3", "clario/gemini-3.7-flash", "clario/gpt-5.6-sol", "clario/hy3", "clario/hy4-preview", "clario/minimax-m3", "clario/opus-5"]
    model = st.selectbox("Model ClarioHub", model_options, index=0, help="Gunakan ID model yang tersedia untuk key standard di katalog ClarioHub.")
    st.caption("API: https://clariohub.id/v1/chat/completions · Tanpa key, aplikasi memakai mode demo.")
    st.divider()
    st.selectbox("Mode channel", ["Global Skeleton", "Indonesia Lokal", "Lokal + Global"], key="mode")
    themes = {
        "Global Skeleton": ["Absurd Comedy", "Horror Comedy", "Gym & Fitness", "Relationship Comedy", "Work & Money", "Gaming Comedy", "Survival Comedy", "Sci-Fi Comedy", "Everyday Life"],
        "Indonesia Lokal": ["Komedi Horor", "Kehidupan Anak Kos", "Komedi Tongkrongan", "Keluarga", "Pekerjaan & Uang", "Mitos Lokal", "Kehidupan Sehari-hari"],
        "Lokal + Global": ["Absurd Comedy", "Komedi Horor", "Everyday Life", "Work & Money", "Relationship Comedy", "Kehidupan Anak Kos", "Survival Comedy"]
    }
    subthemes = {
        "Global Skeleton": {
            "Absurd Comedy": ["Everyday disaster", "Impossible job interview", "Broken bones problem", "Awkward public moment"],
            "Horror Comedy": ["Haunted apartment", "Ghost roommate", "Cursed elevator", "Monster with a day job"],
            "Gym & Fitness": ["First day at gym", "Broken workout equipment", "Overconfident trainer", "Fitness challenge disaster"],
            "Relationship Comedy": ["Awkward first date", "Jealous skeleton", "Text message misunderstanding", "Breakup gone wrong"],
            "Work & Money": ["First day at work", "Rent is due", "Boss from hell", "Broke before payday"],
            "Gaming Comedy": ["Rage quit", "Noob versus pro", "Game bug in real life", "Impossible boss fight"],
            "Survival Comedy": ["Lost in the woods", "Survive one night", "Disaster camping trip", "Wrong survival tip"],
            "Sci-Fi Comedy": ["Alien roommate", "Time travel mistake", "Robot takes over chores", "Portal delivery disaster"],
            "Everyday Life": ["Morning disaster", "Grocery store chaos", "Public transport problem", "Neighbor drama"]
        },
        "Indonesia Lokal": {
            "Komedi Horor": ["Pocong nagih uang kos", "Kuntilanak salah kamar", "Hantu anak kos", "Jin jadi satpam", "Hantu minta subscribe"],
            "Kehidupan Anak Kos": ["Uang kos habis", "Teman kos pelit", "Listrik mati tengah malam", "Mie instan terakhir", "Pemilik kos menagih"],
            "Komedi Tongkrongan": ["Teman sok kaya", "Traktiran palsu", "Utang warung", "Salah kirim chat", "Teman datang cuma saat butuh"],
            "Keluarga": ["Anak ketahuan bohong", "Drama uang belanja", "Ayah salah paham", "Ibu punya jurus rahasia", "Rebutan remote TV"],
            "Pekerjaan & Uang": ["Gaji baru masuk langsung habis", "Bos banyak mau", "Telat gajian", "Pelanggan banyak tingkah", "Cari kerja malah apes"],
            "Mitos Lokal": ["Penunggu pohon ikut ronda", "Jin salah alamat", "Benda keramat hilang", "Suara misterius dari dapur", "Hantu takut manusia"],
            "Kehidupan Sehari-hari": ["Salah naik kendaraan", "Antrean tidak bergerak", "Paket tertukar", "Tetangga kepo", "Warung kehabisan kembalian"]
        },
        "Lokal + Global": {
            "Absurd Comedy": ["Everyday disaster", "Impossible situation", "Awkward public moment"],
            "Komedi Horor": ["Pocong nagih uang kos", "Hantu minta subscribe", "Kuntilanak salah kamar"],
            "Everyday Life": ["Morning disaster", "Grocery store chaos", "Neighbor drama"],
            "Work & Money": ["First day at work", "Rent is due", "Broke before payday"],
            "Relationship Comedy": ["Awkward first date", "Text message misunderstanding", "Breakup gone wrong"],
            "Kehidupan Anak Kos": ["Uang kos habis", "Teman kos pelit", "Listrik mati tengah malam"],
            "Survival Comedy": ["Lost in the woods", "Disaster camping trip", "Wrong survival tip"]
        }
    }
    mode = st.session_state.mode
    theme_options = themes[mode]
    if st.session_state.get("theme") not in theme_options:
        st.session_state.theme = theme_options[0]
    st.selectbox("Tema", theme_options, key="theme")
    active_subthemes = subthemes[mode].get(st.session_state.theme, ["Kejadian absurd", "Masalah sehari-hari"])
    custom_option = "✍️ Tulis subtema sendiri..."
    subtheme_options = active_subthemes + [custom_option]

    # Custom text has its own state. Never copy the current subtheme back into
    # the text input on every Streamlit rerun, or the user's typing gets overwritten.
    if "subtheme_custom_value" not in st.session_state:
        st.session_state.subtheme_custom_value = ""
    if st.session_state.get("subtheme_choice") not in subtheme_options:
        previous_subtheme = st.session_state.get("subtheme", "")
        if previous_subtheme in active_subthemes:
            st.session_state.subtheme_choice = previous_subtheme
        else:
            st.session_state.subtheme_choice = active_subthemes[0]

    chosen_subtheme = st.selectbox(
        "Subtema", subtheme_options, key="subtheme_choice",
        help="Pilih subtema yang tersedia atau pilih 'Tulis subtema sendiri'."
    )
    if chosen_subtheme == custom_option:
        custom_subtheme = st.text_area(
            "Tulis subtema sendiri",
            key="subtheme_custom_value",
            placeholder="Contoh: Pocong, kuntilanak, dan tuyul pergi ke pasar malam untuk naik bom-bom car",
            height=100,
            help="Teks ini akan dipakai sebagai inti cerita. Setelah mengetik, lanjutkan ke tombol Generate Ide."
        ).strip()
        st.session_state.subtheme = custom_subtheme
        if custom_subtheme:
            st.caption("✅ Subtema khusus tersimpan untuk sesi ini.")
        else:
            st.caption("Tulis subtema di atas sebelum menekan Generate Ide.")
    else:
        st.session_state.subtheme = chosen_subtheme

    if mode == "Indonesia Lokal":
        character_options = ["Pocong", "Kuntilanak", "Genderuwo", "Jin", "Manusia + Hantu Lokal"]
        base_setting_options = ["Pasar malam", "Taman hiburan", "Kos-kosan Indonesia", "Warung pinggir jalan", "Kampung malam hari", "Rumah tua Indonesia", "Pos ronda", "Kantor Indonesia", "Sekolah", "Pantai", "Hutan"]
        audience_options = ["Umum", "Remaja dan dewasa", "Ramah keluarga"]
        humor_options = ["Komedi absurd cepat", "Komedi deadpan", "Komedi horor", "Komedi keseharian"]
    elif mode == "Global Skeleton":
        character_options = ["Overconfident Skeleton", "Realistic Skeleton", "Ghost roommate", "Human + supernatural character"]
        base_setting_options = ["Amusement park", "Night market", "Small apartment", "Modern gym", "Office", "Supermarket", "Suburban street", "Hospital", "Beach", "Forest"]
        audience_options = ["General audience", "Teens and adults", "Family-friendly"]
        humor_options = ["Absurd, fast-paced, visual", "Deadpan comedy", "Horror-comedy", "Relatable everyday comedy"]
    else:
        character_options = ["Realistic Skeleton", "Overconfident Skeleton", "Pocong", "Kuntilanak", "Human + supernatural character"]
        base_setting_options = ["Pasar malam", "Night market", "Amusement park", "Apartment", "Kos-kosan Indonesia", "Warung", "Office", "Old house", "Beach", "Forest"]
        audience_options = ["General audience", "Remaja dan dewasa", "Family-friendly"]
        humor_options = ["Absurd comedy", "Komedi horor", "Deadpan comedy", "Relatable everyday comedy"]

    # Add context-matched locations when the custom subtheme mentions a specific place.
    subtheme_text = str(st.session_state.get("subtheme", "")).lower()
    contextual_locations = []
    context_rules = [
        (("pasar malam", "bom-bom", "bombom", "komidi putar", "bianglala"), "Pasar malam" if mode != "Global Skeleton" else "Night market"),
        (("pantai", "laut", "ombak"), "Pantai" if mode != "Global Skeleton" else "Beach"),
        (("hutan", "pohon", "kemah", "camping"), "Hutan" if mode != "Global Skeleton" else "Forest"),
        (("warung", "nasi goreng", "arom manis", "arum manis"), "Warung pinggir jalan" if mode == "Indonesia Lokal" else ("Warung" if mode == "Lokal + Global" else "Food stall")),
        (("kos", "uang kos", "kamar kos"), "Kos-kosan Indonesia" if mode != "Global Skeleton" else "Small apartment"),
        (("kantor", "bos", "rapat"), "Kantor Indonesia" if mode == "Indonesia Lokal" else ("Office" if mode == "Global Skeleton" else "Office")),
    ]
    for keywords, location in context_rules:
        if any(word in subtheme_text for word in keywords):
            contextual_locations.append(location)
    setting_options = list(dict.fromkeys(contextual_locations + base_setting_options))
    custom_location_option = "✍️ Tulis lokasi sendiri..."
    setting_options.append(custom_location_option)

    # When the subtheme changes, suggest a matching location rather than keeping an unrelated default.
    previous_setting_subtheme = st.session_state.get("last_setting_subtheme")
    if previous_setting_subtheme != st.session_state.get("subtheme") and contextual_locations:
        st.session_state.setting_choice = contextual_locations[0]
        st.session_state.setting = contextual_locations[0]
    st.session_state.last_setting_subtheme = st.session_state.get("subtheme", "")

    if st.session_state.get("character") not in character_options:
        st.session_state.character = character_options[0]
    if st.session_state.get("setting_choice") not in setting_options:
        old_setting = st.session_state.get("setting", "")
        st.session_state.setting_choice = old_setting if old_setting in setting_options else (contextual_locations[0] if contextual_locations else base_setting_options[0])
    if "setting_custom_value" not in st.session_state:
        st.session_state.setting_custom_value = ""

    st.selectbox("Karakter utama", character_options, key="character")
    chosen_setting = st.selectbox(
        "Lokasi utama", setting_options, key="setting_choice",
        help="Lokasi otomatis menyarankan tempat yang cocok dengan subtema. Pilih 'Tulis lokasi sendiri' untuk tempat lain."
    )
    if chosen_setting == custom_location_option:
        custom_setting = st.text_input(
            "Tulis lokasi sendiri", key="setting_custom_value",
            placeholder="Contoh: pasar malam yang ramai dengan wahana bom-bom car",
            help="Lokasi ini akan dipakai sebagai latar utama prompt cerita dan visual."
        ).strip()
        st.session_state.setting = custom_setting or "Lokasi sesuai subtema (belum diisi)"
        if custom_setting:
            st.caption("✅ Lokasi khusus tersimpan untuk sesi ini.")
        else:
            st.caption("Tulis lokasi yang sesuai sebelum menekan Generate.")
    else:
        st.session_state.setting = chosen_setting
    st.selectbox("Target penonton", audience_options, key="audience")
    st.selectbox("Gaya humor", humor_options, key="humor")
    st.selectbox("Tujuan video", ["Subscriber growth", "Views / reach", "Comments / discussion", "Shares", "Return viewers / series"], key="goal")
    st.selectbox("Durasi total (detik)", [10, 15, 20, 30, 40, 60], key="duration")
    st.selectbox("Gaya visual", ["Photorealistic live-action", "Realistic cinematic", "Realistic cinematic CGI"], key="style")
    st.caption("Pilih subtema siap pakai atau tulis subtema sendiri. Visual video diarahkan realistis — bukan kartun.")

ensure_current()
cfg = current_config()

# ----------------------------- HEADER -----------------------------
st.markdown(f"""
<div class="hero">
  <h1>💀 {APP_NAME}</h1>
  <p><b>KLIK → BERTAHAN → KEMBALI</b> · Atur sekali, pilih judul, lalu hasilkan paket konten lengkap.</p>
  <span class="pill">Hook otomatis</span><span class="pill">CTA menyatu dengan punchline</span>
  <span class="pill">Prompt Flow</span><span class="pill">B-roll otomatis</span>
</div>
""", unsafe_allow_html=True)

st.caption("Alur singkat: atur mode, tema, subtema, karakter, lokasi, dan durasi di panel pengaturan → Generate Ide → pilih judul → Generate Paket Lengkap.")
if not api_key.strip():
    st.warning("MODE DEMO AKTIF: tanpa API key ClarioHub, aplikasi tidak memanggil AI. Ide demo kini mengikuti subtema/karakter/lokasi yang dipilih, tetapi untuk ide dan cerita yang benar-benar baru setiap kali generate, isi API key ClarioHub di panel pengaturan.")

# ----------------------------- STEP 1: IDEAS -----------------------------
st.header("1. 💡 Pilih ide video")
col_a, col_b = st.columns([1, 3])
with col_a:
    idea_count = st.selectbox("Jumlah ide", [5, 8, 10], index=0)
with col_b:
    if st.button("🚀 Generate Ide", type="primary", use_container_width=True):
        clear_from("ideas")
        with st.spinner("Mencari ide yang cocok dengan tema dan subtema..."):
            try:
                result = ai_or_demo(make_ideas_prompt(cfg, idea_count), api_key, model,
                                    lambda: demo_ideas(cfg, idea_count), temperature=0.9)
                raw_ideas = result.get("ideas", [])
                # Normalize and remove duplicate/near-identical titles; preserve distinct plot angles.
                unique_ideas = []
                seen_titles = set()
                seen_premises = set()
                for idea in raw_ideas:
                    if not isinstance(idea, dict):
                        continue
                    title = re.sub(r"\s+", " ", str(idea.get("title", "")).strip())
                    premise = re.sub(r"\s+", " ", str(idea.get("premise", "")).strip())
                    title_key = re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()
                    premise_key = re.sub(r"[^a-z0-9]+", " ", premise.lower()).strip()
                    if not title or title_key in seen_titles or (premise_key and premise_key in seen_premises):
                        continue
                    idea["title"] = title
                    unique_ideas.append(idea)
                    seen_titles.add(title_key)
                    if premise_key:
                        seen_premises.add(premise_key)
                st.session_state.ideas = unique_ideas
                st.session_state.selected_idea = {}
                st.session_state.selected_title = ""
                st.session_state.chosen_idea_title = str(st.session_state.ideas[0].get("title", "")) if st.session_state.ideas else ""
                st.session_state.story = {}
                st.session_state.flow_prompts = []
                st.session_state.broll = []
                if not st.session_state.ideas:
                    raise ValueError("Ide tidak berhasil dibuat. Coba lagi.")
            except Exception as e:
                st.error(str(e))

if st.session_state.ideas:
    titles = [str(i.get("title", f"Ide {n+1}")) for n, i in enumerate(st.session_state.ideas)]
    selected_title = st.selectbox("Pilih judul yang ingin dikembangkan", titles, key="chosen_idea_title")
    selected_idea = next((i for i in st.session_state.ideas if str(i.get("title", "")) == selected_title), st.session_state.ideas[0])
    st.session_state.selected_idea = selected_idea
    st.session_state.selected_title = selected_title
    st.markdown(f"### {selected_title}")
    st.write(selected_idea.get("premise", ""))
    with st.expander("Lihat konflik, twist, dan potensi serial"):
        st.markdown("**Konflik**")
        st.write(selected_idea.get("conflict", ""))
        st.markdown("**Twist / payoff**")
        st.write(selected_idea.get("twist", ""))
        st.markdown("**Potensi serial**")
        st.write(selected_idea.get("series_potential", ""))

    # One action generates the full production package; hook selection is automatic.
    if st.button("🎬 GENERATE PAKET LENGKAP", type="primary", use_container_width=True):
        st.session_state.story = {}
        st.session_state.flow_prompts = []
        st.session_state.broll = []
        st.session_state.continuity_frame_bytes = None
        st.session_state.continuity_video_name = ""
        st.session_state.continuity_prompt_ready = False
        st.session_state.hooks = []
        st.session_state.selected_hook = ""
        try:
            with st.spinner("1/4 Membuat hook terkuat yang sesuai judul..."):
                hook_result = ai_or_demo(
                    make_hooks_prompt(cfg, selected_idea), api_key, model,
                    lambda: demo_hooks(cfg, selected_idea), temperature=0.9)
                hooks = hook_result.get("hooks", [])
                if not hooks:
                    raise ValueError("Hook otomatis tidak berhasil dibuat.")
                # First hook is required to be strongest by prompt; no manual hook selection.
                hook_obj = hooks[0]
                st.session_state.hooks = hooks
                st.session_state.selected_hook = hook_obj.get("hook", "")
            with st.spinner("2/4 Merangkai cerita, twist, CTA, dan loop... "):
                story = ai_or_demo(
                    make_story_prompt(cfg, selected_idea, hook_obj), api_key, model,
                    lambda: demo_story(cfg, selected_idea, hook_obj), temperature=0.85)
                story["title"] = selected_idea.get("title", selected_title)
                story["hook"] = story.get("hook") or {
                    "visual": hook_obj.get("visual", ""),
                    "dialogue": hook_obj.get("hook", ""),
                    "duration_seconds": 2,
                }
                story["automatic_hook_strength"] = hook_obj.get("strength", "Hook dipilih otomatis dari ide terpilih.")
                story = enforce_cta_requirements(story, cfg)
                st.session_state.story = story
            with st.spinner("3/4 Menyusun prompt Flow dari adegan dan dialog cerita yang sudah ditetapkan... "):
                # Build from the canonical story beats instead of asking the model to invent a second timeline.
                # This prevents timeline drift, abstract placeholder dialogue, and language mismatch.
                st.session_state.flow_prompts = build_flow_prompts(cfg, story)
            with st.spinner("4/4 Membuat B-roll yang cocok dengan cerita... "):
                if api_key:
                    broll_result = clariohub_generate(make_broll_prompt(cfg, story), api_key, model, 0.7)
                else:
                    broll_result = demo_broll(cfg, story)
                st.session_state.broll = broll_result.get("broll", [])
                # B-roll is automatically embedded into the corresponding Flow prompts,
                # while remaining separately visible for optional manual editing.
                st.session_state.flow_prompts = embed_broll_into_flow(
                    st.session_state.flow_prompts, st.session_state.broll, story
                )
            st.success("Paket selesai: hook, CTA, prompt Flow, dan B-roll terintegrasi otomatis sesuai judul serta cerita.")
        except Exception as e:
            st.error(f"Paket belum selesai: {e}")

# ----------------------------- FULL PACKAGE OUTPUT -----------------------------
if st.session_state.story:
    story = st.session_state.story
    st.divider()
    st.header("2. 🎬 Hasil paket lengkap")
    st.subheader(story.get("title", "Cerita"))
    st.markdown("#### 🧲 KLIK — Hook otomatis")
    hook_data = story.get("hook", {})
    st.success(hook_data.get("dialogue", st.session_state.selected_hook))
    if hook_data.get("visual"):
        st.write("**Visual pembuka:** " + str(hook_data.get("visual")))
    if story.get("automatic_hook_strength"):
        st.caption(story["automatic_hook_strength"])

    st.markdown("#### ⏳ BERTAHAN — Alur cerita")
    st.write(story.get("logline", ""))
    beats = story.get("beats", [])
    if beats:
        st.dataframe([{
            "Waktu": f"{b.get('start','?')}–{b.get('end','?')}s",
            "Tahap": b.get("purpose", ""),
            "Visual": b.get("visual", ""),
            "Aksi": b.get("action", ""),
            "Dialog": b.get("dialogue", ""),
        } for b in beats], use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💥 Punchline")
        st.write(story.get("punchline", ""))
    with c2:
        st.markdown("#### 🧲 CTA otomatis — SUBSCRIBE + LIKE + TONTON ULANG")
        st.write(story.get("cta", ""))
    st.markdown("#### 🔁 KEMBALI — Alasan menonton ulang")
    st.write(story.get("return_potential", "Akhiri dengan pose/gerakan yang menyambung secara alami ke awal."))

    with st.expander("🎥 Prompt Google Flow + B-roll terintegrasi", expanded=True):
        for seg in st.session_state.flow_prompts:
            st.markdown(f"**SEGMENT {seg['segment']} · {seg['start']}–{seg['end']} detik**")
            st.caption("Prompt siap ditempel langsung ke Google Flow — tidak perlu download file TXT.")
            st.code(seg["prompt"], language="text")
            render_copy_prompt(seg["prompt"], f"📋 Salin Prompt Scene {seg['segment']}",
                              key=f"copy_flow_{seg['segment']}")
    # Continuity helper for multi-segment videos. This is deliberately a user-upload step:
    # Streamlit cannot fetch a generated Flow video unless the user provides the downloaded file.
    if int(cfg.get("duration", 10)) > 10 and len(st.session_state.flow_prompts) > 1:
        st.divider()
        st.subheader("🔗 Sambungkan Scene Berikutnya")
        st.caption("Setelah membuat dan mengunduh Scene 1 dari Google Flow, unggah videonya di sini. Aplikasi mengambil frame terakhir agar bisa dipakai sebagai gambar referensi Scene 2.")
        scene_numbers = list(range(1, len(st.session_state.flow_prompts)))
        uploaded_scene_number = st.selectbox(
            "Video yang kamu upload ini Scene ke-", scene_numbers, index=0,
            key="continuity_source_scene_number",
            help="Contoh: upload hasil Scene 1 untuk menyiapkan referensi Scene 2. Upload hasil Scene 2 untuk menyiapkan Scene 3."
        )
        uploaded_scene = st.file_uploader(
            "Upload video scene sebelumnya", type=["mp4", "mov", "webm", "m4v"],
            key="continuity_video_upload",
            help="Upload file video hasil download Google Flow untuk scene yang dipilih di atas."
        )
        if uploaded_scene is not None:
            current_upload_signature = f"{uploaded_scene.name}:{uploaded_scene.size}:scene{uploaded_scene_number}"
            if st.session_state.get("continuity_video_name") != current_upload_signature:
                try:
                    with st.spinner("Mengambil frame terakhir video..."):
                        frame_bytes = extract_last_video_frame(uploaded_scene.getvalue(), uploaded_scene.name)
                    st.session_state.continuity_frame_bytes = frame_bytes
                    st.session_state.continuity_video_name = current_upload_signature
                    st.session_state.continuity_prompt_ready = True
                except Exception as exc:
                    st.session_state.continuity_frame_bytes = None
                    st.session_state.continuity_prompt_ready = False
                    st.error(f"Tidak bisa mengambil frame: {exc}")
        if st.session_state.get("continuity_frame_bytes"):
            frame_bytes = st.session_state.continuity_frame_bytes
            st.success("Frame terakhir berhasil diambil. Unduh gambar ini lalu unggah ke Google Flow sebagai start frame / reference image untuk scene berikutnya, jika fitur tersebut tersedia.")
            st.image(frame_bytes, caption="Frame terakhir dari video yang diunggah", use_container_width=True)
            st.download_button(
                "🖼️ Download frame referensi PNG", frame_bytes,
                file_name=f"scene_{len(st.session_state.flow_prompts)}_last_frame.png",
                mime="image/png", use_container_width=True, key="download_continuity_frame"
            )
            next_seg = next((seg for seg in st.session_state.flow_prompts
                             if int(seg.get("segment", 0)) == int(uploaded_scene_number) + 1), None)
            if next_seg:
                continuity_note = f"""

CONTINUITY FROM USER-PROVIDED LAST FRAME — MANDATORY:
The uploaded reference image is the exact final frame of the immediately preceding scene. Treat it as the starting visual state for this segment. Preserve the same character identities, facial features, body proportions, costumes, props, prop hand positions, background layout, lighting, time of day, camera side, and screen direction. Start from the exact pose and composition shown in the reference image; continue the next physical action naturally. Do NOT recreate the opening, jump to a new location, reset character positions, or repeat prior dialogue. The story is continuing, not restarting. The reference image controls visual continuity; the timed action and dialogue in this prompt control what happens next.
"""
                next_prompt = next_seg.get("prompt", "")
                if "CONTINUITY FROM USER-PROVIDED LAST FRAME" not in next_prompt:
                    next_prompt += continuity_note
                st.markdown("**Prompt scene berikutnya dengan instruksi continuity**")
                st.code(next_prompt, language="text")
                render_copy_prompt(next_prompt, f"📋 Salin Prompt Scene {next_seg.get('segment')} + Continuity",
                                  key="copy_continuity_prompt")
            st.info("Catatan: aplikasi menyiapkan frame PNG dan prompt lanjutan. Gambar tetap perlu kamu masukkan ke Flow secara manual; ini bukan koneksi otomatis ke akun Google Flow.")

    with st.expander("🎞️ B-roll otomatis", expanded=False):
        for i, shot in enumerate(st.session_state.broll):
            st.markdown(f"**{i+1}. {shot.get('type','B-roll')} · {shot.get('duration_seconds',2)} detik**")
            st.write(shot.get("purpose", ""))
            st.code(shot.get("prompt", ""), language="text")

    export_obj = {
        "app": APP_NAME,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "config": cfg,
        "selected_idea": st.session_state.selected_idea,
        "selected_hook": story.get("hook", {}),
        "story": story,
        "flow_prompts": st.session_state.flow_prompts,
        "broll": st.session_state.broll,
    }
    export_json = json.dumps(export_obj, ensure_ascii=False, indent=2)
    export_text = [f"{APP_NAME} — {story.get('title','')}", "="*72,
                   f"MODE: {cfg['mode']} | THEME: {cfg['theme']} / {cfg['subtheme']}",
                   f"DURATION: {cfg['duration']} seconds", "", "STORY",
                   json.dumps(story, ensure_ascii=False, indent=2), "", "GOOGLE FLOW PROMPTS"]
    for seg in st.session_state.flow_prompts:
        export_text.append(f"\n--- SEGMENT {seg['segment']} ({seg['start']}–{seg['end']}s) ---\n{seg['prompt']}")
    export_text.extend(["", "B-ROLL", json.dumps(st.session_state.broll, ensure_ascii=False, indent=2)])
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📦 Download semua (TXT)", "\n".join(export_text),
                           file_name="cadas_resonance_output.txt", mime="text/plain", use_container_width=True)
    with col2:
        st.download_button("📁 Download project (JSON)", export_json,
                           file_name="cadas_resonance_project.json", mime="application/json", use_container_width=True)

with st.expander("⚙️ Petunjuk singkat"):
    st.write("1. Atur mode, tema, subtema, karakter, lokasi, durasi, dan visual di panel pengaturan.")
    st.write("2. Tekan **Generate Ide**, pilih judul, lalu tekan **Generate Paket Lengkap** satu kali.")
    st.write("3. Hook, cerita, CTA, prompt Flow, B-roll, dan file export dibuat otomatis. Untuk durasi >10 detik, unggah hasil scene sebelumnya di bagian Sambungkan Scene Berikutnya untuk mengekstrak frame referensi.")
    st.caption("Tanpa ClarioHub API key, aplikasi menggunakan demo fallback; hasilnya bukan generasi AI langsung. API key dan kuota mengikuti penyedia layanan.")
