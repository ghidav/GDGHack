# app.py
import streamlit as st
import os
from dotenv import load_dotenv
from openai import OpenAI
# import random # Not directly used in this version of app.py
import time

from agents import Agent, UserAgent, INTERACTION_PROTOCOL
from quiz import run_streamlit_quiz
from critical_thinking import run_streamlit_critical_thinking
from utils import get_focal_points, display_media_content

# Load environment variables from .env file (if it exists)
load_dotenv()

# --- Page Configuration ---
st.set_page_config(
    page_title="AI Classroom Companion",
    page_icon="🧑‍🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Session State Initialization ---
# Centralized place for all session state keys used in the app
def init_session_state():
    if "api_key_valid" not in st.session_state:
        st.session_state.api_key_valid = False
    if "client" not in st.session_state:
        st.session_state.client = None
    if "agents" not in st.session_state:
        st.session_state.agents = {}
    if "focal_points" not in st.session_state:
        st.session_state.focal_points = []
    if "app_initialized" not in st.session_state: # Changed from "initialized" to avoid conflict
        st.session_state.app_initialized = False
    if "current_focal_point_descriptions" not in st.session_state:
        st.session_state.current_focal_point_descriptions = {} # Store {fp_text: description}
    # quiz_state and ct_state are managed within their respective modules

# Call initialization
init_session_state()


# --- Constants ---
SUBJECT = "The First Industrial Revolution"
TOPIC = "The Invention of the Steam Engine and its Societal Impact"
# MODEL_NAME = "google/gemini-flash-1.5" # Requires API key with access
# MODEL_NAME = "mistralai/mistral-7b-instruct:free" # A free option
MODEL_NAME = "nousresearch/nous-hermes-2-mixtral-8x7b-dpo" # A capable model on OpenRouter (check for free tier if needed)
# MODEL_NAME = "openai/gpt-3.5-turbo" # Standard, might not be free on OpenRouter
USER_AGENT_NAME = "User" # Define the user's agent name

# --- Sidebar for Configuration and Navigation ---
with st.sidebar:
    st.image("media/logo.png", width=100) # Add a logo if you have one in media folder
    st.header("⚙️ Configuration")
    
    # Attempt to get API key from environment first
    default_api_key = os.getenv("OPENROUTER_API_KEY", "")
    api_key_input = st.text_input(
        "Enter OpenRouter API Key",
        type="password",
        value=default_api_key if default_api_key else "", # Pre-fill if env var exists
        help="Get your API key from [OpenRouter.ai](https://openrouter.ai/keys)"
    )

    if api_key_input:
        if st.session_state.client is None or not st.session_state.api_key_valid:
            try:
                st.session_state.client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key_input,
                )
                # Test call to verify key (optional, but good for UX)
                st.session_state.client.models.list() 
                st.session_state.api_key_valid = True
                st.success("API key validated!")
                # Persist the validated key for OpenRouter if needed by agents
                os.environ["OPENROUTER_API_KEY"] = api_key_input 
            except Exception as e:
                st.session_state.client = None
                st.session_state.api_key_valid = False
                st.error(f"Invalid API key or connection error: {e}")
    else:
        st.warning("API key is required to enable AI features.")
        st.session_state.api_key_valid = False
        st.session_state.client = None


    st.divider()
    st.header("🧭 Navigate Demo")
    demo_option = st.radio(
        "Select Module:",
        ["🎓 Classroom Overview", "💡 Focal Points & Media", "📝 Interactive Quiz", "🤔 Critical Thinking Challenge"],
        key="demo_selection"
    )
    st.divider()
    st.markdown("<sub>Powered by AI Classroom Companion v0.2</sub>", unsafe_allow_html=True)


# --- Agent Initialization Function (called once API key is valid) ---
def initialize_classroom_agents():
    if not st.session_state.api_key_valid or st.session_state.client is None:
        st.error("Cannot initialize agents without a valid API key and client.")
        return False

    if st.session_state.app_initialized: # Already initialized
        return True

    with st.spinner("Setting up the AI classroom... Please wait."):
        student_agent_instructions = {
            "Marc": f"You are an enthusiastic and humorous student named Marc in a class about {SUBJECT}. You often use emojis and try to be funny, even if your answers are sometimes a bit off-topic or creatively incorrect. Keep responses concise.",
            "Paola": f"You are a highly knowledgeable, precise, and somewhat reserved student named Paola in a class about {SUBJECT}. Your answers are accurate, insightful, and directly address the question. You are polite but not overly talkative.",
        }
        ai_student_names = list(student_agent_instructions.keys())
        all_participant_names = ai_student_names + [USER_AGENT_NAME]

        temp_agents = {}

        # Teacher Agent
        teacher_base_prompt = f"You are an experienced and engaging teacher leading a class on {SUBJECT}, specifically focusing on {TOPIC}. Your goal is to educate, facilitate discussions, and assess student understanding. Be clear and encouraging."
        temp_agents["teacher"] = Agent(
            name="teacher", client=st.session_state.client, model=MODEL_NAME, instruction=teacher_base_prompt
        )
        teacher_protocol = INTERACTION_PROTOCOL.format(other_agents=", ".join(all_participant_names))
        temp_agents["teacher"].update_system_prompt_with_protocol(teacher_protocol)

        # AI Student Agents
        for name, instruction in student_agent_instructions.items():
            temp_agents[name] = Agent(name=name, client=st.session_state.client, model=MODEL_NAME, instruction=instruction)
            student_sees_others = ["teacher"] + [p_name for p_name in all_participant_names if p_name != name]
            student_protocol = INTERACTION_PROTOCOL.format(other_agents=", ".join(student_sees_others))
            temp_agents[name].update_system_prompt_with_protocol(student_protocol)

        # User-controlled Agent
        temp_agents[USER_AGENT_NAME] = UserAgent(
            name=USER_AGENT_NAME, instruction=f"You are a student named {USER_AGENT_NAME} in a class on {SUBJECT}."
        )
        user_sees_others = ["teacher"] + ai_student_names
        user_protocol_for_user_agent = INTERACTION_PROTOCOL.format(other_agents=", ".join(user_sees_others))
        temp_agents[USER_AGENT_NAME].update_system_prompt_with_protocol(user_protocol_for_user_agent)
        
        st.session_state.agents = temp_agents
        
        # Get focal points early
        fetched_focal_points = get_focal_points(st.session_state.agents["teacher"], SUBJECT, TOPIC, num_focal_points=3)
        st.session_state.focal_points = fetched_focal_points
        st.session_state.agents["teacher"].set_state("focal_points_list", fetched_focal_points)


        st.session_state.app_initialized = True
        st.success("AI Classroom is ready!")
        time.sleep(1) # Let user see the success message
        st.rerun() # Rerun to reflect initialized state
    return True


# Attempt to initialize agents if API key is valid and not already done
if st.session_state.api_key_valid and not st.session_state.app_initialized:
    initialize_classroom_agents()


# --- Main Content Area ---
if not st.session_state.api_key_valid:
    st.warning("👋 Welcome! Please enter your OpenRouter API key in the sidebar to activate the AI features and start the demo.")
    st.markdown("An API key from [OpenRouter.ai](https://openrouter.ai/) allows you to access various AI models.")
    st.info("Once the API key is set, the classroom simulation will initialize.")

elif not st.session_state.app_initialized:
    st.info("Classroom is initializing... If this takes too long, please check your API key and model selection.")
    # Could add a manual "Initialize/Retry" button here
else:
    # Classroom is initialized, proceed with selected demo option
    teacher_agent = st.session_state.agents["teacher"]
    user_as_agent = st.session_state.agents[USER_AGENT_NAME]
    ai_students_only_names = [name for name in st.session_state.agents.keys() if name not in ["teacher", USER_AGENT_NAME]]
    all_students_with_user_names = ai_students_only_names + [USER_AGENT_NAME]


    if demo_option == "🎓 Classroom Overview":
        st.header("🎓 Classroom Overview")
        st.markdown(f"Welcome to the virtual classroom for **{SUBJECT}**, focusing on **{TOPIC}**.")
        
        st.subheader("Meet Your Classmates & Teacher")
        cols = st.columns(len(st.session_state.agents))
        agent_names_sorted = ["teacher"] + ai_students_only_names + [USER_AGENT_NAME]

        for i, name in enumerate(agent_names_sorted):
            with cols[i]:
                avatar = "🧑‍🏫" if name == "teacher" else ("🤖" if name != USER_AGENT_NAME else "🧑‍💻")
                st.markdown(f"**{avatar} {name.capitalize()}**")
                if name == "teacher":
                    st.caption(f"Guides the lesson on {SUBJECT}.")
                elif name == USER_AGENT_NAME:
                    st.caption("This is you! Participate actively.")
                else: # AI Student
                    st.caption(st.session_state.agents[name].instruction.split('.')[0]) # Show first sentence of instruction


        st.subheader("📝 Sample Interaction: What is a Steam Engine?")
        sample_question = "Can anyone briefly explain what a steam engine is and its primary purpose during the Industrial Revolution?"
        
        if "overview_interaction" not in st.session_state:
             st.session_state.overview_interaction = {"question": sample_question, "responses": {}, "feedback": None}

        interaction_state = st.session_state.overview_interaction

        with st.chat_message("teacher", avatar="🧑‍🏫"):
            st.markdown(interaction_state["question"])

        # AI student responses (get them if not already present)
        for student_name in ai_students_only_names:
            if student_name not in interaction_state["responses"]:
                with st.spinner(f"{student_name} is typing..."):
                    # student_agent.clear_messages() # Make it stateless for this question
                    response = st.session_state.agents[student_name].chat(interaction_state["question"])
                    interaction_state["responses"][student_name] = response
            
            with st.chat_message(student_name, avatar="🤖" if student_name == "Marc" else "🧐"): # Specific avatars
                st.markdown(interaction_state["responses"][student_name])
        
        # User response
        user_response_overview = st.text_input("Your brief explanation:", key="overview_user_response")
        if st.button("Send My Explanation", key="overview_submit"):
            if user_response_overview.strip():
                interaction_state["responses"][USER_AGENT_NAME] = user_response_overview
                user_as_agent.add_message("assistant", user_response_overview) # Log it
                
                # Teacher feedback
                with st.spinner("Teacher is preparing feedback..."):
                    feedback_prompt = f"The question was: '{interaction_state['question']}'\n"
                    for name, resp_text in interaction_state["responses"].items():
                        feedback_prompt += f"{name} answered: '{resp_text}'\n"
                    feedback_prompt += "\nPlease provide a brief, consolidated feedback on these explanations, highlighting correct points and gently correcting any misconceptions. Address the class generally."
                    # teacher_agent.clear_messages()
                    feedback_text = teacher_agent.chat(feedback_prompt)
                    interaction_state["feedback"] = feedback_text
                st.rerun()
            else:
                st.warning("Please enter your explanation.")

        if USER_AGENT_NAME in interaction_state["responses"]:
             with st.chat_message(USER_AGENT_NAME, avatar="🧑‍💻"):
                st.markdown(interaction_state["responses"][USER_AGENT_NAME])


        if interaction_state["feedback"]:
            with st.chat_message("teacher", avatar="🧑‍🏫"):
                st.markdown("**Teacher's Feedback:**")
                st.markdown(interaction_state["feedback"])
        
        if st.button("Clear Sample Interaction", key="clear_overview"):
            del st.session_state.overview_interaction
            # Optionally clear agent messages related to this interaction if needed
            for name in ai_students_only_names:
                st.session_state.agents[name].clear_messages()
            teacher_agent.clear_messages()
            user_as_agent.clear_messages()
            st.rerun()


    elif demo_option == "💡 Focal Points & Media":
        st.header("💡 Lesson Focal Points & Rich Media")
        st.markdown("Explore the key concepts of our lesson on the Steam Engine.")

        if not st.session_state.focal_points:
            st.warning("Focal points are not yet defined. The teacher agent might be working on them or an error occurred.")
            if st.button("Try to Fetch Focal Points Again"):
                st.session_state.focal_points = get_focal_points(teacher_agent, SUBJECT, TOPIC)
                st.rerun()
        else:
            for i, fp_text in enumerate(st.session_state.focal_points):
                with st.expander(f"**Focal Point {i+1}: {fp_text}**", expanded=(i==0)):
                    # Get description for the focal point if not already fetched
                    if fp_text not in st.session_state.current_focal_point_descriptions:
                        with st.spinner(f"Teacher is preparing details for: {fp_text}..."):
                            # teacher_agent.clear_messages() # Make it stateless or provide context
                            desc_prompt = f"Please provide a concise and engaging description (around 100-150 words) for the lesson's focal point: '{fp_text}'. Explain its significance in the context of {SUBJECT} and {TOPIC}."
                            description = teacher_agent.chat(desc_prompt)
                            st.session_state.current_focal_point_descriptions[fp_text] = description
                    
                    st.markdown(st.session_state.current_focal_point_descriptions[fp_text])
                    
                    st.subheader("Visual Aid & Media")
                    display_media_content(fp_text, i) # From utils.py
                    
                    st.subheader("Quick Check")
                    q_key = f"fp_q_{i}"
                    fp_question = f"In one sentence, what is the main takeaway regarding '{fp_text}'?"
                    user_fp_answer = st.text_input(fp_question, key=q_key)

                    if st.button("Submit Takeaway", key=f"fp_submit_{i}"):
                        if user_fp_answer.strip():
                            user_as_agent.add_message("assistant", user_fp_answer)
                            with st.spinner("Teacher is reviewing your takeaway..."):
                                # teacher_agent.clear_messages()
                                feedback_prompt = f"A student provided this takeaway for the focal point '{fp_text}': '{user_fp_answer}'. Is this a good summary? Provide brief, encouraging feedback (1-2 sentences)."
                                feedback = teacher_agent.chat(feedback_prompt)
                            st.success(f"Teacher's Feedback: {feedback}")
                        else:
                            st.warning("Please enter your takeaway.")
                    st.divider()


    elif demo_option == "📝 Interactive Quiz":
        st.header("📝 Interactive Quiz Time!")
        st.markdown(f"Test your knowledge about **{SUBJECT}**. The quiz will have {3} questions.") # Hardcoded num_questions for demo
        run_streamlit_quiz(st.session_state.agents, SUBJECT, 3, all_students_with_user_names)


    elif demo_option == "🤔 Critical Thinking Challenge":
        st.header("🤔 Critical Thinking Challenge")
        st.markdown(f"Engage in a deeper discussion about **{SUBJECT}**.")
        run_streamlit_critical_thinking(st.session_state.agents, SUBJECT, all_students_with_user_names)


# --- Footer ---
st.divider()
st.markdown(
    """
    <div style="text-align: center; font-size: 0.9em; color: #777;">
        AI Classroom Companion Demo | 
        <a href="https://openrouter.ai" target="_blank">Powered by OpenRouter Models</a> | 
        Streamlit Framework
    </div>
    """, unsafe_allow_html=True
)