from openai import OpenAI
from os import getenv
import re
from dotenv import load_dotenv

from agents import Agent, UserAgent, INTERACTION_PROTOCOL
from quiz import make_quiz

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
student_agent_configs = {
    "student_a": f"You are an enthusiastic student named EagerStudent. You are knowledgeable about {SUBJECT}. Provide thorough and enthusiastic answers to the teacher's questions.",
    "student_b": f"You are a knowledgeable but quiet and concise student named QuietStudent. You know a lot about {SUBJECT}. Provide accurate but brief answers.",
}
student_base_prompt = "You are a student in a {subject} class."

agents = {}
all_student_names = list(student_agent_configs.keys()) + ["student_c"]

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
for name, instruction in student_agent_configs.items():
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
agents["student_c"] = UserAgent(
    name="student_c",
    instruction=f"You are {"student_c"}, a student in a {SUBJECT} class.",
)

user_sees_others = ["teacher"] + list(student_agent_configs.keys())

user_protocol = INTERACTION_PROTOCOL.format(other_agents=", ".join(user_sees_others))

agents["student_c"].update_system_prompt_with_protocol(
    user_protocol
)  # UserAgent can just print this if desired


make_quiz(agents, SUBJECT, NUM_QUESTIONS, all_student_names)