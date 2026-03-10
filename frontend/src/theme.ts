import { createTheme, alpha } from '@mui/material/styles';

const darkTokens = {
    primary: '#3B82F6',
    secondary: '#2563EB',
    bgBase: '#09090B',
    bgSurface: '#0F1117',
    bgElevated: '#181B25',
    textPrimary: '#F8FAFC',
    textSecondary: '#A1A1AA',
    textMuted: '#71717A',
    border: 'rgba(161, 161, 170, 0.10)',
    borderHover: 'rgba(161, 161, 170, 0.20)',
    success: '#22C55E',
    warning: '#EAB308',
    error: '#EF4444',
    info: '#3B82F6',
};

const lightTokens = {
    primary: '#3B82F6',
    secondary: '#2563EB',
    bgBase: '#F8FAFC',
    bgSurface: '#FFFFFF',
    bgElevated: '#F1F5F9',
    textPrimary: '#0F172A',
    textSecondary: '#64748B',
    textMuted: '#94A3B8',
    border: 'rgba(15, 23, 42, 0.10)',
    borderHover: 'rgba(15, 23, 42, 0.20)',
    success: '#16A34A',
    warning: '#CA8A04',
    error: '#DC2626',
    info: '#3B82F6',
};

// ─── Design Tokens ────────────────────────────────────────────────
// Exported as CSS variables for existing components
export const palette = {
    primary: 'var(--color-primary)',
    secondary: 'var(--color-secondary)',
    bgBase: 'var(--color-bg-base)',
    bgSurface: 'var(--color-bg-surface)',
    bgElevated: 'var(--color-bg-elevated)',
    textPrimary: 'var(--color-text-primary)',
    textSecondary: 'var(--color-text-secondary)',
    textMuted: 'var(--color-text-muted)',
    border: 'var(--color-border)',
    borderHover: 'var(--color-border-hover)',
    success: 'var(--color-success)',
    warning: 'var(--color-warning)',
    error: 'var(--color-error)',
    info: 'var(--color-info)',
};

// ─── Semantic Overlays ────────────────────────────────────────────
export const overlays = {
    primaryGlow: 'var(--color-primary-glow)',
    primaryGlowSubtle: 'var(--color-primary-glow-subtle)',
    primaryGlowFaint: 'var(--color-primary-glow-faint)',
    overlayLight: 'var(--color-overlay-light)',
    overlayDark: 'var(--color-overlay-dark)',
    warningSubtle: 'var(--color-warning-subtle)',
    heroGradient: `radial-gradient(ellipse at 50% 0%, var(--color-primary-glow) 0%, transparent 70%)`,
    heroGradientSubtle: `radial-gradient(ellipse at 50% 0%, var(--color-primary-glow-subtle) 0%, transparent 60%)`,
};

const radius = {
    sm: 8,
    md: 10,
    lg: 12,
    xl: 16,
    full: 9999,
};

// ─── Theme ────────────────────────────────────────────────────────
export const getThemeByMode = (mode: 'light' | 'dark') => {
    const tokens = mode === 'light' ? lightTokens : darkTokens;
    return createTheme({
        palette: {
            mode,
            primary: {
                main: tokens.primary,
                light: '#60A5FA',
                dark: tokens.secondary,
            },
            secondary: {
                main: tokens.secondary,
            },
            background: {
                default: tokens.bgBase,
                paper: tokens.bgSurface,
            },
            text: {
                primary: tokens.textPrimary,
                secondary: tokens.textSecondary,
            },
            divider: tokens.border,
            success: { main: tokens.success },
            warning: { main: tokens.warning },
            error: { main: tokens.error },
            info: { main: tokens.info },
        },

        typography: {
            fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
            fontSize: 14,
            h1: { fontSize: '2.25rem', fontWeight: 700, lineHeight: 1.2, letterSpacing: '-0.025em' },
            h2: { fontSize: '1.875rem', fontWeight: 700, lineHeight: 1.25, letterSpacing: '-0.02em' },
            h3: { fontSize: '1.5rem', fontWeight: 600, lineHeight: 1.3, letterSpacing: '-0.015em' },
            h4: { fontSize: '1.25rem', fontWeight: 600, lineHeight: 1.35 },
            h5: { fontSize: '1.125rem', fontWeight: 600, lineHeight: 1.4 },
            h6: { fontSize: '1rem', fontWeight: 600, lineHeight: 1.5 },
            body1: { fontSize: '0.9375rem', lineHeight: 1.6 },
            body2: { fontSize: '0.8125rem', lineHeight: 1.5 },
            caption: { fontSize: '0.75rem', lineHeight: 1.5, color: tokens.textMuted },
            button: { textTransform: 'none', fontWeight: 600, fontSize: '0.875rem' },
        },

        shape: {
            borderRadius: radius.md,
        },

        shadows: [
            'none',
            `0 1px 2px ${alpha('#000', mode === 'light' ? 0.1 : 0.3)}`,
            `0 1px 3px ${alpha('#000', mode === 'light' ? 0.1 : 0.3)}, 0 1px 2px ${alpha('#000', mode === 'light' ? 0.05 : 0.2)}`,
            `0 4px 6px ${alpha('#000', mode === 'light' ? 0.1 : 0.25)}`,
            `0 10px 15px ${alpha('#000', mode === 'light' ? 0.1 : 0.2)}`,
            `0 20px 25px ${alpha('#000', mode === 'light' ? 0.1 : 0.15)}`,
            ...Array(19).fill(`0 20px 25px ${alpha('#000', mode === 'light' ? 0.1 : 0.15)}`),
        ] as any,

        components: {
            MuiCssBaseline: {
                styleOverrides: {
                    body: {
                        backgroundColor: tokens.bgBase,
                        color: tokens.textPrimary,
                    },
                },
            },
            MuiButton: {
                defaultProps: { disableElevation: true },
                styleOverrides: {
                    root: {
                        borderRadius: radius.md,
                        padding: '10px 20px',
                        fontWeight: 600,
                        fontSize: '0.875rem',
                        transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                    },
                    contained: {
                        backgroundColor: tokens.primary,
                        color: '#FFFFFF',
                        '&:hover': {
                            backgroundColor: tokens.secondary,
                            transform: 'translateY(-1px)',
                            boxShadow: `0 4px 12px ${alpha(tokens.primary, 0.4)}`,
                        },
                        '&:active': { transform: 'translateY(0)' },
                    },
                    outlined: {
                        borderColor: alpha(tokens.primary, 0.5),
                        color: tokens.primary,
                        backgroundColor: 'transparent',
                        '&:hover': {
                            borderColor: tokens.primary,
                            backgroundColor: alpha(tokens.primary, 0.08),
                        },
                    },
                    text: {
                        color: tokens.textSecondary,
                        '&:hover': {
                            backgroundColor: alpha(tokens.textPrimary, 0.05),
                            color: tokens.textPrimary,
                        },
                    },
                    sizeSmall: { padding: '6px 14px', fontSize: '0.8125rem' },
                    sizeLarge: { padding: '14px 28px', fontSize: '1rem' },
                },
            },
            MuiIconButton: {
                styleOverrides: {
                    root: {
                        borderRadius: radius.sm,
                        transition: 'all 0.2s ease',
                        '&:hover': { backgroundColor: alpha(tokens.textPrimary, 0.06) },
                    },
                },
            },
            MuiPaper: {
                defaultProps: { elevation: 0 },
                styleOverrides: {
                    root: {
                        backgroundColor: tokens.bgSurface,
                        backgroundImage: 'none',
                        border: `1px solid ${tokens.border}`,
                        borderRadius: radius.lg,
                    },
                },
            },
            MuiCard: {
                defaultProps: { elevation: 0 },
                styleOverrides: {
                    root: {
                        backgroundColor: tokens.bgSurface,
                        backgroundImage: 'none',
                        border: `1px solid ${tokens.border}`,
                        borderRadius: radius.lg,
                        transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                        '&:hover': {
                            borderColor: tokens.borderHover,
                            boxShadow: `0 4px 16px ${alpha('#000', mode === 'light' ? 0.05 : 0.2)}`,
                        },
                    },
                },
            },
            MuiCardContent: {
                styleOverrides: {
                    root: { padding: '24px', '&:last-child': { paddingBottom: '24px' } },
                },
            },
            MuiTextField: {
                defaultProps: { variant: 'outlined' },
                styleOverrides: {
                    root: {
                        '& .MuiOutlinedInput-root': {
                            borderRadius: radius.md,
                            backgroundColor: alpha(tokens.textPrimary, 0.03),
                            transition: 'all 0.2s ease',
                            '& fieldset': {
                                borderColor: tokens.border,
                                transition: 'border-color 0.2s ease',
                            },
                            '&:hover fieldset': { borderColor: tokens.borderHover },
                            '&.Mui-focused fieldset': {
                                borderColor: tokens.primary,
                                borderWidth: '1.5px',
                            },
                        },
                        '& .MuiInputLabel-root': {
                            color: tokens.textMuted,
                            '&.Mui-focused': { color: tokens.primary },
                        },
                    },
                },
            },
            MuiSelect: { styleOverrides: { root: { borderRadius: radius.md } } },
            MuiOutlinedInput: {
                styleOverrides: {
                    root: {
                        borderRadius: radius.md,
                        '& .MuiOutlinedInput-notchedOutline': { borderColor: tokens.border },
                        '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: tokens.borderHover },
                        '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: tokens.primary },
                    },
                },
            },
            MuiChip: {
                styleOverrides: {
                    root: { borderRadius: radius.full, fontWeight: 500, fontSize: '0.75rem' },
                    sizeSmall: { height: 24 },
                },
            },
            MuiTableContainer: { styleOverrides: { root: { borderRadius: radius.lg } } },
            MuiTableHead: {
                styleOverrides: {
                    root: {
                        '& .MuiTableCell-head': {
                            backgroundColor: alpha(tokens.textPrimary, 0.03),
                            color: tokens.textSecondary,
                            fontWeight: 600,
                            fontSize: '0.75rem',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            borderBottom: `1px solid ${tokens.border}`,
                            padding: '12px 16px',
                        },
                    },
                },
            },
            MuiTableBody: {
                styleOverrides: {
                    root: {
                        '& .MuiTableRow-root': {
                            transition: 'background-color 0.15s ease',
                            '&:hover': { backgroundColor: alpha(tokens.textPrimary, 0.03) },
                        },
                    },
                },
            },
            MuiTableCell: {
                styleOverrides: {
                    root: {
                        borderBottom: `1px solid ${tokens.border}`,
                        padding: '14px 16px',
                        fontSize: '0.875rem',
                    },
                },
            },
            MuiTablePagination: { styleOverrides: { root: { color: tokens.textSecondary } } },
            MuiDialog: {
                styleOverrides: {
                    paper: {
                        borderRadius: radius.xl,
                        backgroundColor: tokens.bgElevated,
                        border: `1px solid ${tokens.border}`,
                        backgroundImage: 'none',
                    },
                },
            },
            MuiDialogTitle: {
                styleOverrides: { root: { fontSize: '1.125rem', fontWeight: 600, padding: '24px 24px 16px' } },
            },
            MuiDialogContent: { styleOverrides: { root: { padding: '8px 24px 24px' } } },
            MuiDialogActions: { styleOverrides: { root: { padding: '16px 24px 24px' } } },
            MuiAlert: { styleOverrides: { root: { borderRadius: radius.md } } },
            MuiLinearProgress: {
                styleOverrides: {
                    root: {
                        borderRadius: radius.full,
                        backgroundColor: alpha(tokens.textPrimary, 0.08),
                    },
                    bar: {
                        borderRadius: radius.full,
                        backgroundColor: tokens.primary,
                    },
                },
            },
            MuiCircularProgress: { styleOverrides: { root: { color: tokens.primary } } },
            MuiTypography: { styleOverrides: { root: { color: tokens.textPrimary } } },
            MuiDivider: { styleOverrides: { root: { borderColor: tokens.border } } },
            MuiListItemIcon: {
                styleOverrides: {
                    root: { color: tokens.textSecondary, minWidth: 36 },
                },
            },
            MuiSnackbar: {
                styleOverrides: {
                    root: { '& .MuiPaper-root': { borderRadius: radius.md } },
                },
            },
            MuiCheckbox: {
                styleOverrides: {
                    root: {
                        color: tokens.textMuted,
                        '&.Mui-checked': { color: tokens.primary },
                    },
                },
            },
            MuiAvatar: {
                styleOverrides: {
                    root: {
                        backgroundColor: alpha(tokens.primary, 0.15),
                        color: tokens.primary,
                    },
                },
            },
            MuiTooltip: {
                styleOverrides: {
                    tooltip: {
                        backgroundColor: tokens.bgElevated,
                        border: `1px solid ${tokens.border}`,
                        borderRadius: radius.sm,
                        fontSize: '0.75rem',
                        padding: '8px 12px',
                    },
                },
            },
            MuiMenu: {
                styleOverrides: {
                    paper: {
                        backgroundColor: tokens.bgElevated,
                        border: `1px solid ${tokens.border}`,
                        borderRadius: radius.md,
                        backgroundImage: 'none',
                    },
                },
            },
            MuiMenuItem: {
                styleOverrides: {
                    root: {
                        borderRadius: radius.sm,
                        margin: '2px 6px',
                        padding: '8px 12px',
                        fontSize: '0.875rem',
                        '&:hover': { backgroundColor: alpha(tokens.textPrimary, 0.05) },
                    },
                },
            },
            MuiFormControlLabel: { styleOverrides: { label: { fontSize: '0.875rem' } } },
            MuiInputLabel: {
                styleOverrides: {
                    root: {
                        color: tokens.textMuted,
                        '&.Mui-focused': { color: tokens.primary },
                    },
                },
            },
            MuiTab: {
                styleOverrides: {
                    root: {
                        textTransform: 'none',
                        fontWeight: 500,
                        fontSize: '0.875rem',
                        minHeight: 40,
                        borderRadius: radius.sm,
                        '&.Mui-selected': { color: tokens.primary },
                    },
                },
            },
        },
    });
};

const theme = getThemeByMode('dark');
export default theme;
