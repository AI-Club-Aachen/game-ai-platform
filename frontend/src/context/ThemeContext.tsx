import React, { createContext, useContext, useState, useEffect } from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import { getThemeByMode } from '../theme';

type ThemeMode = 'light' | 'dark';

interface ThemeContextType {
    mode: ThemeMode;
    toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function AppThemeProvider({ children }: { children: React.ReactNode }) {
    const [mode, setMode] = useState<ThemeMode>(() => {
        const saved = localStorage.getItem('theme_mode');
        return (saved === 'light' || saved === 'dark') ? saved : 'dark';
    });

    useEffect(() => {
        document.documentElement.setAttribute('data-theme', mode);
        localStorage.setItem('theme_mode', mode);
    }, [mode]);

    const toggleTheme = () => setMode(prev => prev === 'dark' ? 'light' : 'dark');

    const muiTheme = getThemeByMode(mode);

    return (
        <ThemeContext.Provider value={{ mode, toggleTheme }}>
            <MuiThemeProvider theme={muiTheme}>
                {children}
            </MuiThemeProvider>
        </ThemeContext.Provider>
    );
}

export const useAppTheme = () => {
    const context = useContext(ThemeContext);
    if (!context) throw new Error('useAppTheme must be used within AppThemeProvider');
    return context;
};
