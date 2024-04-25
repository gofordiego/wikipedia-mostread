import { useEffect, useSyncExternalStore } from "react";


type Listener = () => void

let listeners: Listener[] = [];


export function useTheme() {
    const theme = useSyncExternalStore(subscribe, getTheme);

    useEffect(() => {
        updateBootstrapTheme(theme);
        window.matchMedia('(prefers-color-scheme: light)').addEventListener('change', handleSystemThemeChange)
        return () => {
            window.matchMedia('(prefers-color-scheme: light)').removeEventListener('change', handleSystemThemeChange)
        };
    }, []);

    return theme;
}

export function toggleTheme(theme: string) {
    const newTheme = (theme == 'light' ? 'dark' : 'light');
    setStoredTheme(newTheme);
    emitChange(newTheme);
}


function updateBootstrapTheme(theme: string) {
    if (theme !== null) {
        document.documentElement.setAttribute('data-bs-theme', theme);
    }
}

function subscribe(listener: Listener) {
    listeners = [...listeners, listener];
    return () => {
        listeners = listeners.filter(l => l !== listener);
    };
}

function getTheme(): string {
    const theme = getStoredTheme();
    if (theme !== null) {
        return theme;
    }
    return getSystemTheme();
}

function emitChange(theme: string) {
    updateBootstrapTheme(theme);

    for (let listener of listeners) {
        listener();
    }
}

function getSystemTheme(): string {
    return window.matchMedia('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
}

function getStoredTheme() {
    return localStorage.getItem('theme');
}

function setStoredTheme(theme: string) {
    localStorage.setItem('theme', theme);
}

function handleSystemThemeChange() {
    const storedTheme = getStoredTheme();
    if (storedTheme === null) {
        const theme = getSystemTheme();
        emitChange(theme);
    }
}
