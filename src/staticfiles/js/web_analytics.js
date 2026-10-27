(function () {
    'use strict';
    const allowed = new Set(['reply_generated', 'sign_up', 'copy_suggestion']);
    const fields = new Set(['event_id', 'landing_path', 'acquisition_source', 'acquisition_medium']);
    const seen = new Set();
    const storageKey = 'tat_analytics_events_v1';
    let previous = [];
    try { previous = JSON.parse(sessionStorage.getItem(storageKey) || '[]'); } catch (_) {}
    if (Array.isArray(previous)) previous.slice(-200).forEach(value => seen.add(value));

    function track(name, input) {
        if (!allowed.has(name) || typeof window.gtag !== 'function') return false;
        const parameters = {};
        Object.entries(input || {}).forEach(([key, value]) => {
            if (fields.has(key) && typeof value === 'string') parameters[key] = value.slice(0, 255);
        });
        if (!parameters.event_id) return false;
        const key = name + ':' + parameters.event_id;
        if (seen.has(key)) return false;
        window.gtag('event', name, parameters);
        seen.add(key);
        try { sessionStorage.setItem(storageKey, JSON.stringify(Array.from(seen).slice(-200))); } catch (_) {}
        return true;
    }
    window.webAnalytics = {track: track};
    document.addEventListener('replyGenerated', function (event) {
        track('reply_generated', event.detail && (event.detail.value || event.detail));
    });
    document.addEventListener('DOMContentLoaded', function () {
        const queue = document.getElementById('web-analytics-events');
        if (!queue) return;
        try {
            JSON.parse(queue.textContent).forEach(event => track(event.name, event.parameters));
        } catch (_) {}
    });
})();
