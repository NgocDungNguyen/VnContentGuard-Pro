/**
 * VnContentGuard Pro v6.0 — Domain Control Module (Feature 6.2)
 * Manages user-defined domain blacklist and whitelist for parental control.
 *
 * Storage keys:
 *   domainBlacklist  — array of domain strings blocked by parent
 *   domainWhitelist  — array of domain strings always allowed (overrides blacklist)
 *
 * Rules:
 *   - Whitelist WINS: if domain is in both lists, it is NOT blocked.
 *   - Subdomain matching: "xvideos.com" blocks "m.xvideos.com" etc.
 *   - Inputs are sanitised: scheme, www, path all stripped to bare hostname.
 *   - Domain comparison is always lower-case.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Strip scheme, www. prefix, port, path and trailing slash from any URL or
 * bare domain string.  Returns lower-cased hostname, e.g.
 *   "https://www.XVideos.com/video/123" → "xvideos.com"
 *   "m.Facebook.com"                   → "m.facebook.com"
 */
function cleanDomain(input) {
    if (!input) return '';
    let s = input.trim().toLowerCase();
    // Add dummy scheme so URL() can parse bare domains
    if (!s.startsWith('http://') && !s.startsWith('https://')) {
        s = 'https://' + s;
    }
    try {
        const host = new URL(s).hostname.replace(/^www\./, '').split(':')[0];
        return host;
    } catch {
        // Fallback: just strip www. and path
        return s.replace(/^https?:\/\//, '').replace(/^www\./, '').split('/')[0].split(':')[0];
    }
}

/**
 * Return true if `hostname` (already cleaned) is covered by `entry` (also
 * cleaned).  Covers exact match and subdomain match:
 *   entry="xvideos.com", hostname="m.xvideos.com" → true
 *   entry="xvideos.com", hostname="xvideos.com"   → true
 */
function domainMatches(hostname, entry) {
    return hostname === entry || hostname.endsWith('.' + entry);
}

// ─────────────────────────────────────────────────────────────────────────────
// DomainControl public API
// ─────────────────────────────────────────────────────────────────────────────

const DomainControl = {

    // ── Readers ───────────────────────────────────────────────────────────────

    async getBlacklist() {
        const d = await chrome.storage.local.get(['domainBlacklist']);
        return d.domainBlacklist || [];
    },

    async getWhitelist() {
        const d = await chrome.storage.local.get(['domainWhitelist']);
        return d.domainWhitelist || [];
    },

    // ── Blacklist mutators ────────────────────────────────────────────────────

    async addToBlacklist(rawDomain) {
        const domain = cleanDomain(rawDomain);
        if (!domain) return { ok: false, error: 'Tên miền không hợp lệ' };
        const list = await this.getBlacklist();
        if (list.includes(domain)) return { ok: false, error: 'Đã có trong danh sách' };
        list.push(domain);
        list.sort();
        await chrome.storage.local.set({ domainBlacklist: list });
        return { ok: true, domain };
    },

    async removeFromBlacklist(rawDomain) {
        const domain = cleanDomain(rawDomain);
        const list = (await this.getBlacklist()).filter(d => d !== domain);
        await chrome.storage.local.set({ domainBlacklist: list });
        return { ok: true };
    },

    async setBlacklist(rawArray) {
        const list = [...new Set(rawArray.map(cleanDomain).filter(Boolean))].sort();
        await chrome.storage.local.set({ domainBlacklist: list });
        return { ok: true, count: list.length };
    },

    // ── Whitelist mutators ────────────────────────────────────────────────────

    async addToWhitelist(rawDomain) {
        const domain = cleanDomain(rawDomain);
        if (!domain) return { ok: false, error: 'Tên miền không hợp lệ' };
        const list = await this.getWhitelist();
        if (list.includes(domain)) return { ok: false, error: 'Đã có trong danh sách' };
        list.push(domain);
        list.sort();
        await chrome.storage.local.set({ domainWhitelist: list });
        return { ok: true, domain };
    },

    async removeFromWhitelist(rawDomain) {
        const domain = cleanDomain(rawDomain);
        const list = (await this.getWhitelist()).filter(d => d !== domain);
        await chrome.storage.local.set({ domainWhitelist: list });
        return { ok: true };
    },

    async setWhitelist(rawArray) {
        const list = [...new Set(rawArray.map(cleanDomain).filter(Boolean))].sort();
        await chrome.storage.local.set({ domainWhitelist: list });
        return { ok: true, count: list.length };
    },

    // ── URL checks ────────────────────────────────────────────────────────────

    /** True if the URL's domain is in the whitelist (always allow). */
    async isWhitelisted(url) {
        try {
            const hostname = new URL(url).hostname.replace(/^www\./, '').toLowerCase();
            const list = await this.getWhitelist();
            return list.some(entry => domainMatches(hostname, entry));
        } catch { return false; }
    },

    /** True if the URL's domain is blocked (blacklisted AND NOT whitelisted). */
    async isBlacklisted(url) {
        try {
            const hostname = new URL(url).hostname.replace(/^www\./, '').toLowerCase();
            const [blacklist, whitelist] = await Promise.all([
                this.getBlacklist(),
                this.getWhitelist()
            ]);
            // Whitelist wins
            if (whitelist.some(entry => domainMatches(hostname, entry))) return false;
            return blacklist.some(entry => domainMatches(hostname, entry));
        } catch { return false; }
    },

    // ── Import / Export ───────────────────────────────────────────────────────

    /**
     * Import domains from a newline-separated (or comma/space-separated) string.
     * @param {'blacklist'|'whitelist'} listType
     * @param {string} text
     * @param {boolean} replace  true = replace existing, false = append (default)
     */
    async importFromText(listType, text, replace = false) {
        const incoming = text
            .split(/[\n,\s]+/)
            .map(cleanDomain)
            .filter(Boolean);

        if (listType === 'blacklist') {
            const existing = replace ? [] : await this.getBlacklist();
            const merged = [...new Set([...existing, ...incoming])].sort();
            await chrome.storage.local.set({ domainBlacklist: merged });
            return { ok: true, added: incoming.length, total: merged.length };
        } else {
            const existing = replace ? [] : await this.getWhitelist();
            const merged = [...new Set([...existing, ...incoming])].sort();
            await chrome.storage.local.set({ domainWhitelist: merged });
            return { ok: true, added: incoming.length, total: merged.length };
        }
    },

    /**
     * Export domains as a newline-separated string.
     * @param {'blacklist'|'whitelist'} listType
     */
    async exportToText(listType) {
        const list = listType === 'blacklist'
            ? await this.getBlacklist()
            : await this.getWhitelist();
        return list.join('\n');
    },

    // ── Seed Loader ───────────────────────────────────────────────────────────

    /**
     * Fetch the server-provided seed blacklist of harmful Vietnamese domains
     * and merge it into the local blacklist (never replaces user additions).
     */
    async loadSeedBlacklist() {
        const ENDPOINTS = [
            'https://vncontentguard-pro.onrender.com/api/blacklist/seed',
        ];
        for (const url of ENDPOINTS) {
            try {
                const resp = await fetch(url, { method: 'GET' });
                if (!resp.ok) continue;
                const data = await resp.json();
                const domains = data.domains || [];
                if (!domains.length) return { ok: false, error: 'Danh sách trống' };
                const result = await this.importFromText('blacklist', domains.join('\n'), false);
                return { ok: true, added: result.added, total: result.total };
            } catch { /* try next */ }
        }
        return { ok: false, error: 'Không thể tải danh sách mặc định' };
    },
};
