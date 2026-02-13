// report.js — Weekly Safety Report logic for VnContentGuard Pro v4.9
(function () {
    'use strict';

    // ── Date helpers ──
    function formatDate(d) {
        return d.toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }
    function getWeekRange() {
        const now = new Date();
        const start = new Date(now);
        start.setDate(now.getDate() - 7);
        return { start, end: now };
    }

    // ── Load & render ──
    function loadReport() {
        const { start, end } = getWeekRange();
        document.getElementById('periodDisplay').textContent =
            `${formatDate(start)} — ${formatDate(end)}`;

        chrome.storage.local.get(['scanHistory', 'feedbackHistory'], (data) => {
            const history = data.scanHistory || [];
            const feedback = data.feedbackHistory || [];

            // Filter to this week
            const weekScans = history.filter(s => {
                const d = new Date(s.timestamp || s.date);
                return d >= start && d <= end;
            });

            // ── Stats ──
            const total = weekScans.length;
            let high = 0, med = 0, safe = 0;
            const domainRiskMap = {};
            const domainCountMap = {};

            weekScans.forEach(s => {
                const risk = s.risk_score || s.riskScore || 0;
                const level = s.risk_level || s.riskLevel || '';

                if (risk >= 70 || level === 'HIGH') high++;
                else if (risk >= 40 || level === 'MEDIUM') med++;
                else safe++;

                // Domain stats
                let domain = 'unknown';
                try { domain = new URL(s.url).hostname.replace('www.', ''); } catch {}
                if (!domainRiskMap[domain]) domainRiskMap[domain] = [];
                domainRiskMap[domain].push(risk);
                domainCountMap[domain] = (domainCountMap[domain] || 0) + 1;
            });

            document.getElementById('totalScans').textContent = total;
            document.getElementById('highRisk').textContent = high;
            document.getElementById('medRisk').textContent = med;
            document.getElementById('safeScans').textContent = safe;

            // ── Risk bar ──
            if (total > 0) {
                const sp = (v) => Math.max(Math.round((v / total) * 100), v > 0 ? 5 : 0);
                const safeP = sp(safe), medP = sp(med), highP = sp(high);
                document.getElementById('riskBar').innerHTML = `
                    <div class="risk-safe" style="width:${safeP}%">An toàn ${safeP}%</div>
                    <div class="risk-medium" style="width:${medP}%">TB ${medP}%</div>
                    <div class="risk-high" style="width:${highP}%">Cao ${highP}%</div>
                `;
            }

            // ── Top risky domains ──
            const riskDomains = Object.entries(domainRiskMap)
                .map(([d, scores]) => ({ domain: d, avg: scores.reduce((a, b) => a + b, 0) / scores.length }))
                .sort((a, b) => b.avg - a.avg)
                .slice(0, 5);

            const riskList = document.getElementById('topRiskDomains');
            if (riskDomains.length > 0) {
                riskList.innerHTML = riskDomains.map(d => {
                    const tag = d.avg >= 70 ? 'risk-tag-high' : (d.avg >= 40 ? 'risk-tag-medium' : 'risk-tag-safe');
                    const level = d.avg >= 70 ? 'Cao' : (d.avg >= 40 ? 'TB' : 'Thấp');
                    return `<li><span class="domain-name">${d.domain}</span><span class="domain-risk ${tag}">${level} (${Math.round(d.avg)})</span></li>`;
                }).join('');
            }

            // ── Top scanned domains ──
            const scannedDomains = Object.entries(domainCountMap)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5);

            const scanList = document.getElementById('topScannedDomains');
            if (scannedDomains.length > 0) {
                scanList.innerHTML = scannedDomains.map(([d, c]) => {
                    return `<li><span class="domain-name">${d}</span><span style="color:#3498db;font-size:13px;">${c} lần</span></li>`;
                }).join('');
            }

            // ── Feedback stats ──
            const weekFb = feedback.filter(f => {
                const d = new Date(f.timestamp || f.date);
                return d >= start && d <= end;
            });
            const fbTotal = weekFb.length;
            const fbPos = weekFb.filter(f => f.is_correct === true || f.feedback === 'agree').length;
            const fbNeg = fbTotal - fbPos;
            const accuracy = fbTotal > 0 ? Math.round((fbPos / fbTotal) * 100) : 0;

            document.getElementById('fbTotal').textContent = fbTotal;
            document.getElementById('fbPositive').textContent = fbPos;
            document.getElementById('fbNegative').textContent = fbNeg;
            document.getElementById('fbAccuracy').textContent = fbTotal > 0 ? `${accuracy}%` : '-';
        });
    }

    // ── Export / Print ──
    document.getElementById('btnExport').addEventListener('click', () => {
        window.print();
    });

    // ── Init ──
    loadReport();
})();
