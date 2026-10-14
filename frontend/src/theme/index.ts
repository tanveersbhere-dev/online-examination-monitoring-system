import { createTheme, alpha } from '@mui/material/styles';

declare module '@mui/material/styles' {
  interface Palette {
    examiner: Palette['primary'];
  }
  interface PaletteOptions {
    examiner?: PaletteOptions['primary'];
  }
}

// ─── Design Tokens ───────────────────────────────────────────────────────────
// Primary: Deep navy-blue (trust, security, professionalism)
// Accent:  Teal/cyan (highlights, CTAs)
// Semantic: Emerald success, amber warning, crimson error
// Neutral: Slate gray scale
// ─────────────────────────────────────────────────────────────────────────────

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2563EB',       // vivid blue — CTAs, primary actions
      dark: '#1E40AF',       // deeper blue — hover states
      light: '#3B82F6',      // lighter blue — highlights
      contrastText: '#FFFFFF',
    },
    secondary: {
      main: '#0EA5E9',       // sky-teal accent
      dark: '#0284C7',
      light: '#38BDF8',
      contrastText: '#FFFFFF',
    },
    error: {
      main: '#DC2626',
      light: '#FEE2E2',
      dark: '#B91C1C',
      contrastText: '#FFFFFF',
    },
    warning: {
      main: '#D97706',
      light: '#FEF3C7',
      dark: '#B45309',
      contrastText: '#FFFFFF',
    },
    success: {
      main: '#059669',
      light: '#D1FAE5',
      dark: '#047857',
      contrastText: '#FFFFFF',
    },
    info: {
      main: '#0EA5E9',
      light: '#E0F2FE',
      dark: '#0284C7',
      contrastText: '#FFFFFF',
    },
    background: {
      default: '#F8FAFC',    // very light slate — page backgrounds
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0F172A',    // near-black slate — high contrast
      secondary: '#475569',  // mid slate — secondary content
      disabled: '#94A3B8',   // muted slate
    },
    divider: '#E2E8F0',
    examiner: {
      main: '#2563EB',
      light: '#EFF6FF',
      dark: '#1E40AF',
      contrastText: '#FFFFFF',
    },
  },

  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontSize: '3.5rem',   fontWeight: 800, lineHeight: 1.1,   letterSpacing: '-0.02em' },
    h2: { fontSize: '2.75rem',  fontWeight: 700, lineHeight: 1.15,  letterSpacing: '-0.015em' },
    h3: { fontSize: '2.125rem', fontWeight: 700, lineHeight: 1.2,   letterSpacing: '-0.01em' },
    h4: { fontSize: '1.75rem',  fontWeight: 700, lineHeight: 1.25,  letterSpacing: '-0.008em' },
    h5: { fontSize: '1.375rem', fontWeight: 600, lineHeight: 1.35 },
    h6: { fontSize: '1.125rem', fontWeight: 600, lineHeight: 1.4  },
    subtitle1: { fontSize: '1rem',    fontWeight: 500, lineHeight: 1.5,  letterSpacing: '0.005em' },
    subtitle2: { fontSize: '0.875rem',fontWeight: 500, lineHeight: 1.57, letterSpacing: '0.005em' },
    body1: { fontSize: '1rem',    fontWeight: 400, lineHeight: 1.6,  letterSpacing: '0.01em' },
    body2: { fontSize: '0.875rem',fontWeight: 400, lineHeight: 1.5,  letterSpacing: '0.01em' },
    button: { fontSize: '0.875rem',fontWeight: 600, letterSpacing: '0.01em', textTransform: 'none' },
    caption: { fontSize: '0.75rem',  fontWeight: 400, lineHeight: 1.4,  letterSpacing: '0.02em' },
    overline: { fontSize: '0.6875rem',fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' },
  },

  shape: {
    borderRadius: 10,
  },

  shadows: [
    'none',
    // elevation 1 — cards at rest
    '0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)',
    // elevation 2 — hovered cards
    '0 4px 8px rgba(15,23,42,0.08), 0 2px 4px rgba(15,23,42,0.05)',
    // elevation 3 — dropdowns, menus
    '0 8px 16px rgba(15,23,42,0.10), 0 3px 6px rgba(15,23,42,0.06)',
    // elevation 4 — modals, dialogs
    '0 16px 32px rgba(15,23,42,0.12), 0 6px 12px rgba(15,23,42,0.08)',
    // elevation 5 — popovers
    '0 24px 48px rgba(15,23,42,0.14), 0 8px 16px rgba(15,23,42,0.08)',
    // elevation 6-8 — high-elevation elements
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
    '0 32px 64px rgba(15,23,42,0.16)',
  ],

  components: {
    // ── Global baseline ──────────────────────────────────────────────────────
    MuiCssBaseline: {
      styleOverrides: `
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        *, *::before, *::after { box-sizing: border-box; }
        html { scroll-behavior: smooth; }
        body { margin: 0; font-family: 'Inter', sans-serif; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #F1F5F9; border-radius: 10px; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: #94A3B8; }
        ::selection { background: rgba(37,99,235,0.15); color: #1E40AF; }
      `,
    },

    // ── Buttons ──────────────────────────────────────────────────────────────
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 600,
          fontSize: '0.875rem',
          padding: '9px 22px',
          letterSpacing: '0.01em',
          transition: 'all 0.18s ease',
          // Visible focus ring for keyboard accessibility
          '&:focus-visible': {
            outline: '3px solid rgba(37,99,235,0.5)',
            outlineOffset: '2px',
          },
        },
        sizeLarge: {
          padding: '12px 28px',
          fontSize: '0.9375rem',
          borderRadius: 10,
        },
        sizeSmall: {
          padding: '5px 14px',
          fontSize: '0.8125rem',
          borderRadius: 7,
        },
        // ── Contained (primary) ─────────────────────────────────────────────
        contained: {
          boxShadow: '0 1px 3px rgba(37,99,235,0.25)',
          '&:hover': {
            boxShadow: '0 4px 12px rgba(37,99,235,0.35)',
            transform: 'translateY(-1px)',
          },
          '&:active': {
            boxShadow: '0 1px 2px rgba(37,99,235,0.2)',
            transform: 'translateY(0)',
          },
          '&.Mui-disabled': {
            backgroundColor: '#E2E8F0',
            color: '#94A3B8',
            boxShadow: 'none',
          },
        },
        containedPrimary: {
          background: 'linear-gradient(135deg, #2563EB 0%, #1E40AF 100%)',
          color: '#FFFFFF',
          '&:hover': {
            background: 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)',
          },
        },
        containedSecondary: {
          background: 'linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%)',
          color: '#FFFFFF',
          '&:hover': {
            background: 'linear-gradient(135deg, #38BDF8 0%, #0EA5E9 100%)',
          },
        },
        containedError: {
          background: 'linear-gradient(135deg, #DC2626 0%, #B91C1C 100%)',
          color: '#FFFFFF',
          '&:hover': {
            background: 'linear-gradient(135deg, #EF4444 0%, #DC2626 100%)',
          },
        },
        // ── Outlined ────────────────────────────────────────────────────────
        outlined: {
          borderWidth: '1.5px',
          '&:hover': {
            borderWidth: '1.5px',
            backgroundColor: alpha('#2563EB', 0.04),
          },
          '&.Mui-disabled': {
            borderColor: '#E2E8F0',
            color: '#94A3B8',
          },
        },
        // ── Text ────────────────────────────────────────────────────────────
        text: {
          '&:hover': {
            backgroundColor: alpha('#2563EB', 0.06),
          },
        },
      },
    },

    // ── Cards ────────────────────────────────────────────────────────────────
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          boxShadow: '0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)',
          border: '1px solid #F1F5F9',
          transition: 'box-shadow 0.2s ease, transform 0.2s ease',
        },
      },
    },

    // ── Paper ────────────────────────────────────────────────────────────────
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
        elevation1: {
          boxShadow: '0 1px 3px rgba(15,23,42,0.06), 0 1px 2px rgba(15,23,42,0.04)',
        },
        elevation2: {
          boxShadow: '0 4px 8px rgba(15,23,42,0.08), 0 2px 4px rgba(15,23,42,0.05)',
        },
        elevation3: {
          boxShadow: '0 8px 16px rgba(15,23,42,0.10), 0 3px 6px rgba(15,23,42,0.06)',
        },
      },
    },

    // ── Chip ─────────────────────────────────────────────────────────────────
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 600,
          fontSize: '0.75rem',
          height: 26,
          letterSpacing: '0.01em',
        },
        sizeSmall: {
          height: 22,
          fontSize: '0.6875rem',
        },
      },
    },

    // ── TextField / Input ────────────────────────────────────────────────────
    MuiTextField: {
      defaultProps: { variant: 'outlined', fullWidth: true },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          borderRadius: 9,
          backgroundColor: '#F8FAFC',
          transition: 'background-color 0.15s ease, box-shadow 0.15s ease',
          '&:hover': {
            backgroundColor: '#F1F5F9',
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: '#94A3B8',
            },
          },
          '&.Mui-focused': {
            backgroundColor: '#FFFFFF',
            boxShadow: '0 0 0 3px rgba(37,99,235,0.12)',
            '& .MuiOutlinedInput-notchedOutline': {
              borderColor: '#2563EB',
              borderWidth: '1.5px',
            },
          },
          '&.Mui-error': {
            '&.Mui-focused': {
              boxShadow: '0 0 0 3px rgba(220,38,38,0.12)',
            },
          },
          '&.Mui-disabled': {
            backgroundColor: '#F1F5F9',
          },
        },
        notchedOutline: {
          borderColor: '#E2E8F0',
          transition: 'border-color 0.15s ease',
        },
      },
    },
    MuiInputBase: {
      styleOverrides: {
        root: { borderRadius: 9 },
        input: {
          '&::placeholder': {
            color: '#94A3B8',
            opacity: 1,
          },
        },
      },
    },
    MuiInputLabel: {
      styleOverrides: {
        root: {
          color: '#64748B',
          fontWeight: 500,
          fontSize: '0.875rem',
          '&.Mui-focused': {
            color: '#2563EB',
          },
        },
      },
    },

    // ── AppBar ───────────────────────────────────────────────────────────────
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: '#FFFFFF',
          color: '#0F172A',
          borderBottom: '1px solid #E2E8F0',
        },
      },
    },

    // ── Nav list items ───────────────────────────────────────────────────────
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          margin: '1px 8px',
          width: 'calc(100% - 16px)',
          transition: 'all 0.15s ease',
          '&.Mui-selected': {
            backgroundColor: alpha('#2563EB', 0.12),
            borderLeft: '3px solid #2563EB',
            color: '#2563EB',
            '& .MuiListItemIcon-root': { color: '#2563EB' },
            '&:hover': { backgroundColor: alpha('#2563EB', 0.16) },
          },
          '&:hover': { backgroundColor: alpha('#2563EB', 0.06) },
        },
      },
    },

    // ── Table ────────────────────────────────────────────────────────────────
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 600,
          fontSize: '0.75rem',
          color: '#475569',
          backgroundColor: '#F8FAFC',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          borderBottom: '1px solid #E2E8F0',
        },
        body: {
          fontSize: '0.875rem',
          color: '#1E293B',
          borderBottom: '1px solid #F1F5F9',
        },
      },
    },
    MuiTableRow: {
      styleOverrides: {
        root: {
          '&:hover': {
            backgroundColor: '#F8FAFC',
          },
        },
      },
    },

    // ── Alert ────────────────────────────────────────────────────────────────
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 10,
          fontSize: '0.875rem',
          fontWeight: 500,
          alignItems: 'center',
        },
        standardError:   { backgroundColor: '#FEE2E2', color: '#991B1B' },
        standardWarning: { backgroundColor: '#FEF3C7', color: '#92400E' },
        standardSuccess: { backgroundColor: '#D1FAE5', color: '#065F46' },
        standardInfo:    { backgroundColor: '#E0F2FE', color: '#075985' },
      },
    },

    // ── Dialog ───────────────────────────────────────────────────────────────
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 16,
          boxShadow: '0 24px 48px rgba(15,23,42,0.18), 0 8px 16px rgba(15,23,42,0.10)',
        },
      },
    },
    MuiDialogTitle: {
      styleOverrides: {
        root: {
          fontSize: '1.125rem',
          fontWeight: 700,
          color: '#0F172A',
          paddingBottom: 8,
        },
      },
    },

    // ── Tooltip ──────────────────────────────────────────────────────────────
    MuiTooltip: {
      styleOverrides: {
        tooltip: {
          borderRadius: 7,
          fontSize: '0.75rem',
          fontWeight: 500,
          backgroundColor: '#1E293B',
          color: '#F8FAFC',
          padding: '5px 10px',
        },
        arrow: {
          color: '#1E293B',
        },
      },
    },

    // ── Stepper ──────────────────────────────────────────────────────────────
    MuiStepIcon: {
      styleOverrides: {
        root: {
          color: '#CBD5E1',
          '&.Mui-active': { color: '#2563EB' },
          '&.Mui-completed': { color: '#059669' },
        },
      },
    },
    MuiStepLabel: {
      styleOverrides: {
        label: {
          fontSize: '0.75rem',
          fontWeight: 500,
          color: '#94A3B8',
          '&.Mui-active': { color: '#2563EB', fontWeight: 600 },
          '&.Mui-completed': { color: '#059669', fontWeight: 600 },
        },
      },
    },
    MuiStepConnector: {
      styleOverrides: {
        line: {
          borderColor: '#E2E8F0',
        },
        root: {
          '&.Mui-active .MuiStepConnector-line': { borderColor: '#2563EB' },
          '&.Mui-completed .MuiStepConnector-line': { borderColor: '#059669' },
        },
      },
    },

    // ── Select ───────────────────────────────────────────────────────────────
    MuiSelect: {
      styleOverrides: {
        root: {
          borderRadius: 9,
        },
      },
    },

    // ── Divider ──────────────────────────────────────────────────────────────
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: '#E2E8F0',
        },
      },
    },

    // ── Badge ────────────────────────────────────────────────────────────────
    MuiBadge: {
      styleOverrides: {
        badge: {
          fontWeight: 600,
          fontSize: '0.625rem',
        },
      },
    },

    // ── Skeleton ─────────────────────────────────────────────────────────────
    MuiSkeleton: {
      styleOverrides: {
        root: {
          backgroundColor: '#E2E8F0',
          borderRadius: 8,
        },
      },
    },

    // ── Linear Progress ──────────────────────────────────────────────────────
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 999,
          height: 6,
          backgroundColor: '#E2E8F0',
        },
        bar: {
          borderRadius: 999,
        },
      },
    },

    // ── Avatar ───────────────────────────────────────────────────────────────
    MuiAvatar: {
      styleOverrides: {
        root: {
          fontWeight: 700,
          fontSize: '0.875rem',
        },
      },
    },

    // ── Menu ─────────────────────────────────────────────────────────────────
    MuiMenu: {
      styleOverrides: {
        paper: {
          borderRadius: 10,
          boxShadow: '0 8px 24px rgba(15,23,42,0.12), 0 2px 8px rgba(15,23,42,0.08)',
          border: '1px solid #E2E8F0',
          minWidth: 160,
        },
      },
    },
    MuiMenuItem: {
      styleOverrides: {
        root: {
          fontSize: '0.875rem',
          fontWeight: 500,
          borderRadius: 6,
          margin: '1px 4px',
          width: 'calc(100% - 8px)',
          padding: '8px 12px',
          '&:hover': {
            backgroundColor: '#F1F5F9',
          },
          '&.Mui-selected': {
            backgroundColor: alpha('#2563EB', 0.08),
            color: '#2563EB',
          },
        },
      },
    },

    // ── Popover ──────────────────────────────────────────────────────────────
    MuiPopover: {
      styleOverrides: {
        paper: {
          borderRadius: 12,
          boxShadow: '0 8px 24px rgba(15,23,42,0.12), 0 2px 8px rgba(15,23,42,0.08)',
          border: '1px solid #E2E8F0',
        },
      },
    },

    // ── Breadcrumbs ──────────────────────────────────────────────────────────
    MuiBreadcrumbs: {
      styleOverrides: {
        root: {
          fontSize: '0.8125rem',
        },
      },
    },
  },
});

export default theme;
