document.addEventListener("DOMContentLoaded", () => {
    // Check if user is authenticated
    const currentUser = JSON.parse(localStorage.getItem("mbcet_user"));
    if (!currentUser) {
        alert("You must be logged in to access the Dashboard.");
        window.location.href = "/";
        return;
    }

    // DOM Elements
    const profileEmail = document.getElementById("profile-email");
    const profileId = document.getElementById("profile-id");
    const groqKeyInput = document.getElementById("groq-key");
    const groqKeyForm = document.getElementById("groq-key-form");
    const timelineList = document.getElementById("timeline-list");
    const deleteAccountBtn = document.getElementById("delete-account-btn");
    const toastNotification = document.getElementById("toast-notification");
    const toastMessage = document.getElementById("toast-message");

    const showToast = (message, icon = "✨") => {
        if (!toastNotification || !toastMessage) return;
        toastMessage.textContent = message;
        const iconEl = toastNotification.querySelector(".toast-icon");
        if (iconEl) iconEl.textContent = icon;
        toastNotification.style.display = "flex";
        setTimeout(() => {
            toastNotification.style.display = "none";
        }, 4000);
    };

    // Load Profile details on load
    const loadProfile = async () => {
        profileEmail.textContent = currentUser.email;
        profileId.textContent = currentUser.user_id;

        try {
            const response = await fetch(`/api/auth/profile?user_id=${currentUser.user_id}`);
            if (response.ok) {
                const data = await response.json();
                if (data.groq_api_key) {
                    groqKeyInput.value = data.groq_api_key;
                }
            }
        } catch (err) {
            console.error("Failed to fetch user profile details:", err);
        }
    };

    // Load timeline sessions from database
    const loadTimelines = async () => {
        try {
            const response = await fetch(`/api/sessions?user_id=${currentUser.user_id}`);
            if (!response.ok) throw new Error("Could not retrieve sessions.");
            
            const sessions = await response.json();
            timelineList.innerHTML = "";

            if (sessions.length === 0) {
                timelineList.innerHTML = `<div style="padding: 16px; font-style: italic; color: var(--text-low); font-size: 12px;">No saved discussions found.</div>`;
                return;
            }

            sessions.forEach(session => {
                const item = document.createElement("div");
                item.className = "timeline-item";

                const dateStr = session.created_at ? new Date(session.created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                }) : "Recent Session";

                item.innerHTML = `
                    <div class="timeline-info">
                        <span class="timeline-title">${session.title}</span>
                        <span class="timeline-date">${dateStr}</span>
                    </div>
                    <div class="timeline-actions">
                        <button class="action-icon-btn download-btn" title="Download Transcript" data-id="${session.session_id}">
                            <svg viewBox="0 0 24 24" width="14" height="14">
                                <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM17 13l-5 5-5-5h3V9h4v4h3z" fill="currentColor"/>
                            </svg>
                        </button>
                        <button class="action-icon-btn delete-btn" title="Delete Session" data-id="${session.session_id}">
                            <svg viewBox="0 0 24 24" width="14" height="14">
                                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" fill="currentColor"/>
                            </svg>
                        </button>
                    </div>
                `;

                // Download transcript handler
                item.querySelector(".download-btn").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const sId = session.session_id;
                    try {
                        const mRes = await fetch(`/api/sessions/${sId}/messages`);
                        if (!mRes.ok) throw new Error("Could not retrieve transcript.");
                        const messages = await mRes.json();
                        
                        if (messages.length === 0) {
                            showToast("Discussion is empty.", "⚠️");
                            return;
                        }

                        let textBlobContent = "";
                        messages.forEach(m => {
                            const sender = m.sender === "user" ? "User" : "MBAssist AI";
                            textBlobContent += `[${sender}]\n${m.text.trim()}\n\n`;
                        });

                        const blob = new Blob([textBlobContent], { type: "text/plain;charset=utf-8" });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement("a");
                        a.href = url;
                        a.download = `mbcet_chat_${sId}.txt`;
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                        showToast("Transcript downloaded!", "💾");
                    } catch (err) {
                        showToast("Failed to compile transcript.", "⚠️");
                    }
                });

                // Delete timeline handler
                item.querySelector(".delete-btn").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    if (confirm("Are you sure you want to delete this discussion timeline permanently?")) {
                        try {
                            const dRes = await fetch(`/api/sessions/${session.session_id}`, { method: "DELETE" });
                            if (dRes.ok) {
                                item.remove();
                                showToast("Timeline deleted successfully.", "🗑️");
                                if (timelineList.children.length === 0) {
                                    timelineList.innerHTML = `<div style="padding: 16px; font-style: italic; color: var(--text-low); font-size: 12px;">No saved discussions found.</div>`;
                                }
                            }
                        } catch (err) {
                            showToast("Timeline deletion failed.", "⚠️");
                        }
                    }
                });

                timelineList.appendChild(item);
            });

        } catch (err) {
            console.error("Failed to load sessions:", err);
            timelineList.innerHTML = `<div style="padding: 16px; font-style: italic; color: #ef4444; font-size: 12px;">Failed to load discussions.</div>`;
        }
    };

    // Save Groq API Key
    if (groqKeyForm) {
        groqKeyForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const groq_key = groqKeyInput.value.trim();

            try {
                const response = await fetch("/api/auth/save-key", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ user_id: currentUser.user_id, groq_key })
                });

                if (response.ok) {
                    showToast("API Key updated successfully!", "✨");
                } else {
                    const err = await response.json();
                    showToast(err.error || "Update failed.", "⚠️");
                }
            } catch (err) {
                showToast("Connection error.", "⚠️");
            }
        });
    }

    // Delete User Account
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener("click", async () => {
            if (confirm("Are you sure you want to permanently delete your account and all discussion logs? This action is irreversible.")) {
                try {
                    const response = await fetch("/api/auth/delete-account", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ user_id: currentUser.user_id })
                    });
                    if (response.ok) {
                        localStorage.removeItem("mbcet_user");
                        alert("Your account and all saved histories have been permanently deleted.");
                        window.location.href = "/";
                    } else {
                        showToast("Failed to delete account.", "⚠️");
                    }
                } catch (err) {
                    showToast("Failed to delete account.", "⚠️");
                }
            }
        });
    }

    // Initialize View
    loadProfile();
    loadTimelines();
});
