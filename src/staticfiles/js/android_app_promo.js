(function () {
    'use strict';

    const bar = document.querySelector('[data-android-app-bar]');
    const pageGroup = document.body.dataset.appPromoPage;
    if (!pageGroup) return;

    const isAndroid = navigator.userAgentData?.platform === 'Android' || /Android/i.test(navigator.userAgent || '');
    const dismissalKey = 'flirtfix_android_promo_dismissed_until';
    const week = 7 * 24 * 60 * 60 * 1000;
    let dismissed = false;
    try {
        dismissed = Number(localStorage.getItem(dismissalKey)) > Date.now();
    } catch (_) {
        // Promotion and normal links still work when storage is unavailable.
    }

    function track(event, placement) {
        if (typeof window.gtag === 'function') {
            window.gtag('event', event, {
                app_name: 'FlirtFix',
                placement: placement,
                page_group: pageGroup,
                page_path: window.location.pathname,
                device_platform: isAndroid ? 'android' : 'other',
                transport_type: 'beacon'
            });
        }
    }

    document.addEventListener('click', function (event) {
        const link = event.target.closest('[data-app-promo-placement]');
        if (link) track('android_app_cta_click', link.dataset.appPromoPlacement);
    });

    const viewed = new Set();
    function trackView(link) {
        const placement = link.dataset.appPromoPlacement;
        if (!viewed.has(placement)) {
            viewed.add(placement);
            track('android_app_promo_view', placement);
        }
    }
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    trackView(entry.target);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: .5 });
        document.querySelectorAll('[data-app-promo-placement]').forEach(link => observer.observe(link));
    }

    if (!bar || !isAndroid || dismissed) return;

    function updateBar() {
        const editing = document.activeElement?.matches('input, textarea, select, [contenteditable]:not([contenteditable="false"])');
        const visible = !dismissed && !editing;
        bar.hidden = !visible;
        document.body.classList.toggle('android-app-bar-visible', visible);
        document.documentElement.classList.toggle('android-app-bar-visible', visible);
        if (visible) {
            document.documentElement.style.setProperty('--android-app-bar-height', bar.offsetHeight + 'px');
            trackView(bar.querySelector('[data-app-promo-placement]'));
        }
    }

    bar.querySelector('[data-dismiss-app-promo]').addEventListener('click', function () {
        dismissed = true;
        try {
            localStorage.setItem(dismissalKey, String(Date.now() + week));
        } catch (_) {
            // Dismiss for this page even if persistence is blocked.
        }
        track('android_app_promo_dismiss', 'android_bar');
        updateBar();
    });

    // Keep the keyboard and reply tools clear while someone is writing.
    document.addEventListener('focusin', updateBar);
    document.addEventListener('focusout', function () { window.setTimeout(updateBar, 0); });
    window.addEventListener('resize', updateBar);
    if ('ResizeObserver' in window) new ResizeObserver(updateBar).observe(bar);
    updateBar();
})();
