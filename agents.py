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
        self.messages = [
            {
                "role": "system",
                "content": instruction,
            }
        ]
        self.other_agents = []

    def update_system_prompt_with_protocol(self, protocol_content):
        """Updates the system prompt to include the interaction protocol."""
        # Ensure protocol is appended to the base instruction
        base_instruction = self.messages[0]["content"].split(
            "\n\n" + INTERACTION_PROTOCOL.splitlines()[0]
        )[
            0
        ]  # Get original instruction
        self.messages[0]["content"] = f"{base_instruction}\n\n{protocol_content}"

    def chat(self, prompt):
        self.messages.append({"role": "user", "content": prompt})
        try:
            api_response = self.client.chat.completions.create(
                model=self.model, messages=self.messages
            )
            assistant_response_content = api_response.choices[0].message.content
            self.messages.append(
                {"role": "assistant", "content": assistant_response_content}
            )
            return assistant_response_content
        except Exception as e:
            print(f"Error during API call for agent {self.name}: {e}")
            error_message = f"Error: Could not get a response. {e}"
            self.messages.append({"role": "assistant", "content": error_message})
            return error_message

    def clear_messages(self):
        self.messages = [self.messages[0]]

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
        # User agent doesn't use an LLM, but we can inform the user.
        # print(f"\n--- System Info for {self.name} ---")
        # print(protocol_content)
        # print("--- End System Info ---\n")
        pass  # Or keep it silent

    def chat(self, prompt):
        print(f"\n--- To {self.name} (You) ---")
        print(f"Teacher asks: {prompt}")
        response = input("Your answer: ")
        # Log interaction similar to Agent class for completeness
        self.messages.append({"role": "user", "content": prompt})  # The prompt/question
        self.messages.append(
            {"role": "assistant", "content": response}
        )  # User's actual response
        return response

    def clear_messages(self):
        self.messages = [{"role": "system", "content": self.instruction}]

    # Dummy methods to align with Agent class if needed by orchestrator
    def clear_state(self):
        pass

    def set_state(self, key, value):
        pass
