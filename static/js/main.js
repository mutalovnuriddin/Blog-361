document.addEventListener("DOMContentLoaded", () => {
    const themeRoot = document.documentElement;
    const applyThemeToggleState = () => {
        document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
            const isDark = themeRoot.dataset.theme === "dark";
            button.setAttribute("aria-pressed", String(isDark));
            const icon = button.querySelector(".theme-toggle-icon");
            if (icon) icon.textContent = isDark ? "☀️" : "🌙";
            button.title = isDark ? "Light rejim" : "Dark rejim";
        });
        const metaTheme = document.querySelector('meta[name="theme-color"]');
        if (metaTheme) {
            metaTheme.setAttribute("content", themeRoot.dataset.theme === "dark" ? "#101010" : "#f8f8f8");
        }
    };

    if (!themeRoot.dataset.theme) themeRoot.dataset.theme = "light";
    applyThemeToggleState();

    document.querySelectorAll("[data-theme-toggle]").forEach((button) => {
        button.addEventListener("click", () => {
            const next = themeRoot.dataset.theme === "dark" ? "light" : "dark";
            themeRoot.dataset.theme = next;
            try { localStorage.setItem("theme", next); } catch (error) {}
            applyThemeToggleState();
        });
    });

    document.querySelectorAll("[data-menu-toggle]").forEach((toggle) => {
        const nav = document.getElementById(toggle.getAttribute("aria-controls") || "");
        if (!nav) return;

        let backdrop = document.querySelector("[data-menu-backdrop]");
        if (!backdrop) {
            backdrop = document.createElement("div");
            backdrop.className = "menu-backdrop";
            backdrop.dataset.menuBackdrop = "";
            backdrop.setAttribute("aria-hidden", "true");
            document.body.append(backdrop);
        }

        const setMenu = (open) => {
            nav.classList.toggle("is-open", open);
            toggle.classList.toggle("is-open", open);
            toggle.setAttribute("aria-expanded", String(open));
            backdrop.classList.toggle("is-visible", open);
            document.body.classList.toggle("menu-open", open);
        };

        toggle.addEventListener("click", () => {
            setMenu(!nav.classList.contains("is-open"));
        });
        document.addEventListener("click", (event) => {
            if (!(event.target instanceof Element)) return;
            if (event.target.closest("[data-menu-backdrop]")) {
                setMenu(false);
                return;
            }
            if (!nav.contains(event.target) && !toggle.contains(event.target)) {
                setMenu(false);
            }
        });
    });

    const searchInput = document.querySelector("[data-user-search]");
    const searchResults = document.querySelector("[data-search-results]");
    const searchStatus = document.querySelector("#user-search-status");

    if (
        searchInput instanceof HTMLInputElement &&
        searchResults instanceof HTMLUListElement &&
        searchStatus instanceof HTMLElement
    ) {
        let searchTimeout;
        let activeSearch;

        searchInput.addEventListener("input", () => {
            window.clearTimeout(searchTimeout);
            activeSearch?.abort();

            const query = searchInput.value.trim();
            if (!query) {
                searchResults.replaceChildren();
                searchStatus.textContent = "Qidirish uchun username yoki ismni yozing.";
                searchInput.setAttribute("aria-expanded", "false");
                return;
            }

            searchStatus.textContent = "Qidirilmoqda...";
            searchInput.setAttribute("aria-expanded", "true");
            searchTimeout = window.setTimeout(async () => {
                const controller = new AbortController();
                activeSearch = controller;

                try {
                    const url = new URL(searchInput.dataset.searchUrl, window.location.origin);
                    url.searchParams.set("q", query);
                    const response = await fetch(url, {
                        headers: { "X-Requested-With": "XMLHttpRequest" },
                        credentials: "same-origin",
                        signal: controller.signal,
                    });
                    const contentType = response.headers.get("content-type") || "";
                    if (!response.ok || !contentType.includes("application/json")) {
                        throw new Error("Qidiruv natijalarini olib bo‘lmadi.");
                    }

                    const payload = await response.json();
                    if (searchInput.value.trim() !== query) return;
                    searchResults.innerHTML = payload.html;
                    searchStatus.textContent = payload.count
                        ? `${payload.count} ta foydalanuvchi topildi.`
                        : "Foydalanuvchi topilmadi.";
                } catch (error) {
                    if (error instanceof DOMException && error.name === "AbortError") return;
                    searchResults.replaceChildren();
                    searchStatus.textContent = error instanceof Error
                        ? error.message
                        : "Qidiruvda xatolik yuz berdi.";
                }
            }, 250);
        });
    }

    const connectionsDialog = document.querySelector("[data-connections-dialog]");
    const connectionsTitle = document.querySelector("[data-connections-dialog-title]");
    const connectionsStatus = document.querySelector("[data-connections-status]");
    const connectionsList = document.querySelector("[data-connections-list]");
    const connectionsCloseButton = document.querySelector("[data-connections-close]");

    if (
        connectionsDialog instanceof HTMLDialogElement &&
        connectionsTitle instanceof HTMLElement &&
        connectionsStatus instanceof HTMLElement &&
        connectionsList instanceof HTMLUListElement
    ) {
        let activeConnectionsRequest;

        document.addEventListener("click", async (event) => {
            const target = event.target;
            if (!(target instanceof Element)) return;

            const trigger = target.closest("[data-connections-url]");
            if (!(trigger instanceof HTMLButtonElement)) return;

            activeConnectionsRequest?.abort();
            const controller = new AbortController();
            activeConnectionsRequest = controller;
            connectionsTitle.textContent = trigger.dataset.connectionsTitle || "Obunalar";
            connectionsStatus.textContent = "Ro‘yxat yuklanmoqda...";
            connectionsList.replaceChildren();
            connectionsDialog.showModal();

            try {
                const response = await fetch(trigger.dataset.connectionsUrl, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    credentials: "same-origin",
                    signal: controller.signal,
                });
                const contentType = response.headers.get("content-type") || "";
                if (!response.ok || !contentType.includes("application/json")) {
                    throw new Error("Obunalar ro‘yxatini yuklab bo‘lmadi.");
                }

                const payload = await response.json();
                if (!connectionsDialog.open || controller.signal.aborted) return;
                connectionsList.innerHTML = payload.html;
                connectionsStatus.textContent = payload.count
                    ? `${payload.count} ta foydalanuvchi`
                    : "Bu ro‘yxat hozircha bo‘sh.";
            } catch (error) {
                if (error instanceof DOMException && error.name === "AbortError") return;
                connectionsStatus.textContent = error instanceof Error
                    ? error.message
                    : "Ro‘yxatni yuklashda xatolik yuz berdi.";
            }
        });

        connectionsCloseButton?.addEventListener("click", () => connectionsDialog.close());
        connectionsDialog.addEventListener("close", () => activeConnectionsRequest?.abort());
        connectionsDialog.addEventListener("click", (event) => {
            if (event.target === connectionsDialog) connectionsDialog.close();
        });
    }

    const shareSheet = (() => {
        let backdrop = document.querySelector("[data-share-sheet-backdrop]");
        if (!backdrop) {
            backdrop = document.createElement("div");
            backdrop.className = "share-sheet-backdrop";
            backdrop.dataset.shareSheetBackdrop = "";
            backdrop.innerHTML = [
                '<div class="share-sheet" role="dialog" aria-modal="true" aria-labelledby="share-sheet-title">',
                '    <header class="share-sheet-header">',
                '        <div><span class="chat-kicker">Ulashish</span><h2 id="share-sheet-title">Postni ulashish</h2></div>',
                '        <button type="button" class="chat-tool-button" data-share-close aria-label="Paneldan chiqish" title="Yopish">×</button>',
                '    </header>',
                '    <label class="share-sheet-search">',
                '        <span aria-hidden="true">⌕</span>',
                '        <input type="search" placeholder="Foydalanuvchilarni qidirish..." data-share-search>',
                '    </label>',
                '    <p class="share-sheet-status" data-share-status role="status"></p>',
                '    <ul class="share-user-list" data-share-list></ul>',
                '    <footer class="share-sheet-footer">',
                '        <input type="text" maxlength="200" placeholder="Izoh qo‘shish (ixtiyoriy)" data-share-caption>',
                '        <button type="button" class="share-send-button" data-share-send disabled>',
                '            <span>Yuborish</span><span aria-hidden="true">➤</span>',
                '        </button>',
                '    </footer>',
                '</div>',
            ].join("");
            document.body.append(backdrop);
        }

        const list = backdrop.querySelector("[data-share-list]");
        const status = backdrop.querySelector("[data-share-status]");
        const searchInput = backdrop.querySelector("[data-share-search]");
        const captionInput = backdrop.querySelector("[data-share-caption]");
        const sendButton = backdrop.querySelector("[data-share-send]");

        const state = {
            targetsUrl: "",
            shareUrl: "",
            postCard: null,
            selected: new Map(),
            requestController: undefined,
            searchController: undefined,
            searchTimer: 0,
            busy: false,
        };

        const updateSendButton = () => {
            sendButton.disabled = state.busy || state.selected.size === 0;
            sendButton.querySelector("span")?.replaceWith(
                Object.assign(document.createElement("span"), { textContent: state.busy ? "Yuborilmoqda…" : "Yuborish" }),
            );
        };

        const toggleUser = (button) => {
            const userId = button.dataset.userId;
            const userName = button.dataset.userName || userId;
            if (!userId) return;
            if (state.selected.has(userId)) {
                state.selected.delete(userId);
                button.classList.remove("is-selected");
                button.setAttribute("aria-pressed", "false");
            } else {
                state.selected.set(userId, userName);
                button.classList.add("is-selected");
                button.setAttribute("aria-pressed", "true");
            }
            updateSendButton();
        };

        const resetSelection = () => {
            state.selected.clear();
            list?.querySelectorAll("[data-share-user]").forEach((item) => {
                if (item instanceof HTMLElement) {
                    item.classList.remove("is-selected");
                    item.setAttribute("aria-pressed", "false");
                }
            });
            updateSendButton();
        };

        const renderUsers = (payload, emptyMessage) => {
            list.innerHTML = payload.html;
            const count = Number(payload.count);
            status.textContent = payload.searched
                ? (count ? `${count} ta foydalanuvchi topildi.` : emptyMessage)
                : (count ? `${count} ta obuna — tanlab «Yuborish»ni bosing.` : "Hali obuna yo‘q — yuqorida qidirib ko‘ring.");
            if (count) {
                list.querySelector("[data-share-user]")?.scrollIntoView?.({ block: "start" });
            }
        };

        const loadTargets = async (query = "") => {
            state.requestController?.abort();
            state.searchController?.abort();
            const controller = new AbortController();
            state.requestController = controller;
            status.textContent = "Ro‘yxat yuklanmoqda...";

            try {
                const url = new URL(state.targetsUrl, window.location.origin);
                if (query) url.searchParams.set("q", query);
                const response = await fetch(url, {
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                    credentials: "same-origin",
                    signal: controller.signal,
                });
                const contentType = response.headers.get("content-type") || "";
                if (!response.ok || !contentType.includes("application/json")) {
                    throw new Error("Foydalanuvchilar ro‘yxatini yuklab bo‘lmadi.");
                }
                const payload = await response.json();
                if (!backdrop.classList.contains("is-open") || controller.signal.aborted) return;
                renderUsers(payload, "Foydalanuvchi topilmadi.");
            } catch (error) {
                if (error instanceof DOMException && error.name === "AbortError") return;
                list.replaceChildren();
                status.textContent = error instanceof Error ? error.message : "Ro‘yxatni yuklashda xatolik yuz berdi.";
            }
        };

        const sendShares = async () => {
            if (state.busy || state.selected.size === 0) return;
            state.busy = true;
            updateSendButton();

            const formData = new FormData();
            state.selected.forEach((_, userId) => formData.append("user_ids", userId));
            const caption = captionInput.value.trim();
            if (caption) formData.append("body", caption);

            try {
                const response = await fetch(state.shareUrl, {
                    method: "POST",
                    body: formData,
                    headers: {
                        "X-Requested-With": "XMLHttpRequest",
                        "X-CSRFToken": document.querySelector("[name=csrfmiddlewaretoken]")?.value || "",
                    },
                    credentials: "same-origin",
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || "Postni ulashib bo‘lmadi.");
                }
                const count = Number(payload.count) || 0;
                const shareCount = state.postCard?.querySelector("[data-share-count]");
                if (shareCount instanceof HTMLElement) {
                    shareCount.textContent = String(Number(shareCount.textContent || "0") + count);
                }
                showShareToast(count); //eslint-disable-line @typescript-eslint/no-use-before-define
                dismiss();
            } catch (error) {
                status.textContent = error instanceof Error ? error.message : "Postni ulashda xatolik yuz berdi.";
            } finally {
                state.busy = false;
                if (backdrop.classList.contains("is-open")) updateSendButton();
            }
        };

        const showShareToast = (count) => {
            let toast = document.querySelector("[data-share-toast]");
            if (!(toast instanceof HTMLElement)) {
                toast = document.createElement("div");
                toast.className = "share-toast";
                toast.dataset.shareToast = "";
                toast.setAttribute("role", "status");
                document.body.append(toast);
            }
            toast.textContent = count === 1
                ? "Post 1 ta foydalanuvchiga yuborildi. ✓"
                : `Post ${count} ta foydalanuvchiga yuborildi. ✓`;
            toast.classList.add("is-visible");
            window.setTimeout(() => toast.classList.remove("is-visible"), 4000);
        };

        const dismiss = () => {
            backdrop.classList.remove("is-open");
            document.body.classList.remove("share-sheet-open");
            window.clearTimeout(state.searchTimer);
            state.requestController?.abort();
            state.searchController?.abort();
            window.setTimeout(() => {
                if (backdrop.classList.contains("is-open")) return;
                list.replaceChildren();
                if (searchInput instanceof HTMLInputElement) searchInput.value = "";
                if (captionInput instanceof HTMLInputElement) captionInput.value = "";
                state.selected.clear();
                updateSendButton();
            }, 250);
        };

        document.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) return;

            const trigger = target.closest("[data-share-button]");
            if (trigger instanceof HTMLButtonElement) {
                event.preventDefault();
                const postId = trigger.dataset.postId || "";
                if (state.postId !== postId || !backdrop.classList.contains("is-open")) {
                    state.postId = postId;
                    state.shareUrl = trigger.dataset.shareUrl || "";
                    state.targetsUrl = trigger.dataset.shareTargetsUrl || "";
                    state.postCard = trigger.closest("[data-post-card]");
                    resetSelection();
                    backdrop.classList.add("is-open");
                    document.body.classList.add("share-sheet-open");
                    void loadTargets();
                }
                return;
            }

            if (!backdrop.contains(target)) return;
            if (target.closest("[data-share-close]") || event.target === backdrop) {
                dismiss();
                return;
            }
            const userButton = target.closest("[data-share-user]");
            if (userButton instanceof HTMLButtonElement) {
                toggleUser(userButton);
                return;
            }
            if (target.closest("[data-share-send]")) void sendShares();
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && backdrop.classList.contains("is-open")) dismiss();
        });

        if (searchInput instanceof HTMLInputElement) {
            searchInput.addEventListener("input", () => {
                window.clearTimeout(state.searchTimer);
                const query = searchInput.value.trim();
                if (!query) {
                    void loadTargets();
                    return;
                }
                state.searchTimer = window.setTimeout(() => void loadTargets(query), 250);
            });
        }
    })();

    const notificationSocketLink = document.querySelector("[data-notifications-socket-url]");
    if (
        notificationSocketLink instanceof HTMLAnchorElement &&
        window.WebSocket
    ) {
        let notificationSocket;
        let notificationReconnectTimer;
        let notificationReconnectDelay = 1000;
        let notificationToastTimer;

        const showNotificationToast = (payload) => {
            let toast = document.querySelector("[data-notification-toast]");
            if (!(toast instanceof HTMLAnchorElement)) {
                toast = document.createElement("a");
                toast.className = "notification-toast";
                toast.dataset.notificationToast = "";
                toast.setAttribute("role", "status");
                document.body.append(toast);
            }
            toast.href = payload.notifications_url || notificationSocketLink.href;
            toast.textContent = `${payload.actor_username || "Foydalanuvchi"}: ${payload.message || "Yangi bildirishnoma"}`;
            toast.classList.add("is-visible");
            window.clearTimeout(notificationToastTimer);
            notificationToastTimer = window.setTimeout(() => {
                toast.classList.remove("is-visible");
            }, 5000);
        };

        const connectNotifications = () => {
            const socketUrl = new URL(
                notificationSocketLink.dataset.notificationsSocketUrl,
                window.location.href,
            );
            socketUrl.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            notificationSocket = new WebSocket(socketUrl);

            notificationSocket.addEventListener("open", () => {
                notificationReconnectDelay = 1000;
            });

            notificationSocket.addEventListener("message", (event) => {
                let payload;
                try {
                    payload = JSON.parse(event.data);
                } catch {
                    return;
                }
                if (payload.type !== "notification") return;

                const count = Number(payload.unread_count);
                document.querySelectorAll("[data-notifications-socket-url]").forEach((link) => {
                    let badge = link.querySelector("[data-notification-count]");
                    if (count > 0 && !(badge instanceof HTMLElement)) {
                        badge = document.createElement("span");
                        badge.className = "notification-nav-badge";
                        badge.dataset.notificationCount = "";
                        link.append(badge);
                    }
                    if (badge instanceof HTMLElement) {
                        badge.textContent = String(count);
                        badge.hidden = count < 1;
                    }
                });

                const notificationList = document.querySelector(".notification-list");
                if (notificationList instanceof HTMLElement && typeof payload.html === "string") {
                    notificationList.querySelector(".notifications-empty")?.remove();
                    const template = document.createElement("template");
                    template.innerHTML = payload.html.trim();
                    const notificationItem = template.content.firstElementChild;
                    if (notificationItem) notificationList.prepend(notificationItem);
                }
                showNotificationToast(payload);
            });

            notificationSocket.addEventListener("close", (event) => {
                if (event.code === 4401) return;
                notificationReconnectTimer = window.setTimeout(() => {
                    notificationReconnectDelay = Math.min(notificationReconnectDelay * 2, 15000);
                    connectNotifications();
                }, notificationReconnectDelay);
            });
        };

        connectNotifications();
        window.addEventListener("beforeunload", () => {
            window.clearTimeout(notificationReconnectTimer);
            window.clearTimeout(notificationToastTimer);
            notificationSocket?.close();
        });
    }

    const chatApp = document.querySelector("[data-chat-app]");
    const chatFilter = document.querySelector("[data-chat-filter]");
    const chatFilterEmpty = document.querySelector("[data-chat-filter-empty]");
    if (chatFilter instanceof HTMLInputElement) {
        chatFilter.addEventListener("input", () => {
            const query = chatFilter.value.trim().toLocaleLowerCase();
            const chatItems = document.querySelectorAll("[data-chat-item]");
            let visibleCount = 0;
            chatItems.forEach((item) => {
                if (!(item instanceof HTMLElement)) return;
                const isVisible = item.dataset.chatUsername?.includes(query) ?? false;
                item.hidden = !isVisible;
                if (isVisible) visibleCount += 1;
            });
            if (chatFilterEmpty instanceof HTMLElement) {
                chatFilterEmpty.hidden = !query || visibleCount > 0;
            }
        });
    }

    if (chatApp instanceof HTMLElement && chatApp.dataset.socketUrl) {
        const messages = chatApp.querySelector("[data-chat-messages]");
        const chatForm = chatApp.querySelector("[data-chat-form]");
        const chatInput = chatApp.querySelector("[data-chat-input]");
        const chatFileInput = chatApp.querySelector("[data-chat-file]");
        const chatFileButton = chatApp.querySelector("[data-chat-file-button]");
        const attachmentPreview = chatApp.querySelector("[data-attachment-preview]");
        const attachmentPreviewMedia = chatApp.querySelector("[data-attachment-preview-media]");
        const attachmentPreviewName = chatApp.querySelector("[data-attachment-preview-name]");
        const attachmentPreviewSize = chatApp.querySelector("[data-attachment-preview-size]");
        const attachmentCancel = chatApp.querySelector("[data-attachment-cancel]");
        const emojiToggle = chatApp.querySelector("[data-emoji-toggle]");
        const emojiPicker = chatApp.querySelector("[data-emoji-picker]");
        const audioRecordButton = chatApp.querySelector("[data-audio-record]");
        const recordStatus = chatApp.querySelector("[data-record-status]");
        const chatStatus = chatApp.querySelector("[data-chat-status]");
        const chatTyping = chatApp.querySelector("[data-chat-typing]");
        const chatError = chatApp.querySelector("[data-chat-error]");
        const peerUsername = chatApp.dataset.peerUsername;
        let socket;
        let reconnectTimer;
        let heartbeatTimer;
        let typingTimer;
        let reconnectDelay = 1000;
        let typingSent = false;
        let mediaRecorder;
        let recordedStream;
        let recordedChunks = [];
        let pendingAttachment;
        let previewObjectUrl;

        const showChatError = (message) => {
            if (!(chatError instanceof HTMLElement)) return;
            chatError.textContent = message;
            chatError.hidden = false;
        };

        const setPeerOnline = (online) => {
            if (chatStatus instanceof HTMLElement) {
                chatStatus.textContent = online ? "Online" : "Offline";
                chatStatus.classList.toggle("is-online", online);
            }
            chatApp.querySelectorAll("[data-presence-for]").forEach((indicator) => {
                if (
                    indicator instanceof HTMLElement &&
                    indicator.dataset.presenceFor === peerUsername
                ) {
                    indicator.classList.toggle("is-online", online);
                }
            });
        };

        const updateConversationPreview = (body, attachmentType = "", senderId) => {
            const activeChatItem = chatApp.querySelector(".chat-list-item.is-active");
            const preview = activeChatItem?.querySelector(".chat-list-preview");
            if (!preview) return;
            const previewText = body || {
                image: "📷 Rasm",
                video: "🎬 Video",
                audio: "🎙 Ovozli xabar",
                share: "📄 Post ulashildi",
            }[attachmentType] || "Xabar";
            preview.textContent = senderId === chatApp.dataset.currentUserId
                ? `Siz: ${previewText}`
                : previewText;
        };

        const createMessageActions = (message, content) => {
            if (!message.classList.contains("is-mine")) return;
            const actions = document.createElement("div");
            actions.className = "chat-message-actions";
            actions.dataset.messageActions = "";
            actions.innerHTML = `
                <button type="button" data-message-action="edit" aria-label="Xabarni tahrirlash" title="Tahrirlash">✎</button>
                <button type="button" data-message-action="delete" aria-label="Xabarni o‘chirish" title="O‘chirish">⌫</button>
            `;
            content.append(actions);
        };

        const appendChatMessage = (payload) => {
            if (!(messages instanceof HTMLElement)) return;
            const isDuplicate = [...messages.querySelectorAll("[data-message-id]")]
                .some((existing) => existing.dataset.messageId === payload.id);
            if (isDuplicate) return;
            const startNote = messages.querySelector("[data-chat-start-note]");
            startNote?.remove();

            const message = document.createElement("article");
            message.className = `chat-message${payload.sender === chatApp.dataset.currentUsername ? " is-mine" : ""}`;
            message.dataset.messageId = payload.id;

            const avatarWrap = document.createElement("span");
            avatarWrap.className = "chat-message-avatar";
            const avatar = document.createElement("img");
            avatar.src = payload.sender_avatar || chatApp.dataset.defaultAvatar;
            avatar.alt = "";
            avatarWrap.append(avatar);

            const content = document.createElement("div");
            content.className = "chat-message-content";
            if (payload.body) {
                const body = document.createElement("p");
                body.textContent = payload.body;
                content.append(body);
            }
            if (payload.shared_post) {
                const shared = payload.shared_post;
                const sharedCard = document.createElement("a");
                sharedCard.className = "chat-shared-post";
                sharedCard.href = shared.url || "#";
                sharedCard.target = "_blank";
                sharedCard.rel = "noopener";
                const sharedCopy = document.createElement("span");
                sharedCopy.className = "chat-shared-post-copy";
                const badge = document.createElement("span");
                badge.className = "chat-shared-post-badge";
                badge.textContent = "📄 Ulangan post";
                const title = document.createElement("strong");
                title.textContent = shared.title || shared.desc || "Post";
                const author = document.createElement("span");
                author.className = "chat-shared-post-author";
                author.textContent = `@${shared.author_username}`;
                sharedCopy.append(badge, title, author);
                if (shared.image_url) {
                    const sharedMedia = document.createElement("span");
                    sharedMedia.className = "chat-shared-post-media";
                    const img = document.createElement("img");
                    img.src = shared.image_url;
                    img.alt = "";
                    sharedMedia.append(img);
                    sharedCard.append(sharedMedia);
                }
                sharedCard.append(sharedCopy);
                content.append(sharedCard);
            }
            if (payload.media_url) {
                let media;
                if (payload.attachment_type === "image") {
                    media = document.createElement("img");
                    media.alt = "Yuborilgan rasm";
                    media.className = "chat-message-image";
                } else if (payload.attachment_type === "video") {
                    media = document.createElement("video");
                    media.controls = true;
                    media.playsInline = true;
                    media.preload = "metadata";
                    media.className = "chat-message-video";
                } else if (payload.attachment_type === "audio") {
                    media = document.createElement("audio");
                    media.controls = true;
                    media.preload = "metadata";
                    media.className = "chat-message-audio";
                }
                if (media) {
                    media.src = payload.media_url;
                    content.append(media);
                }
            }
            const time = document.createElement("time");
            time.dateTime = payload.created_at;
            time.textContent = new Intl.DateTimeFormat("uz-UZ", {
                hour: "2-digit",
                minute: "2-digit",
            }).format(new Date(payload.created_at));
            content.append(time);
            createMessageActions(message, content);
            message.append(avatarWrap, content);

            const typingIndicator = messages.querySelector("[data-chat-typing]");
            messages.insertBefore(message, typingIndicator || null);
            messages.scrollTop = messages.scrollHeight;

            const previewText = payload.body || (payload.shared_post
                ? "📄 Post ulashildi"
                : {
                    image: "📷 Rasm",
                    video: "🎬 Video",
                    audio: "🎙 Ovozli xabar",
                }[payload.attachment_type] || "Xabar");
            const activeChatItem = chatApp.querySelector(".chat-list-item.is-active");
            const preview = activeChatItem?.querySelector(".chat-list-preview");
            if (preview) {
                preview.textContent = payload.sender === chatApp.dataset.currentUsername
                    ? `Siz: ${previewText}`
                    : previewText;
            }
        };

        const uploadMedia = async (file, attachmentType) => {
            const formData = new FormData();
            formData.append("file", file);
            formData.append("attachment_type", attachmentType);
            const csrfToken = chatForm?.querySelector("[name=csrfmiddlewaretoken]")?.value;
            if (csrfToken) formData.append("csrfmiddlewaretoken", csrfToken);

            try {
                const response = await fetch(chatApp.dataset.uploadUrl, {
                    method: "POST",
                    body: formData,
                    headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
                    credentials: "same-origin",
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || "Faylni yuborib bo‘lmadi.");
                }
                if (socket?.readyState !== WebSocket.OPEN) {
                    appendChatMessage(payload);
                }
                if (chatError instanceof HTMLElement) chatError.hidden = true;
                return true;
            } catch (error) {
                showChatError(
                    error instanceof Error ? error.message : "Faylni yuborib bo‘lmadi.",
                );
                return false;
            }
        };

        const clearPendingAttachment = () => {
            pendingAttachment = undefined;
            if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
            previewObjectUrl = undefined;
            if (attachmentPreview instanceof HTMLElement) attachmentPreview.hidden = true;
            attachmentPreviewMedia?.replaceChildren();
            if (attachmentPreviewName instanceof HTMLElement) attachmentPreviewName.textContent = "";
            if (attachmentPreviewSize instanceof HTMLElement) attachmentPreviewSize.textContent = "";
            if (chatFileInput instanceof HTMLInputElement) chatFileInput.value = "";
            const sendButton = chatForm?.querySelector("[data-chat-send]");
            if (sendButton instanceof HTMLButtonElement) {
                sendButton.innerHTML = '<span>Yuborish</span><span aria-hidden="true">➤</span>';
            }
        };

        const showAttachmentPreview = (file, attachmentType) => {
            clearPendingAttachment();
            pendingAttachment = { file, attachmentType };
            previewObjectUrl = URL.createObjectURL(file);
            if (attachmentPreviewMedia instanceof HTMLElement) {
                const preview = document.createElement(
                    attachmentType === "image" ? "img" : "video",
                );
                preview.src = previewObjectUrl;
                preview.alt = attachmentType === "image" ? "Tanlangan rasm" : "Tanlangan video";
                if (preview instanceof HTMLVideoElement) {
                    preview.muted = true;
                    preview.playsInline = true;
                }
                attachmentPreviewMedia.replaceChildren(preview);
            }
            if (attachmentPreviewName instanceof HTMLElement) {
                attachmentPreviewName.textContent = file.name;
            }
            if (attachmentPreviewSize instanceof HTMLElement) {
                attachmentPreviewSize.textContent = `${(file.size / (1024 * 1024)).toFixed(2)} MB`;
            }
            if (attachmentPreview instanceof HTMLElement) attachmentPreview.hidden = false;
            const sendButton = chatForm?.querySelector("[data-chat-send]");
            if (sendButton instanceof HTMLButtonElement) {
                sendButton.innerHTML = '<span>Yuborish</span><span aria-hidden="true">➤</span>';
            }
            if (chatError instanceof HTMLElement) chatError.hidden = true;
        };

        const sendMessageAction = async (messageId, action, body = "") => {
            const csrfToken = chatForm?.querySelector("[name=csrfmiddlewaretoken]")?.value;
            const formData = new FormData();
            formData.append("action", action);
            if (action === "edit") formData.append("body", body);
            try {
                const actionUrl = chatApp.dataset.messageActionUrlTemplate
                    .replace("00000000-0000-0000-0000-000000000000", messageId);
                const response = await fetch(actionUrl, {
                    method: "POST",
                    body: formData,
                    headers: csrfToken ? { "X-CSRFToken": csrfToken } : {},
                    credentials: "same-origin",
                });
                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || "Xabar amalini bajarib bo‘lmadi.");
                }
                if (payload.type === "message_updated") updateMessage(payload);
                if (payload.type === "message_deleted") removeMessage(payload.id);
                if (chatError instanceof HTMLElement) chatError.hidden = true;
            } catch (error) {
                showChatError(
                    error instanceof Error ? error.message : "Xabar amalini bajarib bo‘lmadi.",
                );
            }
        };

        const updateMessage = (payload) => {
            const message = messages?.querySelector(`[data-message-id="${payload.id}"]`);
            if (!(message instanceof HTMLElement)) return;
            let body = message.querySelector(".chat-message-content > p");
            if (!(body instanceof HTMLParagraphElement)) {
                body = document.createElement("p");
                const time = message.querySelector(".chat-message-content > time");
                message.querySelector(".chat-message-content")?.insertBefore(body, time || null);
            }
            body.textContent = payload.body;
            body.hidden = false;
            const editor = message.querySelector("[data-message-edit-form]");
            editor?.remove();
            updateConversationPreview(payload.body, "", payload.sender_id);
        };

        const removeMessage = (messageId) => {
            const message = messages?.querySelector(`[data-message-id="${messageId}"]`);
            if (!message) return;
            message?.remove();
            if (messages instanceof HTMLElement && !messages.querySelector("[data-message-id]")) {
                const note = document.createElement("div");
                note.className = "chat-start-note";
                note.dataset.chatStartNote = "";
                note.innerHTML = "<span>✦</span><p>Suhbatni davom ettiring.</p>";
                const typingIndicator = messages.querySelector("[data-chat-typing]");
                messages.insertBefore(note, typingIndicator || null);
            }
            updateConversationPreview("Xabar o‘chirildi", "", "");
        };

        const sendTyping = (isTyping) => {
            if (socket?.readyState !== WebSocket.OPEN) return;
            socket.send(JSON.stringify({ type: "typing", is_typing: isTyping }));
        };

        const connectChat = () => {
            if (!window.WebSocket) {
                showChatError("Brauzeringiz WebSocket’ni qo‘llab-quvvatlamaydi.");
                return;
            }

            const socketUrl = new URL(chatApp.dataset.socketUrl, window.location.href);
            socketUrl.protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            socket = new WebSocket(socketUrl);

            socket.addEventListener("open", () => {
                reconnectDelay = 1000;
                if (chatStatus instanceof HTMLElement) {
                    chatStatus.textContent = "Ulandi";
                    chatStatus.classList.remove("is-online");
                }
                if (typingSent) sendTyping(true);
                heartbeatTimer = window.setInterval(() => {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({ type: "heartbeat" }));
                    }
                }, 25000);
            });

            socket.addEventListener("message", (event) => {
                let payload;
                try {
                    payload = JSON.parse(event.data);
                } catch {
                    showChatError("Chat serveridan noto‘g‘ri javob keldi.");
                    return;
                }

                if (payload.type === "message") {
                    appendChatMessage(payload);
                } else if (payload.type === "message_updated") {
                    updateMessage(payload);
                } else if (payload.type === "message_deleted") {
                    removeMessage(payload.id);
                } else if (payload.type === "presence" && payload.username === peerUsername) {
                    setPeerOnline(payload.online);
                } else if (payload.type === "typing" && payload.username === peerUsername) {
                    if (chatTyping instanceof HTMLElement) {
                        chatTyping.hidden = !payload.is_typing;
                        if (payload.is_typing && messages instanceof HTMLElement) {
                            messages.scrollTop = messages.scrollHeight;
                        }
                    }
                } else if (payload.type === "error") {
                    showChatError(payload.message);
                }
            });

            socket.addEventListener("close", (event) => {
                window.clearInterval(heartbeatTimer);
                setPeerOnline(false);
                if (event.code === 4401 || event.code === 4403) {
                    showChatError("Bu suhbatga kirish uchun ruxsat yo‘q.");
                    return;
                }
                if (chatStatus instanceof HTMLElement) {
                    chatStatus.textContent = "Qayta ulanmoqda...";
                }
                reconnectTimer = window.setTimeout(() => {
                    reconnectDelay = Math.min(reconnectDelay * 2, 15000);
                    connectChat();
                }, reconnectDelay);
            });

            socket.addEventListener("error", () => {
                if (chatStatus instanceof HTMLElement) {
                    chatStatus.textContent = "Ulanishda xatolik";
                }
            });
        };

        connectChat();

        if (chatFileInput instanceof HTMLInputElement) {
            chatFileButton?.addEventListener("click", () => chatFileInput.click());
            chatFileInput.addEventListener("change", () => {
                const file = chatFileInput.files?.[0];
                if (!file) return;
                const attachmentType = file.type.startsWith("image/")
                    ? "image"
                    : file.type.startsWith("video/") ? "video" : "";
                if (!attachmentType) {
                    showChatError("Faqat rasm yoki video yuborishingiz mumkin.");
                } else {
                    showAttachmentPreview(file, attachmentType);
                }
            });
        }

        attachmentCancel?.addEventListener("click", clearPendingAttachment);

        messages?.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) return;
            const actionButton = target.closest("[data-message-action]");
            if (!(actionButton instanceof HTMLButtonElement)) return;
            const message = actionButton.closest("[data-message-id]");
            if (!(message instanceof HTMLElement)) return;
            const messageId = message.dataset.messageId;
            if (!messageId) return;

            if (actionButton.dataset.messageAction === "delete") {
                void sendMessageAction(messageId, "delete");
                return;
            }
            if (actionButton.dataset.messageAction !== "edit") return;

            const content = message.querySelector(".chat-message-content");
            if (!(content instanceof HTMLElement) || content.querySelector("[data-message-edit-form]")) {
                return;
            }
            const body = content.querySelector(":scope > p");
            const editForm = document.createElement("form");
            editForm.className = "chat-message-edit-form";
            editForm.dataset.messageEditForm = "";
            const textarea = document.createElement("textarea");
            textarea.maxLength = 2000;
            textarea.required = true;
            textarea.value = body?.textContent || "";
            textarea.setAttribute("aria-label", "Xabarni tahrirlash");
            const buttons = document.createElement("div");
            buttons.className = "chat-message-edit-actions";
            const saveButton = document.createElement("button");
            saveButton.type = "submit";
            saveButton.textContent = "Saqlash";
            const cancelButton = document.createElement("button");
            cancelButton.type = "button";
            cancelButton.dataset.messageEditCancel = "";
            cancelButton.textContent = "Bekor qilish";
            buttons.append(saveButton, cancelButton);
            editForm.append(textarea, buttons);
            if (body) body.hidden = true;
            content.insertBefore(editForm, content.querySelector("time"));
            textarea.focus();
            textarea.setSelectionRange(textarea.value.length, textarea.value.length);
        });

        messages?.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof Element)) return;
            const cancelButton = target.closest("[data-message-edit-cancel]");
            if (!cancelButton) return;
            const editForm = cancelButton.closest("[data-message-edit-form]");
            const message = cancelButton.closest("[data-message-id]");
            editForm?.remove();
            message?.querySelector(".chat-message-content > p")?.removeAttribute("hidden");
        });

        messages?.addEventListener("submit", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLFormElement) || !target.matches("[data-message-edit-form]")) {
                return;
            }
            event.preventDefault();
            const message = target.closest("[data-message-id]");
            const textarea = target.querySelector("textarea");
            const messageId = message?.getAttribute("data-message-id");
            const body = textarea?.value.trim();
            if (!messageId || !body) return;
            void sendMessageAction(messageId, "edit", body);
        });

        if (
            emojiToggle instanceof HTMLButtonElement &&
            emojiPicker instanceof HTMLElement
        ) {
            emojiToggle.addEventListener("click", () => {
                emojiPicker.hidden = !emojiPicker.hidden;
                emojiToggle.setAttribute("aria-expanded", String(!emojiPicker.hidden));
            });
            emojiPicker.querySelectorAll("[data-emoji]").forEach((button) => {
                button.addEventListener("click", () => {
                    if (!(chatInput instanceof HTMLInputElement)) return;
                    const emoji = button.getAttribute("data-emoji");
                    if (!emoji) return;
                    const start = chatInput.selectionStart ?? chatInput.value.length;
                    const end = chatInput.selectionEnd ?? start;
                    chatInput.setRangeText(emoji, start, end, "end");
                    chatInput.focus();
                    chatInput.dispatchEvent(new Event("input", { bubbles: true }));
                    emojiPicker.hidden = true;
                    emojiToggle.setAttribute("aria-expanded", "false");
                });
            });
        }

        if (audioRecordButton instanceof HTMLButtonElement) {
            audioRecordButton.addEventListener("click", async () => {
                if (mediaRecorder?.state === "recording") {
                    mediaRecorder.stop();
                    return;
                }
                if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
                    showChatError("Brauzeringiz ovoz yozishni qo‘llab-quvvatlamaydi.");
                    return;
                }
                try {
                    recordedStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    const supportedMime = [
                        "audio/webm;codecs=opus",
                        "audio/webm",
                        "audio/mp4",
                    ].find((mime) => MediaRecorder.isTypeSupported(mime));
                    mediaRecorder = new MediaRecorder(
                        recordedStream,
                        supportedMime ? { mimeType: supportedMime } : undefined,
                    );
                    recordedChunks = [];
                    mediaRecorder.addEventListener("dataavailable", (event) => {
                        if (event.data.size) recordedChunks.push(event.data);
                    });
                    mediaRecorder.addEventListener("stop", () => {
                        recordedStream?.getTracks().forEach((track) => track.stop());
                        recordedStream = undefined;
                        audioRecordButton.classList.remove("is-recording");
                        audioRecordButton.setAttribute("aria-label", "Ovozli xabar yozish");
                        audioRecordButton.title = "Ovozli xabar yozish";
                        if (recordStatus instanceof HTMLElement) recordStatus.hidden = true;
                        const mimeType = (mediaRecorder.mimeType || "audio/webm").split(";")[0];
                        const extension = mimeType.includes("mp4") ? "m4a" : "webm";
                        const recording = new File(
                            recordedChunks,
                            `voice-message.${extension}`,
                            { type: mimeType },
                        );
                        if (recording.size) void uploadMedia(recording, "audio");
                        else showChatError("Ovoz yozilmadi, qayta urinib ko‘ring.");
                    }, { once: true });
                    mediaRecorder.start();
                    audioRecordButton.classList.add("is-recording");
                    audioRecordButton.setAttribute("aria-label", "Yozishni to‘xtatish");
                    audioRecordButton.title = "Yozishni to‘xtatish";
                    if (recordStatus instanceof HTMLElement) {
                        recordStatus.textContent = "Yozilmoqda…";
                        recordStatus.hidden = false;
                    }
                    if (chatError instanceof HTMLElement) chatError.hidden = true;
                } catch {
                    recordedStream?.getTracks().forEach((track) => track.stop());
                    recordedStream = undefined;
                    showChatError("Mikrofonga ruxsat bering va qayta urinib ko‘ring.");
                }
            });
        }

        if (chatForm instanceof HTMLFormElement && chatInput instanceof HTMLInputElement) {
            chatForm.addEventListener("submit", async (event) => {
                event.preventDefault();
                if (pendingAttachment) {
                    const { file, attachmentType } = pendingAttachment;
                    if (await uploadMedia(file, attachmentType)) {
                        clearPendingAttachment();
                    }
                    return;
                }
                const body = chatInput.value.trim();
                if (!body) return;
                if (socket?.readyState !== WebSocket.OPEN) {
                    showChatError("Xabar yuborish uchun chat serveriga ulaning.");
                    return;
                }
                socket.send(JSON.stringify({ type: "message", body }));
                chatInput.value = "";
                if (typingSent) {
                    sendTyping(false);
                    typingSent = false;
                }
                window.clearTimeout(typingTimer);
                if (chatError instanceof HTMLElement) chatError.hidden = true;
            });

            chatInput.addEventListener("input", () => {
                if (!typingSent) {
                    sendTyping(true);
                    typingSent = true;
                }
                window.clearTimeout(typingTimer);
                typingTimer = window.setTimeout(() => {
                    sendTyping(false);
                    typingSent = false;
                }, 900);
            });
        }

        window.addEventListener("beforeunload", () => {
            window.clearTimeout(reconnectTimer);
            window.clearInterval(heartbeatTimer);
            window.clearTimeout(typingTimer);
            if (mediaRecorder?.state === "recording") mediaRecorder.stop();
            recordedStream?.getTracks().forEach((track) => track.stop());
            if (previewObjectUrl) URL.revokeObjectURL(previewObjectUrl);
            socket?.close();
        });
    }

    document.querySelectorAll('.auth-form input[type="password"]').forEach((input) => {
        const toggle = document.createElement("button");
        toggle.className = "password-toggle";
        toggle.type = "button";
        toggle.textContent = "Ko‘rsatish";
        toggle.setAttribute("aria-label", "Parolni ko‘rsatish");

        toggle.addEventListener("click", () => {
            const showing = input.type === "password";
            input.type = showing ? "text" : "password";
            toggle.textContent = showing ? "Yashirish" : "Ko‘rsatish";
            toggle.setAttribute("aria-label", showing ? "Parolni yashirish" : "Parolni ko‘rsatish");
        });

        input.insertAdjacentElement("afterend", toggle);
    });

    document.querySelectorAll('.auth-form input[type="file"]').forEach((input) => {
        input.addEventListener("change", () => {
            const fileName = input.files?.[0]?.name;
            const label = input.labels?.[0];

            if (fileName && label) {
                const originalText = label.dataset.originalText || label.textContent;
                label.dataset.originalText = originalText;
                label.textContent = `${originalText}: ${fileName}`;
            }
        });
    });

    document.addEventListener("submit", async (event) => {
        const form = event.target;
        if (!(form instanceof HTMLFormElement)) return;

        const isPostAction = form.matches("[data-ajax-post-action]");
        const isFollowAction = form.matches("[data-ajax-follow]");
        if (!isPostAction && !isFollowAction) return;

        event.preventDefault();
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) submitButton.disabled = true;

        try {
            const csrfToken = form.querySelector('[name="csrfmiddlewaretoken"]')?.value;
            const response = await fetch(form.action, {
                method: "POST",
                body: new FormData(form),
                headers: {
                    "X-Requested-With": "XMLHttpRequest",
                    ...(csrfToken ? { "X-CSRFToken": csrfToken } : {}),
                },
                credentials: "same-origin",
            });
            const contentType = response.headers.get("content-type") || "";
            if (!contentType.includes("application/json")) {
                throw new Error("Server JSON javob qaytarmadi.");
            }

            const payload = await response.json();
            if (!response.ok) {
                const firstError = Object.values(payload.errors || {}).flat()[0];
                throw new Error(firstError?.message || "Amalni bajarib bo‘lmadi.");
            }

            if (isPostAction) {
                const card = form.closest("[data-post-card]");
                if (!card || typeof payload.html !== "string") {
                    throw new Error("Post yangilangan ko‘rinishini yuklab bo‘lmadi.");
                }
                const commentsWereOpen = Boolean(card.querySelector(".comments-panel")?.open);
                const template = document.createElement("template");
                template.innerHTML = payload.html.trim();
                const updatedCard = template.content.firstElementChild;
                if (!(updatedCard instanceof HTMLElement)) {
                    throw new Error("Post yangilangan ko‘rinishi noto‘g‘ri.");
                }
                const updatedComments = updatedCard.querySelector(".comments-panel");
                if (updatedComments && (commentsWereOpen || form.classList.contains("comment-form"))) {
                    updatedComments.open = true;
                }
                card.replaceWith(updatedCard);
            } else {
                const followButton = form.querySelector("[data-follow-button]");
                if (!followButton) throw new Error("Obuna tugmasini yangilab bo‘lmadi.");
                followButton.textContent = payload.is_following
                    ? "Obunani bekor qilish"
                    : "Obuna bo‘lish";
                followButton.classList.toggle("button-primary", !payload.is_following);
                followButton.classList.toggle("button-secondary", payload.is_following);
                const followersCount = document.querySelector("[data-followers-count]");
                const followingCount = document.querySelector("[data-following-count]");
                if (followersCount) followersCount.textContent = payload.followers_count;
                if (followingCount) followingCount.textContent = payload.following_count;
            }
        } catch (error) {
            let feedback = form.querySelector(".interaction-feedback");
            if (!feedback) {
                feedback = document.createElement("p");
                feedback.className = "interaction-feedback";
                feedback.setAttribute("role", "alert");
                form.insertAdjacentElement("afterend", feedback);
            }
            feedback.textContent = error instanceof Error
                ? error.message
                : "Amalni bajarishda xatolik yuz berdi.";
        } finally {
            if (submitButton?.isConnected) submitButton.disabled = false;
        }
    });
});
