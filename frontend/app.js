document.addEventListener('alpine:init', () => {
    Alpine.data('newsApp', () => ({
        articles: [],
        selectedArticle: null,
        isLoading: false,
        isLoadingDetail: false,
        error: null,
        isModalOpen: false,

        // WebSocket/Toast states
        showToast: false,
        toastTitle: '新焦點新聞',
        toastMessage: '有新的焦點新聞已抓取',
        wsSocket: null,

        init() {
            this.fetchArticles();
            this.setupWebSocket();

            // Handle escape key and body scroll lock for modal
            this.$watch('isModalOpen', (value) => {
                if (value) {
                    document.body.style.overflow = 'hidden';
                } else {
                    document.body.style.overflow = '';
                }
            });
        },

        async fetchArticles() {
            this.isLoading = true;
            this.error = null;
            try {
                // Fetch from Django REST Framework endpoint using relative path which Nginx will proxy
                const response = await fetch('/api/articles/');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();

                // DRF typically wraps pagination in 'results'
                if (data.results) {
                    this.articles = data.results;
                } else if (Array.isArray(data)) {
                    this.articles = data;
                } else {
                    console.warn('Unexpected data format', data);
                    this.articles = [];
                }

            } catch (err) {
                console.error('Fetch error:', err);
                this.error = '無法自動載入新聞列表，請確保後端伺服器正常運作並已爬取資料。';
            } finally {
                this.isLoading = false;
            }
        },

        async openModal(article) {
            this.selectedArticle = article;
            this.isModalOpen = true;
            this.isLoadingDetail = true;

            try {
                // Fetch full detail representation
                const response = await fetch(`/api/articles/${article.id}/`);
                if (response.ok) {
                    const fullData = await response.json();
                    this.selectedArticle = { ...this.selectedArticle, ...fullData };
                }
            } catch (err) {
                console.error('Failed to fetch article details', err);
            } finally {
                this.isLoadingDetail = false;
            }
        },

        closeModal() {
            this.isModalOpen = false;
            setTimeout(() => {
                this.selectedArticle = null;
            }, 300); // Wait for transition out
        },

        formatDate(dateString) {
            if (!dateString) return '剛剛';
            const date = new Date(dateString);

            // Check if valid date
            if (isNaN(date.getTime())) return dateString;

            return new Intl.DateTimeFormat('zh-TW', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            }).format(date);
        },

        getKeywords(keywords) {
            if (!keywords) return [];
            return keywords.split(',').map(k => k.trim()).filter(k => k.length > 0);
        },

        formatContent(body) {
            if (!body) return '';

            // body is a structured block array from the spider
            if (Array.isArray(body)) {
                return body.map(block => {
                    switch (block.type) {
                        case 'text':
                            return `<p>${block.value}</p>`;
                        case 'image': {
                            const caption = block.caption
                                ? `<figcaption class="text-sm text-gray-500 text-center mt-2">${block.caption}</figcaption>`
                                : '';
                            return `<figure class="my-6"><img src="${block.url}" alt="${block.caption || ''}" class="rounded-xl w-full object-cover shadow">${caption}</figure>`;
                        }
                        case 'player_card':
                            return `<p><a href="${block.url}" target="_blank" class="inline-flex items-center gap-1 text-udn-blue font-semibold hover:underline">🏀 ${block.name}</a></p>`;
                        case 'tweet':
                            return `<p><a href="${block.url}" target="_blank" class="text-udn-blue hover:underline">🐦 查看原始推文</a></p>`;
                        case 'video':
                            return `<div class="my-6 aspect-video"><iframe src="${block.url}" class="w-full h-full rounded-xl" allowfullscreen></iframe></div>`;
                        case 'livescore':
                            return `<div class="my-4 p-4 bg-gray-100 rounded-xl text-sm text-gray-700">📊 比賽數據：${JSON.stringify(block.data)}</div>`;
                        default:
                            return '';
                    }
                }).join('\n');
            }

            // Fallback: plain string
            if (typeof body === 'string') {
                if (!body || body === 'undefined') return '';
                if (body.includes('<p>') || body.includes('<br')) return body;
                return `<p>${body.replace(/\n\n/g, '</p><p>').replace(/\n/g, '<br>')}</p>`;
            }

            return '';
        },

        setupWebSocket() {
            // Attempt to connect to the backend websocket for live notifications.
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/news/`;

            try {
                this.wsSocket = new WebSocket(wsUrl);

                this.wsSocket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        // Show notification if it's a new article event
                        if (data.type === 'new_article' || data.message) {
                            this.showNotification('焦點新聞更新', data.title || data.message || '剛剛抓取到一篇最新新聞');
                        }
                    } catch (e) {
                        console.warn("WS parsing error", e);
                    }
                };

                this.wsSocket.onerror = () => {
                    console.log('WebSocket connection not ready or configured differently in compose.');
                };
            } catch (e) {
                console.log('WebSocket init error', e);
            }
        },

        showNotification(title, message) {
            this.toastTitle = title;
            this.toastMessage = message;
            this.showToast = true;

            // Automatically hide toast
            setTimeout(() => {
                this.showToast = false;
            }, 5000);
        }
    }));
});
