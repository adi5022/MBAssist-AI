import os
import sys
from flask import Flask, request, jsonify, render_template

from config import PDF_PATH, CACHE_FILE, DATA_DIR
from rag import ask_chatbot
import random
import time
from database import (
    create_user,
    authenticate_user,
    get_user,
    create_session,
    get_user_sessions,
    save_message,
    get_session_messages,
    update_session_summary,
    get_session_summary,
    update_user_api_key,
    delete_user,
    delete_session,
    get_db_connection,
    update_user_password
)

# Initialize Flask application with explicit static and templates folders
app = Flask(__name__,
            static_folder="static",
            template_folder="templates")

# Temporary in-memory OTP verification store
temp_otps = {}

def send_otp_email(receiver_email, otp_code):
    """Send an account verification email containing the 6-digit OTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    
    # Fallback checks
    if not all([sender_email, sender_password, smtp_server, smtp_port]):
        print("\n" + "!" * 60, file=sys.stderr)
        print("[WARN] SMTP Credentials Missing in .env. Falling back to console OTP log.", file=sys.stderr)
        print(f"[OTP VERIFICATION] Code for {receiver_email}: {otp_code}", file=sys.stderr)
        print("!" * 60 + "\n", file=sys.stderr)
        return False
    
    try:
        # Build SMTP MIME message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "Verify Your MBAssist AI Account"
        
        html_content = f"""
        <html>
        <body style="margin: 0; padding: 0; font-family: 'Outfit', 'Inter', sans-serif; background-color: #0b0d1b; color: #f3f4f6;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0b0d1b; min-width: 100%;">
                <tr>
                    <td align="center" style="padding: 40px 10px;">
                        <div style="max-width: 500px; width: 100%; background-color: #11132c; border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45); overflow: hidden; padding: 40px 32px; box-sizing: border-box; text-align: center;">
                            <div style="margin-bottom: 24px; text-align: center;">
                                <span style="font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; font-family: 'Outfit', sans-serif;">MBAssist <span style="color: #6366f1;">AI</span></span>
                            </div>
                            
                            <h2 style="font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 12px; font-family: 'Outfit', sans-serif; text-align: center;">Confirm Your Registration</h2>
                            <p style="font-size: 13.5px; color: #9ca3af; line-height: 1.6; margin-bottom: 28px; font-family: 'Inter', sans-serif; text-align: center; margin-top: 0; padding: 0 10px;">
                                Thank you for signing up for the MBAssist AI admissions guide! Enter the 6-digit verification code below to secure your chat history and unlock your dashboard.
                            </p>
                            
                            <div style="background: rgba(99, 102, 241, 0.1); border: 1px dashed rgba(99, 102, 241, 0.4); border-radius: 12px; padding: 20px 30px; margin-bottom: 28px; display: inline-block; box-shadow: 0 0 15px rgba(99, 102, 241, 0.05); text-align: center;">
                                <span style="font-size: 36px; font-weight: 800; color: #6366f1; letter-spacing: 6px; padding-left: 6px; font-family: monospace;">{otp_code}</span>
                            </div>
                            
                            <p style="font-size: 11.5px; color: #6b7280; line-height: 1.4; margin-bottom: 32px; font-family: 'Inter', sans-serif; text-align: center; padding: 0 20px; margin-top: 0;">
                                This code is valid for a limited time. If you did not initiate this request, you can safely ignore this email.
                            </p>
                            
                            <div style="border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 20px; font-size: 10.5px; color: #4b5563; font-family: 'Inter', sans-serif; line-height: 1.5; text-align: center;">
                                Mar Baselios College of Engineering and Technology Admissions Guide<br>
                                <span style="color: #6366f1;">mbcet.ac.in</span>
                                <div style="margin-top: 12px; font-size: 9px; color: #374151;">Ref ID: {int(time.time())}</div>
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connect and send via SSL or STARTTLS depending on port
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] Verification email successfully sent to {receiver_email}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send SMTP email: {str(e)}. Falling back to console OTP.", file=sys.stderr)
        print(f"[OTP VERIFICATION] Code for {receiver_email}: {otp_code}", file=sys.stderr)
        return False

# Temporary in-memory store for password reset OTPs
temp_reset_otps = {}

def send_reset_otp_email(receiver_email, otp_code):
    """Send an account password reset email containing the 6-digit OTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    sender_email = os.getenv("SMTP_EMAIL")
    sender_password = os.getenv("SMTP_PASSWORD")
    smtp_server = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    
    # Fallback checks
    if not all([sender_email, sender_password, smtp_server, smtp_port]):
        print("\n" + "!" * 60, file=sys.stderr)
        print("[WARN] SMTP Credentials Missing in .env. Falling back to console OTP log for Reset.", file=sys.stderr)
        print(f"[PASSWORD RESET OTP] Code for {receiver_email}: {otp_code}", file=sys.stderr)
        print("!" * 60 + "\n", file=sys.stderr)
        return False
        
    try:
        # Build SMTP MIME message
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = "Reset Your MBAssist AI Password"
        
        html_content = f"""
        <html>
        <body style="margin: 0; padding: 0; font-family: 'Outfit', 'Inter', sans-serif; background-color: #0b0d1b; color: #f3f4f6;">
            <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #0b0d1b; min-width: 100%;">
                <tr>
                    <td align="center" style="padding: 40px 10px;">
                        <div style="max-width: 500px; width: 100%; background-color: #11132c; border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 16px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45); overflow: hidden; padding: 40px 32px; box-sizing: border-box; text-align: center;">
                            <div style="margin-bottom: 24px; text-align: center;">
                                <span style="font-size: 26px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px; font-family: 'Outfit', sans-serif;">MBAssist <span style="color: #6366f1;">AI</span></span>
                            </div>
                            
                            <h2 style="font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 12px; font-family: 'Outfit', sans-serif; text-align: center;">Password Reset Request</h2>
                            <p style="font-size: 13.5px; color: #9ca3af; line-height: 1.6; margin-bottom: 28px; font-family: 'Inter', sans-serif; text-align: center; margin-top: 0; padding: 0 10px;">
                                We received a request to reset the password for your MBAssist AI account. Enter the 6-digit verification code below to authorize this password reset:
                            </p>
                            
                            <div style="background: rgba(239, 68, 68, 0.15); border: 1px dashed rgba(239, 68, 68, 0.4); border-radius: 12px; padding: 20px 30px; margin-bottom: 28px; display: inline-block; box-shadow: 0 0 15px rgba(239, 68, 68, 0.05); text-align: center;">
                                <span style="font-size: 36px; font-weight: 800; color: #ef4444; letter-spacing: 6px; padding-left: 6px; font-family: monospace;">{otp_code}</span>
                            </div>
                            
                            <p style="font-size: 11.5px; color: #6b7280; line-height: 1.4; margin-bottom: 32px; font-family: 'Inter', sans-serif; text-align: center; padding: 0 20px; margin-top: 0;">
                                If you did not request a password reset, you can safely ignore this email. Your password will remain unchanged.
                            </p>
                            
                            <div style="border-top: 1px solid rgba(255, 255, 255, 0.05); padding-top: 20px; font-size: 10.5px; color: #4b5563; font-family: 'Inter', sans-serif; line-height: 1.5; text-align: center;">
                                Mar Baselios College of Engineering and Technology Admissions Guide<br>
                                <span style="color: #6366f1;">mbcet.ac.in</span>
                                <div style="margin-top: 12px; font-size: 9px; color: #374151;">Ref ID: {int(time.time())}</div>
                            </div>
                        </div>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connect and send via SSL or STARTTLS depending on port
        port = int(smtp_port)
        if port == 465:
            server = smtplib.SMTP_SSL(smtp_server, port)
        else:
            server = smtplib.SMTP(smtp_server, port)
            server.starttls()
            
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print(f"[EMAIL] Password reset email sent to {receiver_email}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send Reset SMTP email: {str(e)}. Falling back to console OTP.", file=sys.stderr)
        print(f"[PASSWORD RESET OTP] Code for {receiver_email}: {otp_code}", file=sys.stderr)
        return False

@app.route("/api/auth/forgot-password", methods=["POST"])
def auth_forgot_password():
    """Generate OTP and send email for resetting password."""
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        
        if not email:
            return jsonify({"error": "Email address is required."}), 400
            
        # Check if user exists
        conn = get_db_connection()
        user = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if not user:
            return jsonify({"error": "No account found with this email address."}), 404
            
        otp = f"{random.randint(100000, 999999)}"
        temp_reset_otps[email] = {
            "otp": otp,
            "timestamp": time.time()
        }
        
        email_sent = send_reset_otp_email(email, otp)
        return jsonify({"success": "Password reset code sent.", "email": email, "email_sent": email_sent})
    except Exception as e:
        print(f"[ERROR] Forgot password failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Failed to send reset code: {str(e)}"}), 500

@app.route("/api/auth/reset-password", methods=["POST"])
def auth_reset_password():
    """Verify reset OTP and write new password to SQLite."""
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()
        new_password = data.get("new_password", "").strip()
        
        if not email or not otp or not new_password:
            return jsonify({"error": "All fields are required."}), 400
            
        record = temp_reset_otps.get(email)
        if not record or record["otp"] != otp:
            return jsonify({"error": "Invalid or expired password reset verification code."}), 400
            
        # Reset successful: write to SQLite
        update_user_password(email, new_password)
        
        # Cleanup reset record
        temp_reset_otps.pop(email, None)
        return jsonify({"success": "Password has been successfully updated. You can now log in."})
    except Exception as e:
        print(f"[ERROR] Password reset verification failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Failed to reset password: {str(e)}"}), 500

@app.route("/")
def home():
    """Serve the admissions chatbot HTML page."""
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    """Serve the Account & Timeline Management Dashboard page."""
    return render_template("dashboard.html")

@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Trigger OTP email verification flow during user registration."""
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        groq_api_key = data.get("groq_api_key")
        if groq_api_key:
            groq_api_key = groq_api_key.strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required fields."}), 400

        # Check if email already exists
        conn = get_db_connection()
        exists = conn.execute("SELECT user_id FROM users WHERE email = ?", (email.lower(),)).fetchone()
        conn.close()
        if exists:
            return jsonify({"error": "Registration failed. This email is already in use."}), 400

        # Generate a 6-digit OTP verification code
        otp_code = f"{random.randint(100000, 999999)}"
        temp_otps[email.lower()] = {
            "password": password,
            "groq_api_key": groq_api_key,
            "otp": otp_code,
            "timestamp": time.time()
        }

        # Send actual SMTP email or print console fallback
        email_sent = send_otp_email(email, otp_code)

        return jsonify({"otp_required": True, "email": email, "email_sent": email_sent})
    except Exception as e:
        print(f"[ERROR] Registration flow failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route("/api/auth/verify-otp", methods=["POST"])
def auth_verify_otp():
    """Verify registration OTP code and commit user profile to the SQLite database."""
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()
        otp_entered = data.get("otp", "").strip()

        if not email or not otp_entered:
            return jsonify({"error": "Email and verification code are required."}), 400

        otp_record = temp_otps.get(email)
        if not otp_record or otp_record["otp"] != otp_entered:
            return jsonify({"error": "Invalid or expired verification code."}), 400

        # Verification successful, register user in SQLite
        user_id = create_user(
            email, 
            otp_record["password"], 
            otp_record["groq_api_key"] if otp_record["groq_api_key"] else None
        )
        
        # Cleanup temporary record
        temp_otps.pop(email, None)
        return jsonify({"user_id": user_id, "email": email})
    except Exception as e:
        print(f"[ERROR] OTP Verification failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Verification failed: {str(e)}"}), 500

@app.route("/api/auth/resend-otp", methods=["POST"])
def auth_resend_otp():
    """Generate a new OTP and resend it to the user's email."""
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()

        if not email:
            return jsonify({"error": "Email address is required."}), 400

        otp_record = temp_otps.get(email)
        if not otp_record:
            return jsonify({"error": "Verification request has expired or was not initiated."}), 400

        # Generate a fresh 6-digit OTP
        new_otp = f"{random.randint(100000, 999999)}"
        otp_record["otp"] = new_otp
        otp_record["timestamp"] = time.time()

        # Send SMTP HTML email
        email_sent = send_otp_email(email, new_otp)
        return jsonify({"success": "Verification code resent successfully.", "email_sent": email_sent})
    except Exception as e:
        print(f"[ERROR] OTP Resend failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Resend failed: {str(e)}"}), 500

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate existing credentials and return the associated user_id."""
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()

        if not email or not password:
            return jsonify({"error": "Email and password are required fields."}), 400

        user_id = authenticate_user(email, password)
        if not user_id:
            return jsonify({"error": "Invalid email or password."}), 401

        return jsonify({"user_id": user_id, "email": email})
    except Exception as e:
        print(f"[ERROR] Login failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": "An error occurred during authentication."}), 500

@app.route("/api/auth/save-key", methods=["POST"])
def auth_save_key():
    """Save or update a user's custom Groq API Key."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")
        groq_key = data.get("groq_key")
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400
        
        update_user_api_key(user_id, groq_key)
        return jsonify({"success": "Groq API Key successfully updated."})
    except Exception as e:
        print(f"[ERROR] Save key failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Failed to update API Key: {str(e)}"}), 500

@app.route("/api/auth/profile", methods=["GET"])
def auth_profile():
    """Retrieve user details (filtered) for the dashboard view."""
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400
        
        user = get_user(user_id)
        if not user:
            return jsonify({"error": "User not found."}), 404
            
        # Omit password hash for security
        user.pop("password_hash", None)
        return jsonify(user)
    except Exception as e:
        print(f"[ERROR] Profile load failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Failed to load profile: {str(e)}"}), 500

@app.route("/api/sessions", methods=["POST"])
def session_create():
    """Create a new chat session for an authenticated user."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")
        title = data.get("title", "New Chat").strip()

        if not user_id:
            return jsonify({"error": "User ID is required."}), 400

        session_id = create_session(user_id, title)
        return jsonify({"session_id": session_id, "title": title})
    except Exception as e:
        print(f"[ERROR] Session creation failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": "Failed to create session."}), 500

@app.route("/api/sessions", methods=["GET"])
def session_list():
    """Fetch all chat sessions associated with a specific user."""
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400

        sessions = get_user_sessions(user_id)
        return jsonify(sessions)
    except Exception as e:
        print(f"[ERROR] Session list fetch failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": "Failed to fetch session list."}), 500

@app.route("/api/sessions/<session_id>/messages", methods=["GET"])
def session_messages(session_id):
    """Retrieve message log history for a specific chat session."""
    try:
        messages = get_session_messages(session_id)
        return jsonify(messages)
    except Exception as e:
        print(f"[ERROR] Message log fetch failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": "Failed to fetch messages."}), 500

def generate_updated_summary(old_summary, older_messages, api_key=None):
    """Generate an updated single-paragraph summary of older conversation history."""
    try:
        from llm import get_llm
        dialogue = ""
        for msg in older_messages:
            sender_lbl = "User" if msg.get("sender") == "user" else "Assistant"
            dialogue += f"{sender_lbl}: {msg.get('text')}\n"
        
        prompt = (
            "Integrate the following conversation turns into a single, cohesive, short paragraph "
            "summarizing what the user is seeking and what has been discussed so far.\n\n"
            f"Previous Summary: {old_summary or 'None'}\n\n"
            f"New Turns to Integrate:\n{dialogue}\n"
            "Requirements:\n"
            "- Output ONLY a single concise paragraph (under 80 words).\n"
            "- Do not include greetings, introductions, or pleasantries.\n"
            "- Focus strictly on admissions context."
        )
        llm = get_llm(api_key)
        new_summary = llm.chat("You are a concise conversation summarization assistant.", prompt, max_tokens=150)
        return new_summary.strip()
    except Exception as e:
        print(f"[ERROR] Summarization helper failed: {str(e)}", file=sys.stderr)
        return old_summary

@app.route("/api/chat", methods=["POST"])
def chat():
    """API endpoint to process user messages using the LangGraph RAG pipeline with hybrid summary memory."""
    try:
        data = request.get_json() or {}
        user_message = data.get("message", "").strip()
        user_id = data.get("user_id")
        session_id = data.get("session_id")

        if not user_message:
            return jsonify({"error": "Message content cannot be empty."}), 400

        # Retrieve user-specific Groq API key if logged in
        user_api_key = None
        if user_id:
            user_profile = get_user(user_id)
            if user_profile:
                user_api_key = user_profile.get("groq_api_key")

        # Load session history if available, and save user's incoming message
        session_history = None
        session_summary = None
        if session_id:
            raw_history = get_session_messages(session_id)
            session_summary = get_session_summary(session_id)
            
            # Slice history: keep last 4 messages (2 turns) in full detail, summarize the rest
            if len(raw_history) > 4:
                older_messages = raw_history[:-4]
                session_history = raw_history[-4:]
                
                # Update the running summary dynamically with older messages
                session_summary = generate_updated_summary(session_summary, older_messages, api_key=user_api_key)
                update_session_summary(session_id, session_summary)
            else:
                session_history = raw_history
            
            save_message(session_id, "user", user_message)

        # Invoke the LangGraph workflow pipeline
        result = ask_chatbot(user_message, api_key=user_api_key, history=session_history, summary=session_summary)
        answer = result.get("answer", "No answer was generated.")

        # Save assistant response to session log if session is active
        if session_id:
            save_message(session_id, "bot", answer)

        # Extract unique page numbers from retrieved documents
        pages = []
        if result.get("action") == "retrieve" and result.get("docs"):
            pages = [doc.get("page") for doc in result.get("docs") if doc.get("page")]
        
        # Sort key to handle mixed types (integers vs strings/URLs) safely
        def sort_key(val):
            try:
                # If it's numeric, sort it first as a number
                return (0, int(val))
            except (ValueError, TypeError):
                # Otherwise sort alphabetically as a string
                return (1, str(val))

        return jsonify({
            "answer": answer,
            "action": result.get("action"),
            "lang_code": result.get("lang_code"),
            "lang_name": result.get("lang_name"),
            "pages": sorted(list(set(pages)), key=sort_key)
        })

    except Exception as e:
        print(f"[ERROR] Error in /api/chat: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

@app.route("/api/transcribe", methods=["POST"])
def transcribe():
    """API endpoint to transcribe uploaded audio files using Groq Whisper / Sarvam AI fallback."""
    try:
        if "audio" not in request.files:
            return jsonify({"error": "No audio file provided."}), 400
            
        audio_file = request.files["audio"]
        if audio_file.filename == "":
            return jsonify({"error": "Invalid audio file."}), 400
            
        file_bytes = audio_file.read()
        if not file_bytes:
            return jsonify({"error": "Audio file is empty."}), 400
            
        from speech import transcribe_audio
        language = request.form.get("language", "en")
        
        text, used_sarvam = transcribe_audio(file_bytes, audio_file.filename, language=language)
        return jsonify({"text": text})
        
    except Exception as e:
        print(f"[ERROR] Error in /api/transcribe: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Transcription failed: {str(e)}"}), 500

@app.route("/api/auth/delete-account", methods=["POST"])
def auth_delete_account():
    """Delete a user account and purge all their saved history logs."""
    try:
        data = request.get_json() or {}
        user_id = data.get("user_id")
        if not user_id:
            return jsonify({"error": "User ID is required."}), 400
        
        delete_user(user_id)
        return jsonify({"success": "Account and all chat histories successfully deleted."})
    except Exception as e:
        print(f"[ERROR] Account deletion failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Failed to delete account: {str(e)}"}), 500

@app.route("/api/sessions/<session_id>", methods=["DELETE"])
def api_delete_session(session_id):
    """Delete a specific chat session timeline and all its messages."""
    try:
        delete_session(session_id)
        return jsonify({"success": "Session successfully deleted."})
    except Exception as e:
        print(f"[ERROR] Session deletion failed: {str(e)}", file=sys.stderr)
        return jsonify({"error": f"Failed to delete session: {str(e)}"}), 500

import threading

# Rebuild thread safety lock and status flag
rebuild_lock = threading.Lock()
is_rebuilding = False

def run_background_rebuild():
    global is_rebuilding
    try:
        from scraper import WebScraper
        from knowledge import rebuild_unified_index
        print("[BACKGROUND REBUILD] Starting unified index rebuild...")
        scraper = WebScraper(start_url="https://mbcet.ac.in/", max_pages=150)
        scraped_pages = scraper.start()
        if scraped_pages:
            rebuild_unified_index(scraped_pages)
            print("[BACKGROUND REBUILD] FAISS index rebuilt successfully!")
        else:
            print("[BACKGROUND REBUILD] Scraper returned no pages. Index was not rebuilt.")
    except Exception as e:
        print(f"[BACKGROUND REBUILD ERROR] Index rebuild failed: {e}", file=sys.stderr)
    finally:
        global is_rebuilding
        is_rebuilding = False

def run_weekly_scheduler():
    # Run every 7 days (604800 seconds)
    while True:
        time.sleep(604800)
        global is_rebuilding
        with rebuild_lock:
            if is_rebuilding:
                print("[SCHEDULER] Rebuild already in progress. Skipping scheduled run.")
                continue
            is_rebuilding = True
        print("[SCHEDULER] Starting automatic weekly rebuild of FAISS index...")
        threading.Thread(target=run_background_rebuild, daemon=True).start()

# Start scheduler thread as a daemon
threading.Thread(target=run_weekly_scheduler, daemon=True).start()

@app.route("/api/admin/rebuild-index", methods=["POST"])
def api_rebuild_index():
    """Trigger manual index rebuild in a background thread to prevent API timeout."""
    global is_rebuilding
    with rebuild_lock:
        if is_rebuilding:
            return jsonify({"error": "An index rebuild is already in progress."}), 429
        is_rebuilding = True
    
    threading.Thread(target=run_background_rebuild, daemon=True).start()
    return jsonify({"success": "Web scraper and index rebuild started in the background."})

def check_files():
    """Verify at startup that data or cache dependencies are in place."""
    print("*" * 60)
    if CACHE_FILE.exists():
        print(f"[OK] Found FAISS cache index: {CACHE_FILE.name}")
    elif PDF_PATH.exists():
        print(f"[OK] Found admissions prospectus: {PDF_PATH.name}")
        print("   The FAISS index will be built from scratch on the first query.")
    else:
        print(f"[WARN] Notice: Neither FAISS cache ({CACHE_FILE}) nor PDF prospectus ({PDF_PATH}) was found.")
        print("   Please place 'mbcet_prospectus.pdf' in the 'data/' directory before querying.")
    print("*" * 60)

if __name__ == "__main__":
    check_files()
    # Run the Flask development server locally on port 5000
    app.run(host="127.0.0.1", port=5000, debug=True)
