from agents import Agent
import json  # Added import

def run_quiz(agents, subject, num_questions, all_student_names, user_name):

    NUM_QUESTIONS = num_questions
    SUBJECT = subject

    # 1. Initialize the agents for the quiz
    teacher_instruction = f"""Your task is to:
1.  When prompted for 'Question X', formulate a distinct question about {SUBJECT}. Your response should ONLY be the question itself.
2.  You will then receive the answers from all students for that question.
3.  This will repeat for {NUM_QUESTIONS} questions.
4.  After all questions are answered, you will be prompted to provide a final feedback.
Based on all answers collected (which will be provided to you), provide constructive feedback to each student.".
"""

    # --- Orchestration Logic ---
    max_turns = (
        (NUM_QUESTIONS * (1 + len(all_student_names))) + 2 + NUM_QUESTIONS
    )  # Teacher Q + Student Ans + Teacher receives ans + Final feedback
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

    # 3. After all questions, ask Teacher for feedback
    if current_turn < max_turns:
        current_turn += 1
        print(f"--- Turn {current_turn}: Teacher to provide feedback ---")

        feedback_prompt_parts = [
            "All questions have been answered. Please provide constructive feedback to the students."
        ]
        for q_idx in range(1, NUM_QUESTIONS + 1):
            feedback_prompt_parts.append(f"\nAnswers for Question {q_idx}:")
            for student_name, answer in all_answers_collected.get(q_idx, {}).items():
                feedback_prompt_parts.append(f"- {student_name}: {answer}")

        feedback_prompt = "\n".join(feedback_prompt_parts)
        feedback_prompt += f"\n\nBased on these answers, provide constructive feedback for the students {', '.join(all_student_names)}. Make your response as a json object with the name of the student as key and the feedback as value."

        final_feedback_response = agents["teacher"].chat(feedback_prompt)
        print(f"\n--- Feedback from teacher ---")
        print(final_feedback_response)

        # Parse the feedback response
        feedback_json = {}  # Initialize with an empty dict
        try:
            # Try to find the JSON object within the response string
            # LLMs can sometimes add introductory text or markdown backticks
            json_start_index = final_feedback_response.find('{')
            json_end_index = final_feedback_response.rfind('}')

            if json_start_index != -1 and json_end_index != -1 and json_start_index < json_end_index:
                json_string = final_feedback_response[json_start_index : json_end_index+1]
                # Attempt to parse the extracted string as JSON
                parsed_object = json.loads(json_string)
                if isinstance(parsed_object, dict):
                    feedback_json = parsed_object
                    print("Feedback JSON parsed successfully.")
                else:
                    print(f"Parsed object is not a dictionary, but a {type(parsed_object)}.")
            else:
                print("Could not find a JSON object structure (e.g. '{...}') in the response.")

        except json.JSONDecodeError as e:
            print(f"Error decoding feedback JSON: {e}. Response was: {final_feedback_response}")
        except Exception as e:
            print(f"An unexpected error occurred during feedback parsing: {e}")

        return feedback_json
