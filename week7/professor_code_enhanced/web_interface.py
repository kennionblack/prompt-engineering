"""
Simple Gradio interface for agent chat.
"""

import gradio as gr
import asyncio
from pathlib import Path
from typing import List, Dict
from queue import Queue
import time
import threading

from config import load_config
from s3_sync import sync_from_s3, sync_to_s3
from agent import tool_box, run_agent, _current_agents, add_agent_tools


# Queue to capture talk_to_user messages
message_queue = Queue()
response_queue = Queue()


class SimpleGradioInterface:
    """Minimal Gradio interface for agent chat"""

    def __init__(self):
        self.config = load_config(Path("./agents.yaml"))
        self.agents = {agent["name"]: agent for agent in self.config["agents"]}
        self.main_agent_name = self.config["main"]

        # Update global agents registry
        _current_agents.update(self.agents)

        add_agent_tools(self.agents, tool_box)
        print(f"[WEB] Registered {len(self.agents)} agent tools")

        # We hijack the existing CLI talk_to_user tool to use queues for web interaction
        self._setup_talk_to_user_override()

        # Override needs to load before starting agent
        time.sleep(0.1)

        self._start_agent_background()

    def _setup_talk_to_user_override(self):
        """Override talk_to_user to use queues instead of stdin/stdout"""

        def web_talk_to_user(message: str) -> str:
            # print(f"\n[AGENT] talk_to_user called with: {message[:50]}...")
            # print(f"[AGENT] message_queue size before put: {message_queue.qsize()}")

            message_queue.put(message)
            # print(f"[AGENT] message_queue size after put: {message_queue.qsize()}")

            # print(f"[AGENT] Waiting for response from response_queue...")
            response = response_queue.get()

            # print(f"[AGENT] Got response: {response[:50]}...")
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
            asyncio.run(
                run_agent(
                    self.agents[self.main_agent_name],
                    tool_box,
                    None,  # message=None triggers greeting
                    interactive=False,
                )
            )
            # print("[AGENT THREAD] run_agent completed")

        thread = threading.Thread(target=run_agent_thread, daemon=True)
        thread.start()
        # print("[WEB] Agent thread started")

    def start_session(self) -> tuple[List, str]:
        """Start session by downloading skills from S3"""
        sync_from_s3()
        return [], "Session started"

    def end_session(self) -> str:
        """End session by uploading skills to S3"""
        sync_to_s3()
        return "Session ended - skills uploaded to S3"

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

            # print(f"[WEB] send_message called with: {message}")
            # print(f"[WEB] message_queue.qsize(): {message_queue.qsize()}")
            # print(f"[WEB] response_queue.qsize(): {response_queue.qsize()}")

            # Check if greeting is waiting (first message only)
            if not message_queue.empty():
                greeting = message_queue.get()
                # print(f"[WEB] Got greeting from queue: {greeting[:50]}...")
                history.append({"role": "assistant", "content": greeting})
            # else:
            # print("[WEB] No greeting in queue")
            history.append({"role": "user", "content": message})
            yield history, "Sending..."

            response_queue.put(message)
            # print(f"[WEB] Put user message in response_queue")
            # 3 minutes to allow for sandbox generation, network operations, etc.
            timeout = 180
            start_time = time.time()

            # print(f"[WEB] Waiting for agent response...")
            while time.time() - start_time < timeout:
                if not message_queue.empty():
                    agent_response = message_queue.get()
                    # print(f"[WEB] Got agent response: {agent_response[:50]}...")
                    history.append({"role": "assistant", "content": agent_response})
                    yield history, "✅ Message sent"
                    return
                time.sleep(0.1)

            # Timeout
            # print("[WEB] Timeout waiting for agent response")
            history.append(
                {"role": "assistant", "content": "Agent did not respond (timeout)"}
            )
            yield history, "Timeout"

        except Exception as e:
            import traceback

            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            # print(f"[WEB] Error in send_message: {error_msg}")
            history.append({"role": "assistant", "content": error_msg})
            yield history, f"❌ {str(e)}"

    def launch(self, server_port: int = 7860):
        """Launch Gradio interface"""
        with gr.Blocks(title="Agent Chat") as demo:
            gr.Markdown("# Skynet")

            chatbot = gr.Chatbot(label="Chat", height=600)
            msg_box = gr.Textbox(
                label="Your Message",
                placeholder="Type here and press Enter to send...",
                lines=1,
                max_lines=5,  # Allows expansion up to 5 lines
                submit_btn=True,  # Shows Enter submits
            )

            with gr.Row():
                send_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear")
                end_btn = gr.Button("End Session & Upload", variant="stop")

            status_box = gr.Textbox(label="Status", value="Ready", interactive=False)

            def send(message, history):
                if not message.strip():
                    yield history, "", "⚠️  Empty message"
                    return
                for hist, status in self.send_message(message, history):
                    yield hist, "", status

            send_btn.click(
                send, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box, status_box]
            )

            msg_box.submit(
                send, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box, status_box]
            )

            clear_btn.click(lambda: ([], "Chat cleared"), outputs=[chatbot, status_box])

            end_btn.click(self.end_session, outputs=[status_box])

            demo.load(self.start_session, outputs=[chatbot, status_box])

        print(f"Launching Gradio on port {server_port}...")
        demo.launch(server_port=server_port, share=False)


def main():
    """Launch Gradio interface"""
    interface = SimpleGradioInterface()
    interface.launch()


if __name__ == "__main__":
    main()
