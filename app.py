import os
import json
import re
import streamlit as st
from openai import OpenAI

st.set_page_config(page_title="Cadas Resonance Studio", page_icon="💀", layout="wide")

API_BASE = "https://clariohub.id/v1"
MODE_LOCAL = "🇮🇩 Lokal Indonesia"
MODE_GLOBAL = "🌎 Global Skeleton"

MODELS = {
    "Gemini 3.7 Flash": "clario/gemini-3.7-flash",
    "GPT 5.6 Sol": "clario/gpt-5.6-sol",
    "DeepSeek V4 Pro": "clario/deepseek-v4-pro",
    "DeepSeek V4 Flash": "clario/deepseek-v4-flash",
    "GLM 5.3 Flash": "clario/glm-5.3-flash",
}

GLOBAL_THEMES = {
    "💀 Skeleton Everyday Life": ["Skeleton at Work", "Skeleton at School", "Skeleton Roommate", "Skeleton Grocery Shopping", "Skeleton Family Problems"],
    "😂 Absurd Comedy": ["Unexpected Twist", "Awkward Moments", "Dumb Decisions", "Public Embarrassment", "Overreaction Comedy"],
    "👻 Horror Comedy": ["Haunted House", "Ghost Pranks", "Monster Problems", "Scared Skeleton", "Paranormal Roommate"],
    "🎮 Gaming Comedy": ["Rage Quit", "Noob Moments", "Gaming Addiction", "Online Game Disaster", "Toxic Teammates"],
    "❤️ Relationship Comedy": ["Awkward Dates", "Jealous Skeleton", "Breakup Problems", "Dating App Disaster", "Relationship Misunderstanding"],
    "💪 Gym & Fitness": ["Skeleton at the Gym", "Protein Obsession", "Gym Fails", "Fitness Influencer", "Personal Trainer Disaster"],
    "💰 Money & Work": ["Broke Skeleton", "Office Problems", "Payday Disaster", "Bad Boss", "Online Shopping Addiction"],
    "🍔 Food Comedy": ["Midnight Snacks", "Skeleton Cooking", "Food Addiction", "Restaurant Disaster", "Fast Food Disaster"],
    "🧪 Science & Sci-Fi": ["Alien Encounter", "Mad Experiment", "Time Travel Disaster", "Robot Problems", "Parallel Universe"],
    "🏃 Survival Comedy": ["Zombie Apocalypse", "Bad Survival Skills", "Monster Chase", "Last Person on Earth", "Disaster Preparation"],
}
LOCAL_THEMES = {
    "👻 Horor Komedi": ["Pocong Salah Alamat", "Kuntilanak Lapar", "Genderuwo Cari Kerja", "Hantu Kos", "Setan Takut Manusia"],
    "🍜 Kehidupan Sehari-hari": ["Hantu Beli Bakso", "Pocong Numpang Wi-Fi", "Hantu Pinjam Charger", "Setan Pesan Makanan Online", "Hantu Kehabisan Uang"],
    "😂 Komedi Tongkrongan": ["Teman Sok Berani", "Prank Gagal", "Utang Warung", "Ronda Tengah Malam", "Salah Paham Kocak"],
    "🏚️ Cerita Anak Kos": ["Misteri Kamar Kos", "Hantu Minta Bayar Listrik", "Mie Instan Tengah Malam", "Pintu Kos Misterius", "Penunggu Kamar Mandi"],
}
CTA_OPTIONS = ["🧠 Smart CTA Otomatis", "😂 CTA Komedi", "⏳ CTA Cliffhanger", "🏆 CTA Tantangan", "🚫 Tanpa CTA"]
VISUAL_STYLES = ["Clean cinematic 3D animation", "Cinematic 3D horror comedy", "Stylized 3D cartoon comedy", "High-detail cinematic 3D", "Absurd cinematic 3D animation"]

def get_api_key():
    try:
        value = st.secrets.get("CLARIOHUB_API_KEY", "")
        if value:
            return str(value).strip()
    except Exception:
        pass
    return os.getenv("CLARIOHUB_API_KEY", "").strip()

def call_ai(api_key, model, prompt, max_tokens=3000):
    if not api_key:
        raise RuntimeError("API Key belum tersedia. Tambahkan CLARIOHUB_API_KEY di Streamlit Cloud Secrets.")
    client = OpenAI(api_key=api_key, base_url=API_BASE, timeout=120, max_retries=1)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert short-form comedy writer and cinematic 3D director. Follow instructions. If JSON is requested, return one valid JSON object without Markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    content = response.choices[0].message.content
    if not content or not content.strip():
        raise RuntimeError("Model mengembalikan respons kosong.")
    return content.strip()

def parse_json_response(raw):
    """Parse JSON robustly, including responses wrapped in Markdown fences."""
    raw = raw.strip().lstrip("\ufeff")
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for pos, char in enumerate(raw):
        if char == "{":
            try:
                parsed, _ = decoder.raw_decode(raw[pos:])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    # Ask model to repair malformed/truncated JSON once.
    raise ValueError("JSON_INVALID:" + raw[:9000])

def ai_json(api_key, model, prompt, max_tokens=3000):
    raw = call_ai(api_key, model, prompt, max_tokens)
    try:
        return parse_json_response(raw)
    except ValueError as err:
        if not str(err).startswith("JSON_INVALID:"):
            raise
        bad_response = str(err).split("JSON_INVALID:", 1)[1]
        repair_prompt = f"""
Convert the following model response into one valid JSON object.
Preserve all useful content. Do not invent missing facts. If content is incomplete,
complete it conservatively. Return JSON only, without Markdown fences.

RESPONSE TO REPAIR:
{bad_response}
"""
        repaired = call_ai(api_key, model, repair_prompt, max_tokens)
        return parse_json_response(repaired)

def get_profile(mode):
    if mode == MODE_LOCAL:
        return {
            "language": "Bahasa Indonesia",
            "characters": "Pocong, kuntilanak, genderuwo, tuyul, anak kos, pedagang bakso, atau warga Indonesia.",
            "setting": "Gang kampung, warung bakso, kamar kos, kontrakan, pos ronda, atau pasar malam.",
            "dialogue": "Bahasa Indonesia natural dan gaul. Dialog singkat, jelas, lucu, cocok untuk penonton Indonesia.",
            "continuity": "Pertahankan desain karakter, pakaian, warna, proporsi, dan properti pada setiap shot.",
        }
    return {
        "language": "Natural conversational English",
        "characters": "A recurring expressive 3D skeleton with consistent skull, teeth, eye sockets, bone proportions, accessories, and color palette.",
        "setting": "Choose a setting that specifically matches the selected theme and subtheme.",
        "dialogue": "Natural conversational English, concise dialogue, physical comedy, and memorable punchlines.",
        "continuity": "Maintain the same skeleton design, skull shape, teeth, bone proportions, accessories, and materials across shots.",
    }

def cta_instruction(choice):
    options = {
        "🚫 Tanpa CTA": "No CTA. End on the strongest punchline.",
        "😂 CTA Komedi": "Integrate a short funny CTA into the joke only if natural. Never weaken the punchline.",
        "⏳ CTA Cliffhanger": "Use a funny unresolved ending; add a brief follow request only if a continuation makes sense.",
        "🏆 CTA Tantangan": "Add one short playful challenge related to the story.",
        "🧠 Smart CTA Otomatis": "Use an organic CTA only if it strengthens the punchline. Never add a generic CTA.",
    }
    return options.get(choice, options["🧠 Smart CTA Otomatis"])

def shot_schedule(duration):
    duration = int(duration)
    proportions = [0.15, 0.20, 0.18, 0.22, 0.25]
    lengths = [max(1, round(duration * p)) for p in proportions]
    while sum(lengths) > duration:
        valid = [i for i, n in enumerate(lengths) if n > 1]
        if not valid:
            break
        lengths[max(valid, key=lambda i: lengths[i])] -= 1
    while sum(lengths) < duration:
        lengths[-1] += 1
    labels = ["HOOK / CLOSE-UP", "REACTION SHOT", "INTEGRATED B-ROLL", "CONFLICT ESCALATION", "PUNCHLINE / FINAL REACTION"]
    shots, cursor = [], 0
    for label, length in zip(labels, lengths):
        shots.append({"start": cursor, "end": cursor + length, "label": label})
        cursor += length
    return shots

def format_schedule(shots):
    return "\n".join(f"[{s['start']:02d}s-{s['end']:02d}s] {s['label']}" for s in shots)

def generate_story(api_key, model, mode, theme, subtheme, premise, duration, cta_choice, visual_style):
    profile = get_profile(mode)
    prompt = f"""
Create one original short-form comedy story.
MODE: {mode}
LANGUAGE: {profile['language']}
THEME: {theme}
SUBTHEME: {subtheme}
DURATION: {duration} seconds
VISUAL STYLE: {visual_style}
USER IDEA: {premise.strip() or "Invent an original funny situation based on the selected subtheme."}
CHARACTERS: {profile['characters']}
SETTING: {profile['setting']}
DIALOGUE STYLE: {profile['dialogue']}
CONTINUITY: {profile['continuity']}
CTA: {cta_instruction(cta_choice)}
TIMELINE:
{format_schedule(shot_schedule(duration))}

RULES:
1. Strong visual hook in the first 0-2 seconds.
2. Clear conflict, escalating curiosity, specific punchline.
3. Dialogue must fit the target duration.
4. Keep characters and setting consistent.
5. Apply DILIHAT -> BERTAHAN -> KEMBALI: instant hook, escalation, memorable payoff,
   and a natural loop only when appropriate.
6. For comedy CTA, integrate the joke into the punchline, not a generic request.
7. Return JSON only. Use short strings and a maximum of 8 dialogue lines.
8. Ensure all JSON strings are properly escaped.

JSON schema:
{{
  "language": "...",
  "theme": "...",
  "subtheme": "...",
  "hook": "...",
  "story": "...",
  "characters": "...",
  "setting": "...",
  "dialogue": [{{"time":"00:00-00:02","speaker":"...","line":"..."}}],
  "punchline": "...",
  "ending": "...",
  "cta_note": "...",
  "hashtags": ["#Shorts", "#Comedy"]
}}
"""
    data = ai_json(api_key, model, prompt, 2500)
    defaults = {
        "language": profile["language"], "theme": theme, "subtheme": subtheme,
        "hook": "", "story": "", "characters": profile["characters"],
        "setting": profile["setting"], "dialogue": [], "punchline": "",
        "ending": "", "cta_note": "", "hashtags": ["#Shorts", "#Comedy"]
    }
    for key, value in defaults.items():
        data.setdefault(key, value)
    return data

def generate_titles(api_key, model, story_data):
    prompt = f"""
Create five catchy YouTube Shorts titles.
Language: {story_data.get('language', 'English')}
Theme: {story_data.get('theme', '')}
Subtheme: {story_data.get('subtheme', '')}
Hook: {story_data.get('hook', '')}
Story: {story_data.get('story', '')}
Punchline: {story_data.get('punchline', '')}
Rules: short, specific, memorable, match the story language, no misleading clickbait.
Return valid JSON only:
{{"titles":["Title 1","Title 2","Title 3","Title 4","Title 5"]}}
"""
    data = ai_json(api_key, model, prompt, 700)
    titles = data.get("titles", [])
    if not isinstance(titles, list) or not titles:
        raise RuntimeError("Model tidak menghasilkan pilihan judul.")
    return [str(title) for title in titles[:5]]

def generate_flow_prompt(api_key, model, story_data, mode, duration, visual_style):
    profile = get_profile(mode)
    prompt = f"""
Create a complete ready-to-copy Google Flow prompt for one coherent vertical 9:16 video.
Target duration: {duration} seconds.
Mode: {mode}
Language: {profile['language']}
Visual style: {visual_style}
Story JSON:
{json.dumps(story_data, ensure_ascii=False)}
Character continuity: {profile['continuity']}
Timeline:
{format_schedule(shot_schedule(duration))}

Include timed actions, facial expressions, camera angles and movement, cinematic lighting,
sound effects, ambience, dialogue timestamps, transitions, consistent props and geography,
and a clear final punchline. Integrate close-ups, reaction shots, detail inserts and cutaways
inside the main timeline. Do not make unrelated clips or exceed the target duration.
Return valid JSON only. Keep the prompt detailed but concise enough to avoid output truncation.

JSON:
{{
  "flow_prompt": "Complete timed Google Flow production prompt",
  "broll": [
    {{
      "timestamp": "00:02-00:03",
      "shot": "Specific insert or reaction shot",
      "camera": "Camera angle and movement",
      "lighting": "Lighting description",
      "purpose": "How this shot supports the joke"
    }}
  ]
}}
"""
    data = ai_json(api_key, model, prompt, 3000)
    data.setdefault("flow_prompt", "")
    data.setdefault("broll", [])
    return data

# UI
st.title("💀 Cadas Resonance Studio")
st.caption("Local Indonesian horror comedy + global cinematic skeleton comedy.")

with st.sidebar:
    st.header("⚙️ Pengaturan")
    mode = st.radio("Pilih mode", [MODE_LOCAL, MODE_GLOBAL])
    st.divider()
    st.subheader("🤖 Model AI")
    title_model_name = st.selectbox("Model pembuat judul", list(MODELS.keys()), index=0)
    story_model_name = st.selectbox("Model cerita dan dialog", list(MODELS.keys()), index=2)
    flow_model_name = st.selectbox("Model Google Flow", list(MODELS.keys()), index=2)
    st.caption("Semua proses memakai satu API Key ClarioHub.")
    st.divider()
    duration = st.select_slider("Durasi target video", options=[5, 8, 10, 15, 20, 30, 45, 60], value=30, format_func=lambda v: f"{v} detik")
    visual_style = st.selectbox("Gaya visual", VISUAL_STYLES)
    cta_choice = st.selectbox("Gaya CTA", CTA_OPTIONS)

theme_options = GLOBAL_THEMES if mode == MODE_GLOBAL else LOCAL_THEMES
theme = st.selectbox("🌎 Tema Global" if mode == MODE_GLOBAL else "🇮🇩 Tema Lokal", list(theme_options.keys()))
subtheme = st.selectbox("🎭 Subtema", theme_options[theme])
premise = st.text_area(
    "✍️ Ide cerita (opsional)",
    placeholder="Contoh: skeleton terlambat kerja karena tengkoraknya tertinggal..." if mode == MODE_GLOBAL else "Contoh: pocong pesan bakso tetapi lupa membawa uang...",
    height=100,
)
st.info("Pilih tema dan subtema, tentukan durasi, lalu tekan Generate.")

if "cadas_result" not in st.session_state:
    st.session_state.cadas_result = None

if st.button("🚀 GENERATE VIDEO CONCEPT", type="primary", use_container_width=True):
    api_key = get_api_key()
    if not api_key:
        st.error("API Key belum ditemukan. Tambahkan CLARIOHUB_API_KEY di Streamlit Cloud > Settings > Secrets.")
    else:
        models = {"title": MODELS[title_model_name], "story": MODELS[story_model_name], "flow": MODELS[flow_model_name]}
        try:
            with st.spinner("✍️ Membuat cerita dan dialog..."):
                story = generate_story(api_key, models["story"], mode, theme, subtheme, premise, duration, cta_choice, visual_style)
            with st.spinner("💡 Membuat pilihan judul..."):
                titles = generate_titles(api_key, models["title"], story)
            with st.spinner("🎬 Menyusun prompt Google Flow..."):
                flow = generate_flow_prompt(api_key, models["flow"], story, mode, duration, visual_style)
            st.session_state.cadas_result = {
                "mode": mode, "theme": theme, "subtheme": subtheme, "duration": duration,
                "visual_style": visual_style, "story": story, "titles": titles, "flow": flow, "models": models
            }
            st.success("Konsep video berhasil dibuat!")
        except Exception as exc:
            message = str(exc)
            if message.startswith("JSON_INVALID:"):
                message = "Respons AI bukan JSON valid setelah percobaan perbaikan. Coba model lain."
            st.error(f"Gagal membuat konten: {message}")

result = st.session_state.cadas_result
if result:
    story = result["story"]
    titles = result["titles"]
    flow = result["flow"]
    st.divider()
    st.header("📦 Hasil Generasi")
    tab_title, tab_story, tab_flow, tab_broll, tab_json = st.tabs(["📝 Judul", "📖 Cerita & Dialog", "🎬 Google Flow", "🎞️ B-Roll", "📦 Export JSON"])

    with tab_title:
        selected_title = st.radio("Pilih judul video", titles, key="selected_cadas_title")
        st.subheader("Judul terpilih")
        st.write(selected_title)
        st.download_button("⬇️ Download Judul TXT", selected_title, file_name="cadas_title.txt", mime="text/plain")

    with tab_story:
        for label, key in [("Hook", "hook"), ("Cerita", "story"), ("Karakter", "characters"), ("Setting", "setting"), ("Punchline", "punchline"), ("Ending", "ending"), ("CTA", "cta_note")]:
            st.subheader(label)
            st.write(story.get(key, ""))
        st.subheader("Dialog")
        dialogue = story.get("dialogue", [])
        if isinstance(dialogue, list):
            for item in dialogue:
                if isinstance(item, dict):
                    st.markdown(f"**[{item.get('time', '')}] {item.get('speaker', '')}:** {item.get('line', '')}")
        else:
            st.write(dialogue)
        hashtags = story.get("hashtags", [])
        st.subheader("Hashtags")
        st.write(" ".join(map(str, hashtags)) if isinstance(hashtags, list) else hashtags)
        st.download_button("⬇️ Download Cerita JSON", json.dumps(story, ensure_ascii=False, indent=2), file_name="cadas_story.json", mime="application/json")

    with tab_flow:
        flow_prompt = flow.get("flow_prompt", "")
        st.text_area("Google Flow prompt — siap disalin", value=flow_prompt, height=450)
        st.download_button("⬇️ Download Google Flow TXT", flow_prompt, file_name="google_flow_prompt.txt", mime="text/plain")
        st.caption("B-roll, kamera, pencahayaan, dialog, dan timeline diminta terintegrasi dalam satu video.")

    with tab_broll:
        items = flow.get("broll", [])
        if isinstance(items, list) and items:
            for i, item in enumerate(items, 1):
                if isinstance(item, dict):
                    with st.expander(f"🎞️ B-Roll {i}"):
                        st.write("**Waktu:**", item.get("timestamp", ""))
                        st.write("**Shot:**", item.get("shot", ""))
                        st.write("**Kamera:**", item.get("camera", ""))
                        st.write("**Lighting:**", item.get("lighting", ""))
                        st.write("**Tujuan:**", item.get("purpose", ""))
        else:
            st.info("Model tidak menghasilkan daftar B-roll terpisah. Periksa prompt Flow utama.")

    with tab_json:
        chosen = st.session_state.get("selected_cadas_title", titles[0] if titles else "")
        export = {
            "app": "Cadas Resonance Studio", "mode": result["mode"],
            "theme": result["theme"], "subtheme": result["subtheme"],
            "duration_seconds": result["duration"], "visual_style": result["visual_style"],
            "selected_title": chosen, "title_options": titles, "story": story,
            "google_flow_prompt": flow.get("flow_prompt", ""),
            "integrated_broll": flow.get("broll", []), "models": result["models"]
        }
        json_output = json.dumps(export, ensure_ascii=False, indent=2)
        st.download_button("📦 DOWNLOAD SEMUA HASIL JSON", json_output, file_name="cadas_resonance_export.json", mime="application/json", use_container_width=True)
        with st.expander("Lihat JSON"):
            st.code(json_output, language="json")
else:
    st.divider()
    st.markdown("""
    ### 💀 Cara menggunakan
    1. Pilih Local Indonesia atau Global Skeleton.
    2. Pilih tema dan subtema.
    3. Tentukan durasi, visual, dan CTA.
    4. Masukkan ide cerita jika diperlukan.
    5. Tekan **GENERATE VIDEO CONCEPT**.
    6. Periksa judul, cerita, prompt Flow, dan B-roll.
    7. Download hasil dalam format TXT atau JSON.
    """)

st.divider()
st.caption("Cadas Resonance Studio | Local Horror Comedy | Global Skeleton Comedy")
