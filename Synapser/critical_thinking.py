# critical_thinking.py
import streamlit as st
import time
# from agents import Agent # Agent class is used by type hinting or if agents are passed directly

def run_streamlit_critical_thinking(agents, subject, all_student_names_with_user):
    """
    Streamlit version of the critical thinking exercise.
    'agents' is a dictionary of agent objects.
    'all_student_names_with_user' includes "User" and AI agent names.
    """
    SUBJECT = subject
    USER_NAME = "User"
    num_students = len(all_student_names_with_user)

    if "ct_state" not in st.session_state:
        st.session_state.ct_state = {
            "question": None,
            "initial_answers": {},  # {student_name: answer_text}
            "elaborations": {},  # {elaborator_name: {on_student: name, text: elaboration}}
            "current_stage": "formulate_question",  # Stages: formulate_question, initial_answers, elaboration, feedback
            "final_feedback_text": None,
            "exercise_reset_flag": True # To trigger question formulation on first run/reset
        }
    
    ct_state = st.session_state.ct_state

    if st.button("🔄 Restart Critical Thinking Exercise", key="restart_ct_button"):
        for agent_name, agent_obj in agents.items():
             if agent_name == "teacher" or agent_name in all_student_names_with_user:
                agent_obj.clear_messages()
        st.session_state.ct_state = {
            "question": None, "initial_answers": {}, "elaborations": {},
            "current_stage": "formulate_question", "final_feedback_text": None,
            "exercise_reset_flag": True
        }
        st.rerun()

    teacher_agent = agents["teacher"]

    # --- Prompts ---
    teacher_question_formulation_prompt = f"""Your task is to formulate a single, insightful, open-ended critical thinking question about {SUBJECT}.
The question should encourage deep thought, diverse perspectives, and constructive discussion among students.
Respond with ONLY the question itself. No preamble."""

    teacher_final_feedback_prompt_header = f"""The critical thinking exercise on {SUBJECT} has concluded.
You have the original question, all student initial answers, and their elaborations.
Your task is to:
1.  Provide a comprehensive wrap-up of the discussion, highlighting key themes or divergent viewpoints.
2.  Offer constructive feedback to the students as a group, focusing on their critical thinking, the depth of their analysis, how well they built upon or challenged others' ideas, and their engagement.
Avoid individual call-outs unless illustrating a general point positively.
Start your response *exactly* with "Final Wrap-up and Feedback:" for parsing."""


    # --- Exercise Flow ---

    # Stage 0: Teacher formulates question
    if ct_state["current_stage"] == "formulate_question" and ct_state["exercise_reset_flag"]:
        with st.spinner("Teacher is formulating a critical thinking question..."):
            # teacher_agent.clear_messages() # Make question generation stateless
            question = teacher_agent.chat(teacher_question_formulation_prompt)
            ct_state["question"] = question
            ct_state["current_stage"] = "initial_answers"
            ct_state["exercise_reset_flag"] = False # Question is set
            st.rerun()
            
    if not ct_state["question"]:
        st.info("Initializing critical thinking exercise...")
        if not ct_state["exercise_reset_flag"]: # Should have been set by restart
             ct_state["exercise_reset_flag"] = True # force re-init
        st.rerun() # Trigger re-run to formulate question
        return


    st.subheader("Critical Thinking Challenge")
    st.markdown(f"**Teacher's Question**: {ct_state['question']}")
    st.divider()

    # Stage 1: Initial Answers
    if ct_state["current_stage"] == "initial_answers":
        st.markdown("#### Phase 1: Initial Responses")
        
        # Collect AI answers if not already done
        for student_name in all_student_names_with_user:
            if student_name != USER_NAME and student_name not in ct_state["initial_answers"]:
                with st.spinner(f"{student_name} is drafting an initial response..."):
                    student_agent = agents[student_name]
                    # student_agent.clear_messages()
                    prompt_for_student = f'The teacher posed this critical thinking question: "{ct_state["question"]}". Please provide your thoughtful initial answer.'
                    answer = student_agent.chat(prompt_for_student)
                    ct_state["initial_answers"][student_name] = answer
                    time.sleep(0.5)
        
        # Display AI answers collected so far
        for student_name, answer_text in ct_state["initial_answers"].items():
            if student_name != USER_NAME:
                with st.chat_message(student_name, avatar="🤖" if student_name =="Marc" else "🧐"): # Example avatars
                    st.markdown(answer_text)

        # User's initial answer
        user_initial_answer = st.text_area("Your Initial Answer:", height=150, key="ct_user_initial_answer")
        if st.button("Submit Your Initial Answer", type="primary"):
            if user_initial_answer.strip():
                ct_state["initial_answers"][USER_NAME] = user_initial_answer
                agents[USER_NAME].add_message("assistant", user_initial_answer)
                ct_state["current_stage"] = "elaboration"
                st.rerun()
            else:
                st.warning("Please provide your initial answer.")
        return # Wait for user submission or AI to complete

    # Display all initial answers once collected before moving to elaboration
    if ct_state["current_stage"] != "initial_answers" and ct_state["initial_answers"]:
        with st.expander("Show All Initial Answers", expanded=False):
            for student_name, answer_text in ct_state["initial_answers"].items():
                 with st.chat_message(student_name, avatar="🧑‍💻" if student_name == USER_NAME else ("🤖" if student_name =="Marc" else "🧐")):
                    st.write(answer_text)


    # Stage 2: Elaborations
    if ct_state["current_stage"] == "elaboration":
        if len(ct_state["initial_answers"]) < num_students:
            st.info("Waiting for all initial answers before proceeding to elaboration.")
            return

        st.markdown("#### Phase 2: Elaboration on Peers' Responses")
        elaboration_pairs = [] # (elaborator, student_to_elaborate_on)
        shuffled_students = all_student_names_with_user[:] # Create a mutable copy
        # random.shuffle(shuffled_students) # Make it more dynamic

        for i in range(num_students):
            elaborator = shuffled_students[i]
            elaborate_on_student = shuffled_students[(i + 1) % num_students]
            if elaborator != elaborate_on_student: # Avoid self-elaboration if only 1 student
                 elaboration_pairs.append((elaborator, elaborate_on_student))

        for elaborator_name, elaborated_on_name in elaboration_pairs:
            if elaborator_name != USER_NAME and elaborator_name not in ct_state["elaborations"]:
                with st.spinner(f"{elaborator_name} is elaborating on {elaborated_on_name}'s answer..."):
                    student_agent = agents[elaborator_name]
                    # student_agent.clear_messages()
                    answer_to_elaborate = ct_state["initial_answers"].get(elaborated_on_name, "Their answer was not found.")
                    prompt_for_elaboration = f"""Regarding the critical thinking question: "{ct_state["question"]}"
Your classmate, {elaborated_on_name}, provided this initial answer: "{answer_to_elaborate}"
Please elaborate on {elaborated_on_name}'s perspective. You can build upon their points, offer a counter-argument, or explore a different facet. Be constructive."""
                    elaboration_text = student_agent.chat(prompt_for_elaboration)
                    ct_state["elaborations"][elaborator_name] = {"on_student": elaborated_on_name, "text": elaboration_text}
                    time.sleep(0.5)

        # Display AI elaborations
        for student_name, elab_data in ct_state["elaborations"].items():
            if student_name != USER_NAME:
                 with st.chat_message(student_name, avatar="🤖" if student_name =="Marc" else "🧐"):
                    st.markdown(f"*elaborating on {elab_data['on_student']}'s answer:*")
                    st.markdown(elab_data["text"])
        
        # User's elaboration turn
        user_elaboration_target = next((pair[1] for pair in elaboration_pairs if pair[0] == USER_NAME), None)
        if user_elaboration_target and USER_NAME not in ct_state["elaborations"]:
            st.markdown(f"##### Your turn to elaborate on **{user_elaboration_target}**'s answer:")
            st.info(f"**{user_elaboration_target}** said: \"{ct_state['initial_answers'].get(user_elaboration_target, '')}\"")
            user_elaboration_text = st.text_area(f"Your Elaboration:", height=150, key="ct_user_elaboration")
            
            if st.button("Submit Your Elaboration", type="primary"):
                if user_elaboration_text.strip():
                    ct_state["elaborations"][USER_NAME] = {"on_student": user_elaboration_target, "text": user_elaboration_text}
                    agents[USER_NAME].add_message("assistant", user_elaboration_text) # Log user's elaboration
                    # Check if all elaborations are done
                    if len(ct_state["elaborations"]) == num_students:
                        ct_state["current_stage"] = "feedback"
                    st.rerun()
                else:
                    st.warning("Please provide your elaboration.")
        elif len(ct_state["elaborations"]) == num_students and USER_NAME in ct_state["elaborations"]: # All done
             ct_state["current_stage"] = "feedback"
             st.rerun()

        return # Wait for user or AI

    if ct_state["current_stage"] != "elaboration" and ct_state["elaborations"]:
         with st.expander("Show All Elaborations", expanded=False):
            for student_name, elab_data in ct_state["elaborations"].items():
                 with st.chat_message(student_name, avatar="🧑‍💻" if student_name == USER_NAME else ("🤖" if student_name =="Marc" else "🧐")):
                    st.markdown(f"*elaborating on {elab_data['on_student']}'s answer:*")
                    st.write(elab_data["text"])


    # Stage 3: Teacher's Final Feedback
    if ct_state["current_stage"] == "feedback":
        if len(ct_state["elaborations"]) < num_students:
            st.info("Waiting for all elaborations before final feedback.")
            return

        st.markdown("#### Phase 3: Teacher's Wrap-up and Feedback")
        if not ct_state["final_feedback_text"]:
            with st.spinner("Teacher is preparing the final wrap-up and feedback..."):
                # teacher_agent.clear_messages()
                summary_for_feedback = [teacher_final_feedback_prompt_header]
                summary_for_feedback.append(f"\nOriginal Question: {ct_state['question']}")
                summary_for_feedback.append("\n\nInitial Answers:")
                for name, ans in ct_state["initial_answers"].items():
                    summary_for_feedback.append(f"- {name}: {ans}")
                summary_for_feedback.append("\n\nElaborations:")
                for name, elab in ct_state["elaborations"].items():
                    summary_for_feedback.append(f"- {name} (on {elab['on_student']}'s answer): {elab['text']}")
                
                final_prompt = "\n".join(summary_for_feedback)
                feedback = teacher_agent.chat(final_prompt)
                ct_state["final_feedback_text"] = feedback
                st.rerun()

        if ct_state["final_feedback_text"]:
            st.markdown("##### Teacher's Final Thoughts:")
            if ct_state["final_feedback_text"].startswith("Final Wrap-up and Feedback:"):
                 st.markdown(ct_state["final_feedback_text"].replace("Final Wrap-up and Feedback:", "").strip())
            else:
                st.markdown(ct_state["final_feedback_text"])
            st.success("🎉 Critical Thinking Exercise Completed! 🎉")
            st.balloons()