import gradio as gr
import asyncio
from pathlib import Path
from typing import List, Dict
from queue import Queue
import time
import threading

from config import load_config
from s3_sync import sync_from_s3, sync_to_s3
from agent import tool_box, run_agent
from agent_registry import get_current_agents, add_agent_tools


# Queue to capture talk_to_user messages
message_queue = Queue()
response_queue = Queue()

# Sentinel value to signal agent thread to terminate
RESET_SENTINEL = "__RESET_SESSION__"


class AgentResetException(Exception):
    """Exception to signal agent thread should terminate for reset"""

    pass


class SimpleGradioInterface:
    """Minimal Gradio interface for agent chat"""

    def __init__(self):
        self.config = load_config(Path("./agents.yaml"))
        self.agents = {agent["name"]: agent for agent in self.config["agents"]}
        self.main_agent_name = self.config["main"]
        self.session_active = True
        self.agent_thread = None

        # Update global agents registry
        _current_agents = get_current_agents()
        _current_agents.update(self.agents)

        add_agent_tools(self.agents, tool_box, run_agent)
        print(f"[WEB] Registered {len(self.agents)} agent tools")

        # We hijack the existing CLI talk_to_user tool to use queues for web interaction
        self._setup_talk_to_user_override()

        # Override needs to load before starting agent
        time.sleep(0.1)

        self._start_agent_background()

    def _setup_talk_to_user_override(self):
        """Override talk_to_user to use queues instead of stdin/stdout"""

        def web_talk_to_user(message: str) -> str:
            # print(f"\n[AGENT] talk_to_user called with: {message[:100] if message else '(empty)'}...")
            # print(f"[AGENT] message_queue size before put: {message_queue.qsize()}")

            if message:
                message_queue.put(message)
                # print(f"[AGENT] message_queue size after put: {message_queue.qsize()}")
            # else:
            #     print(f"[AGENT] Skipping empty message (initial prompt)")

            # print(f"[AGENT] Waiting for response from response_queue...")
            response = response_queue.get()

            # Check for reset sentinel
            if response == RESET_SENTINEL:
                raise AgentResetException("Agent session reset requested")

            # print(f"[AGENT] Got response: {response[:100] if response else '(empty)'}...")
            return response

        tool_box._funcs["talk_to_user"] = web_talk_to_user
        # print("[WEB] talk_to_user override installed")
        # print(f"[WEB] Verifying override: tool_box._funcs['talk_to_user'] = {tool_box._funcs['talk_to_user']}")
        # print(f"[WEB] All registered tools: {list(tool_box._funcs.keys())}")

    def _start_agent_background(self):
        """Start agent in background thread while interface runs in foreground"""

        # print("[WEB] Starting agent in background thread...")

        def run_agent_thread():
            # print("[AGENT THREAD] Thread started, creating event loop...")
            try:
                asyncio.run(
                    run_agent(
                        self.agents[self.main_agent_name],
                        tool_box,
                        None,  # message=None triggers greeting
                        interactive=False,
                    )
                )
            except AgentResetException:
                print("[AGENT THREAD] Session reset requested, thread terminating")
            # print("[AGENT THREAD] run_agent completed")

        self.agent_thread = threading.Thread(target=run_agent_thread, daemon=True)
        self.agent_thread.start()
        # print("[WEB] Agent thread started")

    def start_session(self) -> list:
        """Start session by downloading skills from S3"""
        sync_from_s3()
        return []

    def end_session(self) -> tuple[gr.update, gr.update, gr.update]:
        """End session by uploading skills to S3"""
        from s3_sync import S3SkillSync

        syncer = S3SkillSync()
        deleted_skills = syncer.get_deleted_skills()
        modified_skills = syncer.get_modified_skills()

        messages = []

        if deleted_skills:
            skills_list = "\n".join(f"  - `{skill}`" for skill in sorted(deleted_skills))
            messages.append(f"### Deleted Locally (exist in S3)\n{skills_list}")

        if modified_skills:
            skills_list = "\n".join(
                f"  - `{skill}`" for skill in sorted(modified_skills.keys())
            )
            messages.append(f"### Modified Locally (different from S3)\n{skills_list}")

        if messages:
            message = "\n\n".join(messages) + "\n\n**Choose an option:**"
            return (
                gr.update(value=message, visible=True),
                gr.update(visible=False),
                gr.update(visible=True),
            )
        else:
            # No changes, just upload
            sync_to_s3()
            return (
                gr.update(visible=False),
                gr.update(visible=True),
                gr.update(visible=False),
            )

    def confirm_delete_and_upload(self, delete_from_s3: bool, history: list) -> list:
        """Handle the confirmation dialog response"""
        from s3_sync import S3SkillSync

        syncer = S3SkillSync()

        if delete_from_s3:
            deleted_skills = syncer.get_deleted_skills()
            if deleted_skills:
                syncer.delete_skills_from_s3(list(deleted_skills))
                message = f"Deleted {len(deleted_skills)} skill(s) from S3. All local skills synced to S3."
            else:
                message = "All local skills synced to S3."
        else:
            message = "Kept all skills in S3. All local skills synced to S3."

        sync_to_s3()
        self.session_active = False
        # Clear history after showing confirmation
        return []

    def cancel_session_end(self) -> list:
        """Cancel session end without uploading to S3"""
        self.session_active = False
        return []

    def reset_agent_session(self):
        """Reset agent session by clearing queues and restarting thread"""
        # Send reset sentinel to terminate old thread if it's waiting
        if self.agent_thread and self.agent_thread.is_alive():
            response_queue.put(RESET_SENTINEL)
            # Give previous thread time to terminate
            time.sleep(0.2)

        # Clear both queues
        while not message_queue.empty():
            message_queue.get()
        while not response_queue.empty():
            response_queue.get()

        # Start a new agent thread with fresh history
        self._start_agent_background()
        self.session_active = True

    def send_message(self, message: str, history: List):
        """
        Send message to agent and get response.
        Generator that yields updates to show user message immediately.

        Args:
            message: User message
            history: Chat history

        Yields:
            Updated history and status tuples
        """
        try:
            import time

            did_reset = False

            # If session ended, restart agent with fresh context
            if not self.session_active:
                did_reset = True
                self.reset_agent_session()

            # print(f"[WEB] send_message called with: {message}")
            # print(f"[WEB] message_queue.qsize(): {message_queue.qsize()}")
            # print(f"[WEB] response_queue.qsize(): {response_queue.qsize()}")

            history.append({"role": "user", "content": message})
            history.append({"role": "assistant", "content": "⏳ Processing..."})
            yield history, "Sending..."

            response_queue.put(message)
            # print(f"[WEB] Put user message in response_queue")

            # print(f"[WEB] Waiting for agent response...")
            while True:
                if not message_queue.empty():
                    agent_response = message_queue.get()
                    # print(f"[WEB] Got agent response: {agent_response[:100] if agent_response else '(empty)'}...")
                    # Replace loading message with actual response
                    history[-1] = {"role": "assistant", "content": agent_response}
                    yield history, "✅ Message sent"
                    return
                time.sleep(0.1)

        except Exception as e:
            import traceback

            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            # print(f"[WEB] Error in send_message: {error_msg}")
            history.append({"role": "assistant", "content": error_msg})
            yield history, f"{str(e)}"

    def launch(self, server_port: int = 7860):
        """Launch Gradio interface"""
        with gr.Blocks(title="Agent Chat") as demo:
            gr.Markdown("# Skynet")

            chatbot = gr.Chatbot(label="Chat", height=400)
            msg_box = gr.Textbox(
                label="Your Message",
                placeholder="Type here and press Enter to send...",
                lines=1,
                max_lines=5,  # Allows expansion up to 5 lines
                submit_btn=True,  # Shows Enter submits
            )

            with gr.Row() as main_buttons:
                send_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear")
                end_btn = gr.Button("End Session & Upload", variant="stop")

            # S3 confirmation buttons (hidden by default)
            confirmation_msg = gr.Markdown(visible=False)
            with gr.Row(visible=False) as s3_buttons:
                confirm_delete_btn = gr.Button(
                    "✓ Update S3 & Delete Removed", variant="stop", scale=1
                )
                confirm_keep_btn = gr.Button(
                    "✓ Update S3 Only (Keep All)", variant="primary", scale=1
                )
                cancel_btn = gr.Button(
                    "✗ Cancel (Don't Upload)", variant="secondary", scale=1
                )

            def send(message, history):
                if not message.strip():
                    yield history, ""
                    return
                for hist, _ in self.send_message(message, history):
                    yield hist, ""

            send_btn.click(send, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box])

            msg_box.submit(send, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box])

            clear_btn.click(lambda: [], outputs=[chatbot])

            end_btn.click(
                self.end_session, outputs=[confirmation_msg, main_buttons, s3_buttons]
            )

            confirm_delete_btn.click(
                lambda hist: self.confirm_delete_and_upload(True, hist),
                inputs=[chatbot],
                outputs=[chatbot],
            ).then(
                lambda: (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                ),
                outputs=[confirmation_msg, main_buttons, s3_buttons],
            )

            confirm_keep_btn.click(
                lambda hist: self.confirm_delete_and_upload(False, hist),
                inputs=[chatbot],
                outputs=[chatbot],
            ).then(
                lambda: (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                ),
                outputs=[confirmation_msg, main_buttons, s3_buttons],
            )

            cancel_btn.click(self.cancel_session_end, outputs=[chatbot]).then(
                lambda: (
                    gr.update(visible=False),
                    gr.update(visible=True),
                    gr.update(visible=False),
                ),
                outputs=[confirmation_msg, main_buttons, s3_buttons],
            )

            demo.load(self.start_session, outputs=[chatbot])

        print(f"Launching Gradio on port {server_port}...")
        demo.launch(server_port=server_port, share=False)


def main():
    """Launch Gradio interface"""
    interface = SimpleGradioInterface()
    interface.launch()


if __name__ == "__main__":
    main()
