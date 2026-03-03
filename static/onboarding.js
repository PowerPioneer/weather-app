/**
 * Onboarding Tour for "Where to Go for Great Weather"
 *
 * A 5-step guided tour that introduces first-time visitors to the
 * site's controls and map interactions. Persisted via localStorage
 * so it only shows once; a "?" header button allows replay.
 */

(function () {
    'use strict';

    var LOCALSTORAGE_KEY = 'onboardingCompleted';

    var STEPS = [
        {
            id: 'welcome',
            target: null,
            title: 'Find Your Perfect Weather Destination',
            body:
                'Weather and climate are not the same thing \u2014 weather is what you experience day to day, while climate describes the long-term patterns of a region. When planning a trip, you can use climate data to give yourself the best chance of enjoying great weather.' +
                '<br><br>' +
                'This interactive map helps you do exactly that. Set your ideal temperature, rainfall, and sunshine preferences for any month \u2014 and discover which destinations are most likely to deliver the weather you\u2019re looking for.',
            position: 'center'
        },
        {
            id: 'month',
            target: '#monthControlBtn',
            title: 'Select a Month',
            body: 'Choose which month you\u2019re planning to travel. The map updates instantly to show weather conditions for that month based on historical climate data.',
            position: 'right'
        },
        {
            id: 'display',
            target: '#displayModeControlBtn',
            title: 'Switch Visualization',
            body: 'View the map in different ways: your overall preference match, or focus on temperature, rainfall, sunshine, or travel safety individually.',
            position: 'right'
        },
        {
            id: 'preferences',
            target: '#preferencesControlBtn',
            title: 'Set Your Preferences',
            body: 'Adjust your ideal temperature range, maximum rainfall, and minimum sunshine hours. The map colors will update to reflect how well each region matches your personal preferences.',
            position: 'right'
        },
        {
            id: 'map-interaction',
            target: null,
            title: 'Explore the Map',
            body: 'Zoom in to see detailed data for provinces and regions. Click any country or region to view its full yearly climate breakdown. Enjoy your search!',
            position: 'center'
        }
    ];

    var state = {
        active: false,
        currentStep: 0,
        backdropEl: null,
        spotlightEl: null,
        bubbleEl: null,
        resizeHandler: null
    };

    // -------------------------------------------------------
    // Initialization
    // -------------------------------------------------------

    function init() {
        var helpBtn = document.getElementById('onboardingHelpBtn');
        if (helpBtn) {
            helpBtn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                replayTour();
            });
        }

        if (localStorage.getItem(LOCALSTORAGE_KEY)) {
            return;
        }

        waitForCookieConsent().then(function () {
            setTimeout(startTour, 800);
        });
    }

    // -------------------------------------------------------
    // Cookie consent detection
    // -------------------------------------------------------

    function isCookieBannerVisible() {
        var banner =
            document.querySelector('[data-enzuzo-cookie-bar]') ||
            document.querySelector('.enzuzo-cookie-bar') ||
            document.getElementById('enzuzo-cookie-bar');
        if (!banner) return false;
        var style = window.getComputedStyle(banner);
        return style.display !== 'none' && style.visibility !== 'hidden' && banner.offsetParent !== null;
    }

    function waitForCookieConsent() {
        return new Promise(function (resolve) {
            var checkCount = 0;
            var maxChecks = 50; // 50 × 200ms = 10s
            var earlyResolve = 15; // 15 × 200ms = 3s — if banner never appeared, no point waiting longer
            var bannerWasSeen = false;

            var interval = setInterval(function () {
                checkCount++;

                if (isCookieBannerVisible()) {
                    bannerWasSeen = true;
                    return;
                }

                if (bannerWasSeen || checkCount >= maxChecks || (!bannerWasSeen && checkCount >= earlyResolve)) {
                    clearInterval(interval);
                    resolve();
                }
            }, 200);
        });
    }

    // -------------------------------------------------------
    // Tour lifecycle
    // -------------------------------------------------------

    function startTour() {
        if (state.active) return;
        state.active = true;
        state.currentStep = 0;

        createOverlayElements();
        showStep(0);

        state.resizeHandler = function () {
            if (state.active) showStep(state.currentStep);
        };
        window.addEventListener('resize', state.resizeHandler);
    }

    function endTour() {
        state.active = false;

        if (state.backdropEl) state.backdropEl.remove();
        if (state.spotlightEl) state.spotlightEl.remove();
        if (state.bubbleEl) state.bubbleEl.remove();
        state.backdropEl = null;
        state.spotlightEl = null;
        state.bubbleEl = null;

        if (state.resizeHandler) {
            window.removeEventListener('resize', state.resizeHandler);
            state.resizeHandler = null;
        }

        localStorage.setItem(LOCALSTORAGE_KEY, 'true');
    }

    function replayTour() {
        if (state.active) return;
        localStorage.removeItem(LOCALSTORAGE_KEY);
        startTour();
    }

    function nextStep() {
        showStep(state.currentStep + 1);
    }

    function skipTour() {
        endTour();
    }

    // -------------------------------------------------------
    // DOM creation
    // -------------------------------------------------------

    function createOverlayElements() {
        var backdrop = document.createElement('div');
        backdrop.className = 'onboarding-backdrop';
        backdrop.style.display = 'none';
        backdrop.addEventListener('click', function (e) { e.stopPropagation(); });
        document.body.appendChild(backdrop);
        state.backdropEl = backdrop;

        var spotlight = document.createElement('div');
        spotlight.className = 'onboarding-spotlight';
        spotlight.style.display = 'none';
        document.body.appendChild(spotlight);
        state.spotlightEl = spotlight;

        var bubble = document.createElement('div');
        bubble.className = 'onboarding-bubble';
        document.body.appendChild(bubble);
        state.bubbleEl = bubble;
    }

    function buildBubbleHTML(step, index) {
        var isLast = index === STEPS.length - 1;
        var hasTarget = !!step.target;

        var arrowHTML = hasTarget ? '<div class="onboarding-arrow arrow-left"></div>' : '';

        var dotsHTML = '<div class="onboarding-steps-indicator">';
        for (var i = 0; i < STEPS.length; i++) {
            dotsHTML += '<div class="onboarding-dot' + (i === index ? ' active' : '') + '"></div>';
        }
        dotsHTML += '</div>';

        var buttonsHTML = '<div class="onboarding-buttons">';
        if (isLast) {
            buttonsHTML += '<div></div>';
            buttonsHTML += '<button class="onboarding-btn onboarding-btn-next">Got it!</button>';
        } else {
            buttonsHTML += '<button class="onboarding-btn onboarding-btn-skip">Skip</button>';
            buttonsHTML += '<button class="onboarding-btn onboarding-btn-next">Next</button>';
        }
        buttonsHTML += '</div>';

        return arrowHTML +
            '<h3 class="onboarding-title">' + step.title + '</h3>' +
            '<p class="onboarding-body">' + step.body + '</p>' +
            dotsHTML +
            buttonsHTML;
    }

    // -------------------------------------------------------
    // Step rendering & positioning
    // -------------------------------------------------------

    function showStep(index) {
        var step = STEPS[index];
        if (!step) {
            endTour();
            return;
        }

        state.currentStep = index;
        var bubble = state.bubbleEl;
        var spotlight = state.spotlightEl;
        var backdrop = state.backdropEl;

        // Reset state
        bubble.classList.remove('active', 'centered');
        bubble.style.top = '';
        bubble.style.left = '';
        bubble.style.transform = '';
        spotlight.style.display = 'none';

        // Build content
        bubble.innerHTML = buildBubbleHTML(step, index);

        // Attach button listeners
        var skipBtn = bubble.querySelector('.onboarding-btn-skip');
        var nextBtn = bubble.querySelector('.onboarding-btn-next');
        if (skipBtn) skipBtn.addEventListener('click', skipTour);
        if (nextBtn) nextBtn.addEventListener('click', nextStep);

        if (step.target) {
            var targetEl = document.querySelector(step.target);
            if (!targetEl) {
                nextStep();
                return;
            }

            var rect = targetEl.getBoundingClientRect();
            var pad = 8;

            // Position spotlight over target
            spotlight.style.display = 'block';
            spotlight.style.top = (rect.top - pad) + 'px';
            spotlight.style.left = (rect.left - pad) + 'px';
            spotlight.style.width = (rect.width + pad * 2) + 'px';
            spotlight.style.height = (rect.height + pad * 2) + 'px';

            // Use backdrop behind spotlight (blocks interaction outside spotlight)
            backdrop.style.display = 'block';
            backdrop.classList.add('active');

            // Position bubble
            positionBubble(bubble, rect, step.position);
        } else {
            // Centered step
            spotlight.style.display = 'none';
            backdrop.style.display = 'block';
            backdrop.classList.add('active');
            bubble.classList.add('centered');
        }

        // Trigger enter animation on next frame
        requestAnimationFrame(function () {
            bubble.classList.add('active');
        });
    }

    function positionBubble(bubble, targetRect, position) {
        var gap = 16;
        var viewportW = window.innerWidth;
        var viewportH = window.innerHeight;

        // Measure the bubble off-screen
        bubble.style.visibility = 'hidden';
        bubble.style.display = 'block';
        bubble.classList.add('active');
        var bRect = bubble.getBoundingClientRect();
        bubble.style.visibility = '';
        bubble.classList.remove('active');

        var top, left;

        if (position === 'right') {
            left = targetRect.right + gap;
            top = targetRect.top + targetRect.height / 2 - bRect.height / 2;

            // If bubble overflows right edge, fall back to below target
            if (left + bRect.width > viewportW - 16) {
                left = targetRect.left;
                top = targetRect.bottom + gap;
                setArrowDirection(bubble, 'up');
            } else {
                setArrowDirection(bubble, 'left');
            }
        }

        // Clamp within viewport
        top = Math.max(16, Math.min(top, viewportH - bRect.height - 16));
        left = Math.max(16, Math.min(left, viewportW - bRect.width - 16));

        bubble.style.top = top + 'px';
        bubble.style.left = left + 'px';
    }

    function setArrowDirection(bubble, direction) {
        var arrow = bubble.querySelector('.onboarding-arrow');
        if (arrow) {
            arrow.className = 'onboarding-arrow arrow-' + direction;
        }
    }

    // -------------------------------------------------------
    // Auto-init
    // -------------------------------------------------------

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
