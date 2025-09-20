import os
from dotenv import load_dotenv
import gradio as gr
from openai import AsyncOpenAI

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

system_prompt = """
You are MarineBot, a friendly and knowledgeable expert in marine biology and ocean sciences.

Your key characteristics:
- You provide accurate, scientific information about marine life, ocean ecosystems, and marine conservation.
- You can discuss topics ranging from deep-sea creatures to coral reefs, from ocean currents to marine biodiversity.
- You communicate in a clear, engaging manner, making complex concepts accessible.
- You know when a conversation has reached its natural conclusion.

When you feel a conversation has reached a natural ending point (such as when you've fully answered a user's question, 
and there's no clear follow-up needed), end your response with the word "DONE" on a new line.

Examples of when to end with DONE:
- After providing comprehensive information with no obvious follow-up questions
- When a user says "thank you" or indicates satisfaction with your answer
- When the conversation has naturally concluded
- After suggesting follow-up topics but before the user has chosen one

Do not use DONE if:
- The user has just asked a new question
- You've invited the user to ask follow-up questions
- The conversation is clearly ongoing
- You're in the middle of explaining a complex topic

Remember to be helpful and informative, but recognize when a conversation has naturally concluded.
"""


async def get_chatbot_response(message, history):
    messages = [{"role": "system", "content": system_prompt}]

    for human, assistant in history:
        messages.append({"role": "user", "content": human})
        messages.append({"role": "assistant", "content": assistant})

    messages.append({"role": "user", "content": message})

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        max_tokens=1000,
    )

    try:
        return response.choices[0].message.content
    except Exception as e:
        print(response)
        return f"I apologize, but I encountered an error: {str(e)}"


def check_conversation_done(chatbot_response):
    if chatbot_response.strip().endswith("DONE"):
        cleaned_response = chatbot_response.strip()[:-4].strip()
        return cleaned_response, True
    else:
        return chatbot_response, False


async def respond(message, chat_history):
    bot_response = await get_chatbot_response(message, chat_history)

    cleaned_response, is_done = check_conversation_done(bot_response)

    chat_history.append((message, cleaned_response))

    return chat_history, is_done


def reset_conversation():
    return [], False


def build_interface():
    with gr.Blocks(
        css="""
    footer {visibility: hidden}
    #conversation-status {
        font-weight: bold;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    """
    ) as demo:
        gr.Markdown("# 🌊 MarineBot: Your Marine Biology Expert")
        gr.Markdown("Ask questions about marine life, ocean ecosystems, and marine conservation.")

        # Initialize conversation state
        chat_state = gr.State([])
        done_state = gr.State(False)

        # Chat interface
        chatbot = gr.Chatbot(height=500)

        # Input components
        with gr.Row():
            msg = gr.Textbox(placeholder="Type your message here...", scale=9)
            submit = gr.Button("Send", scale=1)

        # Status indicator for conversation state
        status = gr.Markdown("Conversation status: Active", elem_id="conversation-status")

        # Reset button
        reset = gr.Button("Reset Conversation")

        async def user_input(message, history, done):
            if done:
                history = []
                done = False

            if not message.strip():
                return history, history, done, "Conversation status: Active"

            updated_history, is_done = await respond(message, history)

            if is_done:
                # Add a system message to the chat when conversation is complete
                updated_history.append(
                    (
                        None,
                        "🔚 This conversation has reached its natural conclusion. Feel free to start a new topic!",
                    )
                )

            status_text = (
                "Conversation status: Complete - You can start a new topic"
                if is_done
                else "Conversation status: Active"
            )

            return "", updated_history, is_done, status_text

        submit.click(
            user_input,
            inputs=[msg, chat_state, done_state],
            outputs=[msg, chatbot, done_state, status],
        )

        msg.submit(
            user_input,
            inputs=[msg, chat_state, done_state],
            outputs=[msg, chatbot, done_state, status],
        )

        def do_reset():
            return [], [], False, "Conversation status: Active"

        reset.click(do_reset, inputs=[], outputs=[msg, chatbot, done_state, status])

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()
