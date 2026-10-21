import os
import json
import random
import re
import streamlit as st
from openai import OpenAI

# Pilihan menu adalah referensi suasana saja. Prompt Flow memakai karakter orisinal
# agar tidak meminta peniruan langsung karakter/IP pihak ketiga.
ICONIC_ARCHETYPES = {
    "Beetlejuice": "an original chaotic supernatural showman with messy moss-green hair, a weathered black-and-cream striped suit, and mischievous undead energy; do not use any existing character name or exact likeness",
    "Art the Clown": "an original silent monochrome nightmare clown with a white face, dark eye markings, a tiny black hat, and unsettling pantomime; do not copy any existing character's exact design",
    "M3GAN": "an original eerie childlike android with porcelain-like features, neat auburn hair, and a retro modest outfit; create a distinct face and design, not an existing doll or film character",
    "Wednesday Addams": "an original deadpan goth teenage sleuth with dark braided hair, a black outfit and dry morbid humor; use a distinct face and outfit, not an existing character",
    "Ghostface": "an original masked slasher-mystery figure wearing a unique elongated pale mask and dark hooded clothing, with a newly designed mask unlike any existing franchise",
}

st.set_page_config(page_title="Global Shorts Studio", page_icon="🌎", layout="wide", initial_sidebar_state="collapsed")

# Tema terang dan nyaman dibaca, termasuk dropdown Streamlit di HP.
st.markdown("""
<style>
:root { color-scheme: light; }
/* Soft studio look: warm canvas, cool glass cards, readable contrast */
.stApp {
  background: linear-gradient(145deg, #f3f6fb 0%, #edf4f5 48%, #f8f2ec 100%) !important;
  color: #243247 !important;
}
[data-testid="stHeader"] { background: rgba(243,246,251,.88) !important; }
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #f8fbff 0%, #eef4f8 100%) !important;
  border-right: 1px solid #dbe5ec !important;
}
[data-testid="stSidebar"] * { color: #26364a; }
[data-testid="stMarkdownContainer"], p, label, h1, h2, h3, h4 { color: #26364a; }
h1 { letter-spacing: -0.035em; font-weight: 800 !important; }
h2, h3 { letter-spacing: -0.02em; }
/* Gentle section surfaces */
[data-testid="stVerticalBlockBorderWrapper"] {
  background: rgba(255,255,255,.66) !important;
  border: 1px solid #dfe7ee !important;
  border-radius: 18px !important;
  box-shadow: 0 6px 22px rgba(48,68,91,.045) !important;
}
/* Inputs and dropdowns: light, not black */
.stApp input, .stApp textarea,
.stApp [data-baseweb="select"] > div,
.stApp [data-baseweb="input"] > div,
.stApp [data-baseweb="textarea"] > div {
  background: #ffffff !important; color: #26364a !important;
  border: 1px solid #cbd8e3 !important; border-radius: 12px !important;
}
.stApp [data-baseweb="select"] *, .stApp [role="option"],
[data-baseweb="popover"], [data-baseweb="menu"] {
  background-color: #ffffff !important; color: #26364a !important;
}
.stApp [role="option"]:hover, .stApp [aria-selected="true"] {
  background: #e5f2f1 !important; color: #183b45 !important;
}
.stApp button {
  border-radius: 12px !important;
  transition: transform .15s ease, box-shadow .15s ease;
}
.stApp button[kind="primary"] {
  background: linear-gradient(100deg, #287f82 0%, #4269a8 100%) !important;
  color: #ffffff !important; border: 0 !important;
  box-shadow: 0 5px 14px rgba(46,111,132,.18) !important;
}
.stApp button[kind="secondary"], .stApp [data-testid="stDownloadButton"] button {
  background: #ffffff !important; color: #2d5968 !important;
  border: 1px solid #cbdde3 !important;
}
[data-testid="stSidebar"] button {
  background: #ffffff !important; color: #26364a !important;
  border: 1px solid #d4e0e8 !important;
}
.block-container { padding-top: 1.35rem; max-width: 1200px; }
hr { border-color: #dbe5ec !important; }
@media (max-width: 768px) {
  .block-container { padding: .8rem .8rem 2rem .8rem; }
  h1 { font-size: 1.8rem !important; }
  h2 { font-size: 1.45rem !important; }
}
</style>
""", unsafe_allow_html=True)
st.title("🌎 Global Shorts Studio (Dynamic CTA & Creative Plots)")
st.caption("PREMIS BEBAS VARIATIF → HOOK 1 DETIK → KONFLIK BERTAHAP → CTA DINAMIS (Support 10s & 20s Multi-Part Flow)")

CULTURAL_PRESETS = {
    "English": {
        "region_label": "United States / Global Western",
        "creatures_examples": "Hollywood Zombie, Horror Clown, Attic Phantom, Alien Invader, Vampire, Creepy Neighbor, Bigfoot",
        "protagonist_examples": "Sleepy gamer, night-shift cashier, tired security guard, stressed college student, food delivery driver, suburban dad in bathrobe",
        "setting_examples": "Suburban bedroom, dark basement, 24/7 convenience store, misty garage, laundry room at 2 AM",
        "slang_tone": "Sharp internet slang ('Bro', 'Dude', 'Caught in 4K', 'Ain't no way', 'Lock in')",
        "default_hook": "STOP! DON'T SCROLL!"
    },
    "Español (Spanish)": {
        "region_label": "Latin America / Spain",
        "creatures_examples": "La Llorona, dramatic shrouded ghost, mischievous goblin (Duende), gothic vampire, Chupacabra",
        "protagonist_examples": "Expressive gamer, night security guard, delivery rider, sleepy college tenant, panicking roommate",
        "setting_examples": "Colonial corridor, rustic kitchen at midnight, dim apartment hallway, quiet patio",
        "slang_tone": "Rhythmic Spanish comedic banter ('¡Oye tú!', '¡Párate ahí!', '¡No manches!', '¡Qué susto!')",
        "default_hook": "¡ALTO AHÍ! ¡NO HAGAS SCROLL!"
    },
    "日本語 (Japanese)": {
        "region_label": "Japan",
        "creatures_examples": "Classic Yūrei, Oni, mischievous Yokai, quirky kappa, urban shadow entity",
        "protagonist_examples": "Exhausted salaryman, anime streamer, konbini midnight clerk, cram school student",
        "setting_examples": "Cramped Tokyo 1R tatami room, dark train platform, narrow neon alley, quiet ramen bar corner",
        "slang_tone": "Manzai rapid comedic timing ('おい！', 'ちょっと待って！', '嘘だろ？！')",
        "default_hook": "待って！スクロールするな！"
    },
    "한국어 (Korean)": {
        "region_label": "South Korea",
        "creatures_examples": "Gwisin in white dress, Dokkaebi, rooftop shadow monster, weird closet goblin",
        "protagonist_examples": "PC bang night gamer, exhausted civil exam student, convenience store part-timer, sleepy delivery rider",
        "setting_examples": "PC bang booth, rooftop room (oktapbang), gosiwon micro-room, dimly lit apartment stairwell",
        "slang_tone": "Punchy Seoul conversational slang ('야!', '잠깐만!', '대박', '헐')",
        "default_hook": "잠깐! 넘기지 마!"
    },
    "Português (Portuguese)": {
        "region_label": "Brazil / Portugal",
        "creatures_examples": "Urban phantom, expressive zombie, Saci-pererê, funny mythical creature",
        "protagonist_examples": "Lively college roommate, motoboy delivery guy, night doorman, casual gamer",
        "setting_examples": "Warm-toned living room, messy bedroom, urban backyard, quiet kitchen alley",
        "slang_tone": "Lively Brazilian slang ('Ei você!', 'Para tudo!', 'Qual é, mano!', 'Caramba')",
        "default_hook": "PARA TUDO! NÃO PASSA O VÍDEO!"
    },
    "Bahasa Indonesia": {
        "region_label": "Indonesia",
        "creatures_examples": "Kuntilanak, pocong absurd, genderuwo nyasar, hantu kosan, tuyul bingung",
        "protagonist_examples": "Anak kos mageran, driver ojol istirahat, penjaga warkop malam, satpam perumahan ronda, mahasiswa skripsi begadang, bapak-bapak sarungan",
        "setting_examples": "Kamar kos remang, teras kontrakan malam hari, warkop 24 jam sepi, pos ronda gardu, dapur kos",
        "slang_tone": "Bahasa gaul tongkrongan ('Woi!', 'Diem dulu!', 'Gokil', 'Kena lu!', 'Santai bang')",
        "default_hook": "STOP! JANGAN SCROLL!"
    }
}

DEFAULT_GLOBAL_PRESET = {
    "region_label": "Global Universal",
    "creatures_examples": "Expressive monster, alien invader, masked shadow entity, mischievous imp",
    "protagonist_examples": "Night shift worker, late-night gamer, tired tenant, casual apartment dweller",
    "setting_examples": "Dimly lit modern apartment, quiet living room, midnight kitchen",
    "slang_tone": "Punchy native colloquial expressions",
    "default_hook": "WAIT! DON'T SWIPE!"
}

LANGUAGES = list(CULTURAL_PRESETS.keys()) + [
    "Français (French)", "Deutsch (German)", "Italiano (Italian)", "العربية (Arabic)",
    "हिन्दी (Hindi)", "Русский (Russian)", "Türkçe (Turkish)", "ไทย (Thai)",
    "Tiếng Việt (Vietnamese)", "Bahasa Melayu (Malay)", "Bahasa lain (isi sendiri)"
]

CTA_STYLE_DESCRIPTIONS = {
    "🎲 Acak Otomatis (Random)": "Pilih secara acak dari variasi taruhan, panik, suap, tuduhan, atau cliffhanger agar cerita selalu berganti.",
    "🏆 Taruhan / Syarat": "Karakter menantang penonton (misal: 'Kalau lu kaget atau ketawa, wajib pencet subscribe!').",
    "😱 Ancaman Lucu / Panik": "Karakter ketakutan atau heboh minta bantuan (misal: 'Pencet subscribe cepetan biar pintunya kekunci!').",
    "🤝 Permintaan Maaf / Suap": "Karakter ketahuan berbuat konyol/salah (misal: 'Ampun bro! Sebagai gantinya subscribe channel ini deh!').",
    "⏳ Gantung / Cliffhanger": "Karakter menghentikan momen kritis di akhir (misal: 'Mau liat kelanjutannya? Subscribe buat Part 2!').",
    "👀 Tuduhan Konyol": "Karakter menuduh penonton dengan fakta receh (misal: 'Ketahuan mantengin doang tapi tombol merahnya anggurin!')."
}

BASE_URL = "https://clariohub.id/v1"

def api_key():
    try:
        val = st.secrets.get("CLARIOHUB_API_KEY", "")
        if val:
            return str(val).strip()
    except Exception:
        pass
    return os.getenv("CLARIOHUB_API_KEY", "").strip()

def call_gemini(key, model, prompt):
    client = OpenAI(api_key=key, base_url=BASE_URL, timeout=90.0, max_retries=1)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "You are an elite short-form comedy screenwriter and continuity supervisor. "
                "Create physically coherent, cause-and-effect stories with dialogue that matches visible action. "
                "Never invent contradictory character actions, locations, props, or speaker positions. "
                "The first spoken line must be delivered by the character named as its speaker. "
                "For two-part stories, Part 2 must directly resolve the exact cliffhanger from Part 1. "
                "Use exactly two canonical character names and never change names, clothing, location, or props between parts. "
                "Every dialogue speaker label must match one canonical character name exactly. "
                "Keep dialogue short enough to speak naturally in the assigned time. "
                "Always return valid JSON only."
            )},
            {"role": "user", "content": prompt},
        ],
        temperature=0.98,
        max_tokens=2500,
    )
    text = response.choices[0].message.content
    if not text:
        raise RuntimeError("API tidak mengembalikan respons.")
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        s, e = text.find("{"), text.rfind("}")
        if s >= 0 and e > s:
            data = json.loads(text[s:e + 1])
        else:
            raise RuntimeError("Respons model bukan format JSON valid.") from exc
    return data

def build_srt(dialogue_list, duration_mode):
    if "20" in duration_mode:
        time_map = [
            ("00:00:00,000", "00:00:02,500"),
            ("00:00:02,500", "00:00:06,000"),
            ("00:00:06,000", "00:00:09,800"),
            ("00:00:10,000", "00:00:13,000"),
            ("00:00:13,000", "00:00:16,500"),
            ("00:00:16,500", "00:00:19,800")
        ]
    else:
        time_map = [
            ("00:00:00,000", "00:00:01,200"),
            ("00:00:01,200", "00:00:03,000"),
            ("00:00:03,000", "00:00:06,000"),
            ("00:00:06,000", "00:00:09,200")
        ]
    
    srt_lines = []
    for idx, d in enumerate(dialogue_list[:len(time_map)], 1):
        start, end = time_map[idx - 1]
        line = d.get("line", "")
        speaker = d.get("speaker", "SPEAKER")
        srt_lines.append(f"{idx}\n{start} --> {end}\n{speaker}: {line}\n")
    return "\n".join(srt_lines)

def prompts(x, style, duration, language, cultural_info, text_mode):
    dialogue_items = [d for d in x.get("dialogue", []) if isinstance(d, dict)]
    is_20s = "20" in duration

    creature_char = x.get("creature_description") or x.get("character_a") or cultural_info.get("creatures_examples", "Creature")
    human_char = x.get("human_character") or x.get("character_b") or cultural_info.get("protagonist_examples", "Human")
    creature_name = str(x.get("creature_name") or "MAKHLUK").strip()
    human_name = str(x.get("human_name") or "MANUSIA").strip()
    scene_env = x.get("setting_description") or cultural_info.get("setting_examples", "Room")

    if text_mode == "Video Bersih (Tanpa Teks AI - Edit di CapCut)":
        caption_rule = "- RESTRICTIONS: Clean visual footage, NO on-screen subtitles, NO text overlays, NO captions."
    else:
        caption_rule = (
            "- ON-SCREEN TEXT & CAPTIONS: Burn-in kinetic, centered word-by-word subtitles matching spoken dialogue in real-time. "
            "Font: Bold modern sans-serif, high-contrast bright yellow with solid black outline. "
            "Highlight the first hook word aggressively in red/yellow flash."
        )

    if is_20s:
        d_p1 = "\n".join(f'{d.get("time", "")} | {d.get("speaker", "CHAR")}: "{d.get("line", "")}"' for d in dialogue_items[:3])
        d_p2 = "\n".join(f'{d.get("time", "")} | {d.get("speaker", "CHAR")}: "{d.get("line", "")}"' for d in dialogue_items[3:])

        # Tie each visual beat to the actual speaker and line; never force a character
        # to perform an action that contradicts the generated dialogue.
        p1_lines = dialogue_items[:3]
        p2_lines = dialogue_items[3:6]
        def visual_beat(index, d):
            speaker = str(d.get("speaker", "")).strip()
            if speaker.casefold() == human_name.casefold():
                role = f"HUMAN {human_name}"
            elif speaker.casefold() == creature_name.casefold():
                role = f"CREATURE {creature_name}"
            else:
                role = f"ONLY the character labeled {speaker}"
            return (
                f'- Beat {index} ({d.get("time", "")}): {role} visibly speaks this exact line: "{d.get("line", "")}". '
                "Only this speaker moves their mouth; the other character reacts naturally. "
                "The action must follow directly from the previous beat and match the line."
            )
        p1_visuals = "\n".join(visual_beat(i + 1, d) for i, d in enumerate(p1_lines))
        p2_visuals = "\n".join(visual_beat(i + 4, d) for i, d in enumerate(p2_lines))

        cliffhanger_line = p1_lines[-1].get("line", "") if p1_lines else ""
        opening_p2_line = p2_lines[0].get("line", "") if p2_lines else ""

        x["flow_prompt_part1"] = f"""[SCENE 1 OF 2 — PART 1 — EXACTLY 10 SECONDS]
Create a coherent vertical 9:16 {style} comedy-horror video for {cultural_info['region_label']}.
ACTIVE TITLE: {x.get('title', '')}
THEME / STYLE: {style}
TARGET REGION: {cultural_info['region_label']}

FIXED CHARACTERS AND LOCATION:
- Location: {scene_env}
- Creature name (use exactly): {creature_name}. Visual description: {creature_char}
- Human name (use exactly): {human_name}. Visual description: {human_char}
- Cinematic, photorealistic look; vertical 9:16 composition.
- Keep both characters' appearance, clothing, scale, props, and screen positions consistent.
- Establish the geography clearly: viewers must understand where each character is and who is speaking.

STORY CONTEXT:
{x.get('story', '')}
Opening hook/action: {x.get('hook', '')}

SHOT PLAN — FOLLOW THE SCRIPT, NOT A GENERIC TEMPLATE:
{p1_visuals}
- Use a clear shot/reverse-shot or two-shot as appropriate. Only the named speaker moves their mouth during their line.
- Do not add dialogue, extra characters, unrelated actions, scene changes, or new props.
- The final beat must visibly set up this exact cliffhanger: "{cliffhanger_line}".
- END FRAME: Hold the final character positions, facial expressions, props, and camera angle for the last 0.5 seconds. This exact moment is the starting state for Part 2.

SCRIPT — KEEP WORDING AND ORDER EXACT:
{d_p1}

{caption_rule}
AUDIO: Speak the listed dialogue in the listed order, with natural timing. No extra narration or improvised words.
CONTINUITY: Part 2 starts from the exact final frame and unresolved situation of this clip."""

        x["flow_prompt_part2"] = f"""[SCENE 2 OF 2 — PART 2 — EXACTLY 10 SECONDS]
ACTIVE TITLE: {x.get('title', '')}
THEME / STYLE: {style}
TARGET REGION: {cultural_info['region_label']}
DIRECT CONTINUATION of Part 1. This is the SAME uninterrupted story, not a new scene or a recap.

MATCH PART 1:
- Same location: {scene_env}
- Same creature named exactly {creature_name}, identical face/body/clothing: {creature_char}
- Same human named exactly {human_name}, identical face/body/clothing: {human_char}
- Match lighting, color grading, camera direction, props, and character screen positions.
- Start from the exact final pose and unresolved action of Part 1. Do not reset or reintroduce the characters.

CONTINUITY CUE:
Part 1 ended with: "{cliffhanger_line}"
The first line here is: "{opening_p2_line}"
Show the immediate reaction/answer to the cliffhanger before moving to the next beat.

SHOT PLAN — FOLLOW THE SCRIPT, NOT A GENERIC TEMPLATE:
{p2_visuals}
- The subscribe CTA must be spoken by the character assigned that dialogue line and must arise naturally from the current conflict.
- The final visual must clearly deliver this payoff: "{x.get('punchline', '')}"
- Final action: {x.get('ending', '')}
- Do not add dialogue, new characters, unrelated actions, scene changes, or new props.

SCRIPT — KEEP WORDING AND ORDER EXACT:
{d_p2}

{caption_rule}
AUDIO: Speak the listed dialogue in the listed order, with natural timing. No extra narration or improvised words.
CONTINUITY: Preserve the exact character identities and resolve the cliffhanger established in Part 1."""

        x["flow_prompt"] = f"=== PART 1 (0-10s) ===\n{x['flow_prompt_part1']}\n\n" + "="*40 + f"\n\n=== PART 2 (10-20s - SEAMLESS CONTINUATION) ===\n{x['flow_prompt_part2']}"

    else:
        dialogue = "\n".join(f'{d.get("time", "")} | {d.get("speaker", "CHAR")}: "{d.get("line", "")}"' for d in dialogue_items)
        x["flow_prompt"] = f"""Create ONE coherent {duration} vertical 9:16 {style} YouTube Short for {cultural_info['region_label']}.

ACTIVE TITLE: {x.get('title', '')}
THEME / STYLE: {style}
TARGET REGION: {cultural_info['region_label']}

VISUALS & ENVIRONMENT:
- Setting: {scene_env}
- Character A (Instigator): {creature_char}
- Character B (Human): {human_char}

TITLE: {x.get('title', '')}
HOOK (0-1s): {x.get('hook', '')}
PREMISE: {x.get('story', '')}
PUNCHLINE: {x.get('punchline', '')}
ENDING: {x.get('ending', '')}

SCRIPT (STRICT SHOT-REVERSE-SHOT PACING):
{dialogue}

EDITING & SHOT BREAKDOWN:
- Shot 1 (0–1s) [Close-Up]: Character A aggressively halts camera ({x.get('hook', '')}).
- Shot 2 (1–3s) [Medium]: Character B reacts defensively in native colloquial slang.
- Shot 3 (3–6s) [Close-Up]: Contextual subscribe callout tied organically to the plot.
- Shot 4 (6–9s) [Two-Shot / Medium-Wide]: Final roast punchline, laughing or dramatic freeze.

{caption_rule}

RESTRICTIONS: Photorealistic cinematic grade, vertical 9:16 framing, seamless continuity across cuts."""

    x["thumbnail_prompt"] = f"""Viral 9:16 YouTube Shorts thumbnail for {cultural_info['region_label']}. TITLE CONCEPT: {x.get('title', '')}. Visual style: {style}. Subject: {creature_char} staring into lens with extreme expression: {x.get('hook', '')}, background showing {human_char} in shock. Setting: {scene_env}. High-contrast chiaroscuro, sharp mobile details, space left clean at bottom, no watermark."""
    x["srt_data"] = build_srt(dialogue_items, duration)
    x.setdefault("hashtags", "#Shorts #Comedy #ViralSkit #Humor")
    return x

def local_idea(cultural_info, chosen_cta, is_20s=False):
    random_human = random.choice([
        "Tired security guard in uniform holding a flashlight and drinking coffee",
        "Sweaty food delivery driver wearing a green helmet and jacket",
        "Sleepy college student in oversized hoodie and messy hair",
        "Grumpy landlord in flip-flops and batik shirt"
    ])
    random_creature = random.choice([
        "Pale mischievous ghost hovering awkwardly",
        "Messy zombie clutching an empty power bank",
        "Confused alien wearing a baseball cap backwards"
    ])
    
    if is_20s:
        return {
            "title": "THE 20-SECOND MIDNIGHT HEIST 🍕👻",
            "hook": "GHOST BANGS SCREEN: 'FREEZE! DON'T SWIPE!'",
            "story": "A supernatural creature gets caught red-handed stealing food and tries to negotiate peace by demanding subscribers.",
            "human_character": random_human,
            "creature_description": random_creature,
            "setting_description": "Dimly lit kitchen with open refrigerator lighting at 3 AM",
            "dialogue": [
                {"time": "00:00–00:02.5", "speaker": "GHOST", "line": "FREEZE! DON'T SWIPE AWAY!"},
                {"time": "00:02.5–00:06", "speaker": "HUMAN", "line": "Bro, it's 3 AM and you're eating my cold pizza?!"},
                {"time": "00:06–00:10", "speaker": "GHOST", "line": "I've been dead for 40 years, I crave mozzarella! Listen to my deal..."},
                {"time": "00:10–00:13", "speaker": "HUMAN", "line": "What deal?! You don't even pay rent here!"},
                {"time": "00:13–00:16.5", "speaker": "GHOST", "line": "Subscribe to this channel right now, or I haunt your bathroom!"},
                {"time": "00:16.5–00:20", "speaker": "HUMAN", "line": "NOT THE BATHROOM! OKAY I SUBSCRIBED! Take the crust too! Hahaha!"}
            ],
            "punchline": "Human frantically subscribes on smartphone while ghost smiles triumphantly holding pizza slice.",
            "ending": "Both sit down together on the kitchen floor eating pizza in peace.",
            "hashtags": "#Shorts #Comedy #MidnightGhost #ViralSkit"
        }
    
    return {
        "title": "ZOMBIE STEALS WIFI PASSWORD?! 🧟‍♂️📡",
        "hook": "Zombie bangs on screen: 'HOLD UP! DON'T SWIPE!'",
        "story": "A zombie sneaks in not to eat brains, but to get the WiFi password and demand subscribers.",
        "human_character": random_human,
        "creature_description": random_creature,
        "setting_description": "Messy midnight apartment room illuminated by computer screen glow",
        "dialogue": [
            {"time": "00:00–00:01", "speaker": "ZOMBIE", "line": "HOLD UP! DON'T SWIPE!"},
            {"time": "00:01–00:03", "speaker": "HUMAN", "line": "Bro, what are you doing in my room?!"},
            {"time": "00:03–00:06", "speaker": "ZOMBIE", "line": "Give me the WiFi password or hit subscribe right now!"},
            {"time": "00:06–00:09", "speaker": "HUMAN", "line": "You've been buried for a century, why do you need 5G?! Hahaha!"}
        ],
        "punchline": "Human bursts out laughing as the zombie stares awkwardly at his decayed hands.",
        "ending": "Zombie slumps in defeat.",
        "hashtags": "#Shorts #ZombieComedy #GamingHumor"
    }

with st.sidebar:
    st.header("Pengaturan API")
    key = api_key()
    if not key:
        key = st.text_input("API Key ClarioHub", type="password").strip()
    st.write("ClarioHub API:", "✅ Key tersedia" if key else "⚠️ Masukkan API key")

    model_options = {
        "Gemini 3.7 Flash": "clario/gemini-3.7-flash",
        "GPT 5.6 Sol": "clario/gpt-5.6-sol",
        "DeepSeek V4 Pro": "clario/deepseek-v4-pro",
        "DeepSeek V4 Flash": "clario/deepseek-v4-flash",
        "GLM 5.3 Flash": "clario/glm-5.3-flash"
    }
    model = model_options[st.selectbox("Model AI", list(model_options.keys()), index=0)]
    st.divider()

    st.header("🎯 Target Budaya & Bahasa")
    lang_choice = st.selectbox("🌎 Bahasa Target", LANGUAGES, index=0)
    target_language = st.text_input("Nama bahasa / Negara").strip() if lang_choice == "Bahasa lain (isi sendiri)" else lang_choice
    if not target_language:
        target_language = "English"

    cultural_info = CULTURAL_PRESETS.get(target_language, DEFAULT_GLOBAL_PRESET)

    # Character menu is available only for English / US-Global targeting.
    iconic_character = "Auto (random character)"
    if target_language == "English":
        st.subheader("🎭 Ikon Karakter — US / Global")
        iconic_character = st.selectbox(
            "Pilih karakter (opsional)",
            ["Auto (random character)", "Beetlejuice", "Art the Clown", "M3GAN", "Wednesday Addams", "Ghostface"],
            index=0,
            help="Pilih karakter untuk dijadikan tokoh utama. Auto akan memilih salah satu secara acak."
        )
        if iconic_character == "Auto (random character)":
            iconic_character = random.choice(["Beetlejuice", "Art the Clown", "M3GAN", "Wednesday Addams", "Ghostface"])

    st.info(f"**Target:** {cultural_info['region_label']}\n\n"
            f"**Inspirasi Karakter:** {cultural_info['creatures_examples']}\n\n"
            f"**Inspirasi Manusia:** {cultural_info['protagonist_examples']}")

    st.header("💡 Format Ajakan Subscribe (CTA)")
    cta_choice = st.selectbox("Gaya Ajakan Subscribe:", list(CTA_STYLE_DESCRIPTIONS.keys()), index=0)
    st.caption(CTA_STYLE_DESCRIPTIONS[cta_choice])

    st.header("🎬 Output Teks Video")
    text_mode = st.radio(
        "Mode Teks untuk Flow:",
        ["Video Bersih (Tanpa Teks AI - Edit di CapCut)", "Teks Kuning Otomatis AI di Video"],
        index=0
    )

    style = st.selectbox("Gaya Visual", [
        "Horor-komedi realistis (Creature vs Human)",
        "Komedi absurd perkotaan",
        "Parodi sci-fi / alien kocak",
        "Karakter bebas"
    ])
    duration = st.selectbox("Durasi Video", ["8 detik", "10 detik", "20 detik (2x 10 detik Part 1 & 2)"], index=2)

st.subheader("📝 Ide / Topik Cerita (Opsional)")
user_premise = st.text_input(
    "Masukkan tema atau situasi konyol yang Anda inginkan:",
    placeholder="Contoh: Hantu minjem charger HP, zombie numpang pesan gofood, alien kaget liat token listrik...",
    help="Jika dikosongkan, AI akan membuat situasi komedi acak yang segar secara otomatis."
)

if "idea" not in st.session_state:
    st.session_state.idea = None

if "history_titles" not in st.session_state:
    st.session_state.history_titles = []

if st.button("🔥 GENERATE SKRIP BARU & SEGAR", type="primary", use_container_width=True):
    st.session_state.pop("selected_short_title", None)
    is_20s = "20" in duration
    history_context = ", ".join(f'"{t}"' for t in st.session_state.history_titles[-6:]) or "None"

    if cta_choice == "🎲 Acak Otomatis (Random)":
        selected_cta_instruction = random.choice([
            "CTA STYLE: BET / CHALLENGE ('If you laughed, you owe a subscribe!')",
            "CTA STYLE: PANIC / SUDDEN THREAT ('Hit subscribe quick before the door locks!')",
            "CTA STYLE: BRIBE / APOLOGY ('I'm sorry! Just subscribe and don't tell anyone!')",
            "CTA STYLE: CLIFFHANGER ('Subscribe now for Part 2 disaster!')",
            "CTA STYLE: CAUGHT IN THE ACT ('Binge-watching without clicking subscribe!')"
        ])
    else:
        selected_cta_instruction = f"CTA STYLE: {cta_choice.upper()} - {CTA_STYLE_DESCRIPTIONS[cta_choice]}"

    user_premise_instruction = (
        f"MANDATORY USER PREMISE: {user_premise.strip()}"
        if user_premise.strip()
        else "NO USER IDEA PROVIDED: Invent a complete, fresh, specific comedic-horror situation automatically. Create a short, punchy title automatically that summarizes the actual gag; do not ask the user for an idea."
    )
    iconic_character_instruction = ""
    if target_language == "English":
        archetype = ICONIC_ARCHETYPES.get(iconic_character, "an original comedic-horror character with a distinctive, newly designed appearance")
        iconic_character_instruction = (
            f"CHARACTER STYLE REFERENCE SELECTED BY USER: {iconic_character}. Use this ORIGINALIZED ARCHETYPE instead: {archetype}. "
            "IMPORTANT: The selected name is only a private style reference. NEVER include that franchise/character name in the generated story, character names, on-screen text, or Google Flow prompt. "
            "Do not recreate, imitate, or make the character recognizable as a specific existing copyrighted character. Make a fresh original design, face, costume details, silhouette, and name while preserving only broad genre traits. "
            "Keep the comedic-horror premise, dialogue, and visuals original and suitable for video generation."
        )

    if is_20s:
        pacing_instruction = """STRUCTURAL 20-SECOND (TWO-PART CONTINUATION) PACING:
- PART 1 (00:00–00:10):
  1. BEAT 1 (00:00–00:02.5): Fast, instantly understandable visual hook.
  2. BEAT 2 (00:02.5–00:06): Shock reaction and a clear comedic confrontation.
  3. BEAT 3 (00:06–00:10): Escalate the conflict and end on a cliffhanger that naturally leads into Part 2.
- PART 2 (00:10–00:20):
  4. BEAT 4 (00:10–00:13): Continue the exact action from the Part 1 cliffhanger.
  5. BEAT 5 (00:13–00:16.5): Deliver the selected subscribe CTA as part of the joke, not as a detached advertisement.
  6. BEAT 6 (00:16.5–00:20): Pay off the setup with a clear, funny punchline and visual ending.
- The two parts must form ONE logical story. Part 2 must directly continue the same action, characters, location, props, and conflict from Part 1.
- Dialogue must be concise, speakable, and fit the timestamps. Use exactly 6 dialogue entries, 3 per part.
- The ending of Part 1 must create a specific question or immediate problem that Part 2 resolves.
- Do not introduce a new unrelated event or reset the scene in Part 2."""
    else:
        pacing_instruction = f"""STRUCTURAL {duration.upper()} PACING:
- Hook immediately in the first second.
- Establish one clear, easy-to-understand comedic conflict.
- Escalate the conflict quickly; make every line advance the story.
- Integrate the subscribe CTA naturally into the conflict or punchline.
- End with a clear visual gag or memorable punchline.
- Dialogue must fit the selected duration. Keep each line short and speakable."""

    prompt = f"""
Create ONE original, coherent YouTube Shorts comedy-sketch concept.
Return VALID JSON ONLY. No markdown fences, no commentary.

TARGET:
- Language: {target_language}
- Region/cultural context: {cultural_info['region_label']}
- Visual style: {style}
- Duration: {duration}
- Text mode: {text_mode}

CREATIVE REQUIREMENTS:
- {user_premise_instruction}
- {iconic_character_instruction}
- {selected_cta_instruction}
- Use natural, locally appropriate dialogue in {target_language}; do not mix languages unnecessarily.
- Invent a fresh situation with specific, filmable actions. Avoid generic, nonsensical dialogue.
- Make cause-and-effect immediately understandable to a viewer who has never seen the channel.
- Every line must be a direct reaction to the previous line/action; no random topic changes.
- The "hook" field must describe the actual opening visual AND be consistent with the first dialogue speaker/line.
- Do not describe one character speaking while assigning the dialogue to another character.
- Each dialogue line must be short enough to say naturally within its timestamp.
- For 20 seconds, Part 1 must end with a concrete visible problem/question; the first line of Part 2 must directly answer/react to it.
- Include the subscribe CTA as a joke that fits the existing conflict; do not let it interrupt or replace the story payoff.
- Avoid repeating these recent titles: {history_context}
- {pacing_instruction}

Return a JSON object with exactly these fields:
{{
  "title": "Strongest title; 3–6 words, short and punchy",
  "title_options": ["Short title 1", "Short title 2", "Short title 3", "Short title 4", "Short title 5"],
  "hook": "Very short opening visual/action AND the first spoken line if applicable",
  "human_name": "One short canonical name for the human character, e.g. BUDI",
  "creature_name": "One short canonical name for the creature, e.g. POCONG",
  "story": "One or two sentences explaining the complete logical story",
  "human_character": "Specific visual description of the human character",
  "creature_description": "Specific visual description of the creature or other character",
  "setting_description": "Specific, consistent location and lighting",
  "dialogue": [
    {{"time": "timestamp range", "speaker": "CHARACTER NAME", "line": "dialogue"}}
  ],
  "punchline": "The actual comedic payoff, consistent with the story",
  "ending": "The final visual action or pose",
  "hashtags": "#Shorts #Comedy and two relevant tags"
}}

DIALOGUE RULES:
- For 20 seconds, return exactly 6 dialogue entries: 3 for Part 1 and 3 for Part 2. Use timestamp ranges 00:00–00:02.5, 00:02.5–00:06, 00:06–00:10, 00:10–00:13, 00:13–00:16.5, 00:16.5–00:20.
- For 10 seconds, return exactly 4 dialogue entries, with short lines timed across 00:00–00:01, 00:01–00:03, 00:03–00:06, 00:06–00:10.
- For 8 seconds, return exactly 4 very short dialogue entries, timed across 00:00–00:01, 00:01–00:02.5, 00:02.5–00:05, 00:05–00:08.
- Keep all dialogue in the selected language ({target_language}).
- Use only the two described characters unless the premise explicitly requires another.
- Define exactly one canonical human_name and one canonical creature_name. Every dialogue speaker value MUST equal one of those two names exactly; never invent or switch names midway.
- Character descriptions must begin with the same canonical name and must describe only that character. Never give the human's name/wardrobe to the creature or vice versa.
- title_options must contain exactly 5 different short, punchy titles, ideally 3–6 words each and never more than 8 words. Set title equal to title_options[0]. Titles must describe this actual story, not generic clickbait. If the user gave no premise, invent both the story and titles automatically; never use placeholder or generic titles.
- Keep the location, time, props, character positions, and physical situation fixed unless a change is explicitly shown in the script.
- For 20 seconds, make dialogue entries 1–3 the complete Part 1 arc and entries 4–6 the direct continuation and payoff.
- The final Part 1 line must create a specific visible unresolved action/problem; entry 4 must directly react to that exact problem, not to a different event.
- Mention every important prop in setting/story before it is used. Do not introduce a stone, phone, flashlight, doorway, or other prop only in Part 2.
- The hook, story, character descriptions, dialogue, punchline, and ending must all describe the SAME event. Before returning JSON, silently check the story beat-by-beat for name, prop, location, speaker, and cause-and-effect contradictions and fix them.
"""

    try:
        if not key:
            st.error("Masukkan API key ClarioHub terlebih dahulu di sidebar.")
            st.stop()

        with st.spinner("Sedang membuat cerita dan prompt video..."):
            idea = call_gemini(key, model, prompt)

        if not isinstance(idea, dict):
            raise ValueError("Respons AI bukan objek JSON.")
        required_fields = ("title", "title_options", "hook", "story", "human_name", "creature_name", "human_character", "creature_description", "setting_description", "dialogue", "punchline", "ending")
        missing = [field for field in required_fields if not idea.get(field)]
        if missing:
            raise ValueError("Respons AI tidak lengkap. Field kosong: " + ", ".join(missing))

        if not isinstance(idea.get("dialogue"), list):
            raise ValueError("Format dialogue dari AI tidak valid.")

        expected_dialogue = 6 if is_20s else 4
        if len(idea["dialogue"]) != expected_dialogue:
            raise ValueError(f"Skrip {duration} harus memiliki tepat {expected_dialogue} baris dialog; AI menghasilkan {len(idea['dialogue'])}. Tekan generate ulang.")

        # Pastikan ada tepat lima judul berbeda dan judul utama selalu pilihan pertama.
        raw_titles = idea.get("title_options", [])
        if not isinstance(raw_titles, list):
            raw_titles = []
        titles = []
        for candidate in [idea.get("title", ""), *raw_titles]:
            candidate = re.sub(r"\s+", " ", str(candidate)).strip().strip('"')
            if candidate and candidate.casefold() not in {t.casefold() for t in titles}:
                titles.append(candidate[:80])
        fallback_titles = ["The Worst Idea Ever", "Nobody Saw That Coming", "One Very Bad Plan", "This Got Weird Fast", "Wait Until The Ending"]
        for candidate in fallback_titles:
            if len(titles) >= 5:
                break
            if candidate.casefold() not in {t.casefold() for t in titles}:
                titles.append(candidate)
        idea["title_options"] = titles[:5]
        idea["title"] = idea["title_options"][0]

        # Jangan keluarkan prompt jika label dialog mengganti identitas karakter.
        allowed_speakers = {
            str(idea.get("human_name", "")).strip().casefold(),
            str(idea.get("creature_name", "")).strip().casefold(),
        }
        if "" in allowed_speakers or len(allowed_speakers) != 2:
            raise ValueError("AI belum menetapkan dua nama karakter yang berbeda. Tekan generate ulang.")
        bad_speakers = []
        for item in idea["dialogue"]:
            if not isinstance(item, dict):
                bad_speakers.append("dialogue bukan objek")
                continue
            speaker = str(item.get("speaker", "")).strip().casefold()
            if speaker not in allowed_speakers:
                bad_speakers.append(str(item.get("speaker", "(kosong)")))
        if bad_speakers:
            raise ValueError("Label pembicara tidak cocok dengan dua nama karakter: " + ", ".join(bad_speakers) + ". Tekan generate ulang.")

        if target_language == "English":
            idea["selected_iconic_character"] = iconic_character
            # Enforce an original archetype in the actual video prompt, not the franchise name.
            archetype = ICONIC_ARCHETYPES.get(iconic_character, "an original comedic-horror character with a distinctive new appearance")
            for field in ("human_character", "creature_description", "story", "hook", "punchline", "ending", "title"):
                value = idea.get(field)
                if isinstance(value, str):
                    for protected_name in ICONIC_ARCHETYPES:
                        value = re.sub(re.escape(protected_name), "original horror-comedy character", value, flags=re.IGNORECASE)
                    idea[field] = value
            creature_desc = str(idea.get("creature_description", ""))
            if not creature_desc or creature_desc == "None":
                idea["creature_description"] = archetype
            elif "original" not in creature_desc.lower():
                idea["creature_description"] = archetype + ". " + creature_desc
        idea = prompts(idea, style, duration, target_language, cultural_info, text_mode)
        if target_language == "English":
            # Final safety pass: remove franchise names from the exact text pasted into Flow.
            for field in ("flow_prompt_part1", "flow_prompt_part2", "flow_prompt"):
                value = str(idea.get(field, ""))
                for protected_name in ICONIC_ARCHETYPES:
                    value = re.sub(re.escape(protected_name), "an original horror-comedy character", value, flags=re.IGNORECASE)
                idea[field] = value
        st.session_state.idea = idea
        title = str(idea.get("title", "")).strip()
        if title:
            st.session_state.history_titles.append(title)
            st.session_state.history_titles = st.session_state.history_titles[-20:]

    except Exception as exc:
        st.error(f"Gagal membuat skrip: {exc}")
        st.stop()


if st.session_state.idea:
    idea = st.session_state.idea
    st.divider()
    st.header("✅ Hasil Skrip")
    title_options = idea.get("title_options", [idea.get("title", "Untitled")])
    current_title = idea.get("title", title_options[0] if title_options else "Untitled")
    if current_title not in title_options:
        title_options = [current_title] + [t for t in title_options if t != current_title]
    selected_title = st.selectbox(
        "🏷️ Pilih judul (5 pilihan)", title_options[:5],
        index=(title_options[:5].index(current_title) if current_title in title_options[:5] else 0),
        key="selected_short_title"
    )
    previous_prompt_title = idea.get("_prompt_title", idea.get("title", ""))
    settings_fingerprint = json.dumps({"style": style, "duration": duration, "language": target_language, "region": cultural_info.get("region_label"), "text_mode": text_mode, "character": idea.get("selected_iconic_character", "")}, sort_keys=True)
    previous_fingerprint = idea.get("_prompt_settings_fingerprint", "")
    idea["title"] = selected_title
    # Rebuild prompts when title OR prompt-affecting settings change; avoid stale Flow output.
    if selected_title != previous_prompt_title or settings_fingerprint != previous_fingerprint:
        idea = prompts(idea, style, duration, target_language, cultural_info, text_mode)
        if target_language == "English":
            for field in ("flow_prompt_part1", "flow_prompt_part2", "flow_prompt"):
                value = str(idea.get(field, ""))
                for protected_name in ICONIC_ARCHETYPES:
                    value = re.sub(re.escape(protected_name), "an original horror-comedy character", value, flags=re.IGNORECASE)
                idea[field] = value
        idea["_prompt_title"] = selected_title
        idea["_prompt_settings_fingerprint"] = settings_fingerprint
        st.session_state.idea = idea
    else:
        idea["_prompt_title"] = selected_title
        idea["_prompt_settings_fingerprint"] = settings_fingerprint
    # A title-specific key forces Streamlit to show the newly generated prompt, not stale text.
    prompt_key = re.sub(r"[^a-zA-Z0-9]+", "_", selected_title).strip("_")[:40] or "title"
    st.subheader(selected_title)
    st.write("**Hook:**", idea.get("hook", ""))
    st.write("**Premis:**", idea.get("story", ""))
    st.write("**Karakter manusia:**", idea.get("human_character", ""))
    st.write("**Karakter makhluk:**", idea.get("creature_description", ""))
    st.write("**Lokasi:**", idea.get("setting_description", ""))

    st.markdown("### 🎭 Dialog")
    for item in idea.get("dialogue", []):
        if isinstance(item, dict):
            st.write(f"**{item.get('time', '')} — {item.get('speaker', 'CHAR')}:** {item.get('line', '')}")

    st.write("**Punchline:**", idea.get("punchline", ""))
    st.write("**Ending visual:**", idea.get("ending", ""))
    st.write("**Hashtag:**", idea.get("hashtags", ""))

    if "20" in duration:
        st.markdown("### 🎬 Prompt Google Flow — Part 1 (10 detik)")
        st.text_area("Salin prompt Part 1", idea.get("flow_prompt_part1", ""), height=320, key=f"flow_part1_{prompt_key}")
        st.download_button(
            "⬇️ Download Prompt Part 1",
            data=idea.get("flow_prompt_part1", ""),
            file_name="prompt_part1.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.markdown("### 🎬 Prompt Google Flow — Part 2 (lanjutan 10 detik)")
        st.text_area("Salin prompt Part 2", idea.get("flow_prompt_part2", ""), height=320, key=f"flow_part2_{prompt_key}")
        st.download_button(
            "⬇️ Download Prompt Part 2",
            data=idea.get("flow_prompt_part2", ""),
            file_name="prompt_part2.txt",
            mime="text/plain",
            use_container_width=True,
        )
    else:
        st.markdown("### 🎬 Prompt Google Flow")
        st.text_area("Salin prompt video", idea.get("flow_prompt", ""), height=420, key=f"flow_prompt_{prompt_key}")
        st.download_button(
            "⬇️ Download Prompt Video",
            data=idea.get("flow_prompt", ""),
            file_name="prompt_video.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown("### 🖼️ Prompt Thumbnail")
    st.text_area("Salin prompt thumbnail", idea.get("thumbnail_prompt", ""), height=140, key=f"thumbnail_prompt_{prompt_key}")
    st.download_button(
        "⬇️ Download Prompt Thumbnail",
        data=idea.get("thumbnail_prompt", ""),
        file_name="prompt_thumbnail.txt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown("### 💬 Subtitle SRT")
    st.text_area("Salin subtitle SRT", idea.get("srt_data", ""), height=180, key="srt_data")
    st.download_button(
        "⬇️ Download Subtitle SRT",
        data=idea.get("srt_data", ""),
        file_name="subtitles.srt",
        mime="text/plain",
        use_container_width=True,
    )

    st.markdown("### 📦 Semua output")
    all_output = {
        "title": idea.get("title", ""),
        "title_options": idea.get("title_options", []),
        "human_name": idea.get("human_name", ""),
        "creature_name": idea.get("creature_name", ""),
        "hook": idea.get("hook", ""),
        "story": idea.get("story", ""),
        "human_character": idea.get("human_character", ""),
        "creature_description": idea.get("creature_description", ""),
        "setting_description": idea.get("setting_description", ""),
        "dialogue": idea.get("dialogue", []),
        "punchline": idea.get("punchline", ""),
        "ending": idea.get("ending", ""),
        "hashtags": idea.get("hashtags", ""),
        "flow_prompt_part1": idea.get("flow_prompt_part1", ""),
        "flow_prompt_part2": idea.get("flow_prompt_part2", ""),
        "flow_prompt": idea.get("flow_prompt", ""),
        "thumbnail_prompt": idea.get("thumbnail_prompt", ""),
        "srt_data": idea.get("srt_data", ""),
    }
    st.download_button(
        "⬇️ Download Semua Hasil (JSON)",
        data=json.dumps(all_output, ensure_ascii=False, indent=2),
        file_name="shorts_studio_output.json",
        mime="application/json",
        use_container_width=True,
    )
