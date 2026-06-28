document.addEventListener("DOMContentLoaded", () => {
    const chatForm = document.getElementById("chat-form");
    const chatInput = document.getElementById("chat-input");
    const chatViewport = document.getElementById("chat-viewport");
    const chatMessages = document.getElementById("chat-messages");
    const welcomeScreen = document.getElementById("welcome-screen");
    const newChatBtn = document.getElementById("new-chat-btn");
    const sidebar = document.getElementById("sidebar");
    const menuToggleBtn = document.getElementById("menu-toggle-btn");
    const sendButton = document.getElementById("send-button");
    const micBtn = document.getElementById("mic-btn");
    const attachBtn = document.getElementById("attach-btn");
    const historyList = document.getElementById("history-list");
    const clearAllBtn = document.getElementById("clear-all-btn");

    // Local Storage Session State
    let sessions = JSON.parse(localStorage.getItem("mbcet_chat_sessions")) || [];
    let activeSessionId = null;

    // Configure marked options for markdown processing
    marked.setOptions({
        gfm: true,
        breaks: true,
        sanitize: false
    });

    const saveSessions = () => {
        localStorage.setItem("mbcet_chat_sessions", JSON.stringify(sessions));
    };

    const scrollToBottom = () => {
        const container = chatViewport.parentElement; // .chat-container
        container.scrollTop = container.scrollHeight;
    };

    // Auto-grow textarea heights
    chatInput.addEventListener("input", () => {
        chatInput.style.height = "auto";
        chatInput.style.height = (chatInput.scrollHeight - 16) + "px";
    });

    // Enter to send, Shift+Enter to go down a line
    chatInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // Mobile Sidebar controls
    menuToggleBtn.addEventListener("click", () => {
        sidebar.classList.toggle("open");
    });

    // Close mobile menu on overlay click
    document.addEventListener("click", (e) => {
        if (window.innerWidth <= 900) {
            if (!sidebar.contains(e.target) && !menuToggleBtn.contains(e.target)) {
                sidebar.classList.remove("open");
            }
        }
    });

    // Reset Chat Window
    const resetChatScreen = () => {
        activeSessionId = null;
        chatMessages.innerHTML = "";
        chatMessages.style.display = "none";
        welcomeScreen.style.display = "flex";
        chatInput.value = "";
        chatInput.style.height = "auto";
        renderHistoryList();
        chatInput.focus();
    };

    newChatBtn.addEventListener("click", resetChatScreen);

    // Clear all history logs completely
    clearAllBtn.addEventListener("click", () => {
        if (confirm("Are you sure you want to clear all chat history?")) {
            sessions = [];
            saveSessions();
            resetChatScreen();
        }
    });

    // Format and append a message row inside the chat window
    const appendMessage = (text, isUser = false, pages = []) => {
        if (welcomeScreen.style.display !== "none") {
            welcomeScreen.style.display = "none";
            chatMessages.style.display = "flex";
        }

        const messageRow = document.createElement("div");
        messageRow.className = `chat-message-row ${isUser ? "user-row" : "system-row"}`;

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = isUser ? "U" : "🤖";

        const content = document.createElement("div");
        content.className = "message-content";

        if (isUser) {
            const p = document.createElement("p");
            p.textContent = text;
            content.appendChild(p);
        } else {
            content.innerHTML = marked.parse(text);

            if (pages && pages.length > 0) {
                const badgeContainer = document.createElement("div");
                badgeContainer.style.marginTop = "8px";
                
                const uniquePages = [...new Set(pages)];
                uniquePages.forEach(pNum => {
                    const badge = document.createElement("span");
                    badge.className = "source-badge";
                    badge.textContent = `Page ${pNum}`;
                    badgeContainer.appendChild(badge);
                });
                content.appendChild(badgeContainer);
            }
        }

        if (isUser) {
            messageRow.appendChild(content);
            messageRow.appendChild(avatar);
        } else {
            messageRow.appendChild(avatar);
            messageRow.appendChild(content);
        }

        chatMessages.appendChild(messageRow);
        scrollToBottom();
    };

    // Load full messages from selected session
    const loadSession = (sessionId) => {
        activeSessionId = sessionId;
        const session = sessions.find(s => s.id === sessionId);
        if (!session) return;

        chatMessages.innerHTML = "";
        welcomeScreen.style.display = "none";
        chatMessages.style.display = "flex";

        session.messages.forEach(msg => {
            appendMessage(msg.text, msg.isUser, msg.pages);
        });

        renderHistoryList();
        
        // Hide sidebar drawer after loading the conversation
        sidebar.classList.remove("open");
    };

    // Delete a specific session
    const deleteSession = (sessionId, event) => {
        event.stopPropagation(); // Avoid triggering loading the session
        
        if (confirm("Delete this discussion?")) {
            sessions = sessions.filter(s => s.id !== sessionId);
            saveSessions();
            if (activeSessionId === sessionId) {
                resetChatScreen();
            } else {
                renderHistoryList();
            }
        }
    };

    // Render Recent Chats Sidebar List
    const renderHistoryList = () => {
        historyList.innerHTML = "";
        
        if (sessions.length === 0) {
            const emptyNotice = document.createElement("div");
            emptyNotice.style.padding = "16px 12px";
            emptyNotice.style.fontSize = "12px";
            emptyNotice.style.color = "var(--text-low)";
            emptyNotice.style.fontStyle = "italic";
            emptyNotice.textContent = "No recent chats";
            historyList.appendChild(emptyNotice);
            return;
        }

        sessions.forEach(session => {
            const item = document.createElement("div");
            item.className = `history-item ${session.id === activeSessionId ? "active" : ""}`;
            item.addEventListener("click", () => loadSession(session.id));

            const leftDiv = document.createElement("div");
            leftDiv.className = "history-item-left";
            
            // Conversation SVG Icon
            leftDiv.innerHTML = `
                <svg viewBox="0 0 24 24" width="14" height="14">
                    <path d="M20 2H4c-1.1 0-1.99.9-1.99 2L2 22l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z" fill="currentColor"/>
                </svg>
                <span class="history-item-title">${session.title}</span>
            `;

            // Delete Button
            const deleteBtn = document.createElement("button");
            deleteBtn.className = "delete-session-btn";
            deleteBtn.title = "Delete Chat";
            deleteBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="14" height="14">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" fill="currentColor"/>
                </svg>
            `;
            deleteBtn.addEventListener("click", (e) => deleteSession(session.id, e));

            item.appendChild(leftDiv);
            item.appendChild(deleteBtn);
            historyList.appendChild(item);
        });
    };

    // Render Suggestion cards click responses
    document.querySelectorAll(".suggestion-card").forEach(card => {
        card.addEventListener("click", () => {
            const query = card.getAttribute("data-query");
            if (query) {
                chatInput.value = query;
                chatForm.dispatchEvent(new Event("submit"));
            }
        });
    });

    // Dictation Engine (Whisper Speech-to-Text Integration)
    let mediaRecorder = null;
    let audioChunks = [];
    let isRecording = false;

    micBtn.addEventListener("click", async () => {
        if (isRecording) {
            isRecording = false;
            micBtn.classList.remove("recording");
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
            }
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            
            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                // Determine native mimetype and file extension
                const mimeType = audioChunks[0]?.type || "audio/webm";
                let extension = "webm";
                if (mimeType.includes("mp4")) extension = "mp4";
                else if (mimeType.includes("ogg")) extension = "ogg";
                else if (mimeType.includes("wav")) extension = "wav";
                
                const audioBlob = new Blob(audioChunks, { type: mimeType });
                
                // Stop microphone tracks
                stream.getTracks().forEach(track => track.stop());

                if (audioBlob.size === 0) {
                    console.error("Recording resulted in an empty audio blob.");
                    alert("Audio recording was empty. Please check your microphone settings.");
                    return;
                }

                const originalPlaceholder = chatInput.placeholder;
                chatInput.placeholder = "Transcribing audio input...";
                chatInput.disabled = true;
                micBtn.disabled = true;

                try {
                    const formData = new FormData();
                    formData.append("audio", audioBlob, `audio.${extension}`);

                    const response = await fetch("/api/transcribe", {
                        method: "POST",
                        body: formData
                    });

                    if (!response.ok) {
                        const errData = await response.json().catch(() => ({}));
                        throw new Error(errData.error || "Transcription server error.");
                    }

                    const data = await response.json();
                    if (data.text && data.text.trim()) {
                        chatInput.value = data.text.trim();
                        chatInput.dispatchEvent(new Event("input"));
                    }
                } catch (error) {
                    console.error("Transcription error:", error);
                    alert(`Speech-to-Text failed: ${error.message}`);
                } finally {
                    chatInput.placeholder = originalPlaceholder;
                    chatInput.disabled = false;
                    micBtn.disabled = false;
                    chatInput.focus();
                }
            };

            isRecording = true;
            micBtn.classList.add("recording");
            // Start recording and emit data chunks every 250ms
            mediaRecorder.start(250);

        } catch (error) {
            console.error("Microphone access error:", error);
            alert("Could not access microphone. Please allow microphone permissions in your browser.");
        }
    });

    attachBtn.addEventListener("click", () => {
        alert("File attachment capability is a placeholder for Phase 2/3.");
    });

    // Form submit event handler
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const query = chatInput.value.trim();
        if (!query) return;

        // Clear and resize input
        chatInput.value = "";
        chatInput.style.height = "auto";

        // Lock form
        chatInput.disabled = true;
        sendButton.disabled = true;

        // Session Setup
        let currentSession;
        if (!activeSessionId) {
            // Create a new session
            const newId = Date.now().toString();
            const truncateTitle = query.length > 22 ? query.substring(0, 22) + "..." : query;
            
            currentSession = {
                id: newId,
                title: truncateTitle,
                messages: []
            };
            sessions.unshift(currentSession); // Add to beginning of history list
            activeSessionId = newId;
        } else {
            currentSession = sessions.find(s => s.id === activeSessionId);
        }

        // Add user query to session object
        currentSession.messages.push({
            text: query,
            isUser: true,
            pages: []
        });
        saveSessions();

        // Render user message on screen
        appendMessage(query, true);

        // Show typing indicator
        const typingIndicator = (() => {
            const messageRow = document.createElement("div");
            messageRow.className = "chat-message-row system-row typing-indicator-container";

            const avatar = document.createElement("div");
            avatar.className = "message-avatar";
            avatar.textContent = "🤖";

            const content = document.createElement("div");
            content.className = "message-content";

            const dots = document.createElement("div");
            dots.className = "typing-dots";
            dots.innerHTML = "<span></span><span></span><span></span>";

            content.appendChild(dots);
            messageRow.appendChild(avatar);
            messageRow.appendChild(content);
            chatMessages.appendChild(messageRow);
            scrollToBottom();
            return messageRow;
        })();

        try {
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: query })
            });

            typingIndicator.remove();

            if (!response.ok) {
                const err = await response.json().catch(() => ({}));
                throw new Error(err.error || "Server failed to respond.");
            }

            const data = await response.json();
            
            // Add bot answer to session object
            currentSession.messages.push({
                text: data.answer,
                isUser: false,
                pages: data.pages || []
            });
            saveSessions();

            // Render bot answer
            appendMessage(data.answer, false, data.pages || []);
            renderHistoryList();

        } catch (error) {
            if (typingIndicator) typingIndicator.remove();
            appendMessage(`⚠️ Error: ${error.message}. Please check your connection and key.`, false);
        } finally {
            chatInput.disabled = false;
            sendButton.disabled = false;
            chatInput.focus();
            scrollToBottom();
        }
    });

    // Initial setups
    renderHistoryList();
    chatInput.focus();

    // ==========================================================================
    // Fullscreen View Toggles (Subtle Icon / Double Click Header)
    // ==========================================================================
    const landingContainer = document.getElementById("landing-container");
    const widgetFullscreenBtn = document.getElementById("widget-fullscreen-btn");
    const dragStatus = document.getElementById("drag-status");

    const toggleFullscreen = () => {
        const isFullscreen = landingContainer.classList.toggle("fullscreen-active");
        
        if (isFullscreen) {
            // Reset position coordinates and size before expanding
            chatbotWidget.style.position = "";
            chatbotWidget.style.left = "";
            chatbotWidget.style.top = "";
            chatbotWidget.style.width = "";
            chatbotWidget.style.height = "";
            chatbotWidget.style.margin = "";
            chatbotWidget.classList.remove("draggable");
            dragStatus.textContent = "Fullscreen Mode";
        } else {
            dragStatus.textContent = "Admissions Guide";
        }
        scrollToBottom();
    };

    widgetFullscreenBtn.addEventListener("click", toggleFullscreen);
    widgetHeader.addEventListener("dblclick", toggleFullscreen);

    // ==========================================================================
    // Draggable Widget Controller (Mouse & Touch)
    // ==========================================================================
    let isDragging = false;
    let offsetX = 0;
    let offsetY = 0;

    const dragStart = (e) => {
        // Disabled when in full screen
        if (landingContainer.classList.contains("fullscreen-active")) return;
        
        // Exclude interactive elements (toggles, buttons) from drag triggers
        if (e.target.closest("button") || e.target.closest("a") || e.target.closest("svg")) return;

        const clientX = e.type === "touchstart" ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === "touchstart" ? e.touches[0].clientY : e.clientY;

        isDragging = true;
        chatbotWidget.classList.add("draggable");

        const rect = chatbotWidget.getBoundingClientRect();
        offsetX = clientX - rect.left;
        offsetY = clientY - rect.top;
    };

    const dragMove = (e) => {
        if (!isDragging) return;
        
        // Prevent background scrolling while dragging on touch devices
        e.preventDefault();

        const clientX = e.type === "touchmove" ? e.touches[0].clientX : e.clientX;
        const clientY = e.type === "touchmove" ? e.touches[0].clientY : e.clientY;

        const leftPos = clientX - offsetX;
        const topPos = clientY - offsetY;

        chatbotWidget.style.left = `${leftPos}px`;
        chatbotWidget.style.top = `${topPos}px`;
        chatbotWidget.style.margin = "0";
    };

    const dragEnd = () => {
        isDragging = false;
    };

    // Mouse Drag Listeners
    widgetHeader.addEventListener("mousedown", dragStart);
    document.addEventListener("mousemove", dragMove);
    document.addEventListener("mouseup", dragEnd);

    // Touch Drag Listeners (Mobile/Tablet)
    widgetHeader.addEventListener("touchstart", dragStart);
    document.addEventListener("touchmove", dragMove, { passive: false });
    document.addEventListener("touchend", dragEnd);
});
