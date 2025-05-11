from openai import OpenAI
import streamlit as st
from os import getenv
from dotenv import load_dotenv
import re
import os
import time
import json
import random
from ast import literal_eval
from io import BytesIO

# Assuming these files are in the same directory or accessible via PYTHONPATH
from agents import Agent, UserAgent, INTERACTION_PROTOCOL

# quiz.py and critical_thinking.py logic will be adapted into process_lesson_step
# from report_generator import generate_report # Make sure this is uncommented if used

load_dotenv()
MODEL = "google/gemini-2.5-flash-preview"  # Using the consistent model

# --- Initialize OpenAI Client ---
try:
    CLIENT = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=getenv("OPENROUTER_API_KEY"),
    )
    if not getenv("OPENROUTER_API_KEY"):
        st.error(
            "OPENROUTER_API_KEY not found. Please set it in your .env file or environment variables."
        )
        st.stop()
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# --- Lesson Constants ---
LESSON_SUBJECT = "First Industrial Revolution"
LESSON_TOPIC = "The Invention of the Steam Engine"
LESSON_STYLE = (
    "Visual and Auditory"  # Style might be used for future media generation hints
)
NUM_FOCAL_POINTS = 2
NUM_QUIZ_QUESTIONS_PER_ACTIVITY = 1  # Number of questions for each quiz activity

avatars = {
    "teacher": "👩‍🏫",
    "Marc": "😄",
    "Paola": "🤓",
    "David": "👤",
}


# --- Helper Functions ---
def add_chat_message(role, content, speaker_name=None):
    """Adds a message to the Streamlit chat session for display."""
    # Determine the display role for st.chat_message (user or assistant)
    display_role = "user" if role == "user" else avatars.get(role, "🤖")

    full_content = f"**{speaker_name}**: {content}" if speaker_name else content

    if "messages" not in st.session_state:
        st.session_state.messages = []
    st.session_state.messages.append(
        {
            "role": display_role,
            "content": full_content,
            "original_speaker": role,
        }
    )


def get_teacher():
    return st.session_state.agents.get("teacher")


def get_ai_student(name):
    return st.session_state.agents.get(name)


def initialize_lesson_agents_and_focal_points():
    """Initializes agents and determines focal points for the lesson."""
    st.session_state.agents = {}
    student_agent_instructions = {
        "Marc": f"You are an enthusiastic funny student named Marc. Provide funny (and sometimes wrong...) answers to the teacher's questions. Use emojis and humor.",
        "Paola": f"You are a knowledgeable but quiet and concise student named Paola. Provide accurate but brief answers.",
    }
    st.session_state.student_agent_instructions = student_agent_instructions
    # Ensure lesson_params is available
    if "lesson_params" not in st.session_state or not st.session_state.lesson_params:
        # Fallback or error, this should be set before calling this function
        st.error("lesson_params not initialized before agent setup!")
        st.stop()
        return  # Added return to prevent further execution if error

    all_student_names = list(student_agent_instructions.keys()) + [
        "David"
    ]  # David is the human user
    st.session_state.all_student_names = all_student_names
    st.session_state.ai_student_names = list(student_agent_instructions.keys())

    # Initialize Teacher Agent
    teacher_base_prompt = (
        f"You are a teacher in a {st.session_state.lesson_params['SUBJECT']} class."
    )
    st.session_state.agents["teacher"] = Agent(
        name="teacher", client=CLIENT, model=MODEL, instruction=teacher_base_prompt
    )
    teacher_protocol = INTERACTION_PROTOCOL.format(
        other_agents=", ".join(all_student_names)
    )
    st.session_state.agents["teacher"].update_system_prompt_with_protocol(
        teacher_protocol
    )

    # Initialize AI Student Agents
    for name, instruction in student_agent_instructions.items():
        st.session_state.agents[name] = Agent(
            name=name, client=CLIENT, model=MODEL, instruction=instruction
        )
        student_sees_others = ["teacher"] + [
            s_name for s_name in all_student_names if s_name != name
        ]
        student_protocol = INTERACTION_PROTOCOL.format(
            other_agents=", ".join(student_sees_others)
        )
        st.session_state.agents[name].update_system_prompt_with_protocol(
            student_protocol
        )

    # UserAgent for David (primarily for compatibility if some shared logic expects it)
    st.session_state.agents["David"] = UserAgent(
        name="David",
        instruction=f"You are David, a student in a {st.session_state.lesson_params['SUBJECT']} class.",
    )

    # Get Focal Points from Teacher
    teacher = get_teacher()
    focal_points_llm_output = teacher.chat(
        f"Identify the {st.session_state.lesson_params['NUM_FOCAL_POINTS']} Key Concepts of the lesson on {st.session_state.lesson_params['SUBJECT']} about {st.session_state.lesson_params['TOPIC']} and list them ordered by prerequisite logic. Output just a python list of strings."
    )
    parsed_focal_points = []
    match = re.search(r"\[.*?\]", focal_points_llm_output, re.DOTALL)
    if match:
        list_string = match.group(0)
        try:
            parsed_focal_points = literal_eval(list_string)
            if not isinstance(parsed_focal_points, list) or not all(
                isinstance(item, str) for item in parsed_focal_points
            ):
                raise ValueError("Parsed data is not a list of strings.")
            if (
                len(parsed_focal_points)
                != st.session_state.lesson_params["NUM_FOCAL_POINTS"]
            ):
                add_chat_message(
                    "system",
                    f"Warning: LLM returned {len(parsed_focal_points)} focal points, expected {st.session_state.lesson_params['NUM_FOCAL_POINTS']}. Using returned points.",
                    "System",
                )

        except (ValueError, SyntaxError) as e:
            add_chat_message(
                "system",
                f"Error parsing focal points list string: '{list_string}'. Error: {e}. Using fallback.",
                "Error",
            )
            parsed_focal_points = [
                f"Default Focal Point {i+1}"
                for i in range(st.session_state.lesson_params["NUM_FOCAL_POINTS"])
            ]
    else:
        add_chat_message(
            "system",
            f"Could not find a Python list in the LLM output for focal points: '{focal_points_llm_output}'. Using fallback.",
            "Error",
        )
        parsed_focal_points = [
            f"Default Focal Point {i+1}"
            for i in range(st.session_state.lesson_params["NUM_FOCAL_POINTS"])
        ]

    st.session_state.focal_points = parsed_focal_points
    teacher.set_state(
        "focal_points", parsed_focal_points
    )  # Store in teacher's state for report
    teacher.clear_messages()


def process_lesson_step(user_prompt=None):
    """Manages the lesson flow based on the current stage and user input."""
    stage = st.session_state.lesson_stage
    teacher = get_teacher()

    # --- INITIALIZATION ---
    if stage == "AWAITING_LESSON_START":
        with st.expander("🛠️ Customize Lesson Parameters", expanded=True):
            subject = st.selectbox("Subject", ["Math", "Science", "History"], index=0)
            topic = st.text_input("Topic", value="Introduction to Algebra")
            style = st.selectbox("Lesson Style", ["Conversational", "Formal", "Interactive"], index=0)
            num_focal_points = st.slider("Number of Focal Points", 1, 5, 3)
            num_questions = st.slider("Number of Quiz Questions", 1, 10, 3)

            if st.button("✅ Confirm Parameters"):
                st.session_state.lesson_params = {
                    "SUBJECT": subject,
                    "TOPIC": topic,
                    "STYLE": style,
                    "NUM_FOCAL_POINTS": num_focal_points,
                    "NUM_QUESTIONS": num_questions,
                }
                st.success("Lesson parameters set. Type 'start lesson' to begin.")
                initialize_lesson_agents_and_focal_points()

        if user_prompt and "start lesson" in user_prompt.lower():
            # Use parameters from session state or fallback defaults
            st.session_state.lesson_params = st.session_state.get("lesson_params", {
                "SUBJECT": LESSON_SUBJECT,
                "TOPIC": LESSON_TOPIC,
                "STYLE": LESSON_STYLE,
                "NUM_FOCAL_POINTS": NUM_FOCAL_POINTS,
                "NUM_QUESTIONS": NUM_QUIZ_QUESTIONS_PER_ACTIVITY,
            })
            initialize_lesson_agents_and_focal_points()
            st.session_state.lesson_stage = "INTRODUCTION"
            st.rerun()
            return

        elif user_prompt:
            response = CLIENT.chat.completions.create(
                model=MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. The lesson has not started. Ask the user to type 'start lesson' to begin.",
                    },
                    {"role": "user", "content": user_prompt},
                ],
            )
            msg = response.choices[0].message.content
            add_chat_message("assistant", msg, "Chatbot")
            st.rerun()
            return
        return  # If no user prompt, just wait

    # --- LESSON FLOW ---
    if not teacher:  # Should not happen after AWAITING_LESSON_START if lesson started
        if stage != "AWAITING_LESSON_START":
            add_chat_message("system", "Error: Teacher agent not initialized.", "Error")
            st.rerun()  # Rerun to show error
        return

    if stage == "INTRODUCTION":
        intro = teacher.chat(
            f"Generate a short introduction for a lesson on {st.session_state.lesson_params['SUBJECT']} about {st.session_state.lesson_params['TOPIC']}. Make sure to include the Key Concepts of the lesson: {'\n'.join(st.session_state.focal_points)}. Don't mention students at this point."
        )
        add_chat_message("teacher", intro, "Teacher")
        teacher.clear_messages()
        st.session_state.lesson_stage = "EXAMPLE"
        st.rerun()
        return

    elif stage == "EXAMPLE":
        example = teacher.chat(
            f"Now generate a brief example related to the lesson that clearly illustrates why the topic is important. Don't mention students at this point."
        )
        add_chat_message("teacher", example, "Teacher")
        teacher.clear_messages()
        st.session_state.current_focal_point_index = 0
        st.session_state.lesson_stage = "FOCAL_POINT_DESCRIPTION"
        st.rerun()
        return

    elif stage == "FOCAL_POINT_DESCRIPTION":
        idx = st.session_state.current_focal_point_index
        if idx < len(st.session_state.focal_points):
            fp = st.session_state.focal_points[idx]
            desc = teacher.chat(
                f"Generate a short description of the focal point: {fp}. Don't mention students at this point."
            )
            add_chat_message("teacher", desc, "Teacher")
            teacher.clear_messages()
            st.session_state.activity_type = random.choice(
                ["quiz", "critical_thinking"]
            )
            # st.session_state.activity_type = "quiz"
            if st.session_state.activity_type == "quiz":
                add_chat_message("system", f"Preparing a quiz for '{fp}'.", "System")
                st.session_state.lesson_stage = "QUIZ_START"
            else:  # Critical Thinking
                add_chat_message(
                    "system",
                    f"Preparing a critical thinking exercise for '{fp}'.",
                    "System",
                )
                st.session_state.lesson_stage = "CRITICAL_THINKING_START"
            st.rerun()
            return
        else:  # All focal points done
            st.session_state.lesson_stage = "FINAL_TEST_SETUP"
            st.rerun()
            return

    # --- QUIZ LOGIC ---
    elif stage == "QUIZ_START":
        fp = st.session_state.focal_points[st.session_state.current_focal_point_index]
        # Display intro and immediately generate the first question
        add_chat_message("teacher", f"Let's have a quick quiz on: {fp}.", "Teacher")
        st.session_state.current_quiz_question_num_for_activity = 0
        st.session_state.quiz_answers_collected_for_activity = {
            q_n: {}
            for q_n in range(1, st.session_state.lesson_params["NUM_QUESTIONS"] + 1)
        }
        st.session_state.quiz_teacher_instruction = f"""Your task is to:
1. When prompted for 'Question X', formulate a distinct question about the current focal point: {fp}. Your response should ONLY be the question itself.
2. You will then receive answers from students. This will repeat for {st.session_state.lesson_params["NUM_QUESTIONS"]} questions.
3. After all questions are answered, provide constructive feedback for each student as a JSON object with student names as keys."""
        
        # Immediately get and display first question instead of just changing state
        q_num_activity = 1
        teacher_prompt_quiz = f"{st.session_state.quiz_teacher_instruction}\n\nPlease provide Question {q_num_activity}. Respond with ONLY the question text."
        question_text = teacher.chat(teacher_prompt_quiz)
        st.session_state.current_activity_question_text = question_text
        add_chat_message("teacher", f"Quiz Question {q_num_activity}: {question_text}", "Teacher")
        teacher.clear_messages()
        
        st.session_state.activity_current_student_turn_index = 0  # Start with David
        st.session_state.lesson_stage = "QUIZ_AWAIT_STUDENT_ANSWER"
        add_chat_message("system", f"Waiting for David's answer to Question {q_num_activity}...", "System")
        st.rerun()
        return

    elif stage == "QUIZ_ASK_QUESTION":
        q_num_activity = st.session_state.current_quiz_question_num_for_activity + 1
        if q_num_activity <= st.session_state.lesson_params["NUM_QUESTIONS"]:
            teacher_prompt_quiz = f"{st.session_state.quiz_teacher_instruction}\n\nPlease provide Question {q_num_activity}. Respond with ONLY the question text."
            if q_num_activity > 1:
                prev_q_ans_summary = (
                    f"\nFor reference, answers to Question {q_num_activity-1}:\n"
                )
                for (
                    student_name,
                    answer,
                ) in st.session_state.quiz_answers_collected_for_activity.get(
                    q_num_activity - 1, {}
                ).items():
                    prev_q_ans_summary += f"- {student_name}: {answer}\n"
                teacher_prompt_quiz = prev_q_ans_summary + teacher_prompt_quiz

            question_text = teacher.chat(teacher_prompt_quiz)
            st.session_state.current_activity_question_text = question_text
            add_chat_message(
                "teacher", f"Quiz Question {q_num_activity}: {question_text}", "Teacher"
            )
            teacher.clear_messages()

            st.session_state.activity_current_student_turn_index = 0  # Start with David
            st.session_state.lesson_stage = "QUIZ_AWAIT_STUDENT_ANSWER"
            add_chat_message(
                "system",
                f"Waiting for David's answer to Question {q_num_activity}...",
                "System",
            )
            # Return and wait for David's input via chat_input. Streamlit will rerun naturally.
            return
        else:  # All questions for this quiz activity done
            st.session_state.lesson_stage = "QUIZ_TEACHER_FEEDBACK"
            st.rerun()
            return

    elif stage == "QUIZ_AWAIT_STUDENT_ANSWER":
        q_num_activity = st.session_state.current_quiz_question_num_for_activity + 1
        current_student_name = st.session_state.all_student_names[
            st.session_state.activity_current_student_turn_index
        ]

        if current_student_name == "David":
            if user_prompt is None:  # Still waiting for David's input
                # Message "Waiting for David's answer..." should have been added by QUIZ_ASK_QUESTION
                return  # Wait for input
            # David's message already added by main handler
            st.session_state.quiz_answers_collected_for_activity[q_num_activity][
                current_student_name
            ] = user_prompt
        else:  # AI student's turn
            if (
                user_prompt is not None
                and st.session_state.activity_current_student_turn_index == 0
            ):
                # This means David (index 0) just answered, and now it's an AI's turn.
                # We proceed to the AI's turn in this same call.
                pass  # Allow flow to AI student's turn processing

            ai_student = get_ai_student(current_student_name)
            student_prompt_for_llm = f'The teacher asks you, {current_student_name}: "{st.session_state.current_activity_question_text}"'
            ai_answer = ai_student.chat(student_prompt_for_llm)
            st.session_state.quiz_answers_collected_for_activity[q_num_activity][
                current_student_name
            ] = ai_answer
            add_chat_message(current_student_name, ai_answer, current_student_name)
            ai_student.clear_messages()

        st.session_state.activity_current_student_turn_index += 1
        if st.session_state.activity_current_student_turn_index < len(
            st.session_state.all_student_names
        ):
            next_student_name = st.session_state.all_student_names[
                st.session_state.activity_current_student_turn_index
            ]
            if (
                next_student_name == "David"
            ):  # Should not happen if David is always first (index 0)
                add_chat_message(
                    "system", f"Waiting for David's answer (unexpected)...", "System"
                )
                return  # Wait for input
            else:  # Next is an AI student, trigger their turn by rerunning
                add_chat_message(
                    "system",
                    f"Now it's {next_student_name}'s turn for Question {q_num_activity}.",
                    "System",
                )
                st.rerun()
                return
        else:  # All students answered this question
            st.session_state.current_quiz_question_num_for_activity += 1
            st.session_state.lesson_stage = (
                "QUIZ_ASK_QUESTION"  # Ask next Q or move to feedback
            )
            st.rerun()
            return

    elif stage == "QUIZ_TEACHER_FEEDBACK":
        feedback_prompt_parts = ["All questions for this quiz have been answered."]
        # Ensure current_quiz_question_num_for_activity reflects completed questions
        num_questions_answered = st.session_state.current_quiz_question_num_for_activity
        if not st.session_state.quiz_answers_collected_for_activity.get(
            num_questions_answered
        ):
            # This means we might have incremented current_quiz_question_num_for_activity too early
            # or not all answers for the last question were collected.
            # For simplicity, let's assume it's based on NUM_QUESTIONS for this activity.
            num_questions_answered = st.session_state.lesson_params["NUM_QUESTIONS"]

        for q_idx in range(1, num_questions_answered + 1):
            feedback_prompt_parts.append(f"\nAnswers for Question {q_idx}:")
            for (
                student_name,
                answer,
            ) in st.session_state.quiz_answers_collected_for_activity.get(
                q_idx, {}
            ).items():
                feedback_prompt_parts.append(f"- {student_name}: {answer}")

        feedback_prompt = "\n".join(feedback_prompt_parts)
        feedback_prompt += f"\n\nBased on these answers, provide constructive feedback as a JSON object (student name as key, feedback as value)."

        final_feedback_response = teacher.chat(feedback_prompt)
        add_chat_message(
            "teacher", f"Quiz Feedback:\n{final_feedback_response}", "Teacher"
        )
        teacher.clear_messages()

        try:
            json_match = re.search(r"\{.*\}", final_feedback_response, re.DOTALL)
            if json_match:
                parsed_feedback = json.loads(json_match.group(0))
                user_specific_feedback = parsed_feedback.get(
                    "David", "No specific feedback for David in JSON."
                )
            else:
                user_specific_feedback = (
                    "Feedback provided, but not in expected JSON format. Raw: "
                    + final_feedback_response
                )
        except json.JSONDecodeError:
            user_specific_feedback = (
                "Error decoding feedback JSON. Raw: " + final_feedback_response
            )

        fp_idx = st.session_state.current_focal_point_index
        teacher.set_state(f"quiz_{fp_idx}_feedback", user_specific_feedback)
        add_chat_message(
            "system",
            f"David's feedback for this quiz: {user_specific_feedback}",
            "System",
        )

        for agent_name in st.session_state.ai_student_names:
            if get_ai_student(agent_name):  # Check if agent exists
                get_ai_student(agent_name).clear_messages()

        st.session_state.current_focal_point_index += 1
        st.session_state.lesson_stage = "FOCAL_POINT_DESCRIPTION"
        st.rerun()
        return

    # --- CRITICAL THINKING STAGES (Simplified - would mirror quiz structure) ---
    elif stage == "CRITICAL_THINKING_START":
        fp = st.session_state.focal_points[st.session_state.current_focal_point_index]
        # Display intro message first
        add_chat_message(
            "teacher", f"Let's do a critical thinking exercise on: {fp}.", "Teacher"
        )
        
        # Immediately generate and display the critical thinking question
        ct_question = teacher.chat(
            f"Pose a single, insightful critical thinking question about {fp}. Respond with ONLY the question."
        )
        st.session_state.current_activity_question_text = ct_question
        add_chat_message(
            "teacher", f"Critical Thinking Question: {ct_question}", "Teacher"
        )
        teacher.clear_messages()
        
        # Setup for student answers
        st.session_state.ct_initial_answers = {}
        st.session_state.ct_elaborations = {}  # If you plan to use this
        st.session_state.activity_current_student_turn_index = 0  # David first
        st.session_state.lesson_stage = "CRITICAL_THINKING_AWAIT_INITIAL_ANSWER"
        add_chat_message(
            "system",
            "Waiting for David's initial answer for Critical Thinking...",
            "System",
        )
        st.rerun()  # Make sure both messages appear before waiting for input
        return

    elif stage == "CRITICAL_THINKING_AWAIT_INITIAL_ANSWER":
        # Simplified: David answers, then we move on.
        # A full implementation would loop through students like the quiz.
        current_student_name = st.session_state.all_student_names[
            st.session_state.activity_current_student_turn_index
        ]

        if current_student_name == "David":
            if user_prompt is None:
                return  # Waiting for David's input
            # David's message added by main handler
            st.session_state.ct_initial_answers["David"] = user_prompt
            add_chat_message(
                "system",
                f"David's critical thinking answer received: {user_prompt}",
                "System",
            )
            teacher.set_state(
                f"critical_thinking_{st.session_state.current_focal_point_index}_feedback",
                f"David's CT answer: {user_prompt} (simplified flow).",
            )
            # For now, end CT after David's answer
            st.session_state.current_focal_point_index += 1
            st.session_state.lesson_stage = "FOCAL_POINT_DESCRIPTION"
            st.rerun()
            return
        else:
            # Placeholder for AI student CT answers if you expand this
            add_chat_message(
                "system", "AI student turn for CT not fully implemented.", "System"
            )
            st.session_state.current_focal_point_index += 1  # Or handle AI turn
            st.session_state.lesson_stage = "FOCAL_POINT_DESCRIPTION"
            st.rerun()
            return

    # --- FINAL TEST ---
    elif stage == "FINAL_TEST_SETUP":
        add_chat_message("teacher", "Now, let's start the final test.", "Teacher")
        st.session_state.current_final_test_question_index = 0
        st.session_state.final_test_user_answers = []
        st.session_state.final_test_questions = []
        st.session_state.final_test_teacher_instruction = f"""Your task is to:
1. Formulate a distinct question for each of the {len(st.session_state.focal_points)} focal points. When prompted for 'Question X about Focal Point Y', respond ONLY with the question.
2. After all questions are answered by David, provide a final overview of his performance."""
        st.session_state.lesson_stage = "FINAL_TEST_ASK_QUESTION"
        st.rerun()
        return

    elif stage == "FINAL_TEST_ASK_QUESTION":
        q_idx = st.session_state.current_final_test_question_index
        if q_idx < len(st.session_state.focal_points):
            fp_for_test = st.session_state.focal_points[q_idx]
            teacher_prompt_final = f"{st.session_state.final_test_teacher_instruction}\n\nPlease provide Question {q_idx + 1} about the Focal Point: {fp_for_test}. Respond with ONLY the question text."
            test_question = teacher.chat(teacher_prompt_final)
            st.session_state.final_test_questions.append(test_question)
            add_chat_message(
                "teacher",
                f"Final Test Question {q_idx + 1}: {test_question}",
                "Teacher",
            )
            teacher.clear_messages()
            st.session_state.lesson_stage = "FINAL_TEST_AWAIT_USER_ANSWER"
            add_chat_message(
                "system",
                f"Waiting for David's answer to Final Test Question {q_idx + 1}...",
                "System",
            )
            return  # Wait for David's input
        else:  # All final test questions asked
            st.session_state.lesson_stage = "FINAL_TEST_TEACHER_FEEDBACK"
            st.rerun()
            return

    elif stage == "FINAL_TEST_AWAIT_USER_ANSWER":
        if user_prompt is None:
            return  # Waiting for David's input
        # David's message already added by main handler
        st.session_state.final_test_user_answers.append(user_prompt)
        st.session_state.current_final_test_question_index += 1
        st.session_state.lesson_stage = (
            "FINAL_TEST_ASK_QUESTION"  # Ask next or go to feedback
        )
        st.rerun()
        return

    elif stage == "FINAL_TEST_TEACHER_FEEDBACK":
        answers_summary = "David's answers for the final test:\n"
        for i, ans in enumerate(st.session_state.final_test_user_answers):
            q_text = (
                st.session_state.final_test_questions[i]
                if i < len(st.session_state.final_test_questions)
                else "Unknown Question"
            )
            answers_summary += f"Q{i+1} ({q_text}): {ans}\n"

        feedback_prompt_final = f"{answers_summary}\n\nPlease provide constructive feedback on David's answers and a general overview of his performance for the final test."
        teacher_final_feedback = teacher.chat(feedback_prompt_final)
        add_chat_message("teacher", teacher_final_feedback, "Teacher")
        teacher.set_state("final_test_feedback", teacher_final_feedback)
        teacher.clear_messages()
        st.session_state.lesson_stage = "REPORTING"
        st.rerun()
        return

    # --- REPORTING ---
    elif stage == "REPORTING":
        add_chat_message("system", "Generating student report...", "System")
        # Ensure report_generator is imported and function is available
        # from report_generator import generate_report # Ensure this is active at top of file
        # For now, let's assume it's a placeholder if not implemented
        report_generated_successfully = False
        if "generate_report" in globals():
            report_filename = f"David_{st.session_state.lesson_params['SUBJECT'].replace(' ', '_')}_Report.pdf"
            try:
                generate_report(  # Make sure generate_report is defined or imported
                    teacher_state=teacher.state,
                    student_name="David",
                    subject=st.session_state.lesson_params["SUBJECT"],
                    topic=st.session_state.lesson_params["TOPIC"],
                    output_filename=report_filename,
                )
                with open(
                    report_filename, "rb"
                ) as fp_report:  # Renamed fp to fp_report
                    st.session_state.pdf_report_bytes = fp_report.read()
                st.session_state.report_filename = report_filename
                add_chat_message(
                    "system",
                    f"Report '{report_filename}' generated. A download button will appear below the chat.",
                    "System",
                )
                report_generated_successfully = True
            except FileNotFoundError:
                add_chat_message(
                    "system",
                    f"Error: Report file {report_filename} could not be read after generation.",
                    "Error",
                )
                st.session_state.pdf_report_bytes = None
            except NameError:  # If generate_report is not defined
                add_chat_message(
                    "system",
                    "Report generation skipped (generate_report function not found).",
                    "System",
                )
                st.session_state.pdf_report_bytes = None
            except Exception as e_report:  # Renamed e to e_report
                add_chat_message(
                    "system",
                    f"An error occurred during report generation: {e_report}",
                    "Error",
                )
                st.session_state.pdf_report_bytes = None
        else:
            add_chat_message(
                "system",
                "Report generation skipped (generate_report function not imported/available).",
                "System",
            )
            st.session_state.pdf_report_bytes = None

        st.session_state.lesson_stage = "LESSON_COMPLETE"
        st.rerun()
        return

    elif stage == "LESSON_COMPLETE":
        add_chat_message(
            "🤖",
            "The lesson is now complete! Type 'start lesson' to begin a new one, or refresh the page.",
            "Chatbot",
        )
        st.session_state.lesson_stage = (
            "AWAITING_LESSON_START"  # Ready for another start
        )
        st.rerun()  # Rerun to show completion message and reset for next lesson start
        return

    return  # Default return if no other path taken


# --- Streamlit UI Setup ---
st.title(f"💬 Interactive Lesson: {LESSON_SUBJECT}")
st.caption(f"Topic: {LESSON_TOPIC}")

# Initialize session state variables if not already present
if "lesson_stage" not in st.session_state:
    st.session_state.lesson_stage = "AWAITING_LESSON_START"
    st.session_state.messages = [
        {"role": "🤖", "content": "Welcome! Type 'start lesson' to begin."}
    ]
    st.session_state.agents = {}
    st.session_state.focal_points = []
    st.session_state.current_focal_point_index = 0
    st.session_state.activity_type = None

    st.session_state.current_quiz_question_num_for_activity = 0
    st.session_state.quiz_answers_collected_for_activity = {}
    st.session_state.current_activity_question_text = ""
    st.session_state.activity_current_student_turn_index = 0

    st.session_state.ct_initial_answers = {}
    st.session_state.ct_elaborations = {}

    st.session_state.final_test_questions = []
    st.session_state.final_test_user_answers = []
    st.session_state.current_final_test_question_index = 0

    st.session_state.pdf_report_bytes = None
    st.session_state.report_filename = None
    st.session_state.lesson_params = {}


# Display chat messages from history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Handle user input
user_action_prompt = None  # Initialize user_action_prompt for this run
if prompt := st.chat_input("Your response:"):
    # Determine speaker name based on lesson stage
    current_stage = st.session_state.get("lesson_stage", "AWAITING_LESSON_START")
    user_speaker_name = (
        "David"
        if current_stage not in ["AWAITING_LESSON_START", "LESSON_COMPLETE"]
        else "User"
    )

    # Add user's message to state. It will be displayed on the next rerun.
    add_chat_message("user", prompt, speaker_name=user_speaker_name)
    user_action_prompt = prompt  # Set for process_lesson_step

# Always call process_lesson_step.
# It will use user_action_prompt if set, or proceed based on current state if None.
# process_lesson_step will call st.rerun() if it needs to advance state automatically.
# If process_lesson_step returns without st.rerun(), it means it's waiting for new user input or finished.
process_lesson_step(user_prompt=user_action_prompt)


# Report download button (appears when report is ready)
if st.session_state.get("pdf_report_bytes") and st.session_state.get("report_filename"):
    st.download_button(
        label=f"Download Report: {st.session_state.report_filename}",
        data=st.session_state.pdf_report_bytes,
        file_name=st.session_state.report_filename,
        mime="application/pdf",
    )

# The explicit st.rerun() calls within process_lesson_step now manage the flow.
