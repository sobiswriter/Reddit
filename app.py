import json
import os
import time
import random
import streamlit as st # NEW: We import Streamlit
import dotenv

dotenv.load_dotenv()

# Reuse SDK/model and persona helpers from mainr to avoid duplication
import mainr
from mainr import load_persona, get_ai_response
# expose model and genai locally for any downstream needs
genai = getattr(mainr, 'genai', None)
model = getattr(mainr, 'model', None)

# --- CORE SIMULATION FUNCTIONS ---
# ... use load_persona and get_ai_response imported from mainr.py

def run_simulation(participants, num_turns):
    """
    Runs the simulation and yields each conversational turn as it happens.
    This allows the front-end to update in real-time.
    """
    # MODERATOR: RANDOMLY SELECT A TOPIC
    try:
        with open('topics.json', 'r') as f:
            topic_data = random.choice(json.load(f))
        subreddit = topic_data['subreddit']
        topic = topic_data['topic']
        yield {'author': 'MODERATOR', 'text': f"Today's discussion is in **{subreddit}** on the topic: *{topic}*"}
    except Exception as e:
        st.error(f"Error loading topics: {e}"); return

    # LOAD PARTICIPANTS
    personas = [load_persona(name) for name in participants]
    if any(p is None for p in personas): return

    # tactic cooldown value (fall back to 2 if mainr doesn't define it)
    TACTIC_COOLDOWN = getattr(mainr, 'TACTIC_COOLDOWN', 2)
    tactic_history = {p['name']: [] for p in personas}

    # RANDOMLY SELECT FIRST POSTER
    first_poster = random.choice(personas)
    post_prompt = f"You are starting a new thread in {subreddit} on the topic: '{topic}'. Write a concise opening post."
    initial_post = get_ai_response(first_poster, post_prompt, use_full_backstory=True)
    yield {'author': first_poster['name'], 'text': initial_post, 'is_post': True}

    conversation_thread = [f"[POST by {first_poster['name']}]: {initial_post}"]

    # DYNAMIC TURN-TAKING LOOP (mirrors mainr.py smart/impulsive logic)
    turn_index = personas.index(first_poster)
    for _ in range(num_turns * len(personas)):
        turn_index = (turn_index + 1) % len(personas)
        current_commenter_persona = personas[turn_index]
        persona_name = current_commenter_persona['name']

        # STEP 1: CHOOSE REPLY STYLE (60% Impulsive, 40% Logical)
        if random.random() < 0.65:
            chosen_style = random.choice(current_commenter_persona.get('reply_style_preference', ['neutral']))
            yield {'author': 'MODERATOR', 'text': f"<{persona_name} impulsively chooses style: {chosen_style}>"}
        else:
            last_message = conversation_thread[-1]
            style_prompt = (
                f"Given the last comment was: \"{last_message[:200]}...\"\n"
                f"Which of these reply styles is the most logical choice for you? {current_commenter_persona.get('reply_style_preference', [])}\n"
                "Just simply choose ONE option from the list, no need to explain why."
            )
            chosen_style = get_ai_response(current_commenter_persona, style_prompt, use_full_backstory=False)
            yield {'author': 'MODERATOR', 'text': f"<{persona_name} logically chooses style: {chosen_style}>"}

        # STEP 2: CHOOSE TACTIC (50% Impulsive, 50% Logical) with cooldown
        unavailable_tactics = tactic_history.get(persona_name, [])
        available_tactics = [t for t in current_commenter_persona.get('possible_tactics', []) if t not in unavailable_tactics]
        if not available_tactics:
            available_tactics = current_commenter_persona.get('possible_tactics', [])

        if random.random() < 0.5:
            chosen_tactic = random.choice(available_tactics)
            yield {'author': 'MODERATOR', 'text': f"<{persona_name} impulsively chooses tactic: {chosen_tactic}>"}
        else:
            tactic_prompt = (
                f"Your chosen reply style will be '{chosen_style}'.\nGiven the last comment, which of these tactics is the most logical choice for you? {available_tactics}\n"
                "Just simply choose ONE option from the list, no need to explain why"
            )
            chosen_tactic = get_ai_response(current_commenter_persona, tactic_prompt, use_full_backstory=False)
            yield {'author': 'MODERATOR', 'text': f"<{persona_name} logically chooses tactic: {chosen_tactic}>"}

        # update tactic history and enforce cooldown
        tactic_history.setdefault(persona_name, []).append(chosen_tactic)
        if len(tactic_history[persona_name]) > TACTIC_COOLDOWN:
            tactic_history[persona_name].pop(0)

        # STEP 3: GENERATE THE FINAL REPLY
        thread_context = "\n".join(conversation_thread)
        memory_recall_instruction = ""
        use_full_backstory = False
        if isinstance(chosen_tactic, str) and "anecdote" in chosen_tactic.lower():
            memory_recall_instruction = "If required you can briefly reference your personal backstory to make your point."
            use_full_backstory = True

        reply_prompt = (
            f"The conversation so far:\n{thread_context}\n\nYour Task: Write a reply.\n"
            f"- Style: {chosen_style}\n- Tactic: {chosen_tactic}\n- {memory_recall_instruction}\n- CRUCIALLY, you MUST reflect your specific voice."
        )

        reply = get_ai_response(current_commenter_persona, reply_prompt, use_full_backstory=use_full_backstory)
        yield {'author': persona_name, 'text': reply}
        conversation_thread.append(f"[REPLY by {persona_name}]: {reply}")
        time.sleep(1)

# --- STREAMLIT FRONT-END ---
st.set_page_config(layout="centered", page_title="Genesis Chamber")
st.title("🤖 The Genesis Chamber")
st.caption("An AI-driven conversation simulator.")

# Sidebar for configuration
st.sidebar.header("Simulation Settings")
# session storage for moderator remarks so they can be hidden/viewed later
if 'mod_remarks' not in st.session_state:
    st.session_state['mod_remarks'] = []

# Option to show moderator remarks inline (hidden by default)
show_mod_inline = st.sidebar.checkbox("Show moderator remarks inline", value=False)

# Expander with a dropdown to inspect moderator remarks (keeps them hidden in chat)
with st.sidebar.expander("Moderator remarks"):
    mod_list = st.session_state.get('mod_remarks', [])
    if mod_list:
        selected_mod = st.selectbox("View a moderator remark:", options=mod_list, key='mod_select')
        if selected_mod:
            st.info(selected_mod)
    else:
        st.write("(no moderator remarks yet)")
try:
    all_persona_files = [f.split('.')[0] for f in os.listdir('personas') if f.endswith('.json')]
    default_selection = [p for p in ["helios", "nyx"] if p in all_persona_files]
    selected_participants = st.sidebar.multiselect("Choose Participants:", all_persona_files, default=default_selection)
except FileNotFoundError:
    st.sidebar.error("'personas' folder not found!")
    selected_participants = []

num_turns = st.sidebar.slider("Number of Replies (per participant):", 1, 10, 3)

if st.sidebar.button("🚀 Run Simulation", use_container_width=True):
    if len(selected_participants) < 2:
        st.sidebar.warning("Please select at least two participants.")
    else:
        st.info("Simulation in progress... The AI personas are thinking. 🧠")

        # initialize storage for this run
        st.session_state['chat_entries'] = []
        st.session_state['mod_remarks'] = []

        # placeholder to update chat progressively
        chat_placeholder = st.empty()

        # run the simulation and stream entries into the UI as they arrive
        for entry in run_simulation(selected_participants, num_turns):
            # persist entry immediately so toggles/readers don't reset conversation
            st.session_state['chat_entries'].append(entry)
            if entry.get('author') == 'MODERATOR':
                st.session_state['mod_remarks'].append(entry.get('text', ''))

            # render current conversation snapshot into the placeholder
            with chat_placeholder.container():
                for e in st.session_state['chat_entries']:
                    # respect the inline moderator toggle (hide moderator lines if unchecked)
                    if e.get('author') == 'MODERATOR' and not show_mod_inline:
                        continue

                    # render posts vs replies slightly differently
                    if e.get('is_post'):
                        st.markdown(f"**{e['author']}** (post): {e['text']}")
                    else:
                        st.write(f"**{e['author']}**: {e['text']}")

            # small pause so UI updates feel smooth (and to avoid tight loop)
            time.sleep(0.3)

        st.success("Simulation Complete!")

# Render the conversation from session state so toggling moderator remarks doesn't reset it
chat_container = st.container()
entries = st.session_state.get('chat_entries', [])
if entries:
    with chat_container:
        for entry in entries:
            if entry.get('author') == 'MODERATOR':
                # ensure moderator remarks are also kept in mod_remarks for the inspector
                if entry['text'] not in st.session_state['mod_remarks']:
                    st.session_state['mod_remarks'].append(entry['text'])
                if show_mod_inline:
                    st.info(entry['text'])
            else:
                with st.chat_message(name=entry.get('author')):
                    st.markdown(entry.get('text', ''), unsafe_allow_html=True)
else:
    with chat_container:
        st.write("No conversation yet. Press 'Run Simulation' to start.")