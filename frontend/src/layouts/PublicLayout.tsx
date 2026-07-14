import { Outlet } from 'react-router-dom';
import { Box } from '@mui/material';

/**
 * PublicLayout — used for the Landing page only.
 * No chrome. Full viewport.
 */
const PublicLayout = () => {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'background.default',
      }}
    >
      <Outlet />
    </Box>
  );
};

export default PublicLayout;
