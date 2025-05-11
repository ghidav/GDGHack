from agents import Agent, UserAgent # Assuming Agent and UserAgent are in agents.py

def run_critical_thinking_exercise(agents, subject, all_student_names):
    """
    Orchestrates a critical thinking exercise.
    1. Teacher poses a critical thinking question.
    2. Students answer the question.
    3. Students elaborate on another student's answer.
    4. Teacher provides a wrap-up and feedback.
    """
    SUBJECT = subject
    num_students = len(all_student_names)

    # --- Instructions for Agents ---
    teacher_initial_prompt_instruction = f"""Your task is to formulate a single, insightful critical thinking question about {SUBJECT}.
The question should encourage deep thought and discussion.
Respond with ONLY the question itself."""

    teacher_final_feedback_instruction_header = f"""The critical thinking exercise on {SUBJECT} has concluded.
You will be provided with the original question, all student initial answers, and their elaborations on each other's points.
Your task is to:
1. Provide a comprehensive wrap-up of the discussion.
2. Offer constructive feedback to the students on their critical thinking, engagement, and the quality of their elaborations.
Start your response *exactly* with "Final Wrap-up and Feedback:"."""

    # --- Orchestration Logic ---
    current_turn = 0
    print(
        f"System: Starting the critical thinking exercise on {SUBJECT} with teacher and students: {', '.join(all_student_names)}.\n"
    )

    # 1. Teacher formulates the critical thinking question
    current_turn += 1
    print(f"--- Turn {current_turn}: Teacher to formulate the critical thinking question ---")
    teacher_agent = agents["teacher"]
    critical_question = teacher_agent.chat(teacher_initial_prompt_instruction)
    print(f'Orchestrator Log: Teacher formulated question: "{critical_question}"\n')

    # 2. Students answer the critical thinking question
    student_initial_answers = {}
    print(f"--- Phase: Students provide initial answers to the question ---")
    for student_name in all_student_names:
        current_turn += 1
        print(f"--- Turn {current_turn}: {student_name} to answer the question ---")
        current_student_agent = agents[student_name]
        
        student_prompt_for_llm = f'The teacher asks the following critical thinking question about {SUBJECT}: "{critical_question}". Please provide your thoughtful answer.'
        actual_prompt_for_student = (
            student_prompt_for_llm
            if isinstance(current_student_agent, Agent) # Assuming Agent is the base LLM agent
            else critical_question # For UserAgent, just show the question
        )
        
        answer = current_student_agent.chat(actual_prompt_for_student)
        student_initial_answers[student_name] = answer
        print(f"Orchestrator Log: {student_name}'s answer: \"{answer[:100]}{'...' if len(answer) > 100 else ''}\"\n")

    # 3. Students elaborate on another student's answer
    student_elaborations = {} # {elaborator_name: {"elaborated_on": other_student_name, "elaboration": text}}
    print(f"--- Phase: Students elaborate on each other's answers ---")
    for i in range(num_students):
        current_turn += 1
        elaborator_name = all_student_names[i]
        # Student i elaborates on student (i+1)%N's answer
        elaborated_on_student_idx = (i + 1) % num_students
        elaborated_on_student_name = all_student_names[elaborated_on_student_idx]
        answer_to_elaborate_on = student_initial_answers[elaborated_on_student_name]

        print(f"--- Turn {current_turn}: {elaborator_name} to elaborate on {elaborated_on_student_name}'s answer ---")
        
        current_student_agent = agents[elaborator_name]
        
        elaboration_prompt_for_llm = f"""Regarding the critical thinking question: "{critical_question}"
Your classmate, {elaborated_on_student_name}, provided the following answer: "{answer_to_elaborate_on}"
What are your thoughts on {elaborated_on_student_name}'s perspective? Please elaborate on their answer, offering your insights, agreements, or disagreements, and why."""
        
        elaboration_prompt_for_user = f"""The critical thinking question was: "{critical_question}"
{elaborated_on_student_name}'s answer was: "{answer_to_elaborate_on}"
What are your thoughts on {elaborated_on_student_name}'s perspective? Please elaborate."""

        actual_prompt_for_student = (
            elaboration_prompt_for_llm
            if isinstance(current_student_agent, Agent)
            else elaboration_prompt_for_user
        )
            
        elaboration = current_student_agent.chat(actual_prompt_for_student)
        student_elaborations[elaborator_name] = {
            "elaborated_on_student": elaborated_on_student_name,
            "elaboration_text": elaboration
        }
        print(f"Orchestrator Log: {elaborator_name} elaborated on {elaborated_on_student_name}'s answer: \"{elaboration[:100]}{'...' if len(elaboration) > 100 else ''}\"\n")

    # 4. Teacher provides wrap-up and constructive feedback
    current_turn += 1
    print(f"--- Turn {current_turn}: Teacher to provide final wrap-up and feedback ---")

    feedback_prompt_parts = [teacher_final_feedback_instruction_header]
    feedback_prompt_parts.append(f"\nOriginal Critical Thinking Question: {critical_question}")

    feedback_prompt_parts.append("\n\nInitial Student Answers:")
    for student_name, answer in student_initial_answers.items():
        feedback_prompt_parts.append(f"- {student_name}: {answer}")

    feedback_prompt_parts.append("\n\nStudent Elaborations:")
    for elaborator_name, elaboration_data in student_elaborations.items():
        elaborated_on = elaboration_data["elaborated_on_student"]
        text = elaboration_data["elaboration_text"]
        feedback_prompt_parts.append(f"- {elaborator_name} (elaborating on {elaborated_on}'s answer): {text}")
    
    feedback_prompt_parts.append(f"\n\nPlease provide your wrap-up and constructive feedback now. Remember to start your response *exactly* with 'Final Wrap-up and Feedback:'.")

    final_feedback_prompt = "\n".join(feedback_prompt_parts)
    final_feedback = teacher_agent.chat(final_feedback_prompt)

    print(f"\n--- Final Wrap-up and Feedback from Teacher ---")
    print(final_feedback)

    print("\n--- Critical Thinking Exercise Ended ---")