# utils.py
import streamlit as st
import re
from ast import literal_eval
# import random # random is imported but not used in the current version of display_media_content

def get_focal_points(teacher_agent, subject, topic, num_focal_points=3):
    """
    Gets the focal points for a lesson from the teacher agent.
    If the teacher agent is not available or an error occurs, returns default focal points.
    """
    default_focal_points = [
        "The Development of the Steam Engine",
        "Impact on Manufacturing Processes",
        "The Transportation Revolution" # Corrected typo from original "Transportation Revolution"
    ]

    if teacher_agent.client is None: # Check if API client is even available
        st.warning("Teacher agent's API client is not initialized. Using default focal points.")
        return default_focal_points

    try:
        focal_points_llm_output = teacher_agent.chat(
            f"Identify the {num_focal_points} Key Concepts of the lesson on {subject} about {topic} and list them ordered by prerequisite logic. Output just a python list of strings. Example: ['Concept 1', 'Concept 2', 'Concept 3']"
        )

        match = re.search(
            r"\[.*?\]", focal_points_llm_output,
            re.DOTALL)

        if match:
            list_string = match.group(0)
            try:
                focal_points = literal_eval(list_string)
                if isinstance(focal_points, list) and all(isinstance(item, str) for item in focal_points):
                    if len(focal_points) == num_focal_points:
                        return focal_points
                    else:
                        st.warning(f"LLM returned {len(focal_points)} focal points, expected {num_focal_points}. Using default or returned points if reasonable.")
                        # Optionally return subset/superset or default
                        return focal_points if focal_points else default_focal_points
                else:
                    st.warning(f"Parsed list is not a list of strings: '{list_string}'. Using default focal points.")
                    return default_focal_points
            except (ValueError, SyntaxError) as e:
                st.warning(
                    f"Error parsing focal points list string: '{list_string}'. Error: {e}. Using default focal points."
                )
                return default_focal_points
        else:
            st.warning(
                f"Could not find a Python list in the LLM output: '{focal_points_llm_output}'. Using default focal points."
            )
            return default_focal_points
    except Exception as e:
        st.error(f"Error getting focal points from teacher agent: {e}. Using default focal points.")
        return default_focal_points


def display_media_content(focal_point, index):
    """
    Displays media content related to a focal point.
    This function selects appropriate images based on the focal point and includes SVGs.
    """
    # Pre-fetched stock photos URLs
    steam_engine_urls = [
        "https://pixabay.com/get/g142eddb02dc0f66483ad03609a5cf474921858069f40fd8951601d866b4555ac8676e0caca8546c145e29c94a908330dc419aca1b396c31eb49bc8c7b197c493_1280.jpg",
        "https://pixabay.com/get/g30e5cea688f4d2daf10351d3ccddd132c10b367f09e842ba78495a06f9db8ea74edb066a05a777ba69ebc96b359cd3e53967172dc53ef9f814496b12b3c309ef_1280.jpg",
        "https://pixabay.com/get/g90868d0719ea7b7c1b079288a6c0f86bcf0f85fb7091d29f9cfaccd82eb0375fcac8acb086088303c01a2e2615efef15dfc5818cf40eece7c2680fa56b2dba1d_1280.jpg",
        "https://pixabay.com/get/g1973fe130ea35bd535a220aa5fd9ecf0aecbaba6fc827ea5e84c3debbc71740cc561d4afe678330a4663aa5be159e858912787e836699e0db579145ed2b05622_1280.jpg"
    ]

    industrial_revolution_urls = [
        "https://pixabay.com/get/g5b0eab50465040d74792ab770ddbeb1e70bf67def23e54b1ef7ac541089023333e49c2aa5b7041c69cc5d01f2e04de58_1280.jpg",
        "https://pixabay.com/get/ge7e582317a41a52618f832b1b8a69954299ec7bd0dfcb1355e71b5b62c2aade574659fa957aa6bcc78916af684c949d98b1c340a6b1ad704ed5120a1f181b714_1280.jpg",
        "https://pixabay.com/get/gc86f4b0feb360b111de75297e1bcbeecf4634eb05cf460ca77ec9003fe26ba1f1bb0239d80ca891b0c39b0a3a1c306bbbefbf8abb78581263ed60424c2ff47eb_1280.jpg",
        "https://pixabay.com/get/gb5fd406b9d6c4e3b0d65bdf2f832420e6fb55bbd8bb822c810e8f9b637d044a971a261331d4028eb0f869ed48b7039e1f347a814f985ac89aea480c19d4b929e_1280.jpg"
    ]
    
    selected_image_urls = []
    image_caption_base = "Industrial Revolution Scene"

    fp_lower = focal_point.lower()
    if "steam" in fp_lower or "engine" in fp_lower:
        selected_image_urls = [steam_engine_urls[index % len(steam_engine_urls)]]
        image_caption_base = "Historical Steam Engine"
        if len(steam_engine_urls) > 1:
             selected_image_urls.append(steam_engine_urls[(index + 1) % len(steam_engine_urls)])
    elif "manufactur" in fp_lower or "factories" in fp_lower:
        selected_image_urls = [industrial_revolution_urls[index % len(industrial_revolution_urls)]]
        image_caption_base = "Industrial Manufacturing"
        if len(industrial_revolution_urls) > 1:
            selected_image_urls.append(industrial_revolution_urls[(index + 1) % len(industrial_revolution_urls)])
    elif "transport" in fp_lower or "railway" in fp_lower or "ship" in fp_lower:
        selected_image_urls = [
            steam_engine_urls[index % len(steam_engine_urls)], # Steam engines were key for transport
            industrial_revolution_urls[(index + 1) % len(industrial_revolution_urls)] # General context
        ]
        image_caption_base = "Steam-Powered Transportation"
    else:
        selected_image_urls = [
            industrial_revolution_urls[index % len(industrial_revolution_urls)],
            steam_engine_urls[index % len(steam_engine_urls)]
        ]
        image_caption_base = "Industrial Revolution Scene"

    if selected_image_urls:
        if len(selected_image_urls) > 1:
            cols = st.columns(len(selected_image_urls))
            for i, (col, img_url) in enumerate(zip(cols, selected_image_urls)):
                with col:
                    st.image(img_url,
                             caption=f"{image_caption_base} ({i+1})",
                             use_container_width=True)
        else:
            st.image(selected_image_urls[0],
                     caption=image_caption_base,
                     use_container_width=True)

    # Display additional media type based on focal point (SVGs or Timeline)
    if "steam" in fp_lower or "engine" in fp_lower:
        st.subheader("Interactive Diagram: Steam Engine Principle")
        st.markdown("""
        <svg width="100%" viewBox="0 0 600 300" xmlns="http://www.w3.org/2000/svg">
            <rect x="100" y="150" width="400" height="100" fill="#777" stroke="#000" stroke-width="2"/>
            <circle cx="150" cy="200" r="50" fill="#555" stroke="#000" stroke-width="2" id="wheel1_svg"/>
            <circle cx="450" cy="200" r="50" fill="#555" stroke="#000" stroke-width="2" id="wheel2_svg"/>
            <rect x="200" y="100" width="200" height="50" fill="#999" stroke="#000" stroke-width="2"/>
            <rect x="250" y="50" width="100" height="50" fill="#666" stroke="#000" stroke-width="2"/>
            <path d="M 270,50 Q 280,30 290,50" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="2,2">
                <animate attributeName="d" values="M 270,50 Q 280,30 290,50; M 270,50 Q 280,20 290,50; M 270,50 Q 280,30 290,50" dur="3s" repeatCount="indefinite"/>
            </path>
            <path d="M 320,50 Q 330,30 340,50" fill="none" stroke="#fff" stroke-width="2" stroke-dasharray="2,2">
                <animate attributeName="d" values="M 320,50 Q 330,30 340,50; M 320,50 Q 330,20 340,50; M 320,50 Q 330,30 340,50" dur="2.5s" repeatCount="indefinite"/>
            </path>
            <g id="wheel1_details_svg">
                <circle cx="150" cy="200" r="40" fill="#444" stroke="#000" stroke-width="1"/>
                <line x1="150" y1="160" x2="150" y2="240" stroke="#222" stroke-width="3"/> <line x1="110" y1="200" x2="190" y2="200" stroke="#222" stroke-width="3"/>
                <line x1="120" y1="170" x2="180" y2="230" stroke="#222" stroke-width="3"/> <line x1="120" y1="230" x2="180" y2="170" stroke="#222" stroke-width="3"/>
            </g>
            <g id="wheel2_details_svg">
                <circle cx="450" cy="200" r="40" fill="#444" stroke="#000" stroke-width="1"/>
                <line x1="450" y1="160" x2="450" y2="240" stroke="#222" stroke-width="3"/> <line x1="410" y1="200" x2="490" y2="200" stroke="#222" stroke-width="3"/>
                <line x1="420" y1="170" x2="480" y2="230" stroke="#222" stroke-width="3"/> <line x1="420" y1="230" x2="480" y2="170" stroke="#222" stroke-width="3"/>
            </g>
            <animateTransform xlink:href="#wheel1_details_svg" attributeName="transform" type="rotate" from="0 150 200" to="360 150 200" dur="4s" repeatCount="indefinite" />
            <animateTransform xlink:href="#wheel2_details_svg" attributeName="transform" type="rotate" from="0 450 200" to="360 450 200" dur="4s" repeatCount="indefinite" />
            <text x="150" y="270" text-anchor="middle" fill="#333" font-family="Arial" font-size="12">Wheel</text>
            <text x="450" y="270" text-anchor="middle" fill="#333" font-family="Arial" font-size="12">Wheel</text>
            <text x="300" y="130" text-anchor="middle" fill="#333" font-family="Arial" font-size="12">Boiler</text>
            <text x="300" y="75" text-anchor="middle" fill="#333" font-family="Arial" font-size="12">Steam Chamber</text>
            <text x="300" y="30" text-anchor="middle" fill="#333" font-family="Arial" font-size="12">Steam Output</text>
        </svg>
        """, unsafe_allow_html=True)

    elif "manufactur" in fp_lower or "factories" in fp_lower:
        st.subheader("Factory Process Visualization")
        st.markdown("""
        <svg width="100%" viewBox="0 0 600 300" xmlns="http://www.w3.org/2000/svg">
            <rect x="50" y="100" width="500" height="150" fill="#b47d49" stroke="#000" stroke-width="2"/>
            <rect x="100" y="150" width="80" height="100" fill="#333" stroke="#000" stroke-width="1"/>
            <rect x="250" y="150" width="80" height="100" fill="#333" stroke="#000" stroke-width="1"/>
            <rect x="400" y="150" width="80" height="100" fill="#333" stroke="#000" stroke-width="1"/>
            <polygon points="50,100 300,30 550,100" fill="#8b5a2b" stroke="#000" stroke-width="2"/>
            <rect x="450" y="20" width="30" height="80" fill="#b47d49" stroke="#000" stroke-width="1"/>
            <path d="M 460,20 Q 470,0 480,20" fill="none" stroke="#aaa" stroke-width="3" stroke-dasharray="3,3">
                <animate attributeName="d" values="M 460,20 Q 470,0 480,20; M 465,20 Q 490,-10 485,20; M 460,20 Q 470,0 480,20" dur="4s" repeatCount="indefinite"/>
            </path>
            <path d="M 455,15 Q 440,-5 470,10" fill="none" stroke="#aaa" stroke-width="3" stroke-dasharray="3,3">
                <animate attributeName="d" values="M 455,15 Q 440,-5 470,10; M 455,15 Q 430,-15 465,5; M 455,15 Q 440,-5 470,10" dur="5s" repeatCount="indefinite"/>
            </path>
            <rect x="150" y="190" width="300" height="10" fill="#333" stroke="#000" stroke-width="1"/>
            <rect id="product1_svg" x="170" y="180" width="20" height="10" fill="#d9b38c" stroke="#000" stroke-width="1">
                <animate attributeName="x" values="170; 430; 170" dur="8s" repeatCount="indefinite"/>
            </rect>
            <rect id="product2_svg" x="230" y="180" width="20" height="10" fill="#d9b38c" stroke="#000" stroke-width="1">
                <animate attributeName="x" values="230; 490; 230" dur="8s" repeatCount="indefinite" begin="-2s"/>
            </rect>
            <rect id="product3_svg" x="310" y="180" width="20" height="10" fill="#d9b38c" stroke="#000" stroke-width="1">
                <animate attributeName="x" values="310; 170; 310" dur="8s" repeatCount="indefinite" begin="-4s"/>
            </rect>
            <text x="300" y="280" text-anchor="middle" fill="#333" font-family="Arial" font-size="14">Mass Production Factory</text>
        </svg>
        """, unsafe_allow_html=True)

    elif "transport" in fp_lower or "railway" in fp_lower or "ship" in fp_lower:
        st.subheader("Transportation Revolution Timeline")
        transportation_data = [
            {"year": 1804, "event": "First steam locomotive (Trevithick)", "icon": "🚂"},
            {"year": 1825, "event": "Stockton & Darlington Railway", "icon": "🛤️"},
            {"year": 1830, "event": "Liverpool & Manchester Railway", "icon": "🚉"},
            {"year": 1838, "event": "First regular transatlantic steamship service (SS Great Western)", "icon": "🚢"}, # Year corrected
            {"year": 1869, "event": "First Transcontinental Railroad (USA)", "icon": "🚞"}
        ]
        for item in transportation_data:
            st.markdown(f"##### {item['icon']} **{item['year']}**: {item['event']}")
            if item != transportation_data[-1]:
                 st.divider()
    else:
        st.subheader("Key Facts & Concepts")
        st.markdown(f"""
        The focal point, **"{focal_point}"**, is a crucial element of the First Industrial Revolution. This period, starting in Great Britain in the late 18th century, signifies a major shift from agrarian, manual labor-based economies to societies dominated by industry and machine manufacturing.
        - Key innovations included steam power, advancements in textile manufacturing (like the spinning jenny and power loom), and new iron production techniques.
        - This era led to unprecedented urban growth, the rise of the factory system, and the formation of a new industrial working class.
        - It had profound social, economic, and cultural impacts, reshaping daily life, societal structures, and global power dynamics.
        """)