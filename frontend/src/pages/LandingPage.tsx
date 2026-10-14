import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Chip,
} from '@mui/material';
import ShieldIcon from '@mui/icons-material/Shield';
import SchoolIcon from '@mui/icons-material/School';
import BadgeIcon from '@mui/icons-material/Badge';
import LockIcon from '@mui/icons-material/Lock';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import InsightsIcon from '@mui/icons-material/Insights';

// ─── Animated keyframes injected via sx / style ───────────────────────────────
const floatKeyframes = `
  @keyframes floatOrb1 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(40px, -60px) scale(1.08); }
    66% { transform: translate(-30px, 30px) scale(0.94); }
  }
  @keyframes floatOrb2 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    33% { transform: translate(-50px, 40px) scale(1.06); }
    66% { transform: translate(60px, -20px) scale(0.96); }
  }
  @keyframes floatOrb3 {
    0%, 100% { transform: translate(0, 0) scale(1); }
    50% { transform: translate(30px, 50px) scale(1.05); }
  }
  @keyframes fadeInUp {
    from { opacity: 0; transform: translateY(28px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes cardEntrance {
    from { opacity: 0; transform: translateY(36px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
  }
  @keyframes shimmer {
    0%   { background-position: -400px 0; }
    100% { background-position: 400px 0; }
  }
`;

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <>
      {/* Inject keyframes into DOM */}
      <style>{floatKeyframes}</style>

      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          // Rich deep-navy mesh gradient background
          background: 'linear-gradient(135deg, #0B1120 0%, #0F1E3C 30%, #0C2340 55%, #091628 80%, #050D1A 100%)',
          px: { xs: 2, sm: 3 },
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        {/* ── Background Orbs (purely decorative) ───────────────────────── */}
        <Box sx={{
          position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden',
        }}>
          {/* Orb 1 — top-left electric blue */}
          <Box sx={{
            position: 'absolute', top: '-10%', left: '-8%',
            width: { xs: 320, md: 520 }, height: { xs: 320, md: 520 },
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(37,99,235,0.28) 0%, rgba(37,99,235,0.04) 70%, transparent 100%)',
            animation: 'floatOrb1 18s ease-in-out infinite',
            filter: 'blur(1px)',
          }} />
          {/* Orb 2 — bottom-right teal */}
          <Box sx={{
            position: 'absolute', bottom: '-12%', right: '-6%',
            width: { xs: 280, md: 480 }, height: { xs: 280, md: 480 },
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(14,165,233,0.22) 0%, rgba(14,165,233,0.03) 70%, transparent 100%)',
            animation: 'floatOrb2 22s ease-in-out infinite',
            filter: 'blur(1px)',
          }} />
          {/* Orb 3 — mid indigo accent */}
          <Box sx={{
            position: 'absolute', top: '40%', right: '15%',
            width: { xs: 180, md: 320 }, height: { xs: 180, md: 320 },
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(99,102,241,0.18) 0%, rgba(99,102,241,0.02) 70%, transparent 100%)',
            animation: 'floatOrb3 14s ease-in-out infinite',
            filter: 'blur(2px)',
          }} />
          {/* Fine dot grid pattern */}
          <Box sx={{
            position: 'absolute', inset: 0,
            backgroundImage: 'radial-gradient(circle at 1px 1px, rgba(255,255,255,0.04) 1px, transparent 0)',
            backgroundSize: '32px 32px',
          }} />
        </Box>

        {/* ── Main Glass Panel ──────────────────────────────────────────────── */}
        <Box
          sx={{
            position: 'relative',
            zIndex: 1,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            width: '100%',
            maxWidth: 960,
            py: { xs: 6, md: 8 },
            px: { xs: 3, sm: 5, md: 8 },
            // Glassmorphism
            background: 'rgba(255,255,255,0.05)',
            backdropFilter: 'blur(24px)',
            WebkitBackdropFilter: 'blur(24px)',
            border: '1px solid rgba(255,255,255,0.12)',
            borderRadius: { xs: '20px', md: '28px' },
            boxShadow: '0 32px 80px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.1)',
            // Fallback for browsers that don't support backdrop-filter
            '@supports not (backdrop-filter: blur(1px))': {
              background: 'rgba(11,17,32,0.92)',
            },
            animation: 'fadeInUp 0.7s ease both',
          }}
        >
          {/* ── Brand Header ─────────────────────────────────────────────── */}
          <Box sx={{ textAlign: 'center', mb: { xs: 4, md: 5 } }}>
            {/* Logo mark */}
            <Box sx={{
              width: { xs: 72, md: 88 },
              height: { xs: 72, md: 88 },
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #2563EB 0%, #0EA5E9 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              mx: 'auto',
              mb: 3,
              boxShadow: '0 0 0 12px rgba(37,99,235,0.15), 0 12px 32px rgba(37,99,235,0.4)',
            }}>
              <ShieldIcon sx={{ color: 'white', fontSize: { xs: 40, md: 48 } }} />
            </Box>

            {/* Product name */}
            <Typography
              component="h1"
              sx={{
                fontSize: { xs: '2.25rem', sm: '2.75rem', md: '3.25rem' },
                fontWeight: 800,
                letterSpacing: '-0.03em',
                lineHeight: 1.05,
                mb: 1.5,
                // White shimmer gradient text
                background: 'linear-gradient(135deg, #FFFFFF 30%, #93C5FD 60%, #38BDF8 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                backgroundClip: 'text',
              }}
            >
              ExamShield
            </Typography>

            {/* System subtitle */}
            <Typography
              sx={{
                fontSize: { xs: '0.875rem', md: '1rem' },
                color: 'rgba(255,255,255,0.55)',
                mb: 2.5,
                letterSpacing: '0.02em',
              }}
            >
              Online Examination Monitoring System
            </Typography>

            {/* Trust tagline */}
            <Chip
              label="Secure · Proctored · Trusted"
              sx={{
                backgroundColor: 'rgba(37,99,235,0.2)',
                color: '#93C5FD',
                border: '1px solid rgba(37,99,235,0.35)',
                fontWeight: 600,
                fontSize: '0.75rem',
                letterSpacing: '0.06em',
                height: 28,
                borderRadius: '8px',
              }}
            />
          </Box>

          {/* ── Feature Highlights (small pill-badges) ────────────────────── */}
          <Box
            sx={{
              display: 'flex',
              gap: { xs: 1.5, sm: 2.5 },
              flexWrap: 'wrap',
              justifyContent: 'center',
              mb: { xs: 5, md: 6 },
            }}
          >
            {[
              { icon: <VerifiedUserIcon sx={{ fontSize: 14 }} />, label: 'AI-Powered Proctoring' },
              { icon: <LockIcon sx={{ fontSize: 14 }} />, label: 'End-to-End Encrypted' },
              { icon: <InsightsIcon sx={{ fontSize: 14 }} />, label: 'Real-Time Analytics' },
            ].map((feat) => (
              <Box
                key={feat.label}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 0.75,
                  px: 1.75,
                  py: 0.6,
                  borderRadius: '999px',
                  background: 'rgba(255,255,255,0.06)',
                  border: '1px solid rgba(255,255,255,0.1)',
                  color: 'rgba(255,255,255,0.65)',
                  fontSize: '0.75rem',
                  fontWeight: 500,
                  letterSpacing: '0.01em',
                  whiteSpace: 'nowrap',
                }}
              >
                {feat.icon}
                {feat.label}
              </Box>
            ))}
          </Box>

          {/* ── Role Selection Cards ──────────────────────────────────────── */}
          <Typography
            sx={{
              fontSize: '0.75rem',
              fontWeight: 600,
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color: 'rgba(255,255,255,0.35)',
              mb: 2.5,
            }}
          >
            Select your role to continue
          </Typography>

          <Box
            sx={{
              display: 'flex',
              gap: { xs: 2, sm: 3 },
              flexDirection: { xs: 'column', sm: 'row' },
              width: '100%',
              justifyContent: 'center',
            }}
          >
            {/* Student Card */}
            <RoleCard
              icon={<SchoolIcon sx={{ fontSize: { xs: 36, md: 44 }, color: '#93C5FD' }} />}
              iconBg="linear-gradient(135deg, rgba(37,99,235,0.35) 0%, rgba(14,165,233,0.25) 100%)"
              iconGlow="rgba(37,99,235,0.4)"
              title="Student"
              subtitle="Enter today's examinations"
              accentColor="#3B82F6"
              onClick={() => navigate('/student')}
              animationDelay="0.15s"
            />

            {/* Examiner Card */}
            <RoleCard
              icon={<BadgeIcon sx={{ fontSize: { xs: 36, md: 44 }, color: '#67E8F9' }} />}
              iconBg="linear-gradient(135deg, rgba(14,165,233,0.35) 0%, rgba(99,102,241,0.25) 100%)"
              iconGlow="rgba(14,165,233,0.4)"
              title="Examiner"
              subtitle="Access the monitoring dashboard"
              accentColor="#0EA5E9"
              onClick={() => navigate('/examiner/login')}
              animationDelay="0.25s"
            />
          </Box>
        </Box>

        {/* ── Footer ───────────────────────────────────────────────────────── */}
        <Typography
          sx={{
            position: 'relative',
            zIndex: 1,
            mt: 4,
            fontSize: '0.75rem',
            color: 'rgba(255,255,255,0.25)',
            letterSpacing: '0.02em',
            animation: 'fadeInUp 0.7s 0.5s ease both',
          }}
        >
          © 2026 ExamShield&nbsp;·&nbsp;v{import.meta.env.VITE_APP_VERSION ?? '1.0.0'}
        </Typography>
      </Box>
    </>
  );
};

// ─── Reusable Role Card Component (layout+visuals only, no logic) ─────────────
interface RoleCardProps {
  icon: React.ReactNode;
  iconBg: string;
  iconGlow: string;
  title: string;
  subtitle: string;
  accentColor: string;
  onClick: () => void;
  animationDelay: string;
}

const RoleCard = ({ icon, iconBg, iconGlow, title, subtitle, accentColor, onClick, animationDelay }: RoleCardProps) => (
  <Box
    onClick={onClick}
    role="button"
    tabIndex={0}
    onKeyDown={(e) => e.key === 'Enter' && onClick()}
    sx={{
      flex: { sm: '1 1 0' },
      maxWidth: { sm: 320 },
      width: { xs: '100%', sm: 'auto' },
      cursor: 'pointer',
      borderRadius: '18px',
      p: { xs: 3.5, md: 4 },
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.09)',
      backdropFilter: 'blur(12px)',
      WebkitBackdropFilter: 'blur(12px)',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      textAlign: 'center',
      gap: 2,
      transition: 'all 0.22s cubic-bezier(0.34, 1.56, 0.64, 1)',
      animation: `cardEntrance 0.6s ${animationDelay} ease both`,
      '@supports not (backdrop-filter: blur(1px))': {
        background: 'rgba(15,30,60,0.85)',
      },
      '&:hover': {
        transform: 'translateY(-8px) scale(1.02)',
        background: 'rgba(255,255,255,0.08)',
        border: `1px solid ${accentColor}55`,
        boxShadow: `0 24px 48px rgba(0,0,0,0.3), 0 0 0 1px ${accentColor}33, 0 0 32px ${iconGlow}`,
      },
      '&:focus-visible': {
        outline: `2px solid ${accentColor}`,
        outlineOffset: '3px',
      },
      '&:active': {
        transform: 'translateY(-2px) scale(0.99)',
      },
    }}
  >
    {/* Icon box */}
    <Box
      sx={{
        width: { xs: 72, md: 84 },
        height: { xs: 72, md: 84 },
        borderRadius: '20px',
        background: iconBg,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        border: '1px solid rgba(255,255,255,0.12)',
        boxShadow: `0 8px 24px ${iconGlow}`,
        flexShrink: 0,
      }}
    >
      {icon}
    </Box>

    <Box>
      <Typography
        sx={{
          fontSize: { xs: '1.25rem', md: '1.375rem' },
          fontWeight: 700,
          color: '#FFFFFF',
          lineHeight: 1.2,
          mb: 0.75,
        }}
      >
        {title}
      </Typography>
      <Typography
        sx={{
          fontSize: '0.875rem',
          color: 'rgba(255,255,255,0.5)',
          lineHeight: 1.4,
        }}
      >
        {subtitle}
      </Typography>
    </Box>

    {/* CTA label */}
    <Box
      sx={{
        mt: 0.5,
        px: 2.5,
        py: 0.9,
        borderRadius: '999px',
        background: `${accentColor}22`,
        border: `1px solid ${accentColor}55`,
        color: accentColor,
        fontSize: '0.8125rem',
        fontWeight: 600,
        letterSpacing: '0.02em',
        width: '100%',
        textAlign: 'center',
      }}
    >
      Enter Portal →
    </Box>
  </Box>
);

export default LandingPage;