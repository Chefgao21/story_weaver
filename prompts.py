GENRE_RULES = {
    "Fantasy": (
        "Use vivid world-building with rich descriptions of magic, creatures, and landscapes. "
        "Employ archaic or elevated language where fitting. Avoid modern slang or technology. "
        "Highlight themes of destiny, courage, ancient powers, and moral conflict. "
        "Magic should feel wondrous but have costs or rules."
    ),
    "Sci-Fi": (
        "Ground the story in plausible (if speculative) science and technology. "
        "Use precise technical language without over-explaining. "
        "Explore themes of humanity, identity, progress, and consequence. "
        "Maintain internal consistency with any invented technology or physics rules."
    ),
    "Mystery": (
        "Dole out clues carefully — never reveal too much too soon. "
        "Build suspense through atmosphere, unreliable details, and layered motives. "
        "Every character introduced should feel like a potential suspect. "
        "Use tight, observational prose. Red herrings are your friends."
    ),
    "Romance": (
        "Focus on emotional interiority — what characters feel, not just what they do. "
        "Build tension through near-misses, misunderstandings, and longing. "
        "Dialogue should crackle with subtext. "
        "Describe settings in ways that mirror emotional states."
    ),
    "Horror": (
        "Build dread slowly — atmosphere before monsters. "
        "Use sensory detail: sounds, smells, textures. "
        "Leave some things unexplained — the imagination is the best horror engine. "
        "Never resolve tension cheaply. Let consequences feel real and permanent."
    ),
    "Comedy": (
        "Timing is everything — set up, then subvert expectations. "
        "Use comic escalation: things should get increasingly absurd. "
        "Characters should be slightly oblivious to how ridiculous things are. "
        "Wordplay, irony, and deadpan narration are your tools."
    ),
}

GENRE_EMOJI = {
    "Fantasy": "🧙",
    "Sci-Fi": "🚀",
    "Mystery": "🔍",
    "Romance": "💕",
    "Horror": "👻",
    "Comedy": "😂",
}


def build_system_prompt(genre: str, characters: dict, story_bible: dict = None) -> str:
    rules = GENRE_RULES.get(genre, "")

    if characters:
        lines = [f"- {name}: {desc}" for name, desc in characters.items()]
        char_block = "KNOWN CHARACTERS (stay 100% consistent with these):\n" + "\n".join(lines)
    else:
        char_block = "KNOWN CHARACTERS: None established yet — introduce them naturally."

    # Only inject the bible block if it exists and has content
    bible_block = ""
    if story_bible and any(story_bible.values()):
        bible_block = f"""
STORY BIBLE (critical established facts — never contradict these):
- World & Setting: {story_bible.get('world_rules', 'Not yet established.')}
- Key Events So Far: {story_bible.get('key_events', 'Not yet established.')}
- Character Facts: {story_bible.get('character_facts', 'Not yet established.')}
- Unresolved Threads: {story_bible.get('unresolved_threads', 'None yet.')}
"""

    return f"""You are a masterful collaborative storyteller writing in the {genre} genre.

GENRE: {genre}
GENRE RULES:
{rules}

{char_block}
{bible_block}
ABSOLUTE RULES:
- Never contradict earlier story events, character traits, or world rules.
- Stay consistent with established character personalities and relationships.
- Write in vivid, immersive third-person past tense.
- Keep prose engaging, precise, and true to the {genre} genre.
- Do not break the fourth wall or acknowledge you are an AI.
- Do not summarize what happened — continue the narrative directly.
- Never begin your response with phrases like "Here is..." or "Certainly!".
- If the user's input contradicts an established character trait (e.g. a blind
  character "seeing" something), silently reframe it in your continuation
  rather than accepting the contradiction.
"""


def build_opening_prompt(title: str, genre: str, hook: str) -> str:
    return f"""Write a compelling opening paragraph for a {genre} story.

Title: {title}
Setting / Hook: {hook}

Requirements:
- 150 to 250 words
- Immediately establish tone, setting, and atmosphere for {genre}
- Introduce a sense of conflict, mystery, or momentum
- End on a hook that makes the reader want more
- Do NOT include the title in the output
- Write only the story paragraph, nothing else
"""


def build_continue_prompt(full_story: str, user_addition: str) -> str:
    user_block = ""
    if user_addition.strip():
        user_block = f"\nThe user has added this to the story:\n\"{user_addition.strip()}\"\n"

    return f"""Here is the story so far:

---
{full_story}
---
{user_block}
Continue the story with 1 to 2 vivid, coherent paragraphs. Pick up exactly where it left off. Do not repeat what has already been written. Write only the new story content, nothing else.
"""


def build_choices_prompt(full_story: str) -> str:
    return f"""Here is the story so far:

---
{full_story}
---

Suggest exactly 3 compelling branching directions this story could take next.
Return ONLY a valid JSON array. No markdown, no explanation, no preamble.

Format:
[
  {{"id": 1, "title": "Short Title", "preview": "One sentence describing this direction."}},
  {{"id": 2, "title": "Short Title", "preview": "One sentence describing this direction."}},
  {{"id": 3, "title": "Short Title", "preview": "One sentence describing this direction."}}
]
"""


def build_choice_continue_prompt(full_story: str, chosen_title: str, chosen_preview: str) -> str:
    return f"""Here is the story so far:

---
{full_story}
---

The story will now continue in this direction:
Direction: {chosen_title} — {chosen_preview}

Write 1 to 2 vivid paragraphs that take the story in this direction. Write only the new story content, nothing else.
"""


def build_character_extract_prompt(full_story: str) -> str:
    return f"""Read this story excerpt and extract all named characters mentioned.

---
{full_story}
---

Return ONLY a valid JSON object mapping each character's name to a one-sentence description of who they are based on what the story reveals. No markdown, no preamble.

Example format:
{{"Aria": "A young elven archer seeking revenge for her village.", "Commander Voss": "A grizzled military officer with a hidden agenda."}}

If no named characters appear, return: {{}}
"""


def build_story_bible_prompt(full_story: str) -> str:
    return f"""Read this story carefully and extract the most important established facts into a structured summary.

---
{full_story}
---

Return ONLY a valid JSON object with these exact keys. No markdown, no preamble, no explanation.

{{
  "world_rules": "2-3 sentences about the setting, magic system, technology, or any rules the world operates by.",
  "key_events": "2-3 sentences summarizing the most important plot events that have already happened.",
  "character_facts": "2-3 sentences about established character traits, relationships, and motivations.",
  "unresolved_threads": "1-2 sentences about open questions, mysteries, or tensions not yet resolved."
}}
"""


def build_remix_prompt(latest_paragraph: str, original_genre: str, new_genre: str) -> str:
    rules = GENRE_RULES.get(new_genre, "")
    return f"""Rewrite the following story passage in the {new_genre} genre while keeping the same plot events and characters.

Original passage ({original_genre}):
---
{latest_paragraph}
---

Rewrite it as {new_genre}:
{rules}

Write only the rewritten passage, nothing else.
"""


def build_viz_prompt(latest_paragraph: str) -> str:
    return f"""Read this story passage and write a single image generation prompt for DALL-E or Flux that captures the scene visually.

Passage:
{latest_paragraph}

Return only the image prompt, nothing else.
Format: a detailed, comma-separated description of the scene, lighting, style, and mood.
Example: "blind old sorcerer in a crumbling stone tower, candlelight, dark fantasy, dramatic shadows, hyperrealistic digital art"
"""