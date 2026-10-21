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
        key = st.secrets.get("CLARIOHUB_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return os.getenv("CLARIOHUB_API_KEY", "").strip()

def call_ai(api_key, model, prompt, max_tokens=3000):
    if not api_key:
        raise RuntimeError("API Key belum tersedia. Atur CLARIOHUB_API_KEY di Streamlit Cloud Secrets.")
    client = OpenAI(api_key=api_key, base_url=API_BASE, timeout=120, max_retries=1)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an expert short-form comedy writer, cinematic 3D director, and Google Flow prompt engineer. Follow instructions carefully. When asked for JSON, return one valid JSON object. Do not use Markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=max_tokens,
    )
    result = response.choices[0].message.content
    if not result:
        raise RuntimeError("Model AI mengembalikan respons kosong.")
    return result.strip()

def parse_json_response(raw):
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.I)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        result = json.loads(raw)
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for i, char in enumerate(raw):
        if char == "{":
            try:
                result, _ = decoder.raw_decode(raw[i:])
                if isinstance(result, dict):
                    return result
            except json.JSONDecodeError:
                continue
    raise RuntimeError("Respons AI bukan JSON valid. Coba generate kembali atau ganti model.")

def get_profile(mode):
    if mode == MODE_LOCAL:
        return {
            "language": "Bahasa Indonesia",
            "characters": "Pocong, kuntilanak, genderuwo, tuyul, anak kos, pedagang bakso, atau warga Indonesia.",
            "setting": "Gang kampung, warung bakso, kamar kos, kontrakan, pos ronda, atau pasar malam.",
            "dialogue": "Bahasa Indonesia natural dan gaul. Dialog singkat, jelas, lucu, dan cocok untuk penonton Indonesia.",
            "continuity": "Pertahankan wajah, pakaian, bentuk tubuh, warna, dan properti karakter pada setiap shot.",
        }
    return {
        "language": "Natural conversational English",
        "characters": "A recurring expressive 3D skeleton with the same skull, teeth, eye sockets, bone proportions, body structure, accessories, and color palette.",
        "setting": "Choose a setting that specifically matches the theme and subtheme.",
        "dialogue": "Natural conversational English, concise dialogue, physical comedy, and memorable punchlines.",
        "continuity": "Maintain the same skeleton design, skull shape, teeth, bone proportions, accessories, and materials across shots.",
    }

def cta_instruction(choice):
    if choice == "🚫 Tanpa CTA":
        return "No CTA. End on the strongest punchline."
    if choice == "😂 CTA Komedi":
        return "Add one short funny CTA only if it fits naturally. Never weaken the main punchline."
    if choice == "⏳ CTA Cliffhanger":
        return "Use a funny unresolved ending and a brief follow request only when a continuation makes sense."
    if choice == "🏆 CTA Tantangan":
        return "Add one short playful challenge related to the story."
    return "Add an organic CTA only if it improves the story. Otherwise omit it. Never ruin the punchline."

def shot_schedule(duration):
    duration = int(duration)
    proportions = [0.15, 0.20, 0.18, 0.22, 0.25]
    lengths = [max(1, round(duration * p)) for p in proportions]
    while sum(lengths) > duration:
        candidates = [i for i, n in enumerate(lengths) if n > 1]
        if not candidates:
            break
        lengths[max(candidates, key=lambda i: lengths[i])] -= 1
    while sum(lengths) < duration:
        lengths[-1] += 1
    labels = ["HOOK / CLOSE-UP", "REACTION SHOT", "INTEGRATED B-ROLL", "CONFLICT ESCALATION", "PUNCHLINE / FINAL REACTION"]
    shots, current = [], 0
    for label, length in zip(labels, lengths):
        shots.append({"start": current, "end": current + length, "label": label})
        current += length
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
USER IDEA: {premise.strip() or "Invent an original funny situation based on the subtheme."}
CHARACTERS: {profile['characters']}
SETTING: {profile['setting']}
DIALOGUE STYLE: {profile['dialogue']}
CONTINUITY: {profile['continuity']}
CTA: {cta_instruction(cta_choice)}
TIMELINE:
{format_schedule(shot_schedule(duration))}
RULES:
1. Start with a strong visual hook.
2. Make the conflict immediately understandable.
3. Use short dialogue that fits the duration.
4. Escalate the absurdity.
5. End with a specific, surprising punchline.
6. Keep all dialogue in the required language.
7. Do not let CTA replace the punchline.
8. Keep the same characters and setting throughout.
9. Avoid unnecessary exposition.
10. Return JSON only, no Markdown.
Required JSON structure:
{{
  "language": "output language",
  "theme": "selected theme",
  "subtheme": "selected subtheme",
  "hook": "Opening hook",
  "story": "Complete concise story",
  "characters": "Character descriptions",
  "setting": "Setting description",
  "dialogue": [{{"time": "00:00-00:02", "speaker": "CHARACTER", "line": "Spoken dialogue"}}],
  "punchline": "Main comedic payoff",
  "ending": "Final visual reaction",
  "cta_note": "CTA or reason for omission",
  "hashtags": ["#Shorts", "#Comedy"]
}}
"""
    result = parse_json_response(call_ai(api_key, model, prompt, 2500))
    defaults = {
        "language": profile["language"], "theme": theme, "subtheme": subtheme,
        "hook": "", "story": "", "characters": profile["characters"],
        "setting": profile["setting"], "dialogue": [], "punchline": "",
        "ending": "", "cta_note": "", "hashtags": ["#Shorts", "#Comedy"],
    }
    for key, value in defaults.items():
        result.setdefault(key, value)
    return result

def generate_titles(api_key, model, story_data):
    prompt = f"""
Create five catchy YouTube Shorts titles.
LANGUAGE: {story_data.get('language', 'English')}
THEME: {story_data.get('theme', '')}
SUBTHEME: {story_data.get('subtheme', '')}
HOOK: {story_data.get('hook', '')}
STORY: {story_data.get('story', '')}
PUNCHLINE: {story_data.get('punchline', '')}
Rules: short, memorable, specific, match story language, no misleading clickbait. Return JSON only.
{{"titles": ["Title option 1", "Title option 2", "Title option 3", "Title option 4", "Title option 5"]}}
"""
    data = parse_json_response(call_ai(api_key, model, prompt, 700))
    titles = data.get("titles", [])
    if not isinstance(titles, list) or not titles:
        raise RuntimeError("Model tidak menghasilkan pilihan judul.")
    return [str(t) for t in titles[:5]]

def generate_flow_prompt(api_key, model, story_data, mode, duration, visual_style):
    profile = get_profile(mode)
    prompt = f"""
Create one complete ready-to-copy Google Flow video prompt.
FORMAT: one coherent vertical 9:16 video; target duration {duration} seconds.
STYLE: {visual_style}. MODE: {mode}. LANGUAGE: {profile['language']}.
STORY:
{json.dumps(story_data, ensure_ascii=False, indent=2)}
CHARACTER CONTINUITY: {profile['continuity']}
TIMELINE:
{format_schedule(shot_schedule(duration))}
REQUIRED:
1. One continuous video, not unrelated clips.
2. Include timestamps covering the target duration.
3. Describe actions, facial expressions, camera angles and movement.
4. Specify cinematic lighting and atmosphere.
5. Place dialogue at appropriate timestamps.
6. Include sound effects and ambience.
7. Keep character designs, props and geography consistent.
8. Finish with the visual punchline and final reaction.
9. Keep actions understandable in vertical 9:16 composition.
INTEGRATED B-ROLL:
Embed close-ups, reaction shots, detail inserts and cutaways inside the main timeline. Each insert must strengthen the joke. Do not create separate unrelated videos, do not place all B-roll outside the main prompt, and do not exceed the target duration.
Return valid JSON only, without Markdown fences:
{{
  "flow_prompt": "Complete timed Google Flow production prompt",
  "broll": [{{"timestamp": "00:02-00:03", "shot": "Specific insert or reaction shot", "camera": "Camera angle and movement", "lighting": "Lighting description", "purpose": "How this shot supports the joke"}}]
}}
"""
    data = parse_json_response(call_ai(api_key, model, prompt, 3500))
    data.setdefault("flow_prompt", "")
    data.setdefault("broll", [])
    return data

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

if mode == MODE_GLOBAL:
    theme = st.selectbox("🌎 Tema Global", list(GLOBAL_THEMES.keys()))
    subtheme = st.selectbox("🎭 Subtema", GLOBAL_THEMES[theme])
else:
    theme = st.selectbox("🇮🇩 Tema Lokal", list(LOCAL_THEMES.keys()))
    subtheme = st.selectbox("🎭 Subtema", LOCAL_THEMES[theme])

premise = st.text_area("✍️ Ide cerita (opsional)", placeholder="Contoh: skeleton terlambat kerja karena tengkoraknya tertinggal di rumah..." if mode == MODE_GLOBAL else "Contoh: pocong pesan bakso tetapi lupa membawa uang...", height=100)
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
                story_data = generate_story(api_key, models["story"], mode, theme, subtheme, premise, duration, cta_choice, visual_style)
            with st.spinner("💡 Membuat pilihan judul..."):
                titles = generate_titles(api_key, models["title"], story_data)
            with st.spinner("🎬 Menyusun prompt Google Flow..."):
                flow_data = generate_flow_prompt(api_key, models["flow"], story_data, mode, duration, visual_style)
            st.session_state.cadas_result = {
                "mode": mode, "theme": theme, "subtheme": subtheme, "duration": duration,
                "visual_style": visual_style, "story": story_data, "titles": titles,
                "flow": flow_data, "models": models,
            }
            st.success("Konsep video berhasil dibuat!")
        except Exception as exc:
            st.error(f"Gagal membuat konten: {exc}")

result = st.session_state.cadas_result
if result:
    story_data, titles, flow_data = result["story"], result["titles"], result["flow"]
    st.divider()
    st.header("📦 Hasil Generasi")
    tab_title, tab_story, tab_flow, tab_broll, tab_json = st.tabs(["📝 Judul", "📖 Cerita & Dialog", "🎬 Google Flow", "🎞️ B-Roll", "📦 Export JSON"])
    with tab_title:
        selected_title = st.radio("Pilih judul video", titles, key="selected_cadas_title")
        st.subheader("Judul terpilih")
        st.write(selected_title)
        st.download_button("⬇️ Download Judul TXT", data=selected_title, file_name="cadas_title.txt", mime="text/plain")
    with tab_story:
        st.subheader("Hook")
        st.write(story_data.get("hook", ""))
        st.subheader("Cerita")
        st.write(story_data.get("story", ""))
        st.subheader("Karakter")
        st.write(story_data.get("characters", ""))
        st.subheader("Setting")
        st.write(story_data.get("setting", ""))
        st.subheader("Dialog")
        dialogue = story_data.get("dialogue", [])
        if isinstance(dialogue, list):
            for item in dialogue:
                if isinstance(item, dict):
                    st.markdown(f"**[{item.get('time', '')}] {item.get('speaker', '')}:** {item.get('line', '')}")
        else:
            st.write(dialogue)
        st.subheader("Punchline")
        st.write(story_data.get("punchline", ""))
        st.subheader("Ending")
        st.write(story_data.get("ending", ""))
        st.subheader("CTA")
        st.write(story_data.get("cta_note", ""))
        st.subheader("Hashtags")
        hashtags = story_data.get("hashtags", [])
        st.write(" ".join(str(tag) for tag in hashtags) if isinstance(hashtags, list) else hashtags)
        st.download_button("⬇️ Download Cerita JSON", data=json.dumps(story_data, ensure_ascii=False, indent=2), file_name="cadas_story.json", mime="application/json")
    with tab_flow:
        flow_prompt = flow_data.get("flow_prompt", "")
        st.text_area("Google Flow prompt — siap disalin", value=flow_prompt, height=450)
        st.download_button("⬇️ Download Google Flow TXT", data=flow_prompt, file_name="google_flow_prompt.txt", mime="text/plain")
        st.caption("B-roll, kamera, pencahayaan, dialog, dan timeline diminta terintegrasi dalam satu video.")
    with tab_broll:
        broll_items = flow_data.get("broll", [])
        if isinstance(broll_items, list) and broll_items:
            for index, item in enumerate(broll_items, start=1):
                if not isinstance(item, dict):
                    continue
                with st.expander(f"🎞️ B-Roll {index}"):
                    st.write("**Waktu:**", item.get("timestamp", ""))
                    st.write("**Shot:**", item.get("shot", ""))
                    st.write("**Kamera:**", item.get("camera", ""))
                    st.write("**Lighting:**", item.get("lighting", ""))
                    st.write("**Tujuan:**", item.get("purpose", ""))
        else:
            st.info("Tidak ada daftar B-roll terpisah dari model. Periksa prompt Google Flow utama.")
    with tab_json:
        chosen = st.session_state.get("selected_cadas_title", titles[0] if titles else "")
        export_data = {
            "app": "Cadas Resonance Studio", "mode": result["mode"], "theme": result["theme"],
            "subtheme": result["subtheme"], "duration_seconds": result["duration"],
            "visual_style": result["visual_style"], "selected_title": chosen,
            "title_options": titles, "story": story_data,
            "google_flow_prompt": flow_data.get("flow_prompt", ""),
            "integrated_broll": flow_data.get("broll", []), "models": result["models"],
        }
        json_output = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button("📦 DOWNLOAD SEMUA HASIL JSON", data=json_output, file_name="cadas_resonance_export.json", mime="application/json", use_container_width=True)
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
