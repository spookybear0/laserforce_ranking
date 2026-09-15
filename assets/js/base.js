function localizeTimes() {
    const browserTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    document.querySelectorAll(".local-time-full").forEach(element => {
        const date = new Date(element.dateTime);

        const gameTimeZone = element.dataset.timezone;

        element.textContent = date.toLocaleString([], {
            dateStyle: "medium",
            timeStyle: "short",
            hourCycle: "h23"
        });

        // show that the time has been converted to user's local timezone if the game timezone is different from the browser timezone
        if (gameTimeZone && gameTimeZone !== browserTimeZone) {
            element.classList.add("font-bold");
        }
    });
    document.querySelectorAll(".local-time-only").forEach(element => {
        const date = new Date(element.dateTime);

        element.textContent = date.toLocaleString([], {
            timeStyle: "short",
            hourCycle: "h23"
        });
    });
}
function initDrawer() {
    const drawerCheckbox = document.getElementById('main-drawer');
    
    if (drawerCheckbox) {
        // get state from storage
        const isDrawerOpen = localStorage.getItem('drawer-open');
        
        // open if never set
        if (isDrawerOpen !== null) {
            drawerCheckbox.checked = isDrawerOpen === 'true';
        }

        // when toggled, save new state
        drawerCheckbox.addEventListener('change', (e) => {
            localStorage.setItem('drawer-open', e.target.checked);
        });
    }
}

document.addEventListener('DOMContentLoaded', () => {
    initDrawer();
    localizeTimes();
});

document.addEventListener("htmx:afterSwap", event => {
    localizeTimes();
});