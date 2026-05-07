/* stream.js — Pi Camera v2 stream page */

'use strict';

// ── Debounce helper for sliders ──────────────────────────────────────────────

let exposureTimer = null;
let gainTimer     = null;

function debounce(fn, delay) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
}

// ── Status helper ────────────────────────────────────────────────────────────

function setStatus(msg, isError = false) {
    const el = document.getElementById('status');
    el.textContent = msg;
    el.className   = 'status' + (isError ? ' error' : '');
    if (msg) setTimeout(() => { if (el.textContent === msg) el.textContent = ''; }, 4000);
}

// ── Stream reload ─────────────────────────────────────────────────────────────

function reloadStream(delayMs = 1000) {
    setTimeout(() => {
        const img = document.getElementById('videoStream');
        img.src   = '/video_feed?t=' + Date.now();
        setStatus('');
    }, delayMs);
}

// ── Stream settings ───────────────────────────────────────────────────────────

function applyStreamSettings() {
    const resolution = document.getElementById('resolution').value;
    const framerate  = parseInt(document.getElementById('framerate').value);
    setStatus('Applying settings…');

    fetch('/update_settings', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ resolution, framerate }),
    })
    .then(r => r.json())
    .then(data => {
        document.getElementById('currentRes').textContent = data.resolution;
        document.getElementById('currentFps').textContent = data.framerate;
        setStatus('Settings updated — reloading stream…');
        reloadStream(1000);
    })
    .catch(() => setStatus('Failed to update settings', true));
}

// ── Rotation ──────────────────────────────────────────────────────────────────

function rotateCamera() {
    setStatus('Rotating…');
    fetch('/rotate', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
        document.getElementById('currentRotation').textContent = data.rotation;
        setStatus('Rotated — reloading stream…');
        reloadStream(1000);
    })
    .catch(() => setStatus('Rotation failed', true));
}

// ── Capture ───────────────────────────────────────────────────────────────────

function captureImage() {
    setStatus('📷 Capturing full-res still…');
    fetch('/capture', { method: 'POST' })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            setStatus('✓ Saved: ' + data.filename + ' (' + data.resolution + ')');
        } else {
            setStatus('✗ Capture failed: ' + data.error, true);
        }
    })
    .catch(() => setStatus('Capture request failed', true));
}

// ── Exposure controls ─────────────────────────────────────────────────────────

function onExposureModeChange() {
    const mode     = document.getElementById('exposureMode').value;
    const manPanel = document.getElementById('manualExposureControls');
    manPanel.style.display = (mode === 'manual') ? 'flex' : 'none';

    pushExposure();
}

function onExposureSlider() {
    const us = parseInt(document.getElementById('exposureSlider').value);
    document.getElementById('exposureDisplay').textContent = (us / 1000).toFixed(1) + ' ms';
    clearTimeout(exposureTimer);
    exposureTimer = setTimeout(pushExposure, 150);
}

function onGainSlider() {
    const gain = parseFloat(document.getElementById('gainSlider').value);
    document.getElementById('gainDisplay').textContent = gain.toFixed(1) + '×';
    clearTimeout(gainTimer);
    gainTimer = setTimeout(pushExposure, 150);
}

function onNoiseMode() {
    pushExposure();
}

function pushExposure() {
    const mode      = document.getElementById('exposureMode').value;
    const isAuto    = (mode === 'auto');
    const exposureUs = parseInt(document.getElementById('exposureSlider').value);
    const gain       = parseFloat(document.getElementById('gainSlider').value);
    const noiseMode  = parseInt(document.getElementById('noiseMode').value);

    fetch('/set_exposure', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
            auto:        isAuto,
            exposure_us: exposureUs,
            gain:        gain,
            noise_mode:  noiseMode,
        }),
    })
    .catch(() => setStatus('Failed to update exposure', true));
}
