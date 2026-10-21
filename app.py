import os
import json
import random
import re
import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="Cadas Resonance Studio",
    page_icon="💀",
    layout="wide"
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

# ======================================================
# TEMA DAN SUBTEMA GLOBAL
# ======================================================

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
        "Skeleton at a Fast Food Restaurant",
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


# ======================================================
# API
# ======================================================

def get_api_key():
    try:
        value = st.secrets.get("CLARIOHUB_API_KEY", "")
        if value:
            return str(value).strip()
    except Exception:
        pass

    return os.getenv("CLARIOHUB_API_KEY", "").strip()


def call_ai(api_key, model, prompt):
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
                    "engineer. Create original, visual stories with "
                    "precise timing, integrated B-roll, consistent "
                    "characters, and strong punchlines. Return valid "
                    "JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.9,
        max_tokens=3500,
    )

    text = response.choices[0].message.content

    if not text:
        raise RuntimeError("AI tidak mengembalikan hasil.")

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
                "Respons AI bukan JSON valid. Coba generate kembali."
            )

        data = json.loads(text[start:end + 1])

    if not isinstance(data, dict):
        raise RuntimeError("Format hasil AI tidak sesuai.")

    return data


# ======================================================
# KONFIGURASI MODE
# ======================================================

def get_profile(mode):
    if mode == MODE_LOCAL:
        return {
            "language": "Bahasa Indonesia",
            "region": "Indonesia",
            "characters": (
                "Pocong, kuntilanak, genderuwo, tuyul, "
                "hantu kos, zombie lokal, dan karakter folklore Indonesia"
            ),
            "protagonist": (
                "Anak kos, penjaga warung, pedagang bakso, "
                "pemuda tongkrongan, atau warga lokal"
            ),
            "setting": (
                "Gang kampung, warung bakso, kamar kos, "
                "kontrakan, pos ronda, atau pasar malam"
            ),
            "dialogue": (
                "Bahasa Indonesia natural dan gaul. "
                "Gunakan humor percakapan sehari-hari."
            ),
            "identity": (
                "Stylized cinematic 3D Indonesian horror comedy. "
                "Karakter ekspresif, detail material berkualitas, "
                "dan desain karakter konsisten."
            ),
        }

    return {
        "language": "Natural conversational English",
        "region": "Global audience",
        "characters": (
            "A recurring expressive 3D skeleton with consistent skull, "
            "teeth, bone proportions, body structure, and accessories. "
            "Supporting humans, ghosts, zombies, or monsters may appear."
        ),
        "protagonist": (
            "A funny recurring skeleton character with expressive "
            "physical comedy and clear visual reactions."
        ),
        "setting": (
            "Choose a setting that specifically fits the selected "
            "theme and subtheme."
        ),
        "dialogue": (
            "Natural conversational English, concise internet humor, "
            "strong comedic timing, and memorable punchlines."
        ),
        "identity": (
            "Clean cinematic 3D animation, detailed bone materials, "
            "expressive animation, cinematic lighting, polished render, "
            "consistent skeleton design, and vertical 9:16 composition."
        ),
    }


# ======================================================
# CTA
# ======================================================

def cta_instruction(choice, language):
    if choice == "🚫 Tanpa CTA":
        return (
            "Do not include any subscribe, like, follow, or comment request. "
            "Finish with the strongest possible punchline."
        )

    if choice == "😂 CTA Komedi":
        return (
            "Include one short, funny subscribe request that naturally "
            "fits the character's predicament. Preserve the final joke."
        )

    if choice == "⏳ CTA Cliffhanger":
        return (
            "If the story supports it, end with a funny unresolved moment "
            "and a brief invitation to follow for the next part. "
            "Do not sacrifice the main punchline."
        )

    if choice == "🏆 CTA Tantangan":
        return (
            "Include one playful challenge to the audience that relates "
            "to the joke. Keep it short and lighthearted."
        )

    return (
        "SMART CTA: Analyze the story first. Add one brief organic CTA "
        "only when it improves the comedy. Otherwise omit it. "
        "Never force a CTA into the opening hook or ruin the punchline."
    )


# ======================================================
# PEMBAGIAN SHOT
# ======================================================

def shot_schedule(duration):
    """
    Membuat shot schedule sesuai durasi target.
    Semua rentang menggunakan detik agar tidak ada timestamp
    yang melebihi durasi target.
    """
    duration = int(duration)

    if duration <= 5:
        proportions = [0.20, 0.22, 0.18, 0.20, 0.20]
    elif duration <= 8:
        proportions = [0.16, 0.20, 0.18, 0.22, 0.24]
    elif duration <= 10:
        proportions = [0.15, 0.19, 0.18, 0.22, 0.26]
    else:
        proportions = [0.12, 0.18, 0.20, 0.22, 0.28]

    lengths = [
        max(1, round(duration * p))
        for p in proportions
    ]

    # Pastikan jumlah durasi tepat sama dengan target.
    lengths[-1] += duration - sum(lengths)

    if lengths[-1] < 1:
        deficit = 1 - lengths[-1]
        lengths[-1] = 1
        lengths[0] -= deficit

    shots = []
    current = 0

    labels = [
        "HOOK / EXTREME CLOSE-UP",
        "REACTION / MEDIUM SHOT",
        "B-ROLL / DETAIL INSERT",
        "CONFLICT ESCALATION",
        "PUNCHLINE / FINAL REACTION",
    ]

    for label, length in zip(labels, lengths):
        start = current
        end = current + length

        shots.append({
            "start": start,
            "end": end,
            "label": label,
        })

        current = end

    return shots


def format_schedule(shots):
    return "\n".join(
        f"[{s['start']:02d}s-{s['end']:02d}s] {s['label']}"
        for s in shots
    )


# ======================================================
# GENERATOR PROMPT
# ======================================================

def build_prompt(
    mode,
    profile,
    theme,
    subtheme,
    premise,
    duration,
    style,
    cta_choice,
    history,
):
    schedule = shot_schedule(duration)
    schedule_text = format_schedule(schedule)

    if mode == MODE_GLOBAL:
        character_rules = """
SKELETON CONTINUITY:
- The same main skeleton must appear throughout the video.
- Preserve skull shape, teeth, eye sockets, bone proportions,
  body structure, accessories, and color palette.
- Do not randomly redesign the skeleton between shots.
- Supporting characters must remain consistent too.
"""
    else:
        character_rules = """
LOCAL CHARACTER CONTINUITY:
- Maintain the same face, hair, clothing, and body proportions
  for every returning character.
- Respect Indonesian setting and cultural details.
- Horror is a setup for comedy, not a reason to abandon the punchline.
"""

    premise_text = premise.strip() or (
        "Invent an original, visually funny situation that fits "
        "the selected theme and subtheme."
    )

    return f"""
Create ONE original YouTube Shorts comedy story.

MODE: {mode}
TARGET REGION: {profile['region']}
OUTPUT LANGUAGE: {profile['language']}
DURATION: EXACTLY {duration} SECONDS TARGET
ASPECT RATIO: Vertical 9:16
VISUAL STYLE: {style}

THEME:
{theme}

SUBTHEME:
{subtheme}

USER PREMISE:
{premise_text}

CHARACTERS:
{profile['characters']}

MAIN PROTAGONIST:
{profile['protagonist']}

SETTING:
{profile['setting']}

DIALOGUE STYLE:
{profile['dialogue']}

VISUAL IDENTITY:
{profile['identity']}

{character_rules}

CTA RULE:
{cta_instruction(cta_choice, profile['language'])}

RECENT TITLES — AVOID REPETITION:
{json.dumps(history[-10:], ensure_ascii=False)}

STORY RULES:
1. Establish a clear visual hook immediately.
2. Make the premise understandable without exposition.
3. Use short, speakable dialogue that fits the duration.
4. Escalate the absurdity in a logical way.
5. Make the punchline surprising and specific to the selected subtheme.
6. Do not end with generic laughter instead of a real joke.
7. Do not let the CTA replace the punchline.
8. Keep all dialogue in the selected output language.
9. Maintain consistent characters, props, geography, and lighting.
10. Avoid excessive dialogue that cannot fit the target duration.

MANDATORY TIMELINE:
Use these shot intervals as the production structure:
{schedule_text}

INTEGRATED B-ROLL REQUIREMENTS:
B-roll MUST be embedded in the main flow_prompt at the relevant timestamps.
Do not output B-roll only as a detached list.

Include appropriate examples such as:
- Extreme close-up of facial expression.
- Close-up of hands, props, or important story objects.
- Reaction shot of the other character.
- Over-the-shoulder shot.
- Brief environmental cutaway.
- Final close-up or reaction freeze.

Choose only B-roll shots that strengthen this particular joke.
Do not interrupt dialogue or add unrelated scenes.
Use quick, readable cuts with continuous story geography.

EVERY SHOT MUST SPECIFY:
- Timestamp.
- Character action and expression.
- Camera angle and movement.
- Lighting and atmosphere.
- Dialogue when necessary.
- Relevant sound effect when appropriate.
- How the shot connects to the next shot.

AUDIO:
Specify dialogue delivery, ambience, and relevant sound effects.
Avoid excessive sound effects that obscure dialogue.

GOOGLE FLOW PROMPT:
The flow_prompt must be a complete ready-to-copy production prompt.
Include the character descriptions, setting, complete timed shot list,
integrated B-roll, lighting, camera movements, dialogue, sound effects,
transitions, and ending.

Do not ask Google Flow to generate unrelated separate videos.
All shots belong to ONE coherent vertical video.

Return valid JSON only:
{{
  "title": "Short memorable title",
  "hook": "Opening hook",
  "story": "Short story premise",
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
  "hashtags": "#Shorts #Comedy",
  "flow_prompt": "Complete Google Flow production prompt",
  "broll": [
    {{
      "shot": "Specific insert shot",
      "camera": "Camera angle and movement",
      "lighting": "Lighting description"
    }}
  ]
}}
"""


# ======================================================
# FALLBACK
# ======================================================

def fallback_idea(mode, theme, subtheme, premise, duration, cta_choice):
    if mode == MODE_GLOBAL:
        title = "The Skeleton's Worst Day at Work"
        hook = "BRO, THIS IS NOT MY JOB!"
        story = (
            premise.strip()
            or f"A skeleton faces an absurd situation: {subtheme}."
        )
        dialogue = [
            {
                "time": "00:00-00:02",
                "speaker": "SKELETON",
                "line": "Bro, this is NOT my job!",
            },
            {
                "time": "00:02-00:04",
                "speaker": "HUMAN",
                "line": "You're literally the only one qualified!",
            },
            {
                "time": "00:04-00:06",
                "speaker": "SKELETON",
                "line": "I don't even have a backbone!",
            },
            {
                "time": "00:06-00:08",
                "speaker": "HUMAN",
                "line": "Finally, an honest employee!",
            },
        ]
        punchline = "The skeleton removes one rib and uses it as a resignation letter."
        hashtags = "#Shorts #SkeletonComedy #3DComedy"
        setting = "A modern office with fluorescent lights."
    else:
        title = "Pocong Salah Pesan Bakso"
        hook = "WOI, BANG!"
        story = (
            premise.strip()
            or f"Pocong causes a ridiculous problem: {subtheme}."
        )
        dialogue = [
            {
                "time": "00:00-00:02",
                "speaker": "POCONG",
                "line": "Bang, bakso satu!",
            },
            {
                "time": "00:02-00:04",
                "speaker": "PEDAGANG",
                "line": "Lah, duitnya mana?",
            },
            {
                "time": "00:04-00:06",
                "speaker": "POCONG",
                "line": "Bayarnya pakai doa, Bang!",
            },
            {
                "time": "00:06-00:08",
                "speaker": "PEDAGANG",
                "line": "Kalau gitu, doain warung gue rame!",
            },
        ]
        punchline = "The pocong hops away while the vendor chases it with a bowl."
        hashtags = "#Shorts #HororKomedi #Pocong"
        setting = "A foggy Indonesian bakso cart at night."

    schedule = shot_schedule(duration)

    flow_prompt = f"""
Create ONE coherent cinematic 3D comedy short, vertical 9:16,
target duration {duration} seconds.

THEME: {theme}
SUBTHEME: {subtheme}
STORY: {story}
SETTING: {setting}

CHARACTER CONTINUITY:
Keep character design, proportions, clothing, props, and lighting
consistent from beginning to end.

TIMED SHOTS:
{format_schedule(schedule)}

SHOT DETAILS:
Opening: Start with an expressive extreme close-up and a quick camera push-in.
Reaction: Cut to the other character's immediate reaction.
B-roll insert: Close-up of an important prop or moving hands, followed by
a quick reaction cutaway. Keep this insert connected to the joke.
Escalation: Medium shot showing the problem becoming more ridiculous.
Punchline: Finish with a clear visual gag and a final reaction close-up.

DIALOGUE:
{json.dumps(dialogue, ensure_ascii=False)}

PUNCHLINE:
{punchline}

CTA:
{cta_instruction(cta_choice, 'English' if mode == MODE_GLOBAL else 'Bahasa Indonesia')}

VISUALS:
Clean cinematic 3D rendering, vertical 9:16, detailed materials,
expressive animation, controlled motion blur, cinematic lighting,
clear silhouettes, consistent character design, readable actions.

AUDIO:
Use natural dialogue, environmental ambience, and one or two relevant
comedic sound effects. Avoid sound that overwhelms the dialogue.

B-ROLL:
Integrate close-ups, object inserts, and reaction shots directly
between the main shots. Do not create separate unrelated videos.
"""

    return {
        "title": title,
        "hook": hook,
        "story": story,
        "dialogue": dialogue,
        "punchline": punchline,
        "ending": "End with a brief visual reaction.",
        "cta_note": (
            "Fallback example; revise the CTA manually if needed."
        ),
        "hashtags": hashtags,
        "flow_prompt": flow_prompt,
        "broll": [
            {
                "shot": "Close-up of an important prop",
                "camera": "Macro insert with shallow depth of field",
                "lighting": "Cinematic key light",
            },
            {
                "shot": "Character reaction",
                "camera": "Tight reaction close-up",
                "lighting": "Contrasting rim light",
            },
        ],
    }


# ======================================================
# SIDEBAR
# ======================================================

st.title("💀 Cadas Resonance S
