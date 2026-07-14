import { createTheme, alpha } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    examiner: Palette['primary'];
  }
  interface PaletteOptions {
    examiner?: PaletteOptions['primary'];
  }
}

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1565C0',
      dark: '#0D47A1',
      light: '#1976D2',
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#1976D2',
      contrastText: '#FFFFFF',
    },
    error: {
      main: '#B00020',
      light: '#FFEBEE',
    },
    warning: {
      main: '#E65100',
      light: '#FFF3E0',
    },
    success: {
      main: '#2E7D32',
      light: '#E8F5E9',
    },
    info: {
      main: '#0277BD',
      light: '#E1F5FE',
    },
    background: {
      default: '#FAFAFA',
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1A237E',
      secondary: '#546E7A',
      disabled: '#B0BEC5',
    },
    divider: '#CFD8DC',
    examiner: {
      main: '#1565C0',
      light: '#E3F2FD',
      dark: '#0D47A1',
      contrastText: '#FFFFFF',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontSize: '3.5625rem', fontWeight: 700, lineHeight: 1.123 },
    h2: { fontSize: '2.8125rem', fontWeight: 700, lineHeight: 1.156 },
    h3: { fontSize: '2rem', fontWeight: 600, lineHeight: 1.25 },
    h4: { fontSize: '1.75rem', fontWeight: 600, lineHeight: 1.286 },
    h5: { fontSize: '1.5rem', fontWeight: 600, lineHeight: 1.333 },
    h6: { fontSize: '1.375rem', fontWeight: 600, lineHeight: 1.273 },
    subtitle1: { fontSize: '1rem', fontWeight: 500, lineHeight: 1.5, letterSpacing: '0.0094em' },
    subtitle2: { fontSize: '0.875rem', fontWeight: 500, lineHeight: 1.571, letterSpacing: '0.00714em' },
    body1: { fontSize: '1rem', fontWeight: 400, lineHeight: 1.5, letterSpacing: '0.03125em' },
    body2: { fontSize: '0.875rem', fontWeight: 400, lineHeight: 1.429, letterSpacing: '0.01563em' },
    button: { fontSize: '0.875rem', fontWeight: 500, letterSpacing: '0.00625em', textTransform: 'none' },
    caption: { fontSize: '0.75rem', fontWeight: 400, lineHeight: 1.333, letterSpacing: '0.025em' },
    overline: { fontSize: '0.6875rem', fontWeight: 500, letterSpacing: '0.03125em' },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
    '0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06)',
    '0 10px 15px rgba(0,0,0,0.08), 0 4px 6px rgba(0,0,0,0.05)',
    '0 20px 25px rgba(0,0,0,0.10), 0 10px 10px rgba(0,0,0,0.06)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
    '0 25px 50px rgba(0,0,0,0.12)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: `
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        * { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body { margin: 0; font-family: 'Inter', sans-serif; -webkit-font-smoothing: antialiased; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #F0F4F8; }
        ::-webkit-scrollbar-thumb { background: #CFD8DC; border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: #90A4AE; }
      `,
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          fontSize: '0.875rem',
          padding: '10px 24px',
          boxShadow: 'none',
          '&:hover': { boxShadow: 'none' },
          '&:active': { boxShadow: 'none' },
        },
        sizeLarge: { padding: '12px 32px', fontSize: '1rem' },
        sizeSmall: { padding: '6px 16px', fontSize: '0.8125rem' },
        contained: {
          '&:hover': { boxShadow: '0 4px 6px rgba(0,0,0,0.07)' },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)',
          border: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: { borderRadius: 12 },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { borderRadius: 9999, fontWeight: 500 },
      },
    },
    MuiTextField: {
      defaultProps: { variant: 'outlined', fullWidth: true },
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 8,
            backgroundColor: '#F0F4F8',
            '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#1565C0' },
          },
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          margin: '2px 8px',
          width: 'calc(100% - 16px)',
          '&.Mui-selected': {
            backgroundColor: '#E3F2FD',
            borderLeft: '3px solid #1565C0',
            color: '#1565C0',
            '& .MuiListItemIcon-root': { color: '#1565C0' },
            '&:hover': { backgroundColor: alpha('#1565C0', 0.12) },
          },
          '&:hover': { backgroundColor: alpha('#1565C0', 0.06) },
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          fontSize: '0.8125rem',
          color: '#546E7A',
          backgroundColor: '#F0F4F8',
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: { borderRadius: 8 },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: { borderRadius: 16 },
      },
    },
    MuiTooltip: {
      styleOverrides: {
        tooltip: { borderRadius: 6, fontSize: '0.75rem' },
      },
    },
  },
});

export default theme;
