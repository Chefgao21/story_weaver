# 📖 Story Weaver
### An AI-Powered Collaborative Storytelling App

> Write stories with an AI co-author

---

## Setup Instructions

### Prerequisites
- Python 3.9 or higher [download here](https://www.python.org/downloads/)
- A free Groq API key [console.groq.com](https://console.groq.com)

### 1. Clone or download the project
```bash
cd story_weaver
```

### 2. Activate your Python environment

**If you use Conda (recommended):**
```bash
conda activate base
```

**If you don't have Conda, create a venv instead:**
```bash
# Mac / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Add your API key
```bash
cp .env.example .env
```
Open `.env` and replace the placeholder:
```
GROQ_API_KEY=gsk_your_key_here
```

### 5. Run the app
```bash
streamlit run app.py
```

Opens automatically at **http://localhost:8501**

---

## Model & Provider

| Setting | Value |
|---|---|
| **Provider** | [Groq](https://console.groq.com) |
| **Model** | `llama-3.3-70b-versatile` |

---

## Final System Prompt

The system prompt is constructed in `prompts.py` with `build_system_prompt()`. 

```
You are a masterful collaborative storyteller writing in the {genre} genre.

GENRE: {genre}
GENRE RULES:
{genre_specific_rules}

KNOWN CHARACTERS (stay 100% consistent with these):
- {name}: {description}
- {name}: {description}

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
```

Each genre has its own rule block. For example, **Horror**:
```
Build dread slowly — atmosphere before monsters. Use sensory detail: sounds,
smells, textures. Leave some things unexplained — the imagination is the best
horror engine. Never resolve tension cheaply. Let consequences feel real and permanent.
```

---

## Memory & Consistency Strategy


### Layer 1 — Full history in every call
Every API call receives the entire story text concatenated from all turns. 

### Layer 2 — Structured character registry
After every AI turn, a second lightweight API call extracts named characters and their descriptions into a dictionary.

This character registry is injected directly into the system prompt on every subsequent call. Even if the model's attention drifts from early paragraphs, the character facts are re-asserted at the system level where they carry the most weight.

### Layer 3 — Adaptive story bible
The biggest memory risk in long stories is that LLMs pay less attention to content buried deep in a long context. The character registry helps, but it only covers characters. The story bible covers everything else. After 8 AI turns (when the story is long enough to benefit), a background call reads the full story and extracts a structured summary:
{
  "world_rules": "The world operates with mysticism and wonder...",
  "key_events": "The golden monkey arrived at the oasis and encountered...",
  "character_facts": "The monk is cautious but curious, the warrior is measured...",
  "unresolved_threads": "The hidden truth behind the oasis energy remains unexplained..."
}
This bible is injected into the system prompt on every subsequent call. The system prompt has the highest attention weight, so these facts act as hard anchors the model cannot drift away from. The bible refreshes every 5 AI turns to stay current. It adds zero overhead for short stories (turns 1–7), then activates exactly when long-context drift becomes a risk.

### Layer 4 — Contradiction guard
A specific instruction tells the model to correct user input that contradicts established facts. This prevents the model from going along with prompts like "Aldric studied her face carefully" when Aldric is established as blind.


## Bonus Features Implemented

| Feature | Description |
|---|---|
| 🎭 **Genre Remix** | Rewrites the latest AI passage in any other genre while keeping the same plot events and characters. Users can choose to replace the original or discard. |
| 👥 **Live Character Tracker** | After each AI turn, a background call extracts named characters and descriptions. This is shown in the sidebar and updated automatically. |
| 🎨 **Visualization Prompt Generator** | Converts the latest story passage into a structured image generation prompt ready to paste into DALL·E, Midjourney, or Flux. |
| 📥 **Export as Markdown** | Downloads the full story as a `.md` file with title, character list, and formatted prose. |
| ↩️ **Undo Last AI Turn** | Removes the last AI-generated turn (and any user addition that preceded it) from the story without needing an API call. |
| ⏳ **Rate-limit retry with countdown** | On Groq rate limit errors, the app retries up to 3 times with a live countdown timer between attempts. |

---

## One Thing That Did Not Work Well at First

**Problem: Sometimes the model would slightly go along with user inputs even if they contradicts established facts.**

To test the memory of the model, I first gave it a prompt where I established that the main character was blind. Approximately 8 turns later, I entered a prompt where I said that the main character held up a candle to see a painting. This is an obvious contradiction since the blind character has no use for a lamp. Ideally, the model would work around this by reframing the action. However, the response was "the candle's flame danced across Mira's features, Aldric's sightless eyes seemed to bore into its very soul". While this isn't terrible since it still mentions that Aldric is sightless, it still insinuates that the light is helping Aldric get a better view. 

**What I changed:**

I added another part to absolute rules in my system prompt. I added "If the user's input contradicts an established character trait (e.g. a blind character "seeing" something), silently correct it in your continuation rather than accepting the contradiction".

When testing the model again, it was less agreeable and would firmly stick to established facts

---

## What I Would Improve With Another Day

**Dynamic character state tracking**
The current character registry only appends new characters but never updates old ones. This means by turn 20, the system prompt might tell the model that a character is "a mysterious traveler with unknown motives" when the story already revealed them as a traitor. With another day I would create a character state object that tracks current emotional state, key relationships, and recent significant actions. This would make the character injection in the system prompt a better representation of who each character is right now, not just who they were when they were first introduced.

**better management for longer stories**
Right now the app sends the full story text on every single call. Groq's context window for LLaMA 3.3 70B is 128k tokens, and a long collaborative story with detailed prose can burn through that fast. More importantly, even within the context window, models pay significantly less attention to content in the middle of a long input. With another day I'd replace the full-story dump with a sliding window plus summary approach. I would always include the last 4-5 turns verbatim and replace everything before that with a rolling prose summary. This would not be the structured bible, but a flowing 300-word narrative recap that reads like the "previously on..." of a TV show. This keeps the token count bounded no matter how long the story gets, and actually puts the most important content in the beginning and end of the context positions. 
