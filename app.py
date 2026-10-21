import os
import json
import re
import streamlit as st
from openai import OpenAI

# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="Cadas Resonance Studio",
    page_icon="💀",
    layout="wide",
)

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

# =========================================================
# THEMES
# =========================================================

GLOBAL_THEMES = {
    "💀 Skeleton Everyday Life": [
        "Skeleton at Work",
        "Skeleton at School",
        "Skeleton Roommate",
        "Skeleton Grocery Shopping",
        "Skeleton Family Problems",
    ],
    "😂 Absurd Comedy": [
        "Unexpected Twist",
        "Awkward Moments",
        "Dumb Decisions",
        "Public Embarrassment",
        "Overreaction Comedy",
    ],
    "👻 Horror Comedy": [
        "Haunted House",
        "Ghost Pranks",
        "Monster Problems",
        "Scared Skeleton",
        "Paranormal Roommate",
    ],
    "🎮 Gaming Comedy": [
        "Rage Quit",
        "Noob Moments",
        "Gaming Addiction",
        "Online Game Disaster",
        "Toxic Teammates",
    ],
    "❤️ Relationship Comedy": [
        "Awkward Dates",
        "Jealous Skeleton",
        "Breakup Problems",
        "Dating App Disaster",
        "Relationship Misunderstanding",
    ],
    "💪 Gym & Fitness": [
        "Skeleton at the Gym",
        "Protein Obsession",
        "Gym Fails",
        "Fitness Influencer",
        "Personal Trainer Disaster",
    ],
    "💰 Money & Work": [
        "Broke Skeleton",
        "Office Problems",
        "Payday Disaster",
        "Bad Boss",
        "Online Shopping Addiction",
    ],
    "🍔 Food Comedy": [
        "Midnight Snacks",
        "Skeleton Cooking",
        "Food Addiction",
        "Restaurant Disaster",
        "Fast Food Disaster",
    ],
    "🧪 Science & Sci-Fi": [
        "Alien Encounter",
        "Mad Experiment",
        "Time Travel Disaster",
        "Robot Problems",
        "Parallel Universe",
    ],
    "🏃 Survival Comedy": [
        "Zombie Apocalypse",
        "Bad Survival Skills",
        "Monster Chase",
        "Last Person on Earth",
        "Disaster Preparation",
    ],
}

LOCAL_THEMES = {
    "👻 Horor Komedi": [
        "Pocong Salah Alamat",
        "Kuntilanak Lapar",
        "Genderuwo Cari Kerja",
        "Hantu Kos",
        "Setan Takut Manusia",
    ],
    "🍜 Kehidupan Sehari-hari": [
        "Hantu Beli Bakso",
        "Pocong Numpang Wi-Fi",
        "Hantu Pinjam Charger",
        "Setan Pesan Makanan Online",
        "Hantu Kehabisan Uang",
    ],
    "😂 Komedi Tongkrongan": [
        "Teman Sok Berani",
        "Prank Gagal",
        "Utang Warung",
        "Ronda Tengah Malam",
        "Salah Paham Kocak",
    ],
    "🏚️ Cerita Anak Kos": [
        "Misteri Kamar Kos",
        "Hantu Minta Bayar Listrik",
        "Mie Instan Tengah Malam",
        "Pintu Kos Misterius",
        "Penunggu Kamar Mandi",
    ],
}

CTA_OPTIONS = [
    "🧠 Smart CTA Otomatis",
    "😂 CTA Komedi",
    "⏳ CTA Cliffhanger",
    "🏆 CTA Tantangan",
    "🚫 Tanpa CTA",
]

VISUAL_STYLES = [
    "Clean cinematic 3D animation",
    "Cinematic 3D horror comedy",
    "Stylized 3D cartoon comedy",
    "High-detail cinematic 3D",
    "Absurd cinematic 3D animation",
]


# =========================================================
# API KEY & API CALL
# =========================================================

def get_api_key():
    try:
        key = st.secrets.get("CLARIOHUB_API_KEY", "")
        if key:
            return str(key).strip()
    except Exception:
        pass

    return os.getenv("CLARIOHUB_API_KEY", "").strip()


def call_ai(api_key, model, prompt, max_tokens=3500):
    if not api_key:
        raise RuntimeError(
            "API Key belum diatur. Tambahkan CLARIOHUB_API_KEY "
            "di Streamlit Cloud > Settings > Secrets."
        )

    client = OpenAI(
        api_key=api_key,
        base_url=API_BASE,
        timeout=90,
        max_retries=1,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert short-form comedy writer, "
                    "cinematic 3D director, and Google Flow prompt "
                    "engineer. Follow all instructions carefully. "
                    "Return valid JSON only when requested."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.8,
        max_tokens=max_tokens,
    )

    result = response.choices[0].message.content

    if not result:
        raise RuntimeError("AI tidak mengembalikan hasil.")

    return result.strip()


def parse_json_response(text):
    text = text.strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")

        if start < 0 or end <= start:
            raise RuntimeError(
                "Respons AI bukan JSON valid. Silakan coba lagi."
            )

        data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise RuntimeError("Format hasil AI tidak sesuai.")

    return data


# =========================================================
# MODE PROFILES
# =========================================================

def get_profile(mode):
    if mode == MODE_LOCAL:
        return {
            "language": "Bahasa Indonesia",
            "characters": (
                "Pocong, kuntilanak, genderuwo, tuyul, "
                "anak kos, pedagang bakso, dan warga lokal."
            ),
            "setting": (
                "Gang kampung, warung bakso, kamar kos, "
                "kontrakan, pos ronda, atau pasar malam."
            ),
            "dialogue": (
                "Bahasa Indonesia natural dan gaul. Dialog singkat, "
                "lucu, mudah dipahami, dan cocok untuk penonton Indonesia."
            ),
            "continuity": (
                "Jaga wajah, pakaian, bentuk tubuh, warna, dan properti "
                "setiap karakter agar konsisten dari awal sampai akhir."
            ),
        }

    return {
        "language": "Natural conversational English",
        "characters": (
            "A recurring expressive 3D skeleton with consistent skull, "
            "teeth, eye sockets, bone proportions, body structure, "
            "accessories, and color palette."
        ),
        "setting": (
            "Choose a location that specifically fits the selected "
            "theme and subtheme."
        ),
        "dialogue": (
            "Natural conversational English, concise internet humor, "
            "expressive physical comedy, and memorable punchlines."
        ),
        "continuity": (
            "Maintain the exact same skeleton design, skull shape, "
            "teeth, bone proportions, accessories, and materials "
            "across all shots."
        ),
    }


# =========================================================
# CTA INSTRUCTIONS
# =========================================================

def cta_instruction(choice):
    if choice == "🚫 Tanpa CTA":
        return (
            "Do not include a subscribe, like, follow, or comment request. "
            "Finish with the strongest possible punchline."
        )

    if choice == "😂 CTA Komedi":
        return (
            "Add one short funny CTA only if it fits naturally. "
            "Never replace or weaken the main punchline."
        )

    if choice == "⏳ CTA Cliffhanger":
        return (
            "If the story supports a continuation, use a funny unresolved "
            "moment and a short invitation to follow for the next part. "
            "Do not sacrifice the main punchline."
        )

    if choice == "🏆 CTA Tantangan":
        return (
            "Include one playful challenge related to the story. "
            "Keep it short and natural."
        )

    return (
        "Analyze the story first. Add one short organic CTA only if "
        "it improves the comedy. Otherwise omit it. Never ruin the "
        "opening hook or final punchline."
    )


# =========================================================
# TIMELINE
# =========================================================

def shot_schedule(duration):
    duration = int(duration)

    proportions = [0.15, 0.20, 0.18, 0.22, 0.25]
    lengths = [max(1, round(duration * p)) for p in proportions]

    while sum(lengths) > duration:
        candidates = [
            i for i, value in enumerate(lengths)
            if value > 1
        ]
        if not candidates:
            break

        index = max(candidates, key=lambda i: lengths[i])
        lengths[index] -= 1

    while sum(lengths) < duration:
        lengths[-1] += 1

    labels = [
        "HOOK / CLOSE-UP",
        "REACTION SHOT",
        "INTEGRATED B-ROLL",
        "CONFLICT ESCALATION",
        "PUNCHLINE / FINAL REACTION",
    ]

    shots = []
    current = 0

    for label, length in zip(labels, lengths):
        shots.append({
            "start": current,
            "end": current + length,
            "label": label,
        })
        current += length

    return shots


def format_schedule(shots):
    return "\n".join(
        f"[{s['start']:02d}s-{s['end']:02d}s] {s['label']}"
        for s in shots
    )


# =========================================================
# GENERATE STORY — DEEPSEEK DEFAULT
# =========================================================

def generate_story(
    api_key,
    model,
    mode,
    theme,
    subtheme,
    premise,
    duration,
    cta_choice,
    visual_style,
):
    profile = get_profile(mode)
    schedule = format_schedule(shot_schedule(duration))

    prompt = f"""
Create one original short-form comedy story.

MODE: {mode}
LANGUAGE: {profile['language']}
THEME: {theme}
SUBTHEME: {subtheme}
TARGET DURATION: {duration} seconds
VISUAL STYLE: {visual_style}

USER PREMISE:
{premise.strip() or "Invent an original funny situation based on the selected subtheme."}

CHARACTERS:
{profile['characters']}

SETTING:
{profile['setting']}

DIALOGUE:
{profile['dialogue']}

CHARACTER CONTINUITY:
{profile['continuity']}

CTA:
{cta_instruction(cta_choice)}

TIMELINE:
{schedule}

STORY REQUIREMENTS:
1. Begin with an immediate visual hook.
2. Make the premise understandable without long exposition.
3. Use dialogue that fits the target duration.
4. Escalate the problem in a logical but absurd way.
5. Deliver a specific and surprising punchline.
6. Use physical comedy and visual storytelling.
7. Do not let the CTA replace the punchline.
8. Keep dialogue in the required language.
9. Avoid unnecessary characters and locations.
10. Make the story suitable for a vertical 9:16 short video.

Return valid JSON only:
{{
  "language": "{profile['language']}",
  "theme": "{theme}",
  "subtheme": "{subtheme}",
  "hook": "Opening hook",
  "story": "Concise complete story",
  "characters": "Character descriptions",
  "setting": "Setting description",
  "dialogue": [
    {{
      "time": "00:00-00:02",
      "speaker": "CHARACTER",
      "line": "Dialogue"
    }}
  ],
  "punchline": "Main comedic payoff",
  "ending": "Final visual reaction",
  "cta_note": "CTA used or reason for omission",
  "hashtags": ["#Shorts", "#Comedy"]
}}
"""

    raw = call_ai(
        api_key,
        model,
        prompt,
        max_tokens=2500,
    )

    return parse_json_response(raw)


# =========================================================
# GENERATE TITLES — GEMINI DEFAULT
# =========================================================

def generate_titles(api_key, model, story_data):
    prompt = f"""
Generate five memorable YouTube Shorts titles for this story.

LANGUAGE: {story_data.get('language', 'English')}
THEME: {story_data.get('theme', '')}
SUBTHEME: {story_data.get('subtheme', '')}
HOOK: {story_data.get('hook', '')}
STORY: {story_data.get('story', '')}
PUNCHLINE: {story_data.get('punchline', '')}

Rules:
- Keep titles short and easy to remember.
- Make them specific to this story.
- Avoid misleading clickbait.
- Use the same language as the story.
- Make them suitable for comedy Shorts.

Return valid JSON only:
{{
  "titles": [
    "Title option 1",
    "Title option 2",
    "Title option 3",
    "Title option 4",
    "Title option 5"
  ]
}}
"""

    raw = call_ai(api_key, model, prompt, max_tokens=600)
    data = parse_json_response(raw)

    titles = data.get("titles", [])

    if not isinstance(titles, list) or not titles:
        raise RuntimeError("Model judul tidak menghasilkan daftar judul.")

    return [str(title) for title in titles[:5]]


# =========================================================
# GENERATE GOOGLE FLOW PROMPT — DEEPSEEK DEFAULT
# =========================================================

def generate_flow_prompt(
    api_key,
    model,
    story_data,
    mode,
    duration,
    visual_style,
):
    profile = get_profile(mode)
    schedule = format_schedule(shot_schedule(duration))

    prompt = f"""
Create a complete ready-to-copy Google Flow prompt.

VIDEO FORMAT:
- One coherent vertical 9:16 video.
- Target duration: {duration} seconds.
- Visual style: {visual_style}.
- Mode: {mode}.
- Language: {profile['language']}.

STORY DATA:
{json.dumps(story_data, ensure_ascii=False, indent=2)}

CHARACTER CONTINUITY:
{profile['continuity']}

TIMELINE:
{schedule}

MANDATORY REQUIREMENTS:
1. Create one continuous video, not unrelated separate clips.
2. Follow the supplied target duration.
3. Include timestamped shots covering the full timeline.
4. Describe character actions and expressions in every shot.
5. Specify camera angle and camera movement.
6. Specify cinematic lighting and atmosphere.
7. Include dialogue at the correct timestamps.
8. Include relevant sound effects and environmental ambience.
9. Include transitions connecting each shot.
10. Preserve the same character appearance, props, and geography.
11. End with a clear visual punchline and memorable reaction.
12. Use cinematic 3D rendering and vertical composition.

INTEGRATED B-ROLL:
B-roll must be embedded directly in the main timeline.
Include relevant close-ups, reaction shots, detail inserts, and cutaways.
For example, show an expressive face close-up, a hand interacting with
an important prop, or the other character reacting to the joke.
Every insert must contribute to the same story.

Do not create unrelated B-roll videos.
Do not put all B-roll outside the main prompt.
Do not add dialogue that cannot fit the target duration.

Return valid JSON only:
{{
  "flow_prompt": "Complete production prompt with timestamps, actions, camera, lighting, dialogue, sound, transitions, and integrated B-roll.",
  "broll": [
    {{
      "timestamp": "00:02-00:03",
      "shot": "Description of the insert or reaction shot",
      "camera": "Camera angle and movement",
      "lighting": "Lighting description",
      "purpose": "How this shot strengthens the joke"
    }}
  ]
}}
"""

    raw = call_ai(
        api_key,
        model,
        prompt,
        max_tokens=3500,
    )

    return parse_json_response(raw)


# =========================================================
# EXPORT
# =========================================================

def make_export(
    mode,
    duration,
    visual_style,
    story_data,
    titles,
    selected_title,
    flow_data,
    selected_models,
):
    return {
        "app": "Cadas Resonance Studio",
        "mode": mode,
        "duration_seconds": duration,
        "visual_style": visual_style,
        "selected_title": selected_title,
        "title_options": titles,
        "story": story_data,
        "google_flow": flow_data.get("flow_prompt", ""),
        "integrated_broll": flow_data.get("broll", []),
        "models": selected_models,
    }


# =========================================================
# USER INTERFACE
# =========================================================

st.title("💀 Cadas Resonance Studio")
st.caption(
    "Local Indonesian horror comedy + global cinematic skeleton comedy."
)

with st.sidebar:
    st.header("⚙️ Pengaturan")

    mode = st.radio(
        "Pilih mode",
        [MODE_LOCAL, MODE_GLOBAL],
    )

    st.divider()
    st.subheader("🤖 Model AI")

    title_model_name = st.selectbox(
        "Model pembuat judul",
        list(MODELS.keys()),
        index=list(MODELS.keys()).index("Gemini 3.7 Flash"),
    )

    story_model_name = st.selectbox(
        "Model cerita dan dialog",
        list(MODELS.keys()),
        index=list(MODELS.keys()).index("DeepSeek V4 Pro"),
    )

    flow_model_name = st.selectbox(
        "Model prompt Google Flow",
        list(MODELS.keys()),
        index=list(MODELS.keys()).index("DeepSeek V4 Pro"),
    )

    st.caption(
        "Semua model menggunakan satu API Key ClarioHub."
    )

    st.divider()
    st.subheader("🎬 Produksi Video")

    duration = st.select_slider(
        "Durasi target video",
        options=[5, 8, 10, 15, 20, 30, 45, 60],
        value=30,
        format_func=lambda x: f"{x} detik",
    )

    visual_style = st.selectbox(
        "Gaya visual",
        VISUAL_STYLES,
    )

    cta_choice = st.selectbox(
        "Gaya CTA",
        CTA_OPTIONS,
    )


# =========================================================
# THEME SELECTORS
# =========================================================

if mode == MODE_GLOBAL:
    theme_options = list(GLOBAL_THEMES.keys())
    theme = st.selectbox("🌎 Tema Global", theme_options)

    subtheme = st.selectbox(
        "🎭 Subtema",
        GLOBAL_THEMES[theme],
    )
else:
    theme_options = list(LOCAL_THEMES.keys())
    theme = st.selectbox("🇮🇩 Tema Lokal", theme_options)

    subtheme = st.selectbox(
        "🎭 Subtema",
        LOCAL_THEMES[theme],
    )


# =========================================================
# PREMISE INPUT
# =========================================================

premise = st.text_area(
    "✍️ Ide cerita (opsional)",
    placeholder=(
        "Contoh: skeleton terlambat kerja karena tengkoraknya "
        "tertinggal di rumah..."
        if mode == MODE_GLOBAL
        else "Contoh: pocong pesan bakso tetapi lupa membawa uang..."
    ),
    height=100,
)

st.info(
    "Pilih tema dan subtema, lalu tekan Generate. "
    "Ide tambahan boleh dikosongkan."
)


# =========================================================
# GENERATION PIPELINE
# =========================================================

if "cadas_result" not in st.session_state:
    st.session_state.cadas_result = None

if st.button("🚀 GENERATE VIDEO CONCEPT", type="primary", use_container_width=True):
    api_key = get_api_key()

    if not api_key:
        st.error(
            "API Key belum ditemukan. Buka Streamlit Cloud → "
            "Settings → Secrets dan tambahkan CLARIOHUB_API_KEY."
        )
    else:
        try:
            selected_models = {
                "title": MODELS[title_model_name],
                "story": MODELS[story_model_name],
                "flow": MODELS[flow_model_name],
            }

                        with st.spinner("✍️ Membuat cerita dan dialog..."):
                story_data = generate_story(
                    api_key=api_key,
                    model=selected_models["story"],
                    mode=mode,
                    theme=theme,
                    subtheme=subtheme,
                    premise=premise,
                    duration=duration,
                    cta_choice=cta_choice,
                    visual_style=visual_style,
                )

            with st.spinner("💡 Membuat pilihan judul..."):
                titles = generate_titles(
                    api_key,
                    selected_models["title"],
                    story_data,
                )

            with st.spinner("🎬 Menyusun prompt Google Flow..."):
                flow_data = generate_flow_prompt(
                    api_key=api_key,
                    model=selected_models["flow"],
                    story_data=story_data,
                    mode=mode,
                    duration=duration,
                    visual_style=visual_style,
                )

            st.session_state.cadas_result = {
                "mode": mode,
                "duration": duration,
                "visual_style": visual_style,
                "story": story_data,
                "titles": titles,
                "flow": flow_data,
                "models": selected_models,
            }

            st.success("Konsep video berhasil dibuat!")

        except Exception as exc:
            st.error(f"Gagal membuat konten: {exc}")
