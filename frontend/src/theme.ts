import { createTheme } from '@mui/material/styles';

const theme = createTheme({
    palette: {
        primary: {
            main: '#00A6FF', // Blue from gradient
        },
        secondary: {
            main: '#00D98B', // Green from gradient
        },
        background: {
            default: '#121212', // Black background
            paper: '#1e1e1e', // Slightly lighter black for cards, etc.
        },
        text: {
            primary: '#ffffff', // White for main text
            secondary: '#cccccc', // Light grey for secondary text
        },
        divider: '#333333'
    },
    typography: {
        fontFamily: "'Lato', sans-serif",
        fontSize: 14,
        h1: {
            fontSize: '2.5rem',
            fontWeight: 700,
            color: '#ffffff',
        },
        h2: {
            fontSize: '2rem',
            fontWeight: 600,
            color: '#ffffff',
        },
        body1: {
            fontSize: '1rem',
            color: '#ffffff',
            lineHeight: 1.6,
        },
        button: {
            textTransform: 'none',
            fontWeight: 600,
        },
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 0, // Sharp edges
                    padding: '0.75rem 2rem',
                    color: '#ffffff', // White text for all buttons
                },
                contained: {
                    background: 'linear-gradient(90deg, #00D98B 0%, #00A6FF 100%)', // Gradient background
                    color: '#ffffff',
                    '&:hover': {
                        background: 'linear-gradient(90deg, #00B67A 0%, #008FE3 100%)', // Darker gradient on hover
                    },
                },
                outlined: {
                    color: '#ffffff', // White text for outlined buttons
                    borderColor: '#00A6FF',
                    '&:hover': {
                        borderColor: '#00D98B',
                        backgroundColor: 'rgba(0, 217, 139, 0.08)',
                    },
                },
            },
        },
        MuiPaper: {
            styleOverrides: {
                root: {
                    backgroundColor: '#1e1e1e',
                    color: '#ffffff',
                    borderRadius: 0,
                    border: '1px solid #333',
                },
            },
        },
        MuiTypography: {
            styleOverrides: {
                root: {
                    color: '#ffffff',
                },
            },
        },
    },
});

export default theme;
