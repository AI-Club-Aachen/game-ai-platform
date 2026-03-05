import { createTheme, alpha } from '@mui/material/styles';

// ─── Design Tokens ────────────────────────────────────────────────
const palette = {
    primary: '#19B5FF',
    secondary: '#1984CD',
    bgBase: '#0B0F1A',
    bgSurface: '#111827',
    bgElevated: '#1A2332',
    textPrimary: '#F1F5F9',
    textSecondary: '#94A3B8',
    textMuted: '#64748B',
    border: 'rgba(148, 163, 184, 0.08)',
    borderHover: 'rgba(148, 163, 184, 0.16)',
    success: '#10B981',
    warning: '#F59E0B',
    error: '#EF4444',
    info: '#19B5FF',
};

const radius = {
    sm: 8,
    md: 10,
    lg: 12,
    xl: 16,
    full: 9999,
};

// ─── Theme ────────────────────────────────────────────────────────
const theme = createTheme({
    palette: {
        mode: 'dark',
        primary: {
            main: palette.primary,
            light: '#47C5FF',
            dark: palette.secondary,
        },
        secondary: {
            main: palette.secondary,
        },
        background: {
            default: palette.bgBase,
            paper: palette.bgSurface,
        },
        text: {
            primary: palette.textPrimary,
            secondary: palette.textSecondary,
        },
        divider: palette.border,
        success: { main: palette.success },
        warning: { main: palette.warning },
        error: { main: palette.error },
        info: { main: palette.info },
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
        caption: { fontSize: '0.75rem', lineHeight: 1.5, color: palette.textMuted },
        button: { textTransform: 'none', fontWeight: 600, fontSize: '0.875rem' },
    },

    shape: {
        borderRadius: radius.md,
    },

    shadows: [
        'none',
        `0 1px 2px ${alpha('#000', 0.3)}`,
        `0 1px 3px ${alpha('#000', 0.3)}, 0 1px 2px ${alpha('#000', 0.2)}`,
        `0 4px 6px ${alpha('#000', 0.25)}`,
        `0 10px 15px ${alpha('#000', 0.2)}`,
        `0 20px 25px ${alpha('#000', 0.15)}`,
        // Fill remaining shadow slots with the same value
        ...Array(19).fill(`0 20px 25px ${alpha('#000', 0.15)}`),
    ] as any,

    components: {
        // ── Global ──────────────────────────────────────────────
        MuiCssBaseline: {
            styleOverrides: {
                body: {
                    backgroundColor: palette.bgBase,
                    color: palette.textPrimary,
                },
            },
        },

        // ── Buttons ─────────────────────────────────────────────
        MuiButton: {
            defaultProps: {
                disableElevation: true,
            },
            styleOverrides: {
                root: {
                    borderRadius: radius.md,
                    padding: '10px 20px',
                    fontWeight: 600,
                    fontSize: '0.875rem',
                    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                },
                contained: {
                    backgroundColor: palette.primary,
                    color: '#FFFFFF',
                    '&:hover': {
                        backgroundColor: palette.secondary,
                        transform: 'translateY(-1px)',
                        boxShadow: `0 4px 12px ${alpha(palette.primary, 0.4)}`,
                    },
                    '&:active': {
                        transform: 'translateY(0)',
                    },
                },
                outlined: {
                    borderColor: alpha(palette.primary, 0.5),
                    color: palette.primary,
                    backgroundColor: 'transparent',
                    '&:hover': {
                        borderColor: palette.primary,
                        backgroundColor: alpha(palette.primary, 0.08),
                    },
                },
                text: {
                    color: palette.textSecondary,
                    '&:hover': {
                        backgroundColor: alpha(palette.textPrimary, 0.05),
                        color: palette.textPrimary,
                    },
                },
                sizeSmall: {
                    padding: '6px 14px',
                    fontSize: '0.8125rem',
                },
                sizeLarge: {
                    padding: '14px 28px',
                    fontSize: '1rem',
                },
            },
        },

        MuiIconButton: {
            styleOverrides: {
                root: {
                    borderRadius: radius.sm,
                    transition: 'all 0.2s ease',
                    '&:hover': {
                        backgroundColor: alpha(palette.textPrimary, 0.06),
                    },
                },
            },
        },

        // ── Cards & Surfaces ────────────────────────────────────
        MuiPaper: {
            defaultProps: {
                elevation: 0,
            },
            styleOverrides: {
                root: {
                    backgroundColor: palette.bgSurface,
                    backgroundImage: 'none',
                    border: `1px solid ${palette.border}`,
                    borderRadius: radius.lg,
                },
            },
        },

        MuiCard: {
            defaultProps: {
                elevation: 0,
            },
            styleOverrides: {
                root: {
                    backgroundColor: palette.bgSurface,
                    backgroundImage: 'none',
                    border: `1px solid ${palette.border}`,
                    borderRadius: radius.lg,
                    transition: 'all 0.25s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&:hover': {
                        borderColor: palette.borderHover,
                        boxShadow: `0 4px 16px ${alpha('#000', 0.2)}`,
                    },
                },
            },
        },

        MuiCardContent: {
            styleOverrides: {
                root: {
                    padding: '24px',
                    '&:last-child': {
                        paddingBottom: '24px',
                    },
                },
            },
        },

        // ── Inputs ──────────────────────────────────────────────
        MuiTextField: {
            defaultProps: {
                variant: 'outlined',
            },
            styleOverrides: {
                root: {
                    '& .MuiOutlinedInput-root': {
                        borderRadius: radius.md,
                        backgroundColor: alpha(palette.textPrimary, 0.03),
                        transition: 'all 0.2s ease',
                        '& fieldset': {
                            borderColor: palette.border,
                            transition: 'border-color 0.2s ease',
                        },
                        '&:hover fieldset': {
                            borderColor: palette.borderHover,
                        },
                        '&.Mui-focused fieldset': {
                            borderColor: palette.primary,
                            borderWidth: '1.5px',
                        },
                    },
                    '& .MuiInputLabel-root': {
                        color: palette.textMuted,
                        '&.Mui-focused': {
                            color: palette.primary,
                        },
                    },
                },
            },
        },

        MuiSelect: {
            styleOverrides: {
                root: {
                    borderRadius: radius.md,
                },
            },
        },

        MuiOutlinedInput: {
            styleOverrides: {
                root: {
                    borderRadius: radius.md,
                    '& .MuiOutlinedInput-notchedOutline': {
                        borderColor: palette.border,
                    },
                    '&:hover .MuiOutlinedInput-notchedOutline': {
                        borderColor: palette.borderHover,
                    },
                    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                        borderColor: palette.primary,
                    },
                },
            },
        },

        // ── Chips & Badges ──────────────────────────────────────
        MuiChip: {
            styleOverrides: {
                root: {
                    borderRadius: radius.full,
                    fontWeight: 500,
                    fontSize: '0.75rem',
                },
                sizeSmall: {
                    height: 24,
                },
            },
        },

        // ── Tables ──────────────────────────────────────────────
        MuiTableContainer: {
            styleOverrides: {
                root: {
                    borderRadius: radius.lg,
                },
            },
        },

        MuiTableHead: {
            styleOverrides: {
                root: {
                    '& .MuiTableCell-head': {
                        backgroundColor: alpha(palette.textPrimary, 0.03),
                        color: palette.textSecondary,
                        fontWeight: 600,
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        borderBottom: `1px solid ${palette.border}`,
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
                        '&:hover': {
                            backgroundColor: alpha(palette.textPrimary, 0.03),
                        },
                    },
                },
            },
        },

        MuiTableCell: {
            styleOverrides: {
                root: {
                    borderBottom: `1px solid ${palette.border}`,
                    padding: '14px 16px',
                    fontSize: '0.875rem',
                },
            },
        },

        MuiTablePagination: {
            styleOverrides: {
                root: {
                    color: palette.textSecondary,
                },
            },
        },

        // ── Dialogs ─────────────────────────────────────────────
        MuiDialog: {
            styleOverrides: {
                paper: {
                    borderRadius: radius.xl,
                    backgroundColor: palette.bgElevated,
                    border: `1px solid ${palette.border}`,
                    backgroundImage: 'none',
                },
            },
        },

        MuiDialogTitle: {
            styleOverrides: {
                root: {
                    fontSize: '1.125rem',
                    fontWeight: 600,
                    padding: '24px 24px 16px',
                },
            },
        },

        MuiDialogContent: {
            styleOverrides: {
                root: {
                    padding: '8px 24px 24px',
                },
            },
        },

        MuiDialogActions: {
            styleOverrides: {
                root: {
                    padding: '16px 24px 24px',
                },
            },
        },

        // ── Alerts ──────────────────────────────────────────────
        MuiAlert: {
            styleOverrides: {
                root: {
                    borderRadius: radius.md,
                },
            },
        },

        // ── Progress ────────────────────────────────────────────
        MuiLinearProgress: {
            styleOverrides: {
                root: {
                    borderRadius: radius.full,
                    backgroundColor: alpha(palette.textPrimary, 0.08),
                },
                bar: {
                    borderRadius: radius.full,
                    backgroundColor: palette.primary,
                },
            },
        },

        MuiCircularProgress: {
            styleOverrides: {
                root: {
                    color: palette.primary,
                },
            },
        },

        // ── Typography ──────────────────────────────────────────
        MuiTypography: {
            styleOverrides: {
                root: {
                    color: palette.textPrimary,
                },
            },
        },

        // ── Divider ─────────────────────────────────────────────
        MuiDivider: {
            styleOverrides: {
                root: {
                    borderColor: palette.border,
                },
            },
        },

        // ── Lists ───────────────────────────────────────────────
        MuiListItemIcon: {
            styleOverrides: {
                root: {
                    color: palette.textSecondary,
                    minWidth: 36,
                },
            },
        },

        // ── Snackbar ────────────────────────────────────────────
        MuiSnackbar: {
            styleOverrides: {
                root: {
                    '& .MuiPaper-root': {
                        borderRadius: radius.md,
                    },
                },
            },
        },

        // ── Checkbox ────────────────────────────────────────────
        MuiCheckbox: {
            styleOverrides: {
                root: {
                    color: palette.textMuted,
                    '&.Mui-checked': {
                        color: palette.primary,
                    },
                },
            },
        },

        // ── Avatar ──────────────────────────────────────────────
        MuiAvatar: {
            styleOverrides: {
                root: {
                    backgroundColor: alpha(palette.primary, 0.15),
                    color: palette.primary,
                },
            },
        },

        // ── Tooltip ─────────────────────────────────────────────
        MuiTooltip: {
            styleOverrides: {
                tooltip: {
                    backgroundColor: palette.bgElevated,
                    border: `1px solid ${palette.border}`,
                    borderRadius: radius.sm,
                    fontSize: '0.75rem',
                    padding: '8px 12px',
                },
            },
        },

        // ── Menu ────────────────────────────────────────────────
        MuiMenu: {
            styleOverrides: {
                paper: {
                    backgroundColor: palette.bgElevated,
                    border: `1px solid ${palette.border}`,
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
                    '&:hover': {
                        backgroundColor: alpha(palette.textPrimary, 0.05),
                    },
                },
            },
        },

        // ── FormControl ─────────────────────────────────────────
        MuiFormControlLabel: {
            styleOverrides: {
                label: {
                    fontSize: '0.875rem',
                },
            },
        },

        MuiInputLabel: {
            styleOverrides: {
                root: {
                    color: palette.textMuted,
                    '&.Mui-focused': {
                        color: palette.primary,
                    },
                },
            },
        },

        // ── Tabs ────────────────────────────────────────────────
        MuiTab: {
            styleOverrides: {
                root: {
                    textTransform: 'none',
                    fontWeight: 500,
                    fontSize: '0.875rem',
                    minHeight: 40,
                    borderRadius: radius.sm,
                    '&.Mui-selected': {
                        color: palette.primary,
                    },
                },
            },
        },
    },
});

export default theme;
