(function () {
    const GUIDELINES_KEY = 'community_guidelines_accepted';
    const CATEGORY_LABELS = {
        help_me_reply: 'Help Me Reply',
        dating_advice: 'Dating Advice',
        rate_my_profile: 'Rate My Profile',
        wins: 'Wins',
    };

    function escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function safeDisplayName(raw) {
        const value = String(raw || '').trim();
        if (!value) return 'Unknown';
        const atIndex = value.indexOf('@');
        if (atIndex > 0) return value.slice(0, atIndex);
        return value;
    }

    function timeAgo(iso) {
        const ts = new Date(iso || '').getTime();
        if (!Number.isFinite(ts)) return 'just now';
        const diff = Math.max(0, Math.floor((Date.now() - ts) / 1000));
        if (diff < 60) return 'just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
        return `${Math.floor(diff / 604800)}w ago`;
    }

    function getCookie(name) {
        const cookies = (document.cookie || '').split(';');
        for (const part of cookies) {
            const value = part.trim();
            if (value.startsWith(`${name}=`)) {
                return decodeURIComponent(value.slice(name.length + 1));
            }
        }
        return '';
    }

    function getCsrfToken(root) {
        return (
            root?.querySelector('input[name=csrfmiddlewaretoken]')?.value ||
            document.querySelector('input[name=csrfmiddlewaretoken]')?.value ||
            getCookie('csrftoken')
        );
    }

    function buildLoginUrl(root) {
        const base = root?.dataset?.loginUrl || '/accounts/login/';
        const sep = base.includes('?') ? '&' : '?';
        const next = encodeURIComponent(window.location.pathname + window.location.search);
        return `${base}${sep}next=${next}`;
    }

    function redirectToLogin(root) {
        window.location.href = buildLoginUrl(root);
    }

    function showToast(message, isError = false) {
        const toast = document.querySelector('[data-community-toast]');
        if (!toast) return;
        toast.textContent = String(message || 'Done.');
        toast.classList.remove('community-hidden');
        toast.style.background = isError ? 'rgba(127, 29, 29, 0.86)' : 'var(--matte-surface)';
        toast.style.color = isError ? '#fecaca' : 'var(--matte-text)';
        toast.style.borderColor = isError ? 'rgba(248, 113, 113, 0.35)' : 'var(--matte-border-soft)';
        window.clearTimeout(showToast._timer);
        showToast._timer = window.setTimeout(() => toast.classList.add('community-hidden'), 2800);
    }

    function ensureGuidelinesAccepted() {
        try {
            if (localStorage.getItem(GUIDELINES_KEY) === '1') return true;
        } catch (_) {
            // Continue to prompt.
        }
        const ok = window.confirm(
            'Community Guidelines:\n\n' +
            '- Be respectful and constructive\n' +
            '- No spam, harassment, or hate speech\n' +
            '- Remove private info before posting\n\n' +
            'Do you agree?'
        );
        if (ok) {
            try {
                localStorage.setItem(GUIDELINES_KEY, '1');
            } catch (_) {
                // Ignore storage errors.
            }
        }
        return ok;
    }

    async function parsePayload(response) {
        const text = await response.text();
        if (!text) return {};
        try {
            return JSON.parse(text);
        } catch (_) {
            return { error: text };
        }
    }

    async function apiRequest(root, url, options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        const headers = new Headers(options.headers || {});
        const body = options.body;

        if (!['GET', 'HEAD', 'OPTIONS'].includes(method)) {
            const csrf = getCsrfToken(root);
            if (csrf) headers.set('X-CSRFToken', csrf);
        }
        if (body && !(body instanceof FormData) && !headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
        }

        const response = await fetch(url, {
            method,
            headers,
            body,
            credentials: 'same-origin',
        });

        if (response.status === 401) {
            redirectToLogin(root);
            return { unauthorized: true, data: null };
        }

        const data = await parsePayload(response);
        if (!response.ok) {
            const error = new Error(data.error || data.detail || data.message || `Request failed (${response.status})`);
            error.status = response.status;
            error.data = data;
            throw error;
        }
        return { unauthorized: false, data };
    }

    function closeAllMoreMenus() {
        document.querySelectorAll('.community-more-menu').forEach((menu) => menu.classList.add('community-hidden'));
    }

    document.addEventListener('click', (event) => {
        if (!event.target.closest('.community-more-wrap')) {
            closeAllMoreMenus();
        }
    });

    const reportFlow = {
        modal: null,
        pending: null,
        init() {
            this.modal = document.querySelector('[data-community-report-modal]');
            if (!this.modal) return;
            this.modal.addEventListener('click', (event) => {
                if (event.target === this.modal || event.target.hasAttribute('data-report-cancel')) {
                    this.close();
                }
            });
            this.modal.querySelectorAll('[data-report-reason]').forEach((button) => {
                button.addEventListener('click', async () => {
                    if (!this.pending) {
                        this.close();
                        return;
                    }
                    const reason = button.getAttribute('data-report-reason');
                    const detail = (window.prompt('Optional details (leave empty to skip):', '') || '').trim().slice(0, 500);
                    try {
                        await this.pending(reason, detail);
                        showToast('Report submitted.');
                    } catch (error) {
                        showToast(error.message || 'Could not submit report.', true);
                    } finally {
                        this.close();
                    }
                });
            });
        },
        open(handler) {
            if (!this.modal) return;
            this.pending = handler;
            this.modal.classList.remove('community-hidden');
        },
        close() {
            if (!this.modal) return;
            this.pending = null;
            this.modal.classList.add('community-hidden');
        },
    };

    function featuredFirst(posts) {
        const seen = new Set();
        const featured = [];
        const regular = [];
        for (const post of posts || []) {
            if (!post || seen.has(post.id)) continue;
            seen.add(post.id);
            if (post.is_featured) featured.push(post);
            else regular.push(post);
        }
        return [...featured, ...regular];
    }

    function badgesHtml(post) {
        const tags = [];
        if (post.author?.is_pro && !post.is_anonymous) tags.push('<span class="community-badge community-badge-pro">PRO</span>');
        if (post.is_featured) tags.push('<span class="community-badge community-badge-featured">Featured</span>');
        if (post.is_trending) tags.push('<span class="community-badge community-badge-trending">Trending</span>');
        else if (post.is_new) tags.push('<span class="community-badge community-badge-new">New</span>');
        return tags.join('');
    }

    function pollHtml(post) {
        if (!post.poll) return '';
        const sendActive = post.poll.user_vote === 'send_it' ? 'is-active' : '';
        const dontActive = post.poll.user_vote === 'dont_send_it' ? 'is-active' : '';
        return [
            '<div class="community-poll">',
            '  <p class="community-poll-head">Quick Poll</p>',
            '  <div class="community-poll-buttons">',
            `    <button type="button" class="community-poll-btn ${sendActive}" data-action="vote-poll" data-post-id="${post.id}" data-choice="send_it">Send It (${post.poll.send_it_count})</button>`,
            `    <button type="button" class="community-poll-btn ${dontActive}" data-action="vote-poll" data-post-id="${post.id}" data-choice="dont_send_it">Don't Send It (${post.poll.dont_send_it_count})</button>`,
            '  </div>',
            '</div>',
        ].join('');
    }

    function postMenuHtml(post, currentUsername, currentUserId, menuId) {
        const authorId = Number(post.author?.id || 0);
        const isOwner = (currentUserId && authorId === currentUserId) || (currentUsername && post.author?.username === currentUsername);
        const items = [];
        if (isOwner) {
            items.push(`<button type="button" class="community-more-item is-danger" data-action="delete-post" data-post-id="${post.id}">Delete Post</button>`);
        } else {
            items.push(`<button type="button" class="community-more-item" data-action="report-content" data-content-type="post" data-content-id="${post.id}">Report Post</button>`);
            if (post.author?.id) {
                items.push(`<button type="button" class="community-more-item is-danger" data-action="block-user" data-user-id="${post.author.id}">Block User</button>`);
            }
        }
        return [
            '<div class="community-more-wrap">',
            `  <button type="button" class="community-more-btn" data-action="toggle-menu" data-menu-id="${menuId}" aria-label="Post actions"><i class="fa fa-ellipsis-h"></i></button>`,
            `  <div id="${menuId}" class="community-more-menu community-hidden">${items.join('')}</div>`,
            '</div>',
        ].join('');
    }
    function postHtml(post, currentUsername, currentUserId, isDetail = false) {
        const authorName = post.is_anonymous ? 'Anonymous' : safeDisplayName(post.author?.username);
        const upClass = post.user_vote === 'up' ? 'is-up' : '';
        const downClass = post.user_vote === 'down' ? 'is-down' : '';
        const body = escapeHtml(isDetail ? (post.body || post.body_preview || '') : (post.body_preview || ''));
        const image = post.image_url
            ? `<div class="community-card-image-wrap"><img class="community-card-image" src="${escapeHtml(post.image_url)}" alt="Community post image"></div>`
            : '';
        return [
            `<article class="community-card ${post.is_featured ? 'community-card-featured' : ''}" data-post-id="${post.id}">`,
            '  <div class="community-card-head">',
            '    <div class="min-w-0">',
            '      <p class="community-card-meta">',
            `        <strong>${escapeHtml(authorName)}</strong>`,
            `        <span>· ${timeAgo(post.published_at || post.created_at)} · ${escapeHtml(CATEGORY_LABELS[post.category] || post.category || 'General')}</span>`,
            `        <span class="community-card-badges">${badgesHtml(post)}</span>`,
            '      </p>',
            isDetail
                ? `      <h1 class="community-card-title matte-headline font-semibold">${escapeHtml(post.title || 'Untitled')}</h1>`
                : `      <h2 class="community-card-title matte-headline font-semibold"><a href="/community/posts/${post.id}/">${escapeHtml(post.title || 'Untitled')}</a></h2>`,
            `      <p class="community-card-body">${body}</p>`,
            pollHtml(post),
            image,
            '    </div>',
            postMenuHtml(post, currentUsername, currentUserId, `community-post-menu-${isDetail ? 'detail' : 'feed'}-${post.id}`),
            '  </div>',
            '  <div class="community-card-footer">',
            '    <div class="community-vote-group">',
            `      <button type="button" class="community-icon-btn ${upClass}" data-action="vote-post" data-post-id="${post.id}" data-vote="up"><i class="fa fa-arrow-up"></i></button>`,
            `      <span class="community-score">${Number(post.vote_score || 0)}</span>`,
            `      <button type="button" class="community-icon-btn ${downClass}" data-action="vote-post" data-post-id="${post.id}" data-vote="down"><i class="fa fa-arrow-down"></i></button>`,
            '    </div>',
            isDetail
                ? `    <span class="community-count"><i class="fa fa-comments mr-1"></i>${Number(post.comment_count || 0)} comments</span>`
                : `    <a class="community-link-inline" href="/community/posts/${post.id}/"><i class="fa fa-comments mr-1"></i>${Number(post.comment_count || 0)} comments</a>`,
            '  </div>',
            '</article>',
        ].join('');
    }

    function initFeedPage(root) {
        const state = {
            root,
            postsBaseUrl: root.dataset.postsUrl || '/api/community/posts/',
            currentUserId: Number(root.dataset.currentUserId || 0),
            currentUsername: root.dataset.currentUsername || '',
            category: '',
            sort: 'hot',
            page: 1,
            hasMore: false,
            posts: [],
            blockedUserIds: new Set(),
            busy: false,
            list: root.querySelector('#communityFeedList'),
            loading: root.querySelector('#communityFeedLoading'),
            error: root.querySelector('#communityFeedError'),
            empty: root.querySelector('#communityFeedEmpty'),
            sortSelect: root.querySelector('#communitySort'),
            chips: Array.from(root.querySelectorAll('[data-community-category]')),
            loadWrap: root.querySelector('#communityFeedLoadMoreWrap'),
            loadBtn: root.querySelector('#communityFeedLoadMore'),
        };

        function render() {
            const visible = state.posts.filter((post) => {
                const id = Number(post.author?.id || 0);
                return !id || !state.blockedUserIds.has(id);
            });
            state.list.innerHTML = visible.map((post) => postHtml(post, state.currentUsername, state.currentUserId, false)).join('');
            state.empty.classList.toggle('community-hidden', visible.length > 0);
            state.loadWrap.classList.toggle('community-hidden', !state.hasMore);
        }

        function setError(message) {
            if (!message) {
                state.error.classList.add('community-hidden');
                state.error.textContent = '';
                return;
            }
            state.error.textContent = message;
            state.error.classList.remove('community-hidden');
        }

        async function fetchPosts(refresh) {
            if (state.busy) return;
            state.busy = true;
            if (refresh) state.loading.classList.remove('community-hidden');
            state.loadBtn.disabled = true;
            state.loadBtn.textContent = refresh ? 'Load More' : 'Loading...';
            setError('');

            const nextPage = refresh ? 1 : state.page + 1;
            const params = new URLSearchParams({ page: String(nextPage), sort: state.sort });
            if (state.category) params.set('category', state.category);

            try {
                const { data, unauthorized } = await apiRequest(root, `${state.postsBaseUrl}?${params.toString()}`);
                if (unauthorized) return;
                const incoming = Array.isArray(data.posts) ? data.posts : [];
                state.page = Number(data.page || nextPage);
                state.sort = data.sort || state.sort;
                state.hasMore = Boolean(data.has_more);
                state.posts = refresh ? featuredFirst(incoming) : featuredFirst([...state.posts, ...incoming]);
                state.sortSelect.value = state.sort;
                render();
            } catch (error) {
                setError(error.message || 'Could not load posts.');
            } finally {
                state.busy = false;
                state.loading.classList.add('community-hidden');
                state.loadBtn.disabled = false;
                state.loadBtn.textContent = 'Load More';
            }
        }

        async function votePost(postId, voteType) {
            const { data, unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${postId}/vote/`, {
                method: 'POST',
                body: JSON.stringify({ vote_type: voteType }),
            });
            if (unauthorized) return;
            state.posts = state.posts.map((post) => {
                if (post.id !== postId) return post;
                return { ...post, vote_score: Number(data.vote_score), user_vote: data.user_vote ?? null };
            });
            render();
        }

        async function votePoll(postId, choice) {
            const { data, unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${postId}/poll/vote/`, {
                method: 'POST',
                body: JSON.stringify({ choice }),
            });
            if (unauthorized) return;
            state.posts = state.posts.map((post) => {
                if (post.id !== postId) return post;
                return {
                    ...post,
                    poll: {
                        ...(post.poll || {}),
                        send_it_count: Number(data.send_it_count || 0),
                        dont_send_it_count: Number(data.dont_send_it_count || 0),
                        user_vote: data.user_vote ?? null,
                    },
                };
            });
            render();
        }
        async function deletePost(postId) {
            if (!window.confirm('Delete this post? This cannot be undone.')) return;
            const { unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${postId}/`, { method: 'DELETE' });
            if (unauthorized) return;
            state.posts = state.posts.filter((post) => post.id !== postId);
            render();
            showToast('Post deleted.');
        }

        async function toggleBlockUser(userId) {
            if (!userId) return;
            if (!window.confirm('Block this user? You will stop seeing their posts and comments.')) return;
            const { data, unauthorized } = await apiRequest(root, `/api/community/users/${userId}/block/`, {
                method: 'POST',
                body: '{}',
            });
            if (unauthorized) return;
            if (data.blocked) {
                state.blockedUserIds.add(userId);
                render();
                showToast('User blocked.');
            } else {
                state.blockedUserIds.delete(userId);
                showToast('User unblocked. Refresh to reload their posts.');
            }
        }

        function openReport(contentType, contentId) {
            reportFlow.open((reason, detail) => {
                const url = contentType === 'comment'
                    ? `/api/community/comments/${contentId}/report/`
                    : `/api/community/posts/${contentId}/report/`;
                return apiRequest(root, url, {
                    method: 'POST',
                    body: JSON.stringify({ reason, detail }),
                });
            });
        }

        state.chips.forEach((chip) => {
            chip.addEventListener('click', () => {
                state.chips.forEach((node) => node.classList.remove('is-active'));
                chip.classList.add('is-active');
                state.category = chip.getAttribute('data-community-category') || '';
                fetchPosts(true);
            });
        });

        state.sortSelect.addEventListener('change', () => {
            state.sort = state.sortSelect.value || 'hot';
            fetchPosts(true);
        });

        state.loadBtn.addEventListener('click', () => fetchPosts(false));

        state.list.addEventListener('click', async (event) => {
            const button = event.target.closest('button');
            if (!button) return;
            const action = button.getAttribute('data-action');
            if (!action) return;
            event.preventDefault();
            try {
                if (action === 'toggle-menu') {
                    const menu = document.getElementById(button.getAttribute('data-menu-id'));
                    if (!menu) return;
                    const open = menu.classList.contains('community-hidden');
                    closeAllMoreMenus();
                    if (open) menu.classList.remove('community-hidden');
                    return;
                }
                if (action === 'vote-post') return votePost(Number(button.getAttribute('data-post-id')), button.getAttribute('data-vote'));
                if (action === 'vote-poll') return votePoll(Number(button.getAttribute('data-post-id')), button.getAttribute('data-choice'));
                if (action === 'delete-post') return deletePost(Number(button.getAttribute('data-post-id')));
                if (action === 'block-user') return toggleBlockUser(Number(button.getAttribute('data-user-id')));
                if (action === 'report-content') return openReport(button.getAttribute('data-content-type'), Number(button.getAttribute('data-content-id')));
            } catch (error) {
                showToast(error.message || 'Action failed.', true);
            }
        });

        fetchPosts(true);
    }

    function commentHtml(comment, post, currentUsername, currentUserId) {
        const commentAuthorId = Number(comment.author?.id || 0);
        const postAuthorId = Number(post.author?.id || 0);
        const isOwner = (currentUserId && commentAuthorId === currentUserId) || (currentUsername && currentUsername === comment.author?.username);
        const showOp = !post.is_anonymous && postAuthorId && commentAuthorId && postAuthorId === commentAuthorId;
        const likeIcon = comment.user_liked ? 'fa-heart' : 'fa-heart-o';
        const menuItems = isOwner
            ? [`<button type="button" class="community-more-item is-danger" data-action="delete-comment" data-comment-id="${comment.id}">Delete Comment</button>`]
            : [
                `<button type="button" class="community-more-item" data-action="report-content" data-content-type="comment" data-content-id="${comment.id}">Report Comment</button>`,
                comment.author?.id
                    ? `<button type="button" class="community-more-item is-danger" data-action="block-user" data-user-id="${comment.author.id}">Block User</button>`
                    : '',
            ];
        return [
            `<article class="community-comment-item" data-comment-id="${comment.id}">`,
            '  <div class="community-comment-meta">',
            `    <span><strong>${escapeHtml(safeDisplayName(comment.author?.username))}</strong>`,
            comment.author?.is_pro ? ' <span class="community-badge community-badge-pro">PRO</span>' : '',
            showOp ? ' <span class="community-badge community-badge-trending">OP</span>' : '',
            ` · ${timeAgo(comment.created_at)}</span>`,
            '    <span class="community-more-wrap">',
            `      <button type="button" class="community-more-btn" data-action="toggle-menu" data-menu-id="community-comment-menu-${comment.id}"><i class="fa fa-ellipsis-h"></i></button>`,
            `      <span id="community-comment-menu-${comment.id}" class="community-more-menu community-hidden">${menuItems.join('')}</span>`,
            '    </span>',
            '  </div>',
            `  <p class="community-comment-body">${escapeHtml(comment.body || '')}</p>`,
            '  <div class="community-comment-actions">',
            `    <button type="button" class="community-icon-btn" data-action="like-comment" data-comment-id="${comment.id}"><i class="fa ${likeIcon}"></i></button>`,
            `    <span class="community-count">${Number(comment.like_count || 0)}</span>`,
            '  </div>',
            '</article>',
        ].join('');
    }
    function initDetailPage(root) {
        const state = {
            root,
            postsBaseUrl: root.dataset.postsUrl || '/api/community/posts/',
            currentUserId: Number(root.dataset.currentUserId || 0),
            currentUsername: root.dataset.currentUsername || '',
            postId: Number(root.dataset.postId || 0),
            post: null,
            loading: root.querySelector('#communityDetailLoading'),
            error: root.querySelector('#communityDetailError'),
            postEl: root.querySelector('#communityDetailPost'),
            panel: root.querySelector('#communityCommentsPanel'),
            list: root.querySelector('#communityCommentsList'),
            empty: root.querySelector('#communityCommentsEmpty'),
            count: root.querySelector('#communityCommentsCount'),
            form: root.querySelector('#communityCommentForm'),
            commentBody: root.querySelector('#communityCommentBody'),
            commentSubmit: root.querySelector('#communityCommentSubmit'),
        };

        function render() {
            if (!state.post) return;
            state.postEl.innerHTML = postHtml(state.post, state.currentUsername, state.currentUserId, true);
            state.postEl.classList.remove('community-hidden');
            state.panel.classList.remove('community-hidden');
            const comments = state.post.comments || [];
            state.count.textContent = String(comments.length);
            state.empty.classList.toggle('community-hidden', comments.length > 0);
            state.list.innerHTML = comments.map((comment) => commentHtml(comment, state.post, state.currentUsername, state.currentUserId)).join('');
        }

        function setError(message) {
            state.error.textContent = message;
            state.error.classList.remove('community-hidden');
        }

        async function loadPost() {
            if (!state.postId) return setError('Invalid post id.');
            try {
                const { data } = await apiRequest(root, `${state.postsBaseUrl}${state.postId}/`);
                state.post = data;
                render();
            } catch (error) {
                setError(error.message || 'Could not load this post.');
            } finally {
                state.loading.classList.add('community-hidden');
            }
        }

        function updatePost(updater) {
            if (!state.post) return;
            state.post = updater(state.post);
            render();
        }

        async function votePost(voteType) {
            const { data, unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${state.post.id}/vote/`, {
                method: 'POST',
                body: JSON.stringify({ vote_type: voteType }),
            });
            if (unauthorized) return;
            updatePost((post) => ({ ...post, vote_score: Number(data.vote_score), user_vote: data.user_vote ?? null }));
        }

        async function votePoll(choice) {
            const { data, unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${state.post.id}/poll/vote/`, {
                method: 'POST',
                body: JSON.stringify({ choice }),
            });
            if (unauthorized) return;
            updatePost((post) => ({
                ...post,
                poll: {
                    ...(post.poll || {}),
                    send_it_count: Number(data.send_it_count || 0),
                    dont_send_it_count: Number(data.dont_send_it_count || 0),
                    user_vote: data.user_vote ?? null,
                },
            }));
        }

        async function deletePost() {
            if (!window.confirm('Delete this post? This cannot be undone.')) return;
            const { unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${state.post.id}/`, { method: 'DELETE' });
            if (unauthorized) return;
            window.location.href = '/community/';
        }

        async function toggleBlockUser(userId) {
            if (!userId) return;
            if (!window.confirm('Block this user? You will stop seeing their posts and comments.')) return;
            const { data, unauthorized } = await apiRequest(root, `/api/community/users/${userId}/block/`, {
                method: 'POST',
                body: '{}',
            });
            if (unauthorized) return;
            if (data.blocked) {
                if (Number(state.post.author?.id || 0) === userId) {
                    showToast('User blocked. Returning to feed.');
                    return window.setTimeout(() => (window.location.href = '/community/'), 500);
                }
                updatePost((post) => {
                    const comments = (post.comments || []).filter((comment) => Number(comment.author?.id || 0) !== userId);
                    return { ...post, comments, comment_count: comments.length };
                });
                showToast('User blocked.');
            } else {
                showToast('User unblocked. Refresh to reload their content.');
            }
        }

        async function likeComment(commentId) {
            const { data, unauthorized } = await apiRequest(root, `/api/community/comments/${commentId}/like/`, {
                method: 'POST',
                body: '{}',
            });
            if (unauthorized) return;
            updatePost((post) => ({
                ...post,
                comments: (post.comments || []).map((comment) => {
                    if (comment.id !== commentId) return comment;
                    return { ...comment, user_liked: Boolean(data.liked), like_count: Number(data.like_count || 0) };
                }),
            }));
        }

        async function deleteComment(commentId) {
            if (!window.confirm('Delete this comment? This cannot be undone.')) return;
            const { unauthorized } = await apiRequest(root, `/api/community/comments/${commentId}/delete/`, { method: 'DELETE' });
            if (unauthorized) return;
            updatePost((post) => {
                const comments = (post.comments || []).filter((comment) => comment.id !== commentId);
                return { ...post, comments, comment_count: comments.length };
            });
            showToast('Comment deleted.');
        }

        function openReport(contentType, contentId) {
            reportFlow.open((reason, detail) => {
                const url = contentType === 'comment'
                    ? `/api/community/comments/${contentId}/report/`
                    : `/api/community/posts/${contentId}/report/`;
                return apiRequest(root, url, {
                    method: 'POST',
                    body: JSON.stringify({ reason, detail }),
                });
            });
        }

        state.postEl.addEventListener('click', async (event) => {
            const button = event.target.closest('button');
            if (!button) return;
            const action = button.getAttribute('data-action');
            if (!action) return;
            event.preventDefault();
            try {
                if (action === 'toggle-menu') {
                    const menu = document.getElementById(button.getAttribute('data-menu-id'));
                    if (!menu) return;
                    const open = menu.classList.contains('community-hidden');
                    closeAllMoreMenus();
                    if (open) menu.classList.remove('community-hidden');
                    return;
                }
                if (action === 'vote-post') return votePost(button.getAttribute('data-vote'));
                if (action === 'vote-poll') return votePoll(button.getAttribute('data-choice'));
                if (action === 'delete-post') return deletePost();
                if (action === 'block-user') return toggleBlockUser(Number(button.getAttribute('data-user-id')));
                if (action === 'report-content') return openReport(button.getAttribute('data-content-type'), Number(button.getAttribute('data-content-id')));
            } catch (error) {
                showToast(error.message || 'Action failed.', true);
            }
        });

        state.list.addEventListener('click', async (event) => {
            const button = event.target.closest('button');
            if (!button) return;
            const action = button.getAttribute('data-action');
            if (!action) return;
            event.preventDefault();
            try {
                if (action === 'toggle-menu') {
                    const menu = document.getElementById(button.getAttribute('data-menu-id'));
                    if (!menu) return;
                    const open = menu.classList.contains('community-hidden');
                    closeAllMoreMenus();
                    if (open) menu.classList.remove('community-hidden');
                    return;
                }
                if (action === 'like-comment') return likeComment(Number(button.getAttribute('data-comment-id')));
                if (action === 'delete-comment') return deleteComment(Number(button.getAttribute('data-comment-id')));
                if (action === 'block-user') return toggleBlockUser(Number(button.getAttribute('data-user-id')));
                if (action === 'report-content') return openReport(button.getAttribute('data-content-type'), Number(button.getAttribute('data-content-id')));
            } catch (error) {
                showToast(error.message || 'Action failed.', true);
            }
        });

        state.form?.addEventListener('submit', async (event) => {
            event.preventDefault();
            const body = (state.commentBody?.value || '').trim();
            if (!body) {
                showToast('Comment cannot be empty.', true);
                return;
            }
            if (!ensureGuidelinesAccepted()) return;
            try {
                state.commentSubmit.disabled = true;
                state.commentSubmit.textContent = 'Posting...';
                const { data, unauthorized } = await apiRequest(root, `${state.postsBaseUrl}${state.post.id}/comments/`, {
                    method: 'POST',
                    body: JSON.stringify({ body }),
                });
                if (unauthorized) return;
                updatePost((post) => {
                    const comments = [...(post.comments || []), data];
                    return { ...post, comments, comment_count: comments.length };
                });
                state.commentBody.value = '';
            } catch (error) {
                showToast(error.message || 'Could not post comment.', true);
            } finally {
                state.commentSubmit.disabled = false;
                state.commentSubmit.textContent = 'Post Comment';
            }
        });

        loadPost();
    }
    function initCreatePage(root) {
        const form = root.querySelector('#communityCreateForm');
        if (!form) return;

        const state = {
            root,
            postsBaseUrl: root.dataset.postsUrl || '/api/community/posts/',
            categoryInput: form.querySelector('#communityCreateCategory'),
            chips: Array.from(form.querySelectorAll('[data-community-create-category]')),
            title: form.querySelector('#communityCreateTitle'),
            titleCount: form.querySelector('#communityCreateTitleCount'),
            body: form.querySelector('#communityCreateBody'),
            image: form.querySelector('#communityCreateImage'),
            imageName: form.querySelector('#communityCreateImageName'),
            anonymous: form.querySelector('#communityCreateAnonymous'),
            poll: form.querySelector('#communityCreatePoll'),
            submit: form.querySelector('#communityCreateSubmit'),
            error: form.querySelector('#communityCreateError'),
            success: form.querySelector('#communityCreateSuccess'),
        };

        function setError(message) {
            state.success.classList.add('community-hidden');
            state.error.textContent = message;
            state.error.classList.remove('community-hidden');
        }

        function clearError() {
            state.error.textContent = '';
            state.error.classList.add('community-hidden');
        }

        function setSuccess(message) {
            state.success.textContent = message;
            state.success.classList.remove('community-hidden');
        }

        function updateTitleCount() {
            state.titleCount.textContent = String((state.title.value || '').length);
        }

        function setCategory(value) {
            state.categoryInput.value = value || '';
            state.chips.forEach((chip) => {
                const isActive = chip.getAttribute('data-community-create-category') === value;
                chip.classList.toggle('is-active', isActive);
            });
        }

        state.chips.forEach((chip) => {
            chip.addEventListener('click', () => setCategory(chip.getAttribute('data-community-create-category') || ''));
        });
        state.title.addEventListener('input', updateTitleCount);
        state.image.addEventListener('change', () => {
            const file = state.image.files && state.image.files[0];
            state.imageName.textContent = file ? file.name : 'No file selected';
        });

        form.addEventListener('submit', async (event) => {
            event.preventDefault();
            clearError();

            const category = (state.categoryInput.value || '').trim();
            const title = (state.title.value || '').trim();
            const body = (state.body.value || '').trim();
            const file = state.image.files && state.image.files[0];

            if (!category) return setError('Please choose a category.');
            if (!title) return setError('Title is required.');
            if (title.length > 200) return setError('Title must be 200 characters or fewer.');
            if (!body) return setError('Details are required.');
            if (!ensureGuidelinesAccepted()) return;

            try {
                state.submit.disabled = true;
                state.submit.textContent = 'Publishing...';

                let options;
                if (file) {
                    const formData = new FormData();
                    formData.append('title', title);
                    formData.append('body', body);
                    formData.append('category', category);
                    if (state.anonymous.checked) formData.append('is_anonymous', 'true');
                    if (state.poll.checked) formData.append('has_poll', 'true');
                    formData.append('image', file);
                    options = { method: 'POST', body: formData };
                } else {
                    options = {
                        method: 'POST',
                        body: JSON.stringify({
                            title,
                            body,
                            category,
                            ...(state.anonymous.checked ? { is_anonymous: true } : {}),
                            ...(state.poll.checked ? { has_poll: true } : {}),
                        }),
                    };
                }

                const { data, unauthorized } = await apiRequest(root, state.postsBaseUrl, options);
                if (unauthorized) return;
                setSuccess('Post created. Redirecting...');
                window.setTimeout(() => {
                    window.location.href = `/community/posts/${data.id}/`;
                }, 300);
            } catch (error) {
                setError(error.message || 'Could not publish post.');
            } finally {
                state.submit.disabled = false;
                state.submit.textContent = 'Publish Post';
            }
        });

        updateTitleCount();
    }

    function initialize() {
        reportFlow.init();

        const feedRoot = document.querySelector('[data-community-feed-root="1"]');
        if (feedRoot) {
            initFeedPage(feedRoot);
            return;
        }

        const detailRoot = document.querySelector('[data-community-detail-root="1"]');
        if (detailRoot) {
            initDetailPage(detailRoot);
            return;
        }

        const createRoot = document.querySelector('[data-community-create-root="1"]');
        if (createRoot) {
            initCreatePage(createRoot);
        }
    }

    document.addEventListener('DOMContentLoaded', initialize);
})();

