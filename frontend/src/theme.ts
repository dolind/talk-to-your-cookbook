import {createTheme} from '@mui/material/styles';

export const theme = createTheme({
    palette: {
        mode: 'dark', // Enable dark mode
        primary: {
            main: '#4caf50',
            light: '#80e27e',
            dark: '#087f23',
        },
        secondary: {
            main: '#ff9800',
            light: '#ffc947',
            dark: '#c66900',
        },
        background: {
            default: '#121212', // Dark background
            paper: '#1e1e1e',   // Slightly lighter for cards/dialogs
        },
        text: {
            primary: '#ffffff',
            secondary: '#cccccc',
        },
    },
    typography: {
        fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
        h1: {fontWeight: 500},
        h2: {fontWeight: 500},
        h3: {fontWeight: 500},
    },
    components: {
        MuiButton: {
            styleOverrides: {
                root: {
                    borderRadius: 8,
                    textTransform: 'none',
                    fontWeight: 600,
                },
            },
        },
        MuiCard: {
            styleOverrides: {
                root: {
                    borderRadius: 12,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
                    backgroundColor: '#1e1e1e', // dark card bg
                },
            },
        },
    },
});
