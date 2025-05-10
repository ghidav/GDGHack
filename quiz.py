from agents import Agent, UserAgent


def make_quiz(agents, subject, num_questions, all_student_names):

    NUM_QUESTIONS = num_questions
    SUBJECT = subject

    # 1. Initialize the agents for the quiz
    teacher_instruction = f"""Your task is to:
1.  When prompted for 'Question X', formulate a distinct question about {SUBJECT}. Your response should ONLY be the question itself.
2.  You will then receive the answers from all students for that question.
3.  This will repeat for {NUM_QUESTIONS} questions.
4.  After all questions are answered, you will be prompted to provide a final ranking.
Based on all answers collected (which will be provided to you), rank the students ({', '.join(all_student_names)}) from 1st to 3rd.
Explain your ranking briefly. Start your ranking response *exactly* with "Final Ranking:".
"""

    # --- Orchestration Logic ---
    max_turns = (
        (NUM_QUESTIONS * (1 + len(all_student_names))) + 2 + NUM_QUESTIONS
    )  # Teacher Q + Student Ans + Teacher receives ans + Final Ranking
    current_turn = 0

    all_answers_collected = {}  # To store {q_num: {student_name: answer}}

    print(
        f"System: Starting the {SUBJECT} class with teacher and students: {', '.join(all_student_names)}.\n"
    )

    for q_num in range(1, NUM_QUESTIONS + 1):
        current_turn += 1
        print(f"--- Turn {current_turn}: Teacher to formulate Question {q_num} ---")

        # 1. Get question from Teacher
        teacher_prompt = f"{teacher_instruction}\n\nPlease provide Question {q_num} about {SUBJECT}. Respond with ONLY the question text."
        if q_num > 1:  # Add context of previous answers if not the first question
            prev_q_answers_summary = (
                f"\nFor your reference, here are the answers to Question {q_num-1}:\n"
            )
            for student_name, answer in all_answers_collected.get(
                q_num - 1, {}
            ).items():
                prev_q_answers_summary += f"- {student_name}: {answer}\n"
            teacher_prompt = prev_q_answers_summary + teacher_prompt

        question_text = agents["teacher"].chat(teacher_prompt)
        print(
            f'Orchestrator Log: teacher formulated Question {q_num}: "{question_text}"\n'
        )

        all_answers_collected[q_num] = {}

        # 2. Ask each student the question
        for student_name in all_student_names:
            current_turn += 1
            print(f"--- Turn {current_turn}: Question {q_num} for {student_name} ---")
            current_student_agent = agents[student_name]

            # For AI students, provide context of who the teacher is.
            # For UserAgent, the prompt is simpler as it's direct input.
            student_prompt_for_llm = (
                f'The teacher asks you, {student_name}: "{question_text}"'
            )
            actual_prompt_for_student = (
                student_prompt_for_llm
                if isinstance(current_student_agent, Agent)
                else question_text
            )

            student_answer = current_student_agent.chat(actual_prompt_for_student)
            all_answers_collected[q_num][student_name] = student_answer
            print(
                f"Orchestrator Log: {student_name}'s answer to Q{q_num}: \"{student_answer[:100]}{'...' if len(student_answer) > 100 else ''}\"\n"
            )

            if current_turn >= max_turns:
                break
        if current_turn >= max_turns:
            print(
                "Orchestrator Log: Max turns reached during student answers. Terminating."
            )
            break

    # 3. After all questions, ask Teacher for ranking
    if current_turn < max_turns:
        current_turn += 1
        print(f"--- Turn {current_turn}: Teacher to provide final ranking ---")

        ranking_prompt_parts = [
            "All questions have been answered. Please provide your final ranking."
        ]
        for q_idx in range(1, NUM_QUESTIONS + 1):
            ranking_prompt_parts.append(f"\nAnswers for Question {q_idx}:")
            for student_name, answer in all_answers_collected.get(q_idx, {}).items():
                ranking_prompt_parts.append(f"- {student_name}: {answer}")

        ranking_prompt = "\n".join(ranking_prompt_parts)
        ranking_prompt += f"\n\nBased on these answers, rank {', '.join(all_student_names)} (1st, 2nd, 3rd) and briefly explain. Start your response *exactly* with 'Final Ranking:'."

        final_ranking_response = agents["teacher"].chat(ranking_prompt)

        print(f"\n--- Final Ranking from teacher ---")
        print(final_ranking_response)

    print("\n--- Classroom Session Ended ---")
