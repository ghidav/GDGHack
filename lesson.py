from openai import OpenAI
from os import getenv
import re
from dotenv import load_dotenv

from agents import Agent, UserAgent, INTERACTION_PROTOCOL
from quiz import run_quiz
from critical_thinking import run_critical_thinking_exercise

load_dotenv()

# gets API Key from environment variable OPENAI_API_KEY
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=getenv("OPENROUTER_API_KEY"),
)

MODEL = "google/gemini-2.5-flash-preview"  # You can change this

# Quiz parameters
SUBJECT = "World War II"
NUM_QUESTIONS = 3

# Initialize the agents
teacher_base_prompt = "You are a teacher in a {subject} class."
student_agent_instructions = {
    "Marc": f"You are an enthusiastic funny student named Marc. Provide funny (and sometimes wrong...) answers to the teacher's questions. Use emojis and humor.",
    "Paola": f"You are a knowledgeable but quiet and concise student named Paola. Provide accurate but brief answers.",
}

agents = {}
all_student_names = list(student_agent_instructions.keys()) + ["David"]

# Initialize Teacher Agent
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

agents["David"].update_system_prompt_with_protocol(
    user_protocol
)  # UserAgent can just print this if desired


# run_quiz(agents, SUBJECT, NUM_QUESTIONS, all_student_names)
run_critical_thinking_exercise(agents, SUBJECT, all_student_names)
