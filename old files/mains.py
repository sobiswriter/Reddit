import json
import os
import time
import random
import dotenv

dotenv.load_dotenv()

# --- MASTER CONFIGURATION ---
PARTICIPANTS = ["helios", "nyx"]
NUM_TURNS = 10
TACTIC_COOLDOWN = 2

# --- SDK & MODEL CONFIGURATION ---
try:
    import google.generativeai as genai
    API_KEY = os.environ.get('GENAI_API_KEY')
    if API_KEY:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
    else:
        model = None
except ImportError:
    genai = None
    model = None

if model is None:
    print("WARNING: Using a local dummy model.")
    class _DummyResponse:
        def __init__(self, text): self.text = text
    class _DummyModel:
        def generate_content(self, prompt):
            return _DummyResponse("This is a simplified, direct simulated reply.")
    model = _DummyModel()

# --- CORE FUNCTIONS ---
def load_persona(persona_name):
    """Loads a persona JSON file from the 'personas' folder."""
    try:
        with open(os.path.join('personas', f'{persona_name}.json'), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Persona file for '{persona_name}' not found.")
        return None

def get_ai_response(persona_data, prompt, use_full_backstory=False):
    """Generates a response from the AI, embodying the given persona."""
    system_prompt = f"""
    You are a human being in an online discussion.
    Your identity:
    - Name: {persona_data['name']}
    - Archetype: {persona_data['archetype']}
    - From: {persona_data['demographics']['location']}
    - Voice: {persona_data['speech_patterns']}
    You must stay in character. Do not reveal you are an AI.
    """
    if use_full_backstory:
        system_prompt += f"""
        == SECRET KNOWLEDGE: YOUR BACKSTORY ==
        Your Bio: {persona_data['biography_summary']}
        Your Defining Moment: {persona_data['defining_moment']}
        """
    full_prompt = system_prompt + "\n---\n" + prompt
    try:
        response = model.generate_content(full_prompt)
        return response.text.strip()
    except Exception as e:
        return f"[Error: {e}]"

def run_simulation():
    """The main engine that runs the entire conversation simulation."""
    print("--- INITIALIZING SIMULATION PLATFORM ---")
    
    # MODERATOR: RANDOMLY SELECT A TOPIC
    try:
        with open('topics.json', 'r') as f:
            topic_data = random.choice(json.load(f))
        subreddit = topic_data['subreddit']
        topic = topic_data['topic']
        print(f"MODERATOR: Today's discussion will be in '{subreddit}' on the topic: '{topic}'")
    except Exception as e:
        print(f"Error loading topics: {e}"); return

    # LOAD PARTICIPANTS DYNAMICALLY
    personas = [load_persona(name) for name in PARTICIPANTS]
    if any(p is None for p in personas):
        print(f"Error: Could not load one or more personas. Aborting.")
        return
    print(f"PARTICIPANTS LOADED: {[p['name'] for p in personas]}\n")
    
    tactic_history = {p['name']: [] for p in personas}
    
    print("--- SIMULATION START ---")
    print(f"Subreddit: {subreddit}\nTopic: {topic}\n")

    # RANDOMLY SELECT FIRST POSTER
    first_poster = random.choice(personas)
    post_prompt = f"You are starting a new thread in {subreddit} on the topic: '{topic}'. Write a concise opening post."
    initial_post = get_ai_response(first_poster, post_prompt, use_full_backstory=True)
    print(f"[POST by {first_poster['name']}]: {initial_post}\n")
    
    conversation_thread = [f"[POST by {first_poster['name']}]: {initial_post}"]
    
    # DYNAMIC TURN-TAKING LOOP
    turn_index = personas.index(first_poster)
    for _ in range(NUM_TURNS * len(personas)):
        print("-" * 20)
        time.sleep(1)
        
        turn_index = (turn_index + 1) % len(personas)
        current_commenter_persona = personas[turn_index]
        persona_name = current_commenter_persona['name']
        
        # --- SIMPLIFIED "DIRECTOR" MODEL ---
        # The script makes all choices randomly. This prevents the AI from "thinking out loud".
        
        chosen_style = random.choice(current_commenter_persona['reply_style_preference'])
        print(f"<{persona_name} style: {chosen_style}>")

        unavailable_tactics = tactic_history[persona_name]
        available_tactics = [t for t in current_commenter_persona['possible_tactics'] if t not in unavailable_tactics]
        if not available_tactics: available_tactics = current_commenter_persona['possible_tactics']
        chosen_tactic = random.choice(available_tactics)
        print(f"<{persona_name} tactic: {chosen_tactic}>")
        
        tactic_history[persona_name].append(chosen_tactic)
        if len(tactic_history[persona_name]) > TACTIC_COOLDOWN:
            tactic_history[persona_name].pop(0)

        # GENERATE THE FINAL REPLY
        thread_context = "\n".join(conversation_thread)
        memory_recall_instruction = ""
        use_full_backstory = False
        if "anecdote" in chosen_tactic:
            memory_recall_instruction = "To do this, you MUST briefly reference your personal backstory to make your point."
            use_full_backstory = True
            
        reply_prompt = f"The conversation so far:\n{thread_context}\n\nYour Task: Write a reply.\n- Style: {chosen_style}\n- Tactic: {chosen_tactic}\n- {memory_recall_instruction}\n- CRUCIALLY, you MUST reflect your specific voice."
        
        reply = get_ai_response(current_commenter_persona, reply_prompt, use_full_backstory=use_full_backstory)
        reply_text = f"[REPLY by {persona_name}]: {reply}"
        print(f"{reply_text}\n")
        conversation_thread.append(reply_text)

    print("--- SIMULATION END ---")

if __name__ == "__main__":
    run_simulation()