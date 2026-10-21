import os
import json
import random
import re
import streamlit as st
from openai import OpenAI

# =========================================================
# CADAS RESONANCE STUDIO
# Local Horror Comedy + Global Skeleton Comedy
# =========================================================

st.set_page_config(
    page_title="Cadas Resonance Studio",
    page_icon="💀",
    layout="wide"
)

BASE_URL = os.getenv(
    "CLARIOHUB_BASE_URL",
    "https://" + "clariohub.id/v1"
)

MODE_LOCAL = "🇮🇩 Lokal Indonesia"
MODE_GLOBAL = "🌎 Global Skeleton"

MODEL_OPTIONS = {
    "Gemini 3.7 Flash": "clario/gemini-3.7-flash",
    "GPT 5.6 Sol": "clario/gpt-5.6-sol",
    "DeepSeek V4 Pro": "clario/deepseek-v4-pro",
    "DeepSeek V4 Flash": "clario/deepseek-v4-flash",
    "GLM 5.3 Flash": "clario/glm-5.3-flash",
}

CTA_OPTIONS = [
    "🧠 Smart CTA Otomatis",
    "😂 CTA Komedi",
    "⏳ CTA Cliffhanger",
    "🏆 CTA Tantangan",
    "🚫 Tanpa CTA",
]

VISUAL_STYLES = [
    "Cinematic 3D comedy",
    "Horror comedy cinematic",
    "Absurd comedy",
    "Dark cinematic comedy",
]

# =========================================================
# API
# =========================================================

def get_api_key():
    try:
        secret = st.secrets.get("CLARIOHUB_API_KEY", "")
        if secret:
            return str(secret).strip()
    except Exception:
        pass

    return os.getenv("CLARIOHUB_API_KEY", "").strip()


def call_ai(api_key, model, prompt):
    client = OpenAI(
        api_key=api_key,
        base_url=BASE_URL,
        timeout=90,
        max_retries=1,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert YouTube Shorts comedy writer "
                    "and cinematic 3D director. Create original, visual, "
                    "fast-paced short-form comedy. Follow the requested "
                    "language, characters, duration, CTA rules, and "
                    "visual continuity. Return valid JSON only."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0.9,
        max_tokens=3000,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("AI tidak memberikan respons.")

    content = content.strip()
    content = re.sub(
        r"^```(?:json)?\s*",
        "",
        content,
        flags=re.IGNORECASE,
    )
    content = re.sub(r"\s*```$", "", content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")

        if start < 0 or end <= start:
            raise RuntimeError(
                "Respons AI bukan JSON valid. Coba generate kembali."
            )

        data = json.loads(content[start:end + 1])

    if not isinstance(data, dict):
        raise RuntimeError("Format hasil AI tidak sesuai.")

    required = [
        "title",
        "hook",
        "story",
        "dialogue",
        "punchline",
        "ending",
        "hashtags",
    ]

    for field in required:
        if field not in data:
            data[field] = ""

    if not isinstance(data["dialogue"], list):
        data["dialogue"] = []

    data["dialogue"] = [
        item for item in data["dialogue"]
        if isinstance(item, dict)
    ]

    return data


# =========================================================
# MODE CONFIGURATION
# =========================================================

def get_mode_config(mode):
    if mode == MODE_LOCAL:
        return {
            "language": "Bahasa Indonesia",
            "region": "Indonesia",
            "characters": (
                "Pocong, kuntilanak, genderuwo, tuyul, "
                "hantu kos, zombie lokal, or other Indonesian folklore creatures"
            ),
            "protagonist": (
                "Anak kos, pemuda tongkrongan, penjaga warung, "
                "ojek online, or everyday Indonesian people"
            ),
            "settings": (
                "Kamar kos, gang sempit, warung kopi, "
                "kontrakan, pos ronda, or Indonesian neighborhood at night"
            ),
            "dialogue_style": (
                "Natural Indonesian conversational slang. "
                "Use expressions like 'Woi!', 'Lah kok?', "
                "'Gila lu!', 'Yaelah!', and 'Kena lu!'."
            ),
            "visual_identity": (
                "High-quality cinematic 3D characters inspired by "
                "Indonesian horror-comedy. Maintain consistent character "
                "design, anatomy, clothing, and facial expressions."
            ),
        }

    return {
        "language": "Natural conversational English",
        "region": "Global audience",
        "characters": (
            "A funny 3D skeleton character, zombie, goofy ghost, "
            "or expressive monster. The main recurring character "
            "must remain a consistent 3D skeleton."
        ),
        "protagonist": (
            "A relatable young adult, gamer, roommate, "
            "or expressive human character"
        ),
        "settings": (
            "Modern apartment, gaming room, convenience store, "
            "suburban kitchen, garage, or nighttime city street"
        ),
        "dialogue_style": (
            "Short, natural English internet humor. "
            "Use punchy reactions such as 'Bro, what?!', "
            "'No way!', 'You serious?', and 'Caught in 4K!'."
        ),
        "visual_identity": (
            "Clean cinematic 3D render. Keep the skeleton's skull shape, "
            "bone proportions, eye sockets, teeth, body structure, "
            "and accessories consistent throughout every shot. "
            "Expressive physical comedy, detailed materials, "
            "cinematic lighting, and polished 3D animation."
        ),
    }


# =========================================================
# CTA LOGIC
# =========================================================

def get_cta_instruction(cta_choice, language):
    if cta_choice == "🚫 Tanpa CTA":
        return """
        CTA RULE:
        Do not ask viewers to subscribe, like, comment, or follow.
        Focus entirely on the story, visual comedy, and punchline.
        """

    if cta_choice == "😂 CTA Komedi":
        return """
        CTA RULE:
        Include one short, funny subscribe request that is part
        of the character's ridiculous situation. Keep it natural.
        """

    if cta_choice == "⏳ CTA Cliffhanger":
        return """
        CTA RULE:
        Build a funny unresolved moment and invite viewers to
        follow or subscribe for the next part. Do not invent
        a continuation if the story does not support one.
        """

    if cta_choice == "🏆 CTA Tantangan":
        return """
        CTA RULE:
        Use a playful challenge related to the joke.
        Keep it short, lighthearted, and non-coercive.
        """

    return """
    SMART CTA RULE:
    Analyze the premise and decide whether a CTA helps the joke.
    If it fits, use one short, organic subscribe request.
    If it weakens the hook or punchline, omit it.
    Never force a CTA into every scene.
    """


# =========================================================
# PROMPT BUILDER
# =========================================================

def build_generation_prompt(
    mode,
    config,
    premise,
    duration,
    style,
    cta_choice,
    history,
):
    if mode == MODE_GLOBAL:
        character_rule = """
        SKELETON CONSISTENCY:
        - The main skeleton is the recurring protagonist.
        - Preserve the exact same skull, teeth, bone proportions,
          body structure, and accessories in every shot.
        - Do not randomly change character design.
        - Use clean cinematic 3D rendering, never live-action footage.
        """
    else:
        character_rule = """
        LOCAL CHARACTER CONSISTENCY:
        - Maintain consistent character appearance in every shot.
        - Use recognizable Indonesian locations and cultural details.
        - Horror elements should support comedy, not overpower it.
        """

    cta_rule = get_cta_instruction(cta_choice, config["language"])

    history_text = json.dumps(history[-10:], ensure_ascii=False)

    premise_text = premise.strip() or (
        "Invent a fresh, visually funny confrontation with an "
        "unexpected twist. Avoid overused jokes."
    )

    return f"""
Create ONE original YouTube Shorts comedy concept.

OUTPUT LANGUAGE: {config["language"]}
TARGET: {config["region"]}
DURATION: {duration} seconds
VISUAL STYLE: {style}
FORMAT: Vertical 9:16

USER PREMISE:
{premise_text}

CHARACTERS:
{config["characters"]}

PROTAGONIST:
{config["protagonist"]}

SETTING:
{config["settings"]}

DIALOGUE STYLE:
{config["dialogue_style"]}

VISUAL IDENTITY:
{config["visual_identity"]}

{character_rule}

CTA:
{cta_rule}

ANTI-REPETITION:
Recently generated titles:
{history_text}

Avoid repeating the same title, premise, punchline, character behavior,
or joke structure from the recent history.

STORY REQUIREMENTS:
1. Start with a strong visual or verbal hook in the first second.
2. Introduce a clear, easy-to-understand conflict.
3. Escalate the absurdity quickly.
4. Make the dialogue short enough for the requested duration.
5. End with a surprising visual gag, roast, or ironic punchline.
6. Keep character actions physically possible within the scene.
7. Use no unnecessary exposition.
8. Make the concept understandable without subtitles.
9. Do not let a CTA ruin the final punchline.
10. Avoid generic endings such as simply laughing without a joke.

SHOT STRUCTURE:
Divide the short into clear timed beats that fit the requested duration.

Include:
- A strong opening close-up or striking visual.
- A medium shot showing the conflict.
- A reaction shot or visual cutaway.
- A close-up for the important reveal.
- A final punchline shot.

B-ROLL INTEGRATION:
Create 3 to 5 brief B-roll inserts inside the same continuous video.
Use close-ups, hand details, object inserts, reaction shots,
over-the-shoulder shots, and short environmental cutaways.
B-roll must support the story and preserve character continuity.
Do not create unrelated scenes or a separate video.
Describe the lighting and camera angle for each important shot.

TIMING:
Every dialogue item must have a timestamp that fits within
the requested duration. Do not use a fixed 9-second timeline
when a different duration is requested.

Return valid JSON only using this structure:
{{
  "title": "Short memorable title",
  "hook": "Opening hook",
  "story": "Brief premise and story progression",
  "dialogue": [
    {{
      "time": "00:00-00:01",
      "speaker": "CHARACTER",
      "line": "Dialogue"
    }}
  ],
  "punchline": "The central comedic payoff",
  "ending": "Final visual reaction or twist",
  "cta_note": "CTA used or reason for omitting it",
  "hashtags": "#Shorts #Comedy",
  "flow_prompt": "Complete production-ready Google Flow prompt",
  "broll": [
    {{
      "shot": "B-roll description",
      "camera": "Camera angle and movement",
      "lighting": "Lighting description"
    }}
  ]
}}

The flow_prompt must be a complete, ready-to-copy video prompt.
Include character design, setting, timed shots, dialogue, camera angles,
lighting, integrated B-roll, sound effects, transitions, and ending.
Maintain clean cinematic 3D quality and vertical 9:16 composition.
Do not include explanations outside the JSON.
"""


# =========================================================
# FALLBACK
# =========================================================

def fallback_idea(mode, config, premise, duration, cta_choice):
    if mode == MODE_LOCAL:
        character = "POCОNG"
        other = "ANAK KOS"
        setting = "a dim Indonesian boarding-house room at night"
        hook = "WOI! BALIK SINI!"
        line2 = "Lah, lu ngapain di kamar gue?"
        line3 = "Gue cuma mau pinjam charger!"
        punchline = "Charger lu ada di leher lu, Bang!"
        title = "Pocong Pinjam Charger"
        tags = "#Shorts #HororKomedi #Pocong"
    else:
        character = "SKELETON"
        other = "GAMER"
        setting = "a modern gaming room at night"
        hook = "BRO! WAIT!"
        line2 = "Dude, why are you in my room?"
        line3 = "I need a charger for my bones!"
        punchline = "Your charger is plugged into your own rib cage!"
        title = "The Skeleton Needs a Charger"
        tags = "#Shorts #SkeletonComedy #3DComedy"

    if premise.strip():
        story = premise.strip()
    else:
        story = (
            f"{character} enters {setting} to borrow a phone charger, "
            "but the request becomes absurd."
        )

    dialogue = [
        {
            "time": "00:00-00:01",
            "speaker": character,
            "line": hook,
        },
        {
            "time": "00:01-00:03",
            "speaker": other,
            "line": line2,
        },
        {
            "time": "00:03-00:06",
            "speaker": character,
            "line": line3,
        },
        {
            "time": "00:06-00:08",
            "speaker": other,
            "line": punchline,
        },
    ]

    if cta_choice == "🚫 Tanpa CTA":
        cta_note = "Tanpa CTA; fokus pada punchline."
    elif cta_choice == "⏳ CTA Cliffhanger":
        cta_note = (
            "CTA cliffhanger belum ditambahkan otomatis oleh fallback; "
            "edit prompt atau generate ulang saat API tersedia."
        )
    elif cta_choice == "🧠 Smart CTA Otomatis":
        cta_note = "Fallback: CTA dilewati agar punchline tetap kuat."
    else:
        cta_note = (
            "Fallback: tambahkan CTA secara manual jika cocok "
            "dengan ritme cerita."
        )

    flow_prompt = f"""
Create one vertical 9:16 cinematic 3D comedy short, approximately
{duration} seconds long.

SETTING:
{setting}

CHARACTERS:
- {character}: expressive, consistent design.
- {other}: expressive comedic reactions.

STORY:
{story}

TIMED SHOTS:
0-1s: Extreme close-up. {character} suddenly faces the camera
and says: "{hook}". Dramatic key light and quick camera push-in.

1-3s: Medium shot. {other} reacts with confusion:
"{line2}". Slight handheld-style camera movement.

3-5s: Insert B-roll close-up of the character's hands and the charger.
Use detailed materials, shallow depth of field, and a quick cutaway.

5-7s: Reaction close-up. {character} says: "{line3}".
Use contrasting rim light and a comedic pause.

7-{duration}s: Two-shot for the reveal. {other} delivers:
"{punchline}". Finish with a visual reaction and brief freeze.

VISUAL STYLE:
Clean cinematic 3D render, vertical 9:16 composition,
expressive character animation, consistent design, dramatic lighting,
polished materials, readable silhouettes, precise comedic timing.

AUDIO:
Natural dialogue, subtle room ambience, one soft comedic sound effect
at the reveal. No music that overwhelms the dialogue.

CTA:
{cta_note}
"""

    return {
        "title": title,
        "hook": hook,
        "story": story,
        "dialogue": dialogue,
        "punchline": punchline,
        "ending": "The characters react awkwardly after the reveal.",
        "cta_note": cta_note,
        "hashtags": tags,
        "flow_prompt": flow_prompt,
        "broll": [
            {
                "shot": "Close-up of the charger and character hands",
                "camera": "Macro insert, shallow depth of field",
                "lighting": "Soft cinematic key light",
            },
            {
                "shot": "Confused reaction from the protagonist",
                "camera": "Tight reaction close-up",
                "lighting": "Contrasting rim light",
            },
            {
                "shot": "Two-character reveal",
                "camera": "Medium two-shot with quick push-in",
                "lighting": "Dramatic cinematic lighting",
            },
        ],
    }


# =========================================================
# SIDEBAR
# =========================================================

st.title("💀 Cadas Resonance Studio")
st.caption(
    "Satu studio untuk horor-komedi Indonesia dan skeleton comedy global."
)

with st.sidebar:
    st.header("⚙️ Pengaturan")

    mode = st.radio(
        "Pilih mode konten",
        [MODE_LOCAL, MODE_GLOBAL],
    )

    model_label = st.selectbox(
        "Model AI",
        list(MODEL_OPTIONS.keys()),
    )
    model = MODEL_OPTIONS[model_label]

    cta_choice = st.selectbox(
        "Strategi CTA",
        CTA_OPTIONS,
    )

    style = st.selectbox(
        "Gaya visual",
        VISUAL_STYLES,
    )

    duration = st.selectbox(
        "Durasi target",
        [5, 8, 10, 15, 20],
        index=2,
    )

    st.caption(
        "Durasi hasil akhir tetap bergantung pada kemampuan "
        "model video yang digunakan."
    )

    key = get_api_key()

    if not key:
        key = st.text_input(
            "ClarioHub API Key",
            type="password",
        ).strip()

    if key:
        st.success("API key tersedia")
    else:
        st.warning("Masukkan API key untuk menggunakan AI.")


# =========================================================
# MAIN INPUT
# =========================================================

config = get_mode_config(mode)

with st.expander("📋 Profil mode aktif", expanded=False):
    st.write("**Bahasa:**", config["language"])
    st.write("**Target:**", config["region"])
    st.write("**Karakter:**", config["characters"])
    st.write("**Lokasi:**", config["settings"])

st.subheader("📝 Ide Cerita")

premise = st.text_area(
    "Topik atau situasi (opsional)",
    placeholder=(
        "Contoh lokal: Pocong nagih utang Wi-Fi di kos.\n"
        "Contoh global: A skeleton tries to impress a gym trainer."
    ),
    height=100,
)

if "idea" not in st.session_state:
    st.session_state.idea = None

if "history_titles" not in st.session_state:
    st.session_state.history_titles = []

if st.button(
    "🔥 GENERATE KONTEN",
    type="primary",
    use_container_width=True,
):
    if not key:
        st.error(
            "API key belum tersedia. Masukkan API key di sidebar "
            "atau atur CLARIOHUB_API_KEY di Secrets."
        )
    else:
        prompt = build_generation_prompt(
            mode=mode,
            config=config,
            premise=premise,
            duration=duration,
            style=style,
            cta_choice=cta_choice,
            history=st.session_state.history_titles,
        )

        with st.spinner("Sedang merancang cerita dan prompt video..."):
            try:
                result = call_ai(key, model, prompt)

                # Fallback if the model omits the video prompt.
                if not result.get("flow_prompt"):
                    fallback = fallback_idea(
                        mode,
                        config,
                        premise,
                        duration,
                        cta_choice,
                    )
                    result["flow_prompt"] = fallback["flow_prompt"]

                result["mode"] = mode
                result["duration_seconds"] = duration
                result["visual_style"] = style
                result["cta_choice"] = cta_choice

                st.session_state.idea = result

                title = result.get("title", "").strip()
                if title:
                    st.session_state.history_titles.append(title)
                    st.session_state.history_titles = (
                        st.session_state.history_titles[-10:]
                    )

            except Exception as exc:
                st.error(f"Generate API gagal: {exc}")

                st.warning(
                    "Menampilkan ide cadangan lokal. "
                    "Ide ini tidak dihasilkan oleh API."
                )

                fallback = fallback_idea(
                    mode,
                    config,
                    premise,
                    duration,
                    cta_choice,
                )

                fallback["mode"] = mode
                fallback["duration_seconds"] = duration
                fallback["visual_style"] = style
                fallback["cta_choice"] = cta_choice

                st.session_state.idea = fallback


# =========================================================
# RESULTS
# =========================================================

result = st.session_state.idea

if result:
    st.divider()

    st.header(result.get("title", "Hasil Shorts"))

    st.caption(
        f"Mode: {result.get('mode', mode)} · "
        f"Durasi target: {result.get('duration_seconds', duration)} detik · "
        f"CTA: {result.get('cta_choice', cta_choice)}"
    )

    st.code(
        result.get("hashtags", "#Shorts #Comedy"),
        language=None,
    )

    tab_story, tab_flow, tab_broll, tab_json = st.tabs(
        [
            "📖 Struktur Cerita",
            "🎬 Prompt Google Flow",
            "🎥 B-Roll",
            "📦 Ekspor JSON",
        ]
    )

    with tab_story:
        st.subheader("🪝 Hook")
        st.write(result.get("hook", ""))

        st.subheader("📚 Premis")
        st.write(result.get("story", ""))

        st.subheader("🗣️ Dialog")

        for item in result.get("dialogue", []):
            st.markdown(
                f"**{item.get('time', '')} — "
                f"{item.get('speaker', 'CHARACTER')}**"
            )
            st.write(item.get("line", ""))

        st.subheader("💥 Punchline")
        st.write(result.get("punchline", ""))

        st.subheader("🎭 Ending")
        st.write(result.get("ending", ""))

        st.subheader("🎯 Catatan CTA")
        st.write(result.get("cta_note", ""))

    with tab_flow:
        flow_prompt = result.get("flow_prompt", "")

        st.text_area(
            "Prompt siap salin ke Google Flow",
            value=flow_prompt,
            height=500,
            key="flow_output",
        )

        st.download_button(
            "⬇️ Unduh Prompt .txt",
            data=flow_prompt,
            file_name="cadas_resonance_flow_prompt.txt",
            mime="text/plain",
            use_container_width=True,
        )

    with tab_broll:
        broll = result.get("broll", [])

        if not broll:
            st.info(
                "B-roll utama dijelaskan di dalam prompt Google Flow."
            )

        for index, shot in enumerate(broll, start=1):
            with st.expander(
                f"🎥 B-Roll {index}: {shot.get('shot', 'Shot')}",
                expanded=True,
            ):
                st.write("**Kamera:**", shot.get("camera", ""))
                st.write("**Lighting:**", shot.get("lighting", ""))

        st.caption(
            "B-roll merupakan bagian dari satu prompt video, "
            "bukan video terpisah."
        )

    with tab_json:
        export_data = json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )

        st.download_button(
            "⬇️ Unduh Paket JSON",
            data=export_data,
            file_name="cadas_resonance_package.json",
            mime="application/json",
            use_container_width=True,
        )

        st.json(result)

    if st.button("🗑️ Hapus Hasil dari Layar"):
        st.session_state.idea = None
        st.rerun()

st.divider()

st.caption(
    "Cadas Resonance Studio · Gunakan karakter dan gaya visual "
    "yang konsisten untuk membangun identitas channel."
)
