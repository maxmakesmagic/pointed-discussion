// Search functionality for the MTG card archive

class CardSearch {
    constructor() {
        this.searchInput = document.getElementById('cardSearch');
        this.searchResults = document.getElementById('searchResults');
        this.cards = this.extractCardsFromPage();
        this.initializeSearch();
    }

    extractCardsFromPage() {
        // Extract all card data from the page
        const cards = [];
        const cardLinks = document.querySelectorAll('.card-link');

        cardLinks.forEach(link => {
            const nameEl = link.querySelector('.card-name');
            const metaEl = link.querySelector('.card-meta');

            if (nameEl) {
                cards.push({
                    name: nameEl.textContent.trim(),
                    href: link.getAttribute('href'),
                    meta: metaEl ? metaEl.textContent.trim() : ''
                });
            }
        });

        // Also extract from category lists
        const categoryLinks = document.querySelectorAll('.card-list a');
        categoryLinks.forEach(link => {
            const name = link.textContent.trim();
            const href = link.getAttribute('href');

            // Avoid duplicates
            if (!cards.find(card => card.name === name)) {
                cards.push({
                    name: name,
                    href: href,
                    meta: ''
                });
            }
        });

        return cards;
    }

    initializeSearch() {
        if (!this.searchInput || !this.searchResults) {
            return;
        }

        // Search on input
        this.searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            this.performSearch(query);
        });

        // Handle keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeyNavigation(e);
        });

        // Hide results when clicking outside
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.searchResults.contains(e.target)) {
                this.hideResults();
            }
        });

        // Handle alphabet navigation
        this.initializeAlphabetNavigation();
    }

    performSearch(query) {
        if (query.length < 2) {
            this.hideResults();
            return;
        }

        const results = this.searchCards(query);
        this.displayResults(results);
    }

    searchCards(query) {
        const lowerQuery = query.toLowerCase();

        return this.cards
            .filter(card => card.name.toLowerCase().includes(lowerQuery))
            .sort((a, b) => {
                // Prioritize exact matches and starts-with matches
                const aLower = a.name.toLowerCase();
                const bLower = b.name.toLowerCase();

                if (aLower === lowerQuery) return -1;
                if (bLower === lowerQuery) return 1;
                if (aLower.startsWith(lowerQuery) && !bLower.startsWith(lowerQuery)) return -1;
                if (bLower.startsWith(lowerQuery) && !aLower.startsWith(lowerQuery)) return 1;

                return a.name.localeCompare(b.name);
            })
            .slice(0, 10); // Limit to 10 results
    }

    displayResults(results) {
        if (results.length === 0) {
            this.searchResults.innerHTML = '<div class="search-result-item">No cards found</div>';
        } else {
            this.searchResults.innerHTML = results
                .map(card => `
                    <div class="search-result-item" data-href="${card.href}">
                        <div class="card-name">${this.highlightMatch(card.name, this.searchInput.value)}</div>
                        ${card.meta ? `<div class="card-meta">${card.meta}</div>` : ''}
                    </div>
                `).join('');
        }

        // Add click handlers to results
        this.searchResults.querySelectorAll('.search-result-item').forEach(item => {
            item.addEventListener('click', () => {
                const href = item.getAttribute('data-href');
                if (href && href !== 'null') {
                    window.location.href = href;
                }
            });
        });

        this.showResults();
    }

    highlightMatch(text, query) {
        if (!query) return text;

        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<strong>$1</strong>');
    }

    handleKeyNavigation(e) {
        const items = this.searchResults.querySelectorAll('.search-result-item');
        const currentSelected = this.searchResults.querySelector('.search-result-item.selected');

        let selectedIndex = currentSelected ?
            Array.from(items).indexOf(currentSelected) : -1;

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
                this.selectResult(items, selectedIndex);
                break;

            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, 0);
                this.selectResult(items, selectedIndex);
                break;

            case 'Enter':
                e.preventDefault();
                if (currentSelected) {
                    currentSelected.click();
                } else if (items.length > 0) {
                    items[0].click();
                }
                break;

            case 'Escape':
                this.hideResults();
                this.searchInput.blur();
                break;
        }
    }

    selectResult(items, index) {
        // Remove previous selection
        items.forEach(item => item.classList.remove('selected'));

        // Add selection to new item
        if (items[index]) {
            items[index].classList.add('selected');
            items[index].scrollIntoView({ block: 'nearest' });
        }
    }

    showResults() {
        this.searchResults.style.display = 'block';
    }

    hideResults() {
        this.searchResults.style.display = 'none';
    }

    initializeAlphabetNavigation() {
        const alphabetLinks = document.querySelectorAll('.alphabet-link');

        alphabetLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetId = link.getAttribute('href');
                const targetElement = document.querySelector(targetId);

                if (targetElement) {
                    targetElement.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });

                    // Update URL without page reload
                    history.pushState(null, null, targetId);
                }
            });
        });

        // Handle direct hash links
        if (window.location.hash) {
            setTimeout(() => {
                const target = document.querySelector(window.location.hash);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth' });
                }
            }, 100);
        }
    }
}

// Add selected state styling
const style = document.createElement('style');
style.textContent = `
    .search-result-item.selected {
        background-color: #3498db !important;
        color: white;
    }
    .search-result-item.selected .card-meta {
        color: rgba(255, 255, 255, 0.8);
    }
`;
document.head.appendChild(style);

// Initialize search when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CardSearch();
});

// Smooth scroll polyfill for older browsers
if (!('scrollBehavior' in document.documentElement.style)) {
    const scrollToElement = (element) => {
        const targetPosition = element.offsetTop;
        const startPosition = window.pageYOffset;
        const distance = targetPosition - startPosition;
        const duration = 500;
        let start = null;

        const animation = (currentTime) => {
            if (start === null) start = currentTime;
            const timeElapsed = currentTime - start;
            const progress = Math.min(timeElapsed / duration, 1);

            window.scrollTo(0, startPosition + distance * progress);

            if (timeElapsed < duration) {
                requestAnimationFrame(animation);
            }
        };

        requestAnimationFrame(animation);
    };

    // Override smooth scroll for alphabet links
    document.querySelectorAll('.alphabet-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href');
            const targetElement = document.querySelector(targetId);

            if (targetElement) {
                scrollToElement(targetElement);
                history.pushState(null, null, targetId);
            }
        });
    });
}
