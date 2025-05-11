from openai import OpenAI
from os import getenv
import re
import random
from ast import literal_eval
from dotenv import load_dotenv

from agents import Agent, UserAgent, INTERACTION_PROTOCOL
from quiz import run_quiz
from critical_thinking import run_critical_thinking_exercise
from report_generator import generate_report # Import the report generator

load_dotenv()

# gets API Key from environment variable OPENAI_API_KEY
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=getenv("OPENROUTER_API_KEY"),
)

MODEL = "google/gemini-2.5-flash-preview" 

# Quiz parameters
SUBJECT = "First Industrial Revolution"
TOPIC = "The Invention of the Steam Engine"
STYLE = "Visual and Auditory"
NUM_FOCAL_POINTS = 2
NUM_QUESTIONS = 1

# --- Initialize the agents
student_agent_instructions = {
    "Marc": f"You are an enthusiastic funny student named Marc. Provide funny (and sometimes wrong...) answers to the teacher's questions. Use emojis and humor.",
    "Paola": f"You are a knowledgeable but quiet and concise student named Paola. Provide accurate but brief answers.",
}

agents = {}
all_student_names = list(student_agent_instructions.keys()) + ["David"]

# Initialize Teacher Agent
teacher_base_prompt = "You are a teacher in a {subject} class."
agents["teacher"] = Agent(
    name="teacher", client=client, model=MODEL, instruction=teacher_base_prompt
)

# The teacher should know about the students.
teacher_protocol = INTERACTION_PROTOCOL.format(
    other_agents=", ".join(all_student_names)
)
agents["teacher"].update_system_prompt_with_protocol(teacher_protocol)

# Initialize AI Student Agents
for name, instruction in student_agent_instructions.items():
    agents[name] = Agent(name=name, client=client, model=MODEL, instruction=instruction)
    # Students should know about the teacher and other students
    student_sees_others = ["teacher"] + [
        s_name for s_name in all_student_names if s_name != name
    ]
    student_protocol = INTERACTION_PROTOCOL.format(
        other_agents=", ".join(student_sees_others)
    )
    agents[name].update_system_prompt_with_protocol(student_protocol)

# Initialize User-controlled Student Agent
agents["David"] = UserAgent(
    name="David",
    instruction=f"You are {"David"}, a student in a {SUBJECT} class.",
)

user_sees_others = ["teacher"] + list(student_agent_instructions.keys())
user_protocol = INTERACTION_PROTOCOL.format(other_agents=", ".join(user_sees_others))
agents["David"].update_system_prompt_with_protocol(user_protocol)


# --- Lesson
# gen_introduction()
# gen_example(learning_objective)
#
# for each point:
#     media_content() [image, audio, animation, web]
#     description()
#     critical_thinking() | quiz()
#
# final_test()
# generate_report()

# 0. Identify the Focal Points of the lesson
focal_points_llm_output = agents["teacher"].chat(
    f"Identify the {NUM_FOCAL_POINTS} Key Concepts of the lesson on {SUBJECT} about {TOPIC} and list them ordered by prerequisite logic. Output just a python list of strings."
)

focal_points = []  # Default to an empty list
# Use regex to extract the list from the string
match = re.search(
    r"\[.*?\]", focal_points_llm_output, re.DOTALL
)  # Use re.DOTALL for multiline and find the list string

if match:
    list_string = match.group(0)  # Get the matched string (e.g., "['item1', 'item2']")
    try:
        focal_points = literal_eval(list_string)
    except (ValueError, SyntaxError) as e:
        print(f"Error parsing focal points list string: '{list_string}'. Error: {e}")
        # focal_points will remain an empty list as initialized
else:
    print(
        f"Could not find a Python list in the LLM output: '{focal_points_llm_output}'"
    )
    # focal_points will remain an empty list as initialized

agents["teacher"].set_state("focal_points", focal_points)
agents["teacher"].clear_messages()

# 1. Generate the introduction
introduction = agents["teacher"].chat(
    f"Generate an short introduction for a lesson on {SUBJECT} about {TOPIC}. Make sure to include the Key Concepts of the lesson: {'\n'.join(focal_points)}. Don't mention students at this point."
)
print(f"Teacher: {introduction}\n")

# 2. Generate an example
example = agents["teacher"].chat(
    f"Now generate a brief example related to the lesson that clearly illustrate why the topic is important. Don't mention students at this point."
)
print(f"Teacher: {example}\n")


# 3. For each focal point, generate a description and a media content
for i, focal_point in enumerate(focal_points):
    # 3.1 Generate a description
    description = agents["teacher"].chat(
        f"Generate a short description of the focal point: {focal_point}. Don't mention students at this point."
    )
    print(f"Teacher: {description}\n")

    # 3.2 Generate media content
    # media_content = agents["teacher"].chat(
    #     f"If you could generate a media content (image, audio, animation, web) related to the focal point: {focal_point} based on the {STYLE} learning style, which one would it be? Output a json object with the following keys: 'type' (image, audio, animation, web), 'content' (the content itself), and 'description' (a brief description of the content)."
    # )
    # print(f"Teacher: {media_content}\n")

    # 3.3 Generate a quiz or critical thinking exercise
    random_choice = random.choice(["quiz", "critical_thinking"])
    if random_choice == "quiz":
        print(f"Teacher: Generating a quiz for {focal_point}...\n")
        feedback_json = run_quiz(
            agents, SUBJECT, NUM_QUESTIONS, all_student_names, "David"
        )
        user_specific_feedback = feedback_json.get(
            "David", "No specific feedback found."
        )
        agents["teacher"].set_state(f"quiz_{i}_feedback", user_specific_feedback)
    else:
        print(
            f"Teacher: Generating a critical thinking exercise for {focal_point}...\n"
        )
        feedback_json = run_critical_thinking_exercise(
            agents, SUBJECT, all_student_names
        )
        user_specific_feedback = feedback_json.get(
            "David", "No specific feedback found."
        )
        agents["teacher"].set_state(
            f"critical_thinking_{i}_feedback", user_specific_feedback
        )

    # 3.4 Clear the messages for the next focal point
    for agent in agents.values():
        agent.clear_messages()

# 4.1 Generate the final test
teacher_instruction = f"""Your task is to:
1.  When prompted for 'Question X', formulate a distinct question about a specific focal point of the lesson. Your response should ONLY be the question itself.
2.  You will then receive the answers from all students for that question.
3.  This will repeat for {NUM_FOCAL_POINTS} questions.
4.  After all questions are answered, you will be prompted to provide a final ranking.
Based on all answers collected provide a general overview of the student performance.
"""
test_questions = []
user_answers = []

for q_num, focal_point in enumerate(focal_points):
    # 4.2 Get test question from Teacher
    teacher_prompt = f"{teacher_instruction}\n\nPlease provide Question {q_num + 1} about the Focal Point: {focal_point}. Respond with ONLY the question text."
    test_question = agents["teacher"].chat(teacher_prompt)
    test_questions.append(test_question)
    print(f"The teacher formulated Question {q_num + 1}: {test_question}\n")

    # 4.3 Ask the user the question
    user_prompt = f"{test_question}\n\nPlease provide your answer."
    user_answer = agents["David"].chat(user_prompt)
    user_answers.append(user_answer)

# 4.4 Let the teacher review the answers and provide feedback
teacher_feedback = agents["teacher"].chat(
    f"Here are the answers from the students:\n\n{user_answers}\n\nPlease provide constructive feedback on the answers and a final ranking."
)
print(f"Teacher: {teacher_feedback}\n")
agents["teacher"].set_state("final_test_feedback", teacher_feedback) # Store final test feedback

# 5. Generate a report
# Ensure fpdf2 is installed: pip install fpdf2
generate_report(
    teacher_state=agents["teacher"].state,
    student_name="David", # Assuming the report is for David
    subject=SUBJECT,
    topic=TOPIC,
    output_filename=f"David_{SUBJECT.replace(' ', '_')}_Report.pdf"
)

# print the final teacher state
print("\nFinal Teacher State:")
for key, value in agents["teacher"].state.items():
    print(f"{key}: {value}")
