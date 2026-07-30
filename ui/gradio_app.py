import gradio as gr
from database import register_user, authenticate_user
from ui.chat import chat_interface
from ui.security_tab import security_tab
from ui.attack_simulator import attack_simulator_tab
from ui.dashboard import dashboard_tab
from ui.evaluate_tab import evaluate_tab
from ui.upload import upload_tab
from ui.manage_documents import manage_documents_tab

CURRENT_USER = {"username": None, "role": None}


def handle_login(username, password):
    success, msg, role = authenticate_user(username, password)
    if success:
        CURRENT_USER["username"] = username
        CURRENT_USER["role"] = role
        return (
            f"✅ Welcome, {username} ({role})",
            gr.update(visible=True),
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(visible=True),
            username,
            gr.update(value=1),
        )
    return (
        f"❌ {msg}",
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
        gr.update(),
    )


def handle_register(username, password):
    success, msg = register_user(username, password)
    if success:
        return f"✅ {msg} You can now log in."
    return f"❌ {msg}"


def logout():
    CURRENT_USER["username"] = None
    CURRENT_USER["role"] = None
    return (
        "Logged out",
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(visible=False),
        "",
        gr.update(value=0),
    )


def create_gradio_app():
    with gr.Blocks(title="🔐 SecureRAG") as demo:
        gr.Markdown("# 🔐 SecureRAG")
        gr.Markdown(
            "### Hybrid RAG • OWASP/MITRE/NIST Compliant • Defense-in-Depth Security"
        )

        with gr.Row():
            with gr.Column(scale=1, min_width=350):
                username = gr.Textbox(label="Username", value="")
                password = gr.Textbox(label="Password", type="password")
                with gr.Row():
                    login_btn = gr.Button("Login", variant="primary")
                    register_btn = gr.Button("Register", variant="secondary")
                auth_status = gr.Textbox(label="Status", interactive=False)
                logout_btn = gr.Button("Logout", variant="stop", visible=False)

        with gr.Column(visible=False) as main_app:
            user_state = gr.State("")
            tab_refresh = gr.State(0)

            with gr.Tabs() as main_tabs:
                # These functions return the main HTML/Component that needs refreshing
                score_html = dashboard_tab(user_state)
                doc_dropdown = manage_documents_tab(user_state, score_html)
                upload_tab(user_state, score_html, doc_dropdown)
                chat_interface(user_state)
                attack_simulator_tab()
                security_tab()
                evaluate_tab(user_state)  # Auto-refreshes on user_state.change

            tab_refresh.change(
                lambda _: gr.update(selected=0),
                inputs=[tab_refresh],
                outputs=[main_tabs],
            )

        login_btn.click(
            handle_login,
            [username, password],
            [auth_status, main_app, login_btn, register_btn, logout_btn, user_state, tab_refresh],
        )

        register_btn.click(
            handle_register,
            [username, password],
            [auth_status],
        )

        logout_btn.click(
            logout,
            None,
            [auth_status, main_app, login_btn, register_btn, logout_btn, user_state, tab_refresh],
            js="() => { setTimeout(() => window.location.reload(), 200); }",
        )

    return demo
