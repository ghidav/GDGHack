# quiz.py
import streamlit as st
import time
# from agents import Agent # Agent class is used by type hinting or if agents are passed directly

def run_streamlit_quiz(agents, subject, num_questions, all_student_names_with_user):
    """
    Streamlit version of the quiz functionality.
    This creates an interactive quiz in the Streamlit interface.
    'agents' is a dictionary of agent objects.
    'all_student_names_with_user' includes "User" and AI agent names.
    """
    NUM_QUESTIONS = num_questions
    SUBJECT = subject
    USER_NAME = "User" # Assuming the user is always named "User" in this context

    # Initialize the quiz state if not already done
    if "quiz_state" not in st.session_state:
        st.session_state.quiz_state = {
            "current_question_idx": 0, # Use index for questions list
            "questions_text": [], # List to store question strings
            "all_answers": {}, # {q_idx: {student_name: answer}}
            "quiz_complete": False,
            "final_ranking": None,
            "teacher_feedback_on_answers": {} # {q_idx: feedback_text}
        }
    
    quiz_state = st.session_state.quiz_state

    # Reset quiz button
    if st.button("🔄 Restart Quiz", key="restart_quiz_button"):
        # Clear relevant agent histories
        for agent_name, agent_obj in agents.items():
            if agent_name == "teacher" or agent_name in all_student_names_with_user:
                agent_obj.clear_messages() # Keep system prompt
        
        st.session_state.quiz_state = {
            "current_question_idx": 0,
            "questions_text": [],
            "all_answers": {},
            "quiz_complete": False,
            "final_ranking": None,
            "teacher_feedback_on_answers": {}
        }
        st.rerun()

    teacher_agent = agents["teacher"]

    # --- Teacher Instructions ---
    teacher_question_formulation_instruction = f"""Your task is to act as a teacher for a quiz on {SUBJECT}.
When prompted for 'Question X', formulate a distinct and clear question appropriate for the subject.
Focus on different aspects of {SUBJECT} for each question.
Your response should ONLY be the question itself, without any preamble like "Here is the question:"."""

    teacher_final_ranking_instruction = f"""The quiz on {SUBJECT} has concluded.
You have received answers from all students for {NUM_QUESTIONS} questions.
Based on all the answers provided (which will be summarized for you), your task is to:
1. Rank the students ({', '.join(all_student_names_with_user)}) from 1st to last.
2. Briefly explain the reasoning behind your ranking for each student, considering accuracy, thoughtfulness, and clarity.
Start your response *exactly* with "Final Ranking:" for easy parsing.
Example:
Final Ranking:
1. Paola - Consistently accurate and well-explained answers.
2. User - Showed good understanding in later questions.
3. Marc - Enthusiastic but sometimes incorrect.
"""

    # --- Quiz Flow ---
    if not quiz_state["quiz_complete"]:
        st.progress((quiz_state["current_question_idx"] / NUM_QUESTIONS))
        st.subheader(f"Question {quiz_state['current_question_idx'] + 1} of {NUM_QUESTIONS}")

        # Generate question if not already generated for current index
        if quiz_state["current_question_idx"] >= len(quiz_state["questions_text"]):
            with st.spinner("Teacher is formulating the question..."):
                # Context for teacher: previous questions and maybe answers
                # For simplicity here, we'll just ask for a new question.
                # More advanced: teacher_agent.clear_messages() # to make it stateless for question generation or provide specific context
                
                # Provide context to teacher about previous questions to avoid repetition
                previous_questions_summary = ""
                if quiz_state["questions_text"]:
                    previous_questions_summary = "You have already asked the following questions:\n"
                    for i, q_text in enumerate(quiz_state["questions_text"]):
                        previous_questions_summary += f"- Q{i+1}: {q_text}\n"
                    previous_questions_summary += "\nPlease formulate a new, distinct question."

                prompt_for_teacher = f"{teacher_question_formulation_instruction}\n{previous_questions_summary}\nProvide Question {quiz_state['current_question_idx'] + 1}."
                
                question_text = teacher_agent.chat(prompt_for_teacher)
                quiz_state["questions_text"].append(question_text)
                quiz_state["all_answers"][quiz_state["current_question_idx"]] = {}
        
        current_question_text = quiz_state["questions_text"][quiz_state["current_question_idx"]]
        st.markdown(f"#### Teacher asks: {current_question_text}")
        
        # Display AI student answers first (if not already answered for this question)
        # This part runs each time, but only calls agent.chat if answer not in quiz_state
        with st.expander("View AI Students' Answers", expanded=True):
            cols = st.columns(len(all_student_names_with_user) -1 if USER_NAME in all_student_names_with_user else len(all_student_names_with_user) )
            col_idx = 0
            for student_name in all_student_names_with_user:
                if student_name == USER_NAME:
                    continue

                if student_name not in quiz_state["all_answers"][quiz_state["current_question_idx"]]:
                    with cols[col_idx]:
                        with st.spinner(f"{student_name} is thinking..."):
                            student_agent = agents[student_name]
                            # student_agent.clear_messages() # Optional: make each answer stateless for the AI student
                            prompt_for_student = f'The teacher asks you, {student_name}: "{current_question_text}". Provide your answer.'
                            answer = student_agent.chat(prompt_for_student)
                            quiz_state["all_answers"][quiz_state["current_question_idx"]][student_name] = answer
                            st.markdown(f"**{student_name}**: {answer}")
                            time.sleep(0.5) # Simulate thinking
                else: # Answer already exists, just display it
                     with cols[col_idx]:
                        st.markdown(f"**{student_name}**: {quiz_state['all_answers'][quiz_state['current_question_idx']][student_name]}")
                col_idx +=1
        
        st.divider()
        
        # User's turn to answer
        user_answer_key = f"user_answer_q{quiz_state['current_question_idx']}"
        user_answer = st.text_area("Your Answer:", key=user_answer_key, height=100)

        if st.button(f"Submit Answer for Q{quiz_state['current_question_idx'] + 1}", type="primary"):
            if user_answer.strip():
                quiz_state["all_answers"][quiz_state["current_question_idx"]][USER_NAME] = user_answer
                agents[USER_NAME].add_message("assistant", user_answer) # Log user's answer

                # Optional: Teacher gives immediate feedback on this question (not in original scope but can be added)

                # Move to next question or finish
                quiz_state["current_question_idx"] += 1
                if quiz_state["current_question_idx"] >= NUM_QUESTIONS:
                    quiz_state["quiz_complete"] = True
                    # Prepare for final ranking
                    with st.spinner("Teacher is evaluating all answers for final ranking..."):
                        summary_for_ranking = ["Here are all the questions and answers for the quiz:"]
                        for i in range(NUM_QUESTIONS):
                            q_text = quiz_state["questions_text"][i]
                            summary_for_ranking.append(f"\nQuestion {i+1}: {q_text}")
                            for s_name, ans in quiz_state["all_answers"][i].items():
                                summary_for_ranking.append(f"- {s_name}: {ans}")
                        
                        summary_for_ranking.append(f"\n\n{teacher_final_ranking_instruction}")
                        final_prompt_for_teacher = "\n".join(summary_for_ranking)
                        
                        # teacher_agent.clear_messages() # Make ranking stateless or keep history
                        ranking_response = teacher_agent.chat(final_prompt_for_teacher)
                        quiz_state["final_ranking"] = ranking_response
                st.rerun()
            else:
                st.warning("Please type your answer before submitting.")

    else: # Quiz is complete
        st.success("🎉 Quiz Finished! 🎉")
        st.balloons