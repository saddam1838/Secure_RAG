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

        # Step 1: Show the main app
        # Step 2: Force the tabs to refresh (using hidden state)
        return (
            f"✅ Welcome, {username} ({role})",
            gr.update(visible=True),  # main_app
            gr.update(visible=False),  # login_btn
            gr.update(visible=False),  # register_btn
            gr.update(visible=True),  # logout_btn
            username,  # user_state
            gr.update(value=1),  # trigger tab refresh (hidden state)
        )
    return (
        f"❌ {msg}",
        gr.update(visible=False),
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(visible=False),
        "",  # Changed from "admin" to empty string
        gr.update(),
    )


def handle_register(username, password):
    success, msg = register_user(username, password)
    if success:
        return (
            f"✅ {msg} You can now log in.",
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
            gr.update(),
        )
    return (
        f"❌ {msg}",
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
        gr.update(),
    )


def logout():
    CURRENT_USER["username"] = None
    CURRENT_USER["role"] = None

    # Step 1: Hide the main app
    # Step 2: Clear the tab selection
    return (
        "Logged out",
        gr.update(visible=False),  # main_app
        gr.update(visible=True),  # login_btn
        gr.update(visible=True),  # register_btn
        gr.update(visible=False),  # logout_btn
        "",  # Changed from "admin" to empty string
        gr.update(value=0),  # reset tab refresh state
    )


def create_gradio_app():
    with gr.Blocks(title="🔐 SecureRAG") as demo:
        gr.Markdown("# 🔐 SecureRAG")
        gr.Markdown(
            "### Hybrid RAG • OWASP/MITRE/NIST Compliant • Defense-in-Depth Security"
        )

        with gr.Row():
            with gr.Column(scale=1, min_width=350):
                username = gr.Textbox(
                    label="Username", value=""
                )  # Changed: removed "admin" default
                password = gr.Textbox(label="Password", type="password")
                with gr.Row():
                    login_btn = gr.Button("Login", variant="primary")
                    register_btn = gr.Button("Register", variant="secondary")
                auth_status = gr.Textbox(label="Status", interactive=False)
                logout_btn = gr.Button("Logout", variant="stop", visible=False)

        with gr.Column(visible=False) as main_app:
            user_state = gr.State("")  # Changed from "admin" to empty string
            tab_refresh = gr.State(0)  # Hidden state to trigger tab refresh

            # Assign Tabs to a variable so we can update its 'selected' index
            with gr.Tabs() as main_tabs:
                score_html = dashboard_tab(user_state)
                doc_dropdown = manage_documents_tab(user_state, score_html)
                upload_tab(user_state, score_html, doc_dropdown)
                chat_interface(user_state)
                attack_simulator_tab()
                security_tab()
                evaluate_tab()

            # FIX: Forces the tab to reset to 0 (Security Dashboard) when tab_refresh changes.
            # Using 'lambda _' safely accepts the state value to prevent TypeError.
            tab_refresh.change(
                lambda _: gr.update(selected=0),
                inputs=[tab_refresh],
                outputs=[main_tabs],
            )

        # Wire up events
        login_btn.click(
            handle_login,
            [username, password],
            [
                auth_status,
                main_app,
                login_btn,
                register_btn,
                logout_btn,
                user_state,
                tab_refresh,
            ],
        )

        register_btn.click(
            handle_register,
            [username, password],
            [auth_status, login_btn, register_btn, logout_btn, user_state, tab_refresh],
        )

        # COMBINED FIX: Resets server state AND forces browser reload to clear cache on logout
        logout_btn.click(
            logout,
            None,
            [
                auth_status,
                main_app,
                login_btn,
                register_btn,
                logout_btn,
                user_state,
                tab_refresh,
            ],
            js="() => { setTimeout(() => window.location.reload(), 200); }",
        )

    return demo
