document.addEventListener('alpine:init', () => {
    Alpine.data('newsApp', () => ({
        articles: [],
        selectedArticle: null,
        isLoading: false,
        isLoadingDetail: false,
        error: null,
        isModalOpen: false,

        // Search state
        searchQuery: '',
        searchTimeout: null,

        // Pagination states
        currentPage: 1,
        totalPages: 1,
        totalCount: 0,
        nextUrl: null,
        previousUrl: null,

        // WebSocket/Toast states
        showToast: false,
        toastTitle: '新焦點新聞',
        toastMessage: '有新的焦點新聞已抓取',
        wsSocket: null,

        init() {
            this.fetchArticles();
            this.setupWebSocket();

            this.$watch('isModalOpen', (value) => {
                if (value) {
                    document.body.style.overflow = 'hidden';
                } else {
                    document.body.style.overflow = '';
                }
            });
        },

        onSearchInput() {
            clearTimeout(this.searchTimeout);
            this.searchTimeout = setTimeout(() => {
                this.currentPage = 1;
                this.fetchArticles('/api/articles/', this.searchQuery);
            }, 400);
        },

        clearSearch() {
            this.searchQuery = '';
            this.fetchArticles();
        },

        async fetchArticles(url = '/api/articles/', query = '') {
            this.isLoading = true;
            this.error = null;
            try {
                let fetchUrl = url;
                if (query && !url.includes('search=')) {
                    const sep = url.includes('?') ? '&' : '?';
                    fetchUrl = `${url}${sep}search=${encodeURIComponent(query)}`;
                }
                const response = await fetch(fetchUrl);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();

                // DRF typically wraps pagination in 'results'
                if (data.results) {
                    this.articles = data.results;
                    this.totalCount = data.count;
                    this.totalPages = Math.ceil(data.count / 20); // DRF is configured for 20 per page
                    this.nextUrl = data.next ? data.next.replace(/^.*\/\/[^\/]+/, '') : null; // Convert to relative URL
                    this.previousUrl = data.previous ? data.previous.replace(/^.*\/\/[^\/]+/, '') : null;

                    // Extract page number from URL if present
                    const urlParams = new URLSearchParams(url.split('?')[1]);
                    this.currentPage = parseInt(urlParams.get('page')) || 1;
                } else if (Array.isArray(data)) {
                    this.articles = data;
                    this.totalCount = data.length;
                    this.totalPages = 1;
                    this.nextUrl = null;
                    this.previousUrl = null;
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

        async goToPage(url) {
            if (url) {
                await this.fetchArticles(url);
                window.scrollTo({ top: 0, behavior: 'smooth' });
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
                        case 'livescore': {
                            const d = block.data || {};
                            const away = d.away_team || '客隊';
                            const home = d.home_team || '主隊';
                            const awayScore = d.away_score ?? '-';
                            const homeScore = d.home_score ?? '-';
                            const status = d.statusWord || d.status || '';
                            const date = d.date ? `<span class="text-gray-400 text-xs ml-2">${d.date}</span>` : '';
                            const winner = (d.away_score > d.home_score) ? 'away' : (d.home_score > d.away_score) ? 'home' : 'tie';
                            return `<div class="my-4 p-4 bg-gray-50 border border-gray-200 rounded-xl">
                                <div class="flex items-center justify-between gap-4">
                                    <div class="flex-1 text-center">
                                        <div class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">客隊</div>
                                        <div class="text-2xl font-black ${winner === 'away' ? 'text-udn-blue' : 'text-gray-700'}">${away}</div>
                                        <div class="text-4xl font-black ${winner === 'away' ? 'text-udn-blue' : 'text-gray-400'} mt-1">${awayScore}</div>
                                    </div>
                                    <div class="text-center px-2">
                                        <div class="text-xs font-semibold text-gray-400 uppercase">${status}</div>
                                        <div class="text-lg text-gray-300 font-light my-1">:</div>
                                        ${date}
                                    </div>
                                    <div class="flex-1 text-center">
                                        <div class="text-xs font-bold text-gray-500 uppercase tracking-widest mb-1">主隊</div>
                                        <div class="text-2xl font-black ${winner === 'home' ? 'text-udn-blue' : 'text-gray-700'}">${home}</div>
                                        <div class="text-4xl font-black ${winner === 'home' ? 'text-udn-blue' : 'text-gray-400'} mt-1">${homeScore}</div>
                                    </div>
                                </div>
                            </div>`;
                        }
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
                            this.showNotification('焦點新聞更新', data.message || '剛剛抓取到一篇最新新聞');
                        }
                    } catch (e) {
                        console.warn("WS parsing error", e);
                    }
                };

                this.wsSocket.onerror = () => {
                    console.log('WebSocket connection not ready or configured differently in compose.');
                };

                this.wsSocket.onclose = () => {
                    setTimeout(() => this.setupWebSocket(), 3000);
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
            console.log('Toast shown:', title, message);
        }
    }));
});
