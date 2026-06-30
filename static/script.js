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
    
    // UI Widget drag & fullscreen selectors
    const chatbotWidget = document.getElementById("chatbot-widget");
    const widgetHeader = document.getElementById("widget-header");

    // Local Storage Session State
    let sessions = [];
    let activeSessionId = null;

    // User Authentications & Sessions DOM variables
    let currentUser = JSON.parse(localStorage.getItem("mbcet_user")) || null;
    const authOverlay = document.getElementById("auth-overlay");
    const authForm = document.getElementById("auth-form");
    const authEmailInput = document.getElementById("auth-email");
    const authPasswordInput = document.getElementById("auth-password");
    const authKeyInput = document.getElementById("auth-groq-key");
    const registerKeyGroup = document.getElementById("register-key-group");
    const authErrorMsg = document.getElementById("auth-error-msg");
    const authSubmitBtn = document.getElementById("auth-submit-btn");
    const authGuestBtn = document.getElementById("auth-guest-btn");
    const tabLogin = document.getElementById("tab-login");
    const tabRegister = document.getElementById("tab-register");
    let authMode = "login"; // "login" or "register"
    let failedLoginAttempts = 0;

    const toastNotification = document.getElementById("toast-notification");
    const toastMessage = document.getElementById("toast-message");
    const welcomeTitle = document.querySelector("#welcome-screen .welcome-title");

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

    // Configure marked options for markdown processing
    marked.setOptions({
        gfm: true,
        breaks: true,
        sanitize: false
    });

    const saveSessions = () => {
        if (!currentUser) {
            localStorage.setItem("mbcet_chat_sessions", JSON.stringify(sessions));
        }
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
                    let isUrl = false;
                    let displayLabel = `Page ${pNum}`;
                    let hrefTarget = null;
                    
                    const pStr = String(pNum).trim();
                    if (pStr.startsWith("URL: ")) {
                        isUrl = true;
                        hrefTarget = pStr.substring(5).trim();
                        displayLabel = "Web Source";
                    } else if (pStr.startsWith("http://") || pStr.startsWith("https://")) {
                        isUrl = true;
                        hrefTarget = pStr;
                        displayLabel = "Web Source";
                    } else if (pStr.startsWith("Syllabus: ")) {
                        displayLabel = pStr;
                    }
                    
                    const badge = document.createElement(isUrl ? "a" : "span");
                    badge.className = "source-badge";
                    if (isUrl) {
                        badge.href = hrefTarget;
                        badge.target = "_blank";
                        badge.rel = "noopener noreferrer";
                        badge.style.cursor = "pointer";
                        badge.style.textDecoration = "none";
                    }
                    badge.textContent = displayLabel;
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

    const appendErrorMessageWithRetry = (errorText, failedQuery) => {
        if (welcomeScreen.style.display !== "none") {
            welcomeScreen.style.display = "none";
            chatMessages.style.display = "flex";
        }

        const messageRow = document.createElement("div");
        messageRow.className = "chat-message-row system-row error-row";

        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.textContent = "⚠️";

        const content = document.createElement("div");
        content.className = "message-content error-content";
        
        const p = document.createElement("p");
        p.textContent = errorText;
        content.appendChild(p);

        // Add Retry Button
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "error-retry-btn";
        retryBtn.textContent = "🔄 Retry Query";
        retryBtn.style.marginTop = "8px";
        retryBtn.style.padding = "4px 10px";
        retryBtn.style.fontSize = "11px";
        retryBtn.style.borderRadius = "6px";
        retryBtn.style.border = "1px solid rgba(239, 68, 68, 0.3)";
        retryBtn.style.background = "rgba(239, 68, 68, 0.08)";
        retryBtn.style.color = "#ef4444";
        retryBtn.style.cursor = "pointer";
        retryBtn.style.fontWeight = "600";
        retryBtn.style.transition = "all 0.15s ease";

        retryBtn.addEventListener("mouseover", () => {
            retryBtn.style.background = "rgba(239, 68, 68, 0.15)";
        });
        retryBtn.addEventListener("mouseout", () => {
            retryBtn.style.background = "rgba(239, 68, 68, 0.08)";
        });

        retryBtn.addEventListener("click", () => {
            messageRow.remove();
            chatInput.value = failedQuery;
            chatForm.dispatchEvent(new Event("submit"));
        });

        content.appendChild(retryBtn);
        messageRow.appendChild(avatar);
        messageRow.appendChild(content);
        chatMessages.appendChild(messageRow);
        scrollToBottom();
    };

    // Load messages or fetch from server if logged in
    const loadSession = async (sessionId) => {
        activeSessionId = sessionId;
        chatMessages.innerHTML = "";
        welcomeScreen.style.display = "none";
        chatMessages.style.display = "flex";

        if (currentUser) {
            try {
                const response = await fetch(`/api/sessions/${sessionId}/messages`);
                if (response.ok) {
                    const messages = await response.json();
                    messages.forEach(msg => {
                        appendMessage(msg.text, msg.sender === 'user');
                    });
                }
            } catch (error) {
                console.error("Failed to load session messages:", error);
            }
        } else {
            const session = sessions.find(s => s.id === sessionId);
            if (session && session.messages) {
                session.messages.forEach(msg => {
                    appendMessage(msg.text, msg.isUser, msg.pages || []);
                });
            }
        }
        renderHistoryList();
        if (window.innerWidth <= 900) {
            sidebar.classList.remove("open");
        }
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
    
    // Web Audio API variables
    let audioCtx = null;
    let analyser = null;
    let audioSource = null;
    let animationFrameId = null;
    let silenceStartTime = null;
    
    // Recording timer variables
    let timerInterval = null;
    let recordingDuration = 0;

    // DOM references for recording overlay
    const recordingOverlay = document.getElementById("recording-overlay");
    const recordingTimer = document.getElementById("recording-timer");
    const cancelRecordBtn = document.getElementById("cancel-record-btn");
    const stopRecordBtn = document.getElementById("stop-record-btn");
    
    const formatTimer = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const stopRecording = () => {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        }
        cleanupRecordingUI();
    };

    const discardRecording = () => {
        isRecording = false;
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        }
        audioChunks = [];
        cleanupRecordingUI();
    };

    const langSelect = document.getElementById("lang-select");
    const langWheelContainer = document.getElementById("lang-wheel-container");
    const wheelTriggerBtn = document.getElementById("wheel-trigger-btn");
    const selectedLangWheelVal = document.getElementById("selected-lang-wheel-val");
    const sarvamWarningBanner = document.getElementById("sarvam-warning-banner");

    // Radial choice wheel toggle controller
    if (wheelTriggerBtn && langWheelContainer) {
        wheelTriggerBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            langWheelContainer.classList.toggle("open");
        });

        document.querySelectorAll(".wheel-item").forEach(item => {
            item.addEventListener("click", (e) => {
                e.stopPropagation();
                const val = item.getAttribute("data-value");
                
                if (langSelect) langSelect.value = val;
                
                if (selectedLangWheelVal) {
                    if (val === "en") selectedLangWheelVal.textContent = "EN";
                    else if (val === "ml-mix") selectedLangWheelVal.textContent = "MIX";
                    else if (val === "ml") selectedLangWheelVal.textContent = "ML";
                }
                
                if (sarvamWarningBanner) {
                    if (val === "ml" || val === "ml-mix") {
                        sarvamWarningBanner.style.display = "flex";
                    } else {
                        sarvamWarningBanner.style.display = "none";
                    }
                }
                
                document.querySelectorAll(".wheel-item").forEach(i => i.classList.remove("active"));
                item.classList.add("active");
                
                langWheelContainer.classList.remove("open");
            });
        });

        document.addEventListener("click", (e) => {
            if (langWheelContainer && !langWheelContainer.contains(e.target)) {
                langWheelContainer.classList.remove("open");
            }
        });
    }

    const cleanupRecordingUI = () => {
        isRecording = false;
        micBtn.classList.remove("recording");
        micBtn.style.display = "";
        sendButton.style.display = "";
        if (chatForm) chatForm.classList.remove("recording"); // Remove panel glow animation
        if (langWheelContainer) langWheelContainer.style.display = ""; // Show wheel again
        if (recordingOverlay) recordingOverlay.style.display = "none";
        
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }

        if (animationFrameId) {
            cancelAnimationFrame(animationFrameId);
            animationFrameId = null;
        }

        if (audioCtx && audioCtx.state !== 'closed') {
            audioCtx.close().catch(() => {});
            audioCtx = null;
        }
    };

    if (cancelRecordBtn) {
        cancelRecordBtn.addEventListener("click", (e) => {
            e.preventDefault();
            discardRecording();
        });
    }

    if (stopRecordBtn) {
        stopRecordBtn.addEventListener("click", (e) => {
            e.preventDefault();
            stopRecording();
        });
    }

    micBtn.addEventListener("click", async () => {
        if (isRecording) {
            stopRecording();
            return;
        }

        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            isRecording = true;
            silenceStartTime = null;
            recordingDuration = 0;
            if (recordingTimer) recordingTimer.textContent = "0:00";
            
            // Hide control buttons and show inline recording pill
            micBtn.style.display = "none";
            sendButton.style.display = "none";
            if (langWheelContainer) langWheelContainer.style.display = "none"; // Hide wheel
            if (chatForm) chatForm.classList.add("recording"); // Trigger panel border glow
            if (recordingOverlay) recordingOverlay.style.display = "inline-flex";

            // Setup Web Audio API for visualizer & silence detection
            audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            analyser = audioCtx.createAnalyser();
            analyser.fftSize = 256;
            audioSource = audioCtx.createMediaStreamSource(stream);
            audioSource.connect(analyser);

            // Timer Interval
            timerInterval = setInterval(() => {
                recordingDuration++;
                if (recordingTimer) recordingTimer.textContent = formatTimer(recordingDuration);
            }, 1000);

            // Animation Loop
            const strokes = document.querySelectorAll(".voice-wave .stroke");
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);

            const visualize = () => {
                if (!isRecording) return;
                analyser.getByteTimeDomainData(dataArray);

                let total = 0;
                for (let i = 0; i < bufferLength; i++) {
                    const val = (dataArray[i] - 128) / 128;
                    total += val * val;
                }
                const rms = Math.sqrt(total / bufferLength);

                strokes.forEach((stroke, idx) => {
                    const variance = 1 + Math.sin(idx + Date.now() / 80) * 0.25;
                    const scale = Math.max(0.15, rms * 28 * variance);
                    stroke.style.transform = `scaleY(${Math.min(2.5, scale)})`;
                });

                // Auto-stop after 3.5s of silence
                const silenceThreshold = 0.015;
                if (rms < silenceThreshold) {
                    if (!silenceStartTime) {
                        silenceStartTime = Date.now();
                    } else if (Date.now() - silenceStartTime > 3500) {
                        console.log("Auto-stopping due to silence...");
                        stopRecording();
                        return;
                    }
                } else {
                    silenceStartTime = null;
                }

                animationFrameId = requestAnimationFrame(visualize);
            };

            mediaRecorder = new MediaRecorder(stream);
            
            mediaRecorder.ondataavailable = (event) => {
                if (event.data && event.data.size > 0) {
                    audioChunks.push(event.data);
                }
            };

            mediaRecorder.onstop = async () => {
                cleanupRecordingUI();
                stream.getTracks().forEach(track => track.stop());

                if (audioChunks.length === 0) {
                    return;
                }

                const mimeType = audioChunks[0]?.type || "audio/webm";
                let extension = "webm";
                if (mimeType.includes("mp4")) extension = "mp4";
                else if (mimeType.includes("ogg")) extension = "ogg";
                else if (mimeType.includes("wav")) extension = "wav";
                
                const audioBlob = new Blob(audioChunks, { type: mimeType });

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
                    
                    const selectedLang = langSelect ? langSelect.value : "en";
                    formData.append("language", selectedLang);
                    formData.append("duration", recordingDuration);

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

            mediaRecorder.start(250);
            visualize();

        } catch (error) {
            console.error("Microphone access error:", error);
            alert("Could not access microphone. Please allow microphone permissions in your browser.");
            cleanupRecordingUI();
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
            const truncateTitle = query.length > 22 ? query.substring(0, 22) + "..." : query;
            
            if (currentUser) {
                try {
                    const response = await fetch("/api/sessions", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ user_id: currentUser.user_id, title: truncateTitle })
                    });
                    if (response.ok) {
                        const sData = await response.json();
                        activeSessionId = sData.session_id;
                        sessions.unshift({
                            id: sData.session_id,
                            title: truncateTitle,
                            messages: []
                        });
                    }
                } catch (error) {
                    console.error("Failed to create remote session:", error);
                }
            }
            
            if (!activeSessionId) {
                const newId = Date.now().toString();
                currentSession = {
                    id: newId,
                    title: truncateTitle,
                    messages: []
                };
                sessions.unshift(currentSession);
                activeSessionId = newId;
            }
        } else {
            currentSession = sessions.find(s => s.id === activeSessionId);
        }

        if (currentSession) {
            currentSession.messages.push({
                text: query,
                isUser: true,
                pages: []
            });
            saveSessions();
        }

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
            const selectedModelVal = document.getElementById("selected-model-val").value;
            const payload = {
                message: query,
                user_id: currentUser ? currentUser.user_id : null,
                session_id: activeSessionId,
                model: selectedModelVal
            };
            
            let response = null;
            let retries = 2; // Try up to 2 additional times (3 total attempts)
            let success = false;
            let lastError = null;

            while (retries >= 0 && !success) {
                try {
                    response = await fetch("/api/chat", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify(payload)
                    });

                    if (response.ok) {
                        success = true;
                    } else {
                        const err = await response.json().catch(() => ({}));
                        lastError = new Error(err.error || "Server failed to respond.");
                        retries--;
                        if (retries >= 0) {
                            console.warn(`Chat request failed. Retrying in 1s... (${2 - retries} of 2)`);
                            await new Promise(resolve => setTimeout(resolve, 1000));
                        }
                    }
                } catch (err) {
                    lastError = err;
                    retries--;
                    if (retries >= 0) {
                        console.warn(`Chat request exception. Retrying in 1s... (${2 - retries} of 2)`);
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                }
            }

            typingIndicator.remove();

            if (!success) {
                throw lastError || new Error("Failed after maximum retries.");
            }

            const data = await response.json();
            
            if (currentSession) {
                currentSession.messages.push({
                    text: data.answer,
                    isUser: false,
                    pages: data.pages || []
                });
                saveSessions();
            }

            // Render bot answer
            appendMessage(data.answer, false, data.pages || []);
            renderHistoryList();

        } catch (error) {
            if (typingIndicator) typingIndicator.remove();
            appendErrorMessageWithRetry(`⚠️ Error: ${error.message}. Please check your connection and key.`, query);
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

    const forgotEmailGroup = document.getElementById("forgot-email-group");
    const resetFieldsGroup = document.getElementById("reset-fields-group");
    const loginForgotLinkWrapper = document.getElementById("login-forgot-link-wrapper");

    // Dynamic Auth Overlay Events
    const resetPasswordFieldsVisibility = () => {
        document.querySelectorAll(".password-wrapper input").forEach(input => {
            input.type = "password";
        });
        document.querySelectorAll(".toggle-password-btn").forEach(btn => {
            btn.textContent = "👁️";
        });
    };

    // Toggle Password Visibility
    document.querySelectorAll(".toggle-password-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const input = btn.parentElement.querySelector("input");
            if (input.type === "password") {
                input.type = "text";
                btn.textContent = "🙈";
            } else {
                input.type = "password";
                btn.textContent = "👁️";
            }
        });
    });

    if (tabLogin && tabRegister) {
        tabLogin.addEventListener("click", () => {
            authMode = "login";
            resetPasswordFieldsVisibility();
            tabLogin.classList.add("active");
            tabRegister.classList.remove("active");
            registerKeyGroup.style.display = "none";
            if (forgotEmailGroup) forgotEmailGroup.style.display = "none";
            if (resetFieldsGroup) resetFieldsGroup.style.display = "none";
            if (loginForgotLinkWrapper) loginForgotLinkWrapper.style.display = "block";
            authEmailInput.parentElement.style.display = "block";
            authPasswordInput.parentElement.style.display = "block";
            authSubmitBtn.textContent = "Log In";
            authErrorMsg.style.display = "none";
        });
        tabRegister.addEventListener("click", () => {
            authMode = "register";
            resetPasswordFieldsVisibility();
            tabRegister.classList.add("active");
            tabLogin.classList.remove("active");
            registerKeyGroup.style.display = "block";
            if (forgotEmailGroup) forgotEmailGroup.style.display = "none";
            if (resetFieldsGroup) resetFieldsGroup.style.display = "none";
            if (loginForgotLinkWrapper) loginForgotLinkWrapper.style.display = "none";
            authEmailInput.parentElement.style.display = "block";
            authPasswordInput.parentElement.style.display = "block";
            authSubmitBtn.textContent = "Register";
            authErrorMsg.style.display = "none";
        });
    }

    const loadSessionsFromServer = async () => {
        if (!currentUser) return;
        try {
            const response = await fetch(`/api/sessions?user_id=${currentUser.user_id}`);
            if (response.ok) {
                const data = await response.json();
                sessions = data.map(s => ({
                    id: s.session_id,
                    title: s.title,
                    messages: []
                }));
                renderHistoryList();
            }
        } catch (error) {
            console.error("Failed to load sessions from server:", error);
        }
    };

    const otpGroup = document.getElementById("otp-group");
    const authOtpInput = document.getElementById("auth-otp");
    const navDashboardBtn = document.getElementById("nav-dashboard-btn");

    if (authForm) {
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            authErrorMsg.style.display = "none";
            const email = authEmailInput.value.trim();
            const password = authPasswordInput.value.trim();
            const groq_api_key = authKeyInput.value.trim();

            if (authMode === "forgot") {
                // Request Reset OTP
                const forgotEmailInput = document.getElementById("forgot-email");
                const forgotEmail = forgotEmailInput.value.trim();
                try {
                    const response = await fetch("/api/auth/forgot-password", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email: forgotEmail })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.error || "Password reset request failed.");
                    }
                    // Transition to Reset Code & New Password Entry
                    forgotEmailGroup.style.display = "none";
                    resetFieldsGroup.style.display = "block";
                    authMode = "reset";
                    authSubmitBtn.textContent = "Verify & Reset";
                    showToast("Password reset code sent!", "🔑");
                } catch (err) {
                    authErrorMsg.textContent = err.message;
                    authErrorMsg.style.display = "block";
                }
            } else if (authMode === "reset") {
                // Verify Code & Update password
                const forgotEmailInput = document.getElementById("forgot-email");
                const forgotEmail = forgotEmailInput.value.trim();
                const resetOtpInput = document.getElementById("reset-otp");
                const resetOtp = resetOtpInput.value.trim();
                const newPasswordInput = document.getElementById("reset-new-password");
                const newPassword = newPasswordInput.value.trim();

                try {
                    const response = await fetch("/api/auth/reset-password", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email: forgotEmail, otp: resetOtp, new_password: newPassword })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.error || "Password reset verification failed.");
                    }
                    // Return back to standard login screen
                    tabLogin.click();
                    showToast("Password updated! Please log in.", "✨");
                } catch (err) {
                    authErrorMsg.textContent = err.message;
                    authErrorMsg.style.display = "block";
                }
            } else if (authMode === "register" && otpGroup && otpGroup.style.display !== "block") {
                // Request OTP code via SMTP
                try {
                    const response = await fetch("/api/auth/register", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email, password, groq_api_key: groq_api_key || null })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.error || "Registration failed.");
                    }
                    const resData = await response.json();
                    const otpHint = otpGroup.querySelector(".field-hint");
                    if (otpHint) {
                        if (resData.email_sent) {
                            otpHint.textContent = "A 6-digit verification code has been emailed to your address.";
                        } else {
                            otpHint.textContent = "A 6-digit verification code has been printed to the server terminal console.";
                        }
                    }
                    // Transition to OTP Code Entry Card
                    otpGroup.style.display = "block";
                    registerKeyGroup.style.display = "none";
                    authEmailInput.parentElement.style.display = "none";
                    authPasswordInput.parentElement.style.display = "none";
                    tabLogin.style.display = "none";
                    tabRegister.style.display = "none";
                    authSubmitBtn.textContent = "Verify Code";
                    showToast("Verification code generated!", "🔑");
                } catch (err) {
                    authErrorMsg.textContent = err.message;
                    authErrorMsg.style.display = "block";
                }
            } else if (authMode === "register" && otpGroup && otpGroup.style.display === "block") {
                // Verify OTP entered
                const otp = authOtpInput.value.trim();
                try {
                    const response = await fetch("/api/auth/verify-otp", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email, otp })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.error || "Verification failed.");
                    }
                    const data = await response.json();
                    
                    // Reset registration modal visibility states
                    otpGroup.style.display = "none";
                    authEmailInput.parentElement.style.display = "block";
                    authPasswordInput.parentElement.style.display = "block";
                    tabLogin.style.display = "block";
                    tabRegister.style.display = "block";
                    authSubmitBtn.textContent = "Register";

                    currentUser = data;
                    localStorage.setItem("mbcet_user", JSON.stringify(data));
                    authOverlay.style.display = "none";
                    checkAuth();
                    showToast("Account registered and verified successfully!", "✨");
                } catch (err) {
                    authErrorMsg.textContent = err.message;
                    authErrorMsg.style.display = "block";
                }
            } else {
                // Standard Login flow
                try {
                    const response = await fetch("/api/auth/login", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ email, password })
                    });
                    if (!response.ok) {
                        const err = await response.json();
                        throw new Error(err.error || "Authentication failed.");
                    }
                    const data = await response.json();
                    currentUser = data;
                    localStorage.setItem("mbcet_user", JSON.stringify(data));
                    authOverlay.style.display = "none";
                    checkAuth();
                    showToast("Logged in successfully!", "✨");
                    failedLoginAttempts = 0;
                } catch (err) {
                    authErrorMsg.textContent = err.message;
                    authErrorMsg.style.display = "block";
                }
            }
        });
    }

    const resendOtpBtn = document.getElementById("resend-otp-btn");
    if (resendOtpBtn) {
        resendOtpBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            authErrorMsg.style.display = "none";
            const email = authEmailInput.value.trim();

            if (!email) {
                showToast("Email address is required.", "⚠️");
                return;
            }

            try {
                resendOtpBtn.textContent = "Resending...";
                resendOtpBtn.style.pointerEvents = "none";

                const response = await fetch("/api/auth/resend-otp", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ email })
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Resend failed.");
                }

                const otpHint = otpGroup.querySelector(".field-hint");
                if (otpHint) {
                    if (data.email_sent) {
                        otpHint.textContent = "A fresh verification code has been emailed to your address.";
                    } else {
                        otpHint.textContent = "A fresh verification code has been printed to the server terminal console.";
                    }
                }

                showToast("Verification code resent!", "🔑");
            } catch (err) {
                authErrorMsg.textContent = err.message;
                authErrorMsg.style.display = "block";
                showToast("Failed to resend code.", "⚠️");
            } finally {
                resendOtpBtn.textContent = "Resend Code";
                resendOtpBtn.style.pointerEvents = "";
            }
        });
    }

    const forgotPasswordLink = document.getElementById("forgot-password-link");
    if (forgotPasswordLink) {
        forgotPasswordLink.addEventListener("click", (e) => {
            e.preventDefault();
            authMode = "forgot";
            resetPasswordFieldsVisibility();
            tabLogin.classList.remove("active");
            tabRegister.classList.remove("active");
            registerKeyGroup.style.display = "none";
            authEmailInput.parentElement.style.display = "none";
            authPasswordInput.parentElement.style.display = "none";
            if (loginForgotLinkWrapper) loginForgotLinkWrapper.style.display = "none";
            
            if (forgotEmailGroup) {
                forgotEmailGroup.style.display = "block";
                const forgotEmailInput = document.getElementById("forgot-email");
                if (forgotEmailInput) forgotEmailInput.value = authEmailInput.value;
            }
            if (resetFieldsGroup) resetFieldsGroup.style.display = "none";
            
            authSubmitBtn.textContent = "Send Reset Code";
            authErrorMsg.style.display = "none";
        });
    }
    let isGuestMode = false;
    const navLoginBtn = document.getElementById("nav-login-btn");

    if (authGuestBtn) {
        authGuestBtn.addEventListener("click", () => {
            currentUser = null;
            isGuestMode = true;
            localStorage.removeItem("mbcet_user");
            sessions = JSON.parse(localStorage.getItem("mbcet_chat_sessions")) || [];
            authOverlay.style.display = "none";
            checkAuth();
            showToast("Continuing as guest. History will not be saved.", "👤");
        });
    }

    // Navbar Login/Logout button toggling
    if (navLoginBtn) {
        navLoginBtn.addEventListener("click", () => {
            if (currentUser) {
                // Log Out action
                currentUser = null;
                isGuestMode = false;
                localStorage.removeItem("mbcet_user");
                sessions = [];
                showToast("Logged out successfully.", "👋");
                checkAuth();
                resetChatScreen();
            } else {
                // Show login overlay
                authOverlay.style.display = "flex";
            }
        });
    }

    // Intercept chat actions to prompt login if not authenticated
    const ensureAuth = (e) => {
        if (!currentUser && !isGuestMode) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }
            chatInput.blur();
            authOverlay.style.display = "flex";
            return false;
        }
        return true;
    };

    // Attach chat interaction checks
    chatInput.addEventListener("focus", ensureAuth);
    chatInput.addEventListener("keydown", (e) => {
        if (!ensureAuth(e)) return;
    });
    micBtn.addEventListener("click", (e) => {
        if (!ensureAuth(e)) return;
    }, true); // Capture phase intercept

    // Initialize Auth state check on load
    const checkAuth = () => {
        // Reset dynamic OTP registration UI elements on check
        if (otpGroup) otpGroup.style.display = "none";
        authEmailInput.parentElement.style.display = "block";
        authPasswordInput.parentElement.style.display = "block";
        tabLogin.style.display = "block";
        tabRegister.style.display = "block";
        if (authMode === "register") {
            authSubmitBtn.textContent = "Register";
        } else {
            authSubmitBtn.textContent = "Log In";
        }

        if (currentUser) {
            authOverlay.style.display = "none";
            if (navLoginBtn) navLoginBtn.textContent = "Log Out";
            if (navDashboardBtn) navDashboardBtn.style.display = "inline-flex";
            loadSessionsFromServer();
        } else {
            authOverlay.style.display = "none"; // Hide by default on load
            if (navLoginBtn) navLoginBtn.textContent = "Log In";
            if (navDashboardBtn) navDashboardBtn.style.display = "none";
            renderHistoryList();
        }
    };

    // Custom Model Selector dropdown interaction logic
    const modelTrigger = document.getElementById("model-dropdown-trigger");
    const modelDropdownList = document.getElementById("model-dropdown-list");
    const selectedModelName = document.getElementById("selected-model-name");
    const selectedModelVal = document.getElementById("selected-model-val");
    const modelOptions = document.querySelectorAll(".model-option");

    if (modelTrigger && modelDropdownList) {
        modelTrigger.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = modelDropdownList.style.display === "flex";
            modelDropdownList.style.display = isOpen ? "none" : "flex";
        });

        document.addEventListener("click", () => {
            modelDropdownList.style.display = "none";
        });

        modelOptions.forEach(opt => {
            opt.addEventListener("click", () => {
                const val = opt.getAttribute("data-value");
                const name = opt.querySelector(".model-option-name").textContent;
                
                selectedModelVal.value = val;
                selectedModelName.textContent = name;
                
                // Update active class
                modelOptions.forEach(o => o.classList.remove("active"));
                opt.classList.add("active");
                
                showToast(`Switched model to ${name}`, "🤖");
            });
        });
    }

    // Export Conversation transcript
    const exportChatBtn = document.getElementById("export-chat-btn");
    const downloadTxtFile = (text, filename) => {
        const blob = new Blob([text], { type: "text/plain;charset=utf-8;" });
        const link = document.createElement("a");
        const url = URL.createObjectURL(blob);
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        showToast("Transcript exported successfully!", "📥");
    };

    if (exportChatBtn) {
        exportChatBtn.addEventListener("click", () => {
            const chatMessagesDiv = document.getElementById("chat-messages");
            const messageRows = chatMessagesDiv.querySelectorAll(".chat-message-row");
            
            if (messageRows.length === 0) {
                showToast("No messages to export.", "⚠️");
                return;
            }

            let text = "==================================================\n";
            text += "   MBAssist AI Chatbot - Admissions Inquiry Logs\n";
            text += `   Date: ${new Date().toLocaleString()}\n`;
            text += "==================================================\n\n";

            // If we have an active session from SQL, prepend details
            if (activeSessionId) {
                const currentSession = sessions.find(s => s.id === activeSessionId);
                if (currentSession) {
                    text += `Session Title: ${currentSession.title}\n`;
                    text += `Session ID: ${activeSessionId}\n\n`;
                }
            }

            messageRows.forEach(row => {
                const isUser = row.classList.contains("user-row");
                const sender = isUser ? "User" : "MBAssist AI";
                const contentDiv = row.querySelector(".message-content");
                if (contentDiv) {
                    // Extract text (preserving spacing/formatting from DOM)
                    const contentText = contentDiv.innerText.trim();
                    text += `[${sender}]\n${contentText}\n\n`;
                }
            });

            text += "==================================================\n";
            text += "End of transcript. Thank you for using MBAssist AI!\n";
            text += "==================================================\n";

            const filename = `mbassist_transcript_${activeSessionId || 'guest'}.txt`;
            downloadTxtFile(text, filename);
        });
    }

    checkAuth();
});
