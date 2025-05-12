# agents.py
import streamlit as st

INTERACTION_PROTOCOL = """You are in a classroom environment.
The other participants are: {other_agents}.
"""


class Agent:
    def __init__(self, name, client, model, instruction):
        self.name = name
        self.instruction = instruction
        self.client = client
        self.model = model
        self.state = {}  # For agents to store information if needed

        # Initialize messages with system prompt.
        system_prompt = self.instruction
        self.messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]
        self.other_agents = []

    def update_system_prompt_with_protocol(self, protocol_content):
        """Updates the system prompt to include the interaction protocol."""
        # Ensure protocol is appended to the base instruction
        # Check if protocol is already there to avoid duplication if method is called multiple times
        if INTERACTION_PROTOCOL.splitlines()[0] not in self.messages[0]["content"]:
            base_instruction = self.messages[0]["content"]
            self.messages[0]["content"] = f"{base_instruction}\n\n{protocol_content}"
        else: # If protocol is already there, replace the other_agents part if needed
            base_instruction_part = self.messages[0]["content"].split(INTERACTION_PROTOCOL.splitlines()[0])[0]
            self.messages[0]["content"] = f"{base_instruction_part.strip()}\n\n{protocol_content}"


    def chat(self, prompt):
        self.messages.append({"role": "user", "content": prompt})
        try:
            # Ensure the client is not None (API key might not be set)
            if self.client is None:
                st.error(f"API Client for agent {self.name} is not initialized. Please check API key.")
                return "Error: API client not initialized."
            api_response = self.client.chat.completions.create(
                model=self.model, messages=self.messages
            )
            assistant_response_content = api_response.choices[0].message.content
            self.messages.append(
                {"role": "assistant", "content": assistant_response_content}
            )
            return assistant_response_content
        except Exception as e:
            st.error(f"Error during API call for agent {self.name}: {e}")
            error_message = f"Error: Could not get a response. Details: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_message})
            return error_message

    def clear_messages(self, keep_system_prompt=True):
        if keep_system_prompt and self.messages:
            self.messages = [self.messages[0]]
        else:
            self.messages = []


    def clear_state(self):
        self.state = {}

    def set_state(self, key, value):
        self.state[key] = value


class UserAgent:
    def __init__(self, name, instruction="You are a student in the class."):
        self.name = name
        self.instruction = instruction  # Store instruction for consistency
        self.messages = [{"role": "system", "content": instruction}]
        # No client, model, or complex state needed for user

    def update_system_prompt_with_protocol(self, protocol_content):
        # User agent doesn't use an LLM, so system prompt primarily for conceptual alignment.
        # We can update its internal system message for consistency if needed for logging.
        if self.messages and self.messages[0]["role"] == "system":
            base_instruction = self.instruction # Or parse from self.messages[0]["content"]
            if INTERACTION_PROTOCOL.splitlines()[0] not in self.messages[0]["content"]:
                 self.messages[0]["content"] = f"{base_instruction}\n\n{protocol_content}"
            else: # If protocol is already there, replace the other_agents part
                base_instruction_part = self.messages[0]["content"].split(INTERACTION_PROTOCOL.splitlines()[0])[0]
                self.messages[0]["content"] = f"{base_instruction_part.strip()}\n\n{protocol_content}"
        else:
            self.messages.insert(0, {"role": "system", "content": f"{self.instruction}\n\n{protocol_content}"})


    def add_message(self, role, content):
        """Manually add a message to the user agent's history (e.g., user's own response)."""
        self.messages.append({"role": role, "content": content})


    def chat(self, prompt_from_teacher):
        """
        This method is conceptually where the user "processes" the teacher's prompt.
        The actual input capture happens in the Streamlit UI.
        We log the prompt from the teacher. The user's response will be added via add_message.
        """
        self.messages.append({"role": "user", "content": prompt_from_teacher}) # Logs the teacher's prompt to the user
        # The response is handled by Streamlit UI and then can be added using self.add_message("assistant", user_response)
        return None # No direct response generated here

    def clear_messages(self, keep_system_prompt=True):
        if keep_system_prompt and self.instruction:
            # Re-initialize with the original instruction, potentially including protocol if added.
            current_system_message = self.messages[0] if (self.messages and self.messages[0]["role"] == "system") else {"role": "system", "content": self.instruction}
            self.messages = [current_system_message]
        else:
            self.messages = []


    # Dummy methods to align with Agent class if needed by orchestrator
    def clear_state(self):
        pass

    def set_state(self, key, value):
        pass