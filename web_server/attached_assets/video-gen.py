import os
import replicate
from elevenlabs.client import ElevenLabs
from openai import OpenAI  # For OpenRouter
from dotenv import load_dotenv
import requests  # For downloading files
import json  # For parsing LLM output

# --- Configuration ---
load_dotenv()

REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Ensure this is the correct base URL for OpenRouter's OpenAI-compatible endpoint
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

TEXT_MODEL = "google/gemini-2.5-flash-preview"
IMAGE_MODEL = "black-forest-labs/flux-dev-lora"
VIDEO_MODEL = "wavespeedai/wan-2.1-i2v-480p"

VOICE_ID_MAP = {
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Fin": "JBFqnCBsd6RMkjVDRZzb",  # Example, was previously hardcoded
    # Add more voices as needed: name: id
}

# --- Initialize API Clients ---
replicate_client = None
if REPLICATE_API_TOKEN:
    replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
else:
    print(
        "Warning: REPLICATE_API_TOKEN not found. Image and video generation will fail."
    )

if ELEVENLABS_API_KEY:
    elevenlabs_client = ElevenLabs(
        api_key=ELEVENLABS_API_KEY,
    )

# if ELEVENLABS_API_KEY:
#     elevenlabs.set_api_key(ELEVENLABS_API_KEY)
# else:
#     print("Warning: ELEVENLABS_API_KEY not found. Narration generation will fail.")

openrouter_client = None
if OPENROUTER_API_KEY:
    openrouter_client = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )
else:
    print("Warning: OPENROUTER_API_KEY not found. Screenwriting will fail.")


# --- Helper Functions ---
def _download_file(url, destination_path):
    """Downloads a file from a URL to a destination path."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with open(destination_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Successfully downloaded: {destination_path}")
        return destination_path
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file from {url}: {e}")
        return None


# --- Core Functions ---


def generate_screenplay(story_text, num_scenes=5):
    """
    Generates a screenplay with a specified number of scenes from a story.
    Each scene should have a 'description' for image/video and 'narration' for audio.
    Outputs a list of scene dictionaries.
    """
    if not openrouter_client:
        print("Error: OpenRouter client not initialized.")
        return None

    prompt = f"""
    You are a screenwriter. Based on the following story, create a screenplay with exactly {num_scenes} scenes.
    For each scene, provide:
    1. A concise visual 'description' (max 2 sentences, focusing on what can be visually represented in a single image or short clip). This will be used for image generation.
    2. A 'narration' script (1-3 sentences) that will be spoken over the scene. This will be used for audio generation.

    Format your output as a JSON array of objects, where each object represents a scene and has keys "scene_number", "description", and "narration".
    Ensure the scene_number starts from 1.

    Story:
    {story_text}

    JSON Output:
    """

    try:
        # Choose a model available on OpenRouter, e.g., "mistralai/mistral-7b-instruct", "openai/gpt-3.5-turbo"
        # Ensure the model supports JSON output mode if available/used.
        chat_completion = openrouter_client.chat.completions.create(
            model=TEXT_MODEL,  # Replace with your preferred OpenRouter model
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that generates screenplays in JSON format. The output must be a valid JSON array of scene objects.",
                },
                {"role": "user", "content": prompt},
            ],
            # Some models/APIs support a response_format parameter for JSON
            # response_format={"type": "json_object"} # Uncomment if your model/OpenRouter setup supports this
        )
        response_content = chat_completion.choices[0].message.content

        # Attempt to parse the JSON
        try:
            # The LLM might sometimes add introductory text before the JSON.
            # Try to find the start of the JSON array.
            json_start_index = response_content.find("[")
            json_end_index = response_content.rfind("]") + 1
            if json_start_index != -1 and json_end_index != 0:
                screenplay_json_str = response_content[json_start_index:json_end_index]
            else:  # Assume the whole string is JSON or try parsing directly
                screenplay_json_str = response_content

            screenplay = json.loads(screenplay_json_str)
        except json.JSONDecodeError:
            print(
                f"Error: Could not parse screenplay JSON. Raw response: {response_content}"
            )
            # Fallback: try to extract JSON if it's wrapped in markdown ```json ... ```
            if "```json" in response_content:
                try:
                    screenplay_json_str = (
                        response_content.split("```json")[1].split("```")[0].strip()
                    )
                    screenplay = json.loads(screenplay_json_str)
                except Exception as e_inner:
                    print(f"Failed to extract/parse JSON from markdown: {e_inner}")
                    return None
            else:
                return None

        if (
            isinstance(screenplay, dict) and "scenes" in screenplay
        ):  # If model wraps in a "scenes" key
            screenplay = screenplay["scenes"]

        if not isinstance(screenplay, list) or not all(
            isinstance(s, dict)
            and "description" in s
            and "narration" in s
            and "scene_number" in s
            for s in screenplay
        ):
            print(
                f"Error: Screenplay not in expected format (list of dicts with 'scene_number', 'description', 'narration'). Received: {screenplay}"
            )
            return None

        print(f"Screenplay generated with {len(screenplay)} scenes.")
        return screenplay
    except Exception as e:
        print(f"Error generating screenplay: {e}")
        return None


def generate_scene_image(scene_description, output_path):
    """
    Generates an image for a scene description using Replicate.
    """
    if not replicate_client:
        print("Error: Replicate client not initialized.")
        return None

    # Example Replicate model for text-to-image (e.g., SDXL or a faster variant)
    # Find model versions on replicate.com.
    # SDXL Lightning is fast: "lucataco/sdxl-lightning-4step:727e49a643e999d602a896c774a0658ffefea21465756a6ce24b7ea4165eba6a"
    # Standard SDXL: "stability-ai/sdxl:c221b2b8ef527988fb59bf24a8b97c4561f1c671f73bd389f866bfb27c061316"
    model_identifier = IMAGE_MODEL
    try:
        print(f'Generating image for: "{scene_description}" using {model_identifier}')
        output = replicate_client.run(
            model_identifier, input={"prompt": scene_description}
        )
        if output and isinstance(output, list) and len(output) > 0:
            image_url = output[0]
            print(f"Image generated: {image_url}")
            return _download_file(image_url, output_path)
        else:
            print(f"Error: No image URL received from Replicate. Output: {output}")
            return None
    except Exception as e:
        print(f"Error generating scene image: {e}")
        return None


def animate_scene_image(
    image_path, output_path, prompt_for_animation="animate this scene"
):
    """
    Animates an image into a short video clip using Replicate.
    Uses Stable Video Diffusion which takes an image file.
    """
    if not replicate_client:
        print("Error: Replicate client not initialized.")
        return None

    # Stable Video Diffusion model: "stability-ai/stable-video-diffusion:..."
    # Check replicate.com for the latest version.
    # Example version: "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438"
    model_identifier = VIDEO_MODEL

    try:
        print(f"Animating image: {image_path} using {model_identifier}")
        with open(image_path, "rb") as img_file_obj:
            output = replicate_client.run(
                model_identifier,
                input={
                    "prompt": prompt_for_animation,
                    "image": img_file_obj,  # Changed from image_path to input_image based on SVD model spec
                    "max_area": "832x480",
                    "fast_mode": "Balanced",
                },
            )
        if output:  # SVD usually returns a direct URL to the video
            video_url = output
            print(f"Video animation generated: {video_url}")
            return _download_file(video_url, output_path)
        else:
            print(
                f"Error: No video URL received from Replicate for animation. Output: {output}"
            )
            return None
    except Exception as e:
        print(f"Error animating image: {e}")
        return None


def generate_narration_audio(text, output_path, voice_name_or_id="Adam"):
    """
    Generates audio narration for the given text using ElevenLabs.
    voice_name_or_id: Can be a predefined name (e.g., 'Adam', 'Rachel') or a specific voice ID.
    """
    if not elevenlabs_client:
        print("Error: ElevenLabs client not initialized. Check ELEVENLABS_API_KEY.")
        return None

    actual_voice_id = VOICE_ID_MAP.get(
        voice_name_or_id, voice_name_or_id
    )  # Use name if in map, else assume it's an ID

    try:
        print(
            f'Generating narration for: "{text[:50]}..." using voice ID: {actual_voice_id}'
        )

        audio_stream = elevenlabs_client.text_to_speech.convert(
            text=text,
            voice_id=actual_voice_id,
            model_id="eleven_turbo_v2_5",  # Or your preferred model like "eleven_multilingual_v2", "eleven_flash_v2_5"
            output_format="mp3_44100_128",  # Example output format
        )
        if audio_stream:
            with open(output_path, "wb") as audio_file:
                for chunk in audio_stream:
                    if chunk:  # Ensure the chunk is not None
                        audio_file.write(chunk)
            print(f"Narration audio saved: {output_path}")
            return output_path
        else:
            print("Error: No audio data stream received from ElevenLabs.")
            return None
    except Exception as e:
        print(f"Error generating narration audio: {e}")
        return None


def compile_scene_assets(scene_assets_info, final_output_path_suggestion):
    """
    Currently, this function just lists the generated assets.
    Actual stitching requires a library like MoviePy or FFmpeg.
    """
    print("\n--- Video Editing (Asset Compilation Stage) ---")
    if not scene_assets_info:
        print("No scene assets to compile.")
        return

    print("Generated assets for each scene:")
    for i, assets in enumerate(scene_assets_info):
        print(f"  Scene {assets.get('scene_number', i+1)}:")
        if assets.get("image_path"):
            print(f"    Image: {assets['image_path']}")
        if assets.get("video_clip_path"):
            print(f"    Video Clip: {assets['video_clip_path']}")
        if assets.get("audio_path"):
            print(f"    Audio: {assets['audio_path']}")

    print(
        f"\nTo stitch these into a final video (e.g., at {final_output_path_suggestion}), you can use a library like MoviePy."
    )
    print(f"Install it using: pip install moviepy")
    print("Then, you could implement stitching similar to this (this is conceptual):")
    print(
        """
# from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
#
# video_clips_for_concatenation = []
# for asset_info in scene_assets_info:
#     video_file = asset_info.get('video_clip_path')
#     audio_file = asset_info.get('audio_path')
#
#     if video_file and audio_file:
#         try:
#             video_segment = VideoFileClip(video_file)
#             audio_segment = AudioFileClip(audio_file)
#
#             # Ensure audio duration matches video, or choose a strategy
#             # If audio is shorter, it will loop or end. If longer, it will be cut.
#             # For precise control, you might need to adjust durations.
#             final_audio_segment = audio_segment.set_duration(video_segment.duration)
#             video_segment_with_audio = video_segment.set_audio(final_audio_segment)
#             
#             video_clips_for_concatenation.append(video_segment_with_audio)
#         except Exception as e:
#             print(f"Error processing scene {asset_info.get('scene_number', '?')} for moviepy: {e}")
#     elif video_file: # Video only, no audio for this scene
#         try:
#             video_clips_for_concatenation.append(VideoFileClip(video_file))
#         except Exception as e:
#             print(f"Error loading video clip {video_file} for moviepy: {e}")
#
# if video_clips_for_concatenation:
#     try:
#         final_cut = concatenate_videoclips(video_clips_for_concatenation, method="compose")
#         final_cut.write_videofile(final_output_path_suggestion, codec="libx264", audio_codec="aac")
#         print(f"Final video conceptually stitched and would be saved to: {final_output_path_suggestion}")
#     except Exception as e:
#         print(f"Error during final video concatenation with MoviePy: {e}")
# else:
#     print("No video clips were successfully prepared for concatenation.")
    """
    )
    return None  # No final path created by this placeholder function


# --- Main Orchestration Function ---
def create_video_from_story(
    story_text, output_project_name="my_video_project", num_scenes=5
):
    """
    Main function to generate a video from a story.
    """
    if not all(
        [replicate_client, ELEVENLABS_API_KEY, openrouter_client]
    ):  # Check if clients initialized
        print(
            "Error: One or more API clients are not initialized. Please check API keys and .env file."
        )
        return

    print(f'Starting video generation for story: "{story_text[:60]}..."')

    base_output_dir = "generated_video_projects"
    os.makedirs(base_output_dir, exist_ok=True)

    project_dir = os.path.join(base_output_dir, output_project_name)
    os.makedirs(project_dir, exist_ok=True)
    print(f"Output will be saved in: {project_dir}")

    # 1. Screenwriting
    print("\n--- 1. Generating Screenplay ---")
    screenplay_scenes = generate_screenplay(story_text, num_scenes=num_scenes)
    if not screenplay_scenes:
        print("Failed to generate screenplay. Aborting.")
        return

    screenplay_file_path = os.path.join(project_dir, "screenplay.json")
    with open(screenplay_file_path, "w") as f:
        json.dump(screenplay_scenes, f, indent=2)
    print(f"Screenplay saved to {screenplay_file_path}")

    collected_scene_assets_info = []  # Stores dicts with paths for each scene

    for scene_info in screenplay_scenes:
        scene_num = scene_info.get(
            "scene_number", screenplay_scenes.index(scene_info) + 1
        )
        print(f"\n--- Processing Scene {scene_num}/{len(screenplay_scenes)} ---")

        scene_specific_dir = os.path.join(project_dir, f"scene_{scene_num}")
        os.makedirs(scene_specific_dir, exist_ok=True)

        scene_desc = scene_info.get("description")
        scene_narrate = scene_info.get("narration")

        current_assets = {
            "scene_number": scene_num,
            "description": scene_desc,
            "narration": scene_narrate,
        }

        if not scene_desc or not scene_narrate:
            print(
                f"Warning: Scene {scene_num} is missing description or narration in screenplay. Skipping asset generation for this scene."
            )
            collected_scene_assets_info.append(current_assets)
            continue

        # 2. Scene Image Generation
        print(f"\n--- 2. Generating Image for Scene {scene_num} ---")
        img_filename = f"scene_{scene_num}_image.png"
        img_path = os.path.join(scene_specific_dir, img_filename)
        generated_img_path = generate_scene_image(scene_desc, img_path)
        current_assets["image_path"] = generated_img_path

        # 3. Scene Animation (Image to Video)
        if generated_img_path:
            print(f"\n--- 3. Animating Image for Scene {scene_num} ---")
            vid_filename = f"scene_{scene_num}_video.mp4"
            vid_path = os.path.join(scene_specific_dir, vid_filename)
            # You could pass part of scene_desc or scene_narrate as prompt_for_animation if model uses it
            generated_vid_path = animate_scene_image(
                generated_img_path, vid_path, prompt_for_animation=scene_desc[:100]
            )
            current_assets["video_clip_path"] = generated_vid_path
        else:
            print(
                f"Skipping animation for scene {scene_num} as image generation failed."
            )
            current_assets["video_clip_path"] = None

        # 4. Narration (Text to Audio)
        print(f"\n--- 4. Generating Narration for Scene {scene_num} ---")
        audio_filename = f"scene_{scene_num}_audio.mp3"
        audio_path = os.path.join(scene_specific_dir, audio_filename)
        generated_audio_path = generate_narration_audio(
            scene_narrate, audio_path, voice_name_or_id="Adam"
        )  # Or another voice
        current_assets["audio_path"] = generated_audio_path

        collected_scene_assets_info.append(current_assets)

    # 5. Editor (Compile assets - placeholder for actual stitching)
    print("\n--- 5. Compiling Video Assets (Placeholder) ---")
    final_video_suggestion_path = os.path.join(
        project_dir, f"{output_project_name}_final_video.mp4"
    )
    compile_scene_assets(collected_scene_assets_info, final_video_suggestion_path)

    print(f"\n--- Video Generation Process Completed for '{output_project_name}' ---")
    print(f"All generated assets are located in subdirectories within: {project_dir}")
    print("To create a final stitched video, consider implementing the MoviePy logic.")


if __name__ == "__main__":
    # --- Example Usage ---
    sample_story_text = """
    A lone astronaut, Kai, drifts in a damaged escape pod, Earth a distant blue marble.
    His AI companion, HALCYON, calculates dwindling oxygen reserves. They must find a solution.
    Suddenly, an uncharted, shimmering nebula appears on the long-range scanners, pulsing with strange energy.
    Taking a desperate gamble, Kai pilots the pod into the nebula, systems flickering wildly.
    Inside, instead of destruction, they find a breathtaking alien construct, a station of light and crystal, offering salvation.
    """

    # Using 3 scenes for a quicker test run. The prompt asked for "about 5 scenes".
    # You can change num_scenes to 5 for the full request.
    create_video_from_story(
        sample_story_text,
        output_project_name="astronaut_kai_journey",
        num_scenes=3,  # Set to 5 for "about 5 scenes"
    )
