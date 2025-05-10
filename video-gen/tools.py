from google.adk.tools import Tool
import openai
import replicate
from elevenlabs import generate
import moviepy.editor as mp
from typing import List

from dotenv import load_dotenv
import os

from ..models import TEXT_2_IMAGE, IMAGE_2_VIDEO

load_dotenv()
# Load environment variables
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
REPLICATE_API_KEY = os.getenv("REPLICATE_API_KEY")


# --- Image Generation Tool (OpenAI) ---
def replicate_image_generator(prompt: str, width: int = 1024, height: int = 1024) -> str:
    """
    Generates an image using Replicate's Stable Diffusion.
    """
    model_version = TEXT_2_IMAGE

    output = replicate.run(
        model_version,
        input={
            "prompt": prompt,
            "width": width,
            "height": height,
            "num_outputs": 1,
        }
    )
    # The output structure can vary slightly between Replicate models.
    # Usually, it's a list of URLs.
    if output and isinstance(output, list):
        return output[0]
    elif isinstance(output, str): # Some models might return a single URL directly
        return output
    else:
        raise Exception(f"Unexpected output format from Replicate: {output}")

image_generation_tool = Tool(
    name="replicate_image_gen",
    func=replicate_image_generator,
    description="Generates high-quality images using Replicate.com models."
)

# --- Video Generation Tool (Replicate) ---  
def animate_image(image_url: str, fps: int = 24) -> str:
    output = replicate.run(
        IMAGE_2_VIDEO,
        input={
            "input_image": image_url,
            "video_frames": 24,
            "fps": fps
        }
    )
    return output[0]

video_generation_tool = Tool(
    name="replicate_video_gen",
    func=animate_image,
    description="Animates images using Replicate.com models."
)

# --- Text-to-Speech Tool (ElevenLabs) ---
def generate_voiceover(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> str:
    audio = generate(
        api_key=ELEVENLABS_API_KEY,
        text=text,
        voice=voice_id,
        model="eleven_multilingual_v2",
        stability=0.5
    )
    return audio  # Returns bytes that can be saved to file

tts_tool = Tool(
    name="elevenlabs_tts",
    func=generate_voiceover,
    description="Generates natural-sounding voiceovers."
)

# --- Video Editing Tool (MoviePy) ---
def merge_videos(scene_paths: List[str], 
                audio_path: str, 
                subtitles: List[dict]) -> str:
    
    # Load video clips
    clips = [mp.VideoFileClip(p) for p in scene_paths]
    final_clip = mp.concatenate_videoclips(clips)
    
    # Add audio
    audio = mp.AudioFileClip(audio_path)
    final_clip = final_clip.set_audio(audio)
    
    # Add subtitles
    text_clips = []
    for sub in subtitles:
        txt_clip = mp.TextClip(sub["text"], fontsize=24, color="white")
        txt_clip = txt_clip.set_pos("bottom").set_duration(sub["duration"])
        text_clips.append(txt_clip)
    
    final_clip = mp.CompositeVideoClip([final_clip] + text_clips)
    output_path = "assets/final_video.mp4"
    final_clip.write_videofile(output_path, codec="libx264", fps=24)
    
    return output_path

video_editing_tool = Tool(
    name="moviepy_editor",
    func=merge_videos,
    description="Merges video scenes with audio and subtitles."
)
