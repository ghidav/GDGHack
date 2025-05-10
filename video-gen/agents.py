from google.adk.agents import SequentialAgent, LlmAgent
from google.adk.sessions import Session
from google.adk.runners import LocalRunner

from tools import (
    image_generation_tool,
    video_generation_tool,
    tts_tool,
    video_editing_tool
)

storyteller = LlmAgent(
    name="storyteller",
    model="gemini-2.5-flash-preview",
    instruction="Generate a compelling story about {topic} for educational purposes",
    output_key="story"
)

screenwriter = LlmAgent(
    name="screenwriter",
    model="gemini-2.0-pro",
    instruction="Convert story into 5-scene screenplay. Focus on visual elements",
    input_key="story",
    output_key="screenplay"
)

scene_generator = LlmAgent(
    name="scene_generator",
    model="gemini-2.5-pro-vision",
    instruction="Generate Stable Diffusion prompts for each scene",
    tools=[image_generation_tool],
    input_key="screenplay",
    output_key="scene_prompts"
)

scene_animator = LlmAgent(
    name="animator",
    model="gemini-flash",
    instruction="Animate images with smooth transitions",
    tools=[video_generation_tool],
    input_key="scene_prompts",
    output_key="animated_scenes"
)

narrator = LlmAgent(
    name="narrator",
    model="text-to-speech",
    instruction="Convert screenplay to timed narration",
    tools=[tts_tool],
    input_key="screenplay", 
    output_key="voiceover"
)

editor = LlmAgent(
    name="editor",
    model="gemini-2.0-pro",
    instruction="Sync voiceover with animated scenes",
    tools=[video_editing_tool],
    input_keys=["animated_scenes", "voiceover"],
    output_key="final_video"
)

video_pipeline = SequentialAgent(
    name="video_creator",
    sub_agents=[
        storyteller,
        screenwriter,
        scene_generator,
        scene_animator,
        narrator,
        editor
    ]
)

session = Session()
runner = LocalRunner(video_pipeline)
result = runner.execute(
    inputs={"topic": "quantum physics basics"},
    session=session
)