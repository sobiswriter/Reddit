import json
import os
import time
import random
import dotenv
dotenv.load_dotenv()
# --- CONFIGURATION ---
try:
    import google.generativeai as genai
except Exception:
    genai = None

NUM_TURNS = 10
TACTIC_COOLDOWN = 2
API_KEY = os.environ.get('GENAI_API_KEY')
model = None

if genai is not None and API_KEY:
    try:
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
    except Exception as e:
        print(f"Error configuring Google AI: {e}")
        model = None

if model is None:
    print("WARNING: Google AI SDK not configured. Using a local dummy model.")
    class _DummyResponse:
        def __init__(self, text):
            self.text = text
    class _DummyModel:
        def generate_content(self, prompt):
            if "style" in str(prompt): return _DummyResponse("two_to_three_sentence_reply")
            if "tactic" in str(prompt): return _DummyResponse("ask_clarifying_question")
            return _DummyResponse("This is a 60/40 balanced simulated reply.")
    model = _DummyModel()

def load_persona(persona_name):
    # ... (unchanged) ...
    try:
        with open(os.path.join('personas', f'{persona_name}.json'), 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_ai_response(persona_data, prompt, use_full_backstory=False):
    # ... (unchanged) ...
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
    print("--- SIMULATION START ---")
    
    persona1 = load_persona("helios")
    persona2 = load_persona("nyx")
    if not persona1 or not persona2:
        print("Error loading persona files.")
        return

    tactic_history = {p['name']: [] for p in [persona1, persona2]}

    # ... (Initial post logic is unchanged) ...
    topic = "The rise of AI-generated art."
    print(f"Subreddit: /r/ArtificialCreativity\nTopic: {topic}\n")
    post_prompt = f"You are starting a new thread on the topic: '{topic}'. Write a concise opening post of 2-4 paragraphs to get the discussion going."
    initial_post = get_ai_response(persona1, post_prompt, use_full_backstory=True)
    print(f"[POST by {persona1['name']}]: {initial_post}\n")
    conversation_thread = [f"[POST by {persona1['name']}]: {initial_post}"]
    current_commenter_persona = persona2
    
    for _ in range(NUM_TURNS):
        print("-" * 20)
        time.sleep(1)

        persona_name = current_commenter_persona['name']
        
        # --- UPDATED: THE 60/40 DECISION LOGIC ---

        # STEP 1: CHOOSE REPLY STYLE (60% Logical, 40% Impulsive)
        if random.random() < 0.4: # 40% chance for an impulsive choice
            chosen_style = random.choice(current_commenter_persona['reply_style_preference'])
            print(f"<{persona_name} impulsively chooses style: {chosen_style}>")
        else: # 60% chance for a logical choice
            last_message = conversation_thread[-1]
            style_prompt = f"""
            Analyze the last comment: "{last_message}". Consider its length and tone.
            Based on that analysis, what is the most logical reply style to use?
            Your available styles: {current_commenter_persona['reply_style_preference']}
            Respond with ONLY the name of your chosen style.
            """
            chosen_style = get_ai_response(current_commenter_persona, style_prompt, use_full_backstory=False)
            print(f"<{persona_name} logically chooses style: {chosen_style}>")

        # STEP 2: CHOOSE TACTIC (60% Logical, 40% Impulsive)
        unavailable_tactics = tactic_history[persona_name]
        available_tactics = [t for t in current_commenter_persona['possible_tactics'] if t not in unavailable_tactics]
        if not available_tactics:
            available_tactics = current_commenter_persona['possible_tactics']

        if random.random() < 0.4: # 40% chance for an impulsive choice
            chosen_tactic = random.choice(available_tactics)
            print(f"<{persona_name} impulsively chooses tactic: {chosen_tactic}>")
        else: # 60% chance for a logical choice
            tactic_prompt = f"""
            Your chosen reply style is '{chosen_style}'. Based on the last comment and your personality, what is the most logical debate tactic to use?
            Your available tactics (you cannot use any on cooldown): {available_tactics}
            Respond with ONLY the name of your chosen tactic.
            """
            chosen_tactic = get_ai_response(current_commenter_persona, tactic_prompt, use_full_backstory=False)
            print(f"<{persona_name} logically chooses tactic: {chosen_tactic}>")
        
        tactic_history[persona_name].append(chosen_tactic)
        if len(tactic_history[persona_name]) > TACTIC_COOLDOWN:
            tactic_history[persona_name].pop(0)

        # STEP 3: GENERATE THE FINAL REPLY
        # ... (rest of the logic is unchanged) ...
        thread_context = "\n".join(conversation_thread)
        memory_recall_instruction = ""
        use_full_backstory = False

        if "anecdote" in chosen_tactic:
            memory_recall_instruction = f"To do this, you MUST briefly reference your personal backstory to make your point."
            use_full_backstory = True

        reply_prompt = f"""
        This is the conversation so far:
        {thread_context}

        Your Task: Write a reply.
        - Your chosen reply style is: **{chosen_style}**.
        - Your chosen debate tactic is: **{chosen_tactic}**.
        - {memory_recall_instruction}
        - CRUCIALLY, your reply MUST reflect your specific voice and speech patterns.
        """
        
        reply = get_ai_response(current_commenter_persona, reply_prompt, use_full_backstory=use_full_backstory)
        
        reply_text = f"[REPLY by {current_commenter_persona['name']}]: {reply}"
        print(f"{reply_text}\n")

        conversation_thread.append(reply_text)
        current_commenter_persona = persona1 if current_commenter_persona['name'] == persona2['name'] else persona2

    print("--- SIMULATION END ---")

if __name__ == "__main__":
    run_simulation()