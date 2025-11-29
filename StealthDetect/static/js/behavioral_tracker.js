/**
 * StealthCAPTCHA Behavioral Tracker
 * Invisible behavioral analysis system for bot detection
 * * FIX IMPLEMENTED: Added 'Total' counters for all metrics to prevent live
 * display from resetting when data arrays are trimmed.
 */

(function() {
    'use strict';

    // Configuration
    const CONFIG = {
        dataCollectionInterval: 5000, // Send data every 5 seconds
        maxMouseEvents: 100,
        maxClickEvents: 50,
        maxKeystrokeEvents: 100,
        maxScrollEvents: 50,
        apiEndpoint: '/api/behavioral_data',
        sessionIdKey: 'stealth_captcha_session'
    };

    // Behavioral data storage
    let behavioralData = {
        sessionId: null,
        mouseMovements: [],
        clickPatterns: [],
        keystrokePatterns: [],
        scrollPatterns: [],
        deviceFingerprint: {},
        startTime: Date.now()
    };

    // Tracking state
    let isTracking = false;
    let dataCollectionTimer = null;
    let lastMouseEvent = null;
    let keystrokeStartTime = null;

    // --- ADDED GLOBAL TOTAL COUNTERS (These will NEVER reset) ---
    let mouseMovementTotal = 0;
    let clickPatternTotal = 0;
    let keystrokePatternTotal = 0;
    let scrollPatternTotal = 0;
    // -----------------------------------------------------------

    /**
     * Initialize the behavioral tracker
     */
    function init(providedSessionId) {
        if (isTracking) return;

        // Use provided session ID if available, otherwise generate one
        behavioralData.sessionId = providedSessionId || generateSessionId();

        // Collect device fingerprint
        collectDeviceFingerprint();

        // Start event listeners
        setupEventListeners();

        // Start data collection timer
        startDataCollection();

        // Expose behavioral data globally for task interface
        window.behavioralData = behavioralData;

        isTracking = true;
        console.log('StealthCAPTCHA: Behavioral tracking initialized with session:', behavioralData.sessionId);
    }

    /**
     * Generate unique session ID
     */
    function generateSessionId() {
        let sessionId = localStorage.getItem(CONFIG.sessionIdKey);
        if (!sessionId) {
            sessionId = 'sc_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            localStorage.setItem(CONFIG.sessionIdKey, sessionId);
        }
        return sessionId;
    }

    /**
     * Collect device and browser fingerprint
     */
    function collectDeviceFingerprint() {
        behavioralData.deviceFingerprint = {
            userAgent: navigator.userAgent,
            screenResolution: screen.width + 'x' + screen.height,
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            language: navigator.language || navigator.userLanguage,
            platform: navigator.platform,
            cookieEnabled: navigator.cookieEnabled,
            doNotTrack: navigator.doNotTrack,
            onlineStatus: navigator.onLine,
            touchSupport: 'ontouchstart' in window || navigator.maxTouchPoints > 0
        };
    }

    /**
     * Setup all event listeners for behavioral tracking
     */
    function setupEventListeners() {
        // Mouse movement tracking
        document.addEventListener('mousemove', handleMouseMove, { passive: true });

        // Click tracking
        document.addEventListener('click', handleClick, { passive: true });
        document.addEventListener('mousedown', handleMouseDown, { passive: true });
        document.addEventListener('mouseup', handleMouseUp, { passive: true });

        // Keyboard tracking
        document.addEventListener('keydown', handleKeyDown, { passive: true });
        document.addEventListener('keyup', handleKeyUp, { passive: true });

        // Scroll tracking
        document.addEventListener('scroll', handleScroll, { passive: true });
        window.addEventListener('wheel', handleWheel, { passive: true });

        // Focus and blur events
        window.addEventListener('focus', handleWindowFocus, { passive: true });
        window.addEventListener('blur', handleWindowBlur, { passive: true });

        // Page visibility changes
        document.addEventListener('visibilitychange', handleVisibilityChange, { passive: true });

        // Touch events for mobile
        document.addEventListener('touchstart', handleTouchStart, { passive: true });
        document.addEventListener('touchmove', handleTouchMove, { passive: true });
        document.addEventListener('touchend', handleTouchEnd, { passive: true });
    }

    /**
     * Mouse movement handler
     */
    function handleMouseMove(event) {
        const now = Date.now();
        const mouseEvent = {
            x: event.clientX,
            y: event.clientY,
            timestamp: now,
            target: event.target.tagName.toLowerCase()
        };

        // Calculate velocity if we have a previous event
        if (lastMouseEvent) {
            const timeDiff = now - lastMouseEvent.timestamp;
            const distance = Math.sqrt(
                Math.pow(mouseEvent.x - lastMouseEvent.x, 2) +
                Math.pow(mouseEvent.y - lastMouseEvent.y, 2)
            );
            mouseEvent.velocity = timeDiff > 0 ? distance / timeDiff : 0;
            mouseEvent.acceleration = lastMouseEvent.velocity ?
                (mouseEvent.velocity - lastMouseEvent.velocity) / timeDiff : 0;
        }

        behavioralData.mouseMovements.push(mouseEvent);
        lastMouseEvent = mouseEvent;

        // FIX: Increment the TOTAL count
        mouseMovementTotal++;

        // Limit array size (This limits the data sent to the server, NOT the counter)
        if (behavioralData.mouseMovements.length > CONFIG.maxMouseEvents) {
            behavioralData.mouseMovements.shift();
        }
    }

    /**
     * Click event handlers
     */
    function handleClick(event) {
        const clickEvent = {
            x: event.clientX,
            y: event.clientY,
            timestamp: Date.now(),
            button: event.button,
            target: event.target.tagName.toLowerCase(),
            targetId: event.target.id || null,
            targetClass: event.target.className || null
        };

        behavioralData.clickPatterns.push(clickEvent);

        // FIX: Increment the TOTAL count
        clickPatternTotal++;

        // Limit array size
        if (behavioralData.clickPatterns.length > CONFIG.maxClickEvents) {
            behavioralData.clickPatterns.shift();
        }
    }

    function handleMouseDown(event) {
        const now = Date.now();
        const mouseDownEvent = {
            x: event.clientX,
            y: event.clientY,
            timestamp: now,
            button: event.button,
            type: 'mousedown'
        };

        // Store for calculating click duration
        event.target._mouseDownTime = now;
        behavioralData.clickPatterns.push(mouseDownEvent);
    }

    function handleMouseUp(event) {
        const now = Date.now();
        const mouseUpEvent = {
            x: event.clientX,
            y: event.clientY,
            timestamp: now,
            button: event.button,
            type: 'mouseup'
        };

        // Calculate click duration
        if (event.target._mouseDownTime) {
            mouseUpEvent.duration = now - event.target._mouseDownTime;
            delete event.target._mouseDownTime;
        }

        behavioralData.clickPatterns.push(mouseUpEvent);
    }

    /**
     * Keyboard event handlers
     */
    function handleKeyDown(event) {
        keystrokeStartTime = Date.now();

        const keystrokeEvent = {
            key: event.key.length === 1 ? 'char' : event.key, // Anonymize actual characters
            keyCode: event.keyCode,
            timestamp: keystrokeStartTime,
            type: 'keydown',
            ctrlKey: event.ctrlKey,
            altKey: event.altKey,
            shiftKey: event.shiftKey,
            metaKey: event.metaKey
        };

        behavioralData.keystrokePatterns.push(keystrokeEvent);
        
        // FIX: Increment the TOTAL count
        keystrokePatternTotal++;
    }

    function handleKeyUp(event) {
        const now = Date.now();
        const keystrokeEvent = {
            key: event.key.length === 1 ? 'char' : event.key, // Anonymize actual characters
            keyCode: event.keyCode,
            timestamp: now,
            type: 'keyup',
            duration: keystrokeStartTime ? now - keystrokeStartTime : 0
        };

        behavioralData.keystrokePatterns.push(keystrokeEvent);

        // FIX: Increment the TOTAL count
        keystrokePatternTotal++;

        // Limit array size
        if (behavioralData.keystrokePatterns.length > CONFIG.maxKeystrokeEvents) {
            behavioralData.keystrokePatterns.shift();
        }
    }

    /**
     * Scroll event handlers
     */
    function handleScroll(event) {
        const scrollEvent = {
            scrollX: window.scrollX || window.pageXOffset,
            scrollY: window.scrollY || window.pageYOffset,
            timestamp: Date.now(),
            target: event.target === document ? 'document' : event.target.tagName.toLowerCase()
        };

        behavioralData.scrollPatterns.push(scrollEvent);

        // FIX: Increment the TOTAL count
        scrollPatternTotal++;

        // Limit array size
        if (behavioralData.scrollPatterns.length > CONFIG.maxScrollEvents) {
            behavioralData.scrollPatterns.shift();
        }
    }

    function handleWheel(event) {
        const wheelEvent = {
            deltaX: event.deltaX,
            deltaY: event.deltaY,
            deltaZ: event.deltaZ,
            deltaMode: event.deltaMode,
            timestamp: Date.now()
        };

        behavioralData.scrollPatterns.push(wheelEvent);

        // FIX: Increment the TOTAL count
        scrollPatternTotal++;
    }

    /**
     * Window focus/blur handlers
     */
    function handleWindowFocus(event) {
        behavioralData.windowEvents = behavioralData.windowEvents || [];
        behavioralData.windowEvents.push({
            type: 'focus',
            timestamp: Date.now()
        });
    }

    function handleWindowBlur(event) {
        behavioralData.windowEvents = behavioralData.windowEvents || [];
        behavioralData.windowEvents.push({
            type: 'blur',
            timestamp: Date.now()
        });
    }

    /**
     * Page visibility change handler
     */
    function handleVisibilityChange() {
        behavioralData.visibilityEvents = behavioralData.visibilityEvents || [];
        behavioralData.visibilityEvents.push({
            hidden: document.hidden,
            timestamp: Date.now(),
            visibilityState: document.visibilityState
        });
    }

    /**
     * Touch event handlers for mobile devices
     */
    function handleTouchStart(event) {
        if (event.touches.length > 0) {
            const touch = event.touches[0];
            const touchEvent = {
                x: touch.clientX,
                y: touch.clientY,
                timestamp: Date.now(),
                type: 'touchstart',
                touchCount: event.touches.length
            };
            behavioralData.touchEvents = behavioralData.touchEvents || [];
            behavioralData.touchEvents.push(touchEvent);
        }
    }

    function handleTouchMove(event) {
        if (event.touches.length > 0) {
            const touch = event.touches[0];
            const touchEvent = {
                x: touch.clientX,
                y: touch.clientY,
                timestamp: Date.now(),
                type: 'touchmove',
                touchCount: event.touches.length
            };
            behavioralData.touchEvents = behavioralData.touchEvents || [];
            behavioralData.touchEvents.push(touchEvent);
        }
    }

    function handleTouchEnd(event) {
        const touchEvent = {
            timestamp: Date.now(),
            type: 'touchend',
            touchCount: event.touches.length
        };
        behavioralData.touchEvents = behavioralData.touchEvents || [];
        behavioralData.touchEvents.push(touchEvent);
    }

    /**
     * Start periodic data collection
     */
    function startDataCollection() {
        dataCollectionTimer = setInterval(sendBehavioralData, CONFIG.dataCollectionInterval);
    }

    /**
     * Send behavioral data to server
     */
    function sendBehavioralData() {
        if (!behavioralData.sessionId || !isTracking) return;

        // Prepare data payload
        const payload = {
            sessionId: behavioralData.sessionId,
            // These arrays are limited to CONFIG.maxXXXEvents to save bandwidth
            mouseMovements: behavioralData.mouseMovements.slice(-CONFIG.maxMouseEvents),
            clickPatterns: behavioralData.clickPatterns.slice(-CONFIG.maxClickEvents),
            keystrokePatterns: behavioralData.keystrokePatterns.slice(-CONFIG.maxKeystrokeEvents),
            scrollPatterns: behavioralData.scrollPatterns.slice(-CONFIG.maxScrollEvents),
            deviceFingerprint: behavioralData.deviceFingerprint,
            timestamp: Date.now()
        };

        console.log('StealthCAPTCHA: Sending behavioral data', {
            sessionId: payload.sessionId,
            mouseEvents: payload.mouseMovements.length,
            clickEvents: payload.clickPatterns.length,
            keystrokeEvents: payload.keystrokePatterns.length,
            scrollEvents: payload.scrollPatterns.length
        });

        fetch(CONFIG.apiEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            console.log('StealthCAPTCHA: Data sent successfully', data);
            // Clear sent data but keep some for continuity (this is why we need total counters)
            behavioralData.mouseMovements = behavioralData.mouseMovements.slice(-10);
            behavioralData.clickPatterns = behavioralData.clickPatterns.slice(-10);
            behavioralData.keystrokePatterns = behavioralData.keystrokePatterns.slice(-10);
            behavioralData.scrollPatterns = behavioralData.scrollPatterns.slice(-10);
        })
        .catch(error => {
            console.log('StealthCAPTCHA: Data collection error', error.message);
        });
    }

    /**
     * Get current behavioral metrics for real-time analysis
     */
    function getCurrentMetrics() {
        const now = Date.now();
        const sessionDuration = now - behavioralData.startTime;

        // Calculate mouse movement metrics
        const mouseVelocities = behavioralData.mouseMovements
            .filter(m => m.velocity !== undefined)
            .map(m => m.velocity);

        // Calculate click intervals
        const clickIntervals = [];
        for (let i = 1; i < behavioralData.clickPatterns.length; i++) {
            const interval = behavioralData.clickPatterns[i].timestamp -
                            behavioralData.clickPatterns[i-1].timestamp;
            clickIntervals.push(interval);
        }

        // Calculate keystroke intervals
        const keystrokeIntervals = [];
        const keydownEvents = behavioralData.keystrokePatterns.filter(k => k.type === 'keydown');
        for (let i = 1; i < keydownEvents.length; i++) {
            const interval = keydownEvents[i].timestamp - keydownEvents[i-1].timestamp;
            keystrokeIntervals.push(interval);
        }

        return {
            sessionId: behavioralData.sessionId,
            sessionDuration: sessionDuration,
            
            // --- RETURN THE NEW TOTAL COUNTERS ---
            mouseEventCount: mouseMovementTotal,
            clickEventCount: clickPatternTotal,
            keystrokeEventCount: keystrokePatternTotal,
            scrollEventCount: scrollPatternTotal,
            // -------------------------------------

            avgMouseVelocity: mouseVelocities.length > 0 ?
                mouseVelocities.reduce((a, b) => a + b, 0) / mouseVelocities.length : 0,
            avgClickInterval: clickIntervals.length > 0 ?
                clickIntervals.reduce((a, b) => a + b, 0) / clickIntervals.length : 0,
            avgKeystrokeInterval: keystrokeIntervals.length > 0 ?
                keystrokeIntervals.reduce((a, b) => a + b, 0) / keystrokeIntervals.length : 0
        };
    }

    /**
     * Perform bot detection analysis
     */
    function detectBot(callback) {
        if (!behavioralData.sessionId) {
            callback({ error: 'No session data available' });
            return;
        }

        // Include the most recent event arrays so the server can analyze the CURRENT task data
        const detectionPayload = {
            sessionId: behavioralData.sessionId,
            page_url: window.location.pathname,
            action_type: 'general',
            // current event arrays (match server expected keys)
            mouseMovements: behavioralData.mouseMovements ? behavioralData.mouseMovements.slice(-CONFIG.maxMouseEvents) : [],
            clickPatterns: behavioralData.clickPatterns ? behavioralData.clickPatterns.slice(-CONFIG.maxClickEvents) : [],
            keystrokePatterns: behavioralData.keystrokePatterns ? behavioralData.keystrokePatterns.slice(-CONFIG.maxKeystrokeEvents) : [],
            scrollPatterns: behavioralData.scrollPatterns ? behavioralData.scrollPatterns.slice(-CONFIG.maxScrollEvents) : [],
            deviceFingerprint: behavioralData.deviceFingerprint || {},
            timestamp: Date.now()
        };

        fetch('/api/detect_bot', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(detectionPayload)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (typeof callback === 'function') {
                callback(data);
            }
        })
        .catch(error => {
            console.error('StealthCAPTCHA: Bot detection error:', error.message);
            if (typeof callback === 'function') {
                callback({ error: error.message });
            }
        });
    }

    /**
     * Stop behavioral tracking
     */
    function stop() {
        if (!isTracking) return;

        // Clear timer
        if (dataCollectionTimer) {
            clearInterval(dataCollectionTimer);
            dataCollectionTimer = null;
        }

        // Remove event listeners
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('click', handleClick);
        document.removeEventListener('mousedown', handleMouseDown);
        document.removeEventListener('mouseup', handleMouseUp);
        document.removeEventListener('keydown', handleKeyDown);
        document.removeEventListener('keyup', handleKeyUp);
        document.removeEventListener('scroll', handleScroll);
        window.removeEventListener('wheel', handleWheel);
        window.removeEventListener('focus', handleWindowFocus);
        window.removeEventListener('blur', handleWindowBlur);
        document.removeEventListener('visibilitychange', handleVisibilityChange);
        document.removeEventListener('touchstart', handleTouchStart);
        document.removeEventListener('touchmove', handleTouchMove);
        document.removeEventListener('touchend', handleTouchEnd);

        isTracking = false;
        console.log('StealthCAPTCHA: Behavioral tracking stopped');
    }

    // Public API
    window.behavioralTracker = {
        init: init,
        stop: stop,
        getCurrentMetrics: getCurrentMetrics,
        detectBot: detectBot,
        // Expose raw data (for debugging, but getCurrentMetrics should be used for display)
        getData: () => behavioralData, 
        behavioralData: behavioralData,
        isTracking: () => isTracking
    };

    function autoInit() {
        // Pass null instead of window.taskSessionId to ensure init runs, even if 
        // the taskSessionId variable is missing on this page.
        window.behavioralTracker.init(null);
    }

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', autoInit);
    } else {
        autoInit();
    }

})();