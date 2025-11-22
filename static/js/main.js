const socket = io();

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('state_change', (data) => {
    console.log('State changed:', data);
    if (data.error) {
        alert(data.error);
    }
    // Reload the page to fetch the new state-dependent UI
    // In a full SPA we would update the DOM, but for this "dumb app" approach, reload is fine/requested
    window.location.reload();
});

// Simple timer logic
function startTimer(elementId, deadline) {
    const el = document.getElementById(elementId);
    if (!el) return;

    function update() {
        const now = new Date().getTime();
        const distance = deadline - now;

        if (distance < 0) {
            el.innerHTML = "00:00";
            // Optionally emit 'timer_expired' or similar if we wanted strict client enforcement,
            // but server should handle timeouts ideally.
            return;
        }

        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        el.innerHTML = (minutes < 10 ? "0" + minutes : minutes) + ":" + (seconds < 10 ? "0" + seconds : seconds);
    }

    update();
    setInterval(update, 1000);
}

document.addEventListener('DOMContentLoaded', () => {
    // Initialize timers based on data-deadline attribute
    const timerElements = document.querySelectorAll('[data-deadline]');
    timerElements.forEach(el => {
        const deadline = parseInt(el.getAttribute('data-deadline'));
        if (!isNaN(deadline)) {
            startTimer(el.id, deadline);
        }
    });

    // Mobile menu toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');

    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', () => {
            mobileMenu.classList.toggle('hidden');
        });
    }
});
