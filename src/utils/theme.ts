// Light/Dark theme support for ClimaCred AI.
// The preference is persisted in localStorage and applied as a `.dark` class on
// <html>, which the Tailwind v4 custom variant in src/index.css uses.

import { useCallback, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark';

const THEME_STORAGE_KEY = 'climacred_theme';
const SWITCHING_CLASS = 'theme-switching';

export function getStoredTheme(): ThemeMode {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // localStorage can be unavailable (private mode) - fall back to light
  }
  return 'light';
}

export function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement;
  // Only add the transition helper while switching so existing hover/transform
  // transitions in the app keep working unchanged.
  root.classList.add(SWITCHING_CLASS);
  root.classList.toggle('dark', mode === 'dark');
  root.setAttribute('data-theme', mode);
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch {
    // ignore persistence errors
  }
  window.setTimeout(() => root.classList.remove(SWITCHING_CLASS), 260);
}

/** Applied once before the app renders to avoid a light-mode flash. */
export function initTheme(): ThemeMode {
  const mode = getStoredTheme();
  applyTheme(mode);
  return mode;
}

export function useTheme(): { theme: ThemeMode; toggleTheme: () => void } {
  const [theme, setTheme] = useState<ThemeMode>(getStoredTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  // Keep multiple browser tabs in sync
  useEffect(() => {
    const onStorage = (event: StorageEvent) => {
      if (event.key === THEME_STORAGE_KEY && (event.newValue === 'dark' || event.newValue === 'light')) {
        setTheme(event.newValue);
      }
    };
    window.addEventListener('storage', onStorage);
    return () => window.removeEventListener('storage', onStorage);
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, toggleTheme };
}
