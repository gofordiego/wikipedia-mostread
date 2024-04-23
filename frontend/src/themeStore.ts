type Listener = () => void

let theme = getTheme();

let listeners: Listener[] = [];

export const themeStore = {
    toggleTheme() {
        theme = (theme == 'light' ? 'dark' : 'light');
        storeTheme(theme);
        emitChange();
    },
    subscribe(listener: Listener) {
        listeners = [...listeners, listener];
        return () => {
            listeners = listeners.filter(l => l !== listener);
        };
    },
    getSnapshot() {
        return theme;
    }
};

function emitChange() {
    updateBootstrapTheme(theme);

    for (let listener of listeners) {
        listener();
    }
}

function getTheme() {
    const theme = fetchTheme();
    if (theme !== null) {
        return theme;
    }
    return getSystemTheme();
}

function getSystemTheme(): string {
    return window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
}

function fetchTheme() {
    return localStorage.getItem('theme');
}

function storeTheme(theme: string) {
    localStorage.setItem('theme', theme);
}

export function updateBootstrapTheme(theme: string) {
    if (theme !== null) {
        document.documentElement.setAttribute('data-bs-theme', theme);
    }
}

window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', () => {
    const storedTheme = fetchTheme()
    if (storedTheme === null) {
        theme = getSystemTheme();
        emitChange();
    }
});
