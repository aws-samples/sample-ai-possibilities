import React, { useState, useEffect } from 'react';
import {
  Box,
  Grid,
  Paper,
  ThemeProvider,
  createTheme,
  CssBaseline,
  AppBar,
  Toolbar,
  Typography,
  Avatar,
  Chip
} from '@mui/material';
import {
  Person,
  Schedule,
  BusinessCenter
} from '@mui/icons-material';
import ChatPanel from './ChatPanel';
import DataPanel from './DataPanel';

// Professional theme for StaffCast
const staffTheme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#2196f3',
      light: '#64b5f6',
      dark: '#1976d2',
    },
    secondary: {
      main: '#f50057',
      light: '#ff5983',
      dark: '#c51162',
    },
    background: {
      default: '#f5f7fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a202c',
      secondary: '#4a5568',
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: {
      fontWeight: 600,
      fontSize: '1.75rem',
    },
    h6: {
      fontWeight: 500,
      fontSize: '1.125rem',
    },
    body1: {
      fontSize: '0.95rem',
      lineHeight: 1.6,
    },
  },
  components: {
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 500,
          borderRadius: 8,
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 6,
        },
      },
    },
  },
});

const SplitScreenLayout = () => {
  const [activePanel, setActivePanel] = useState('roster'); // Default panel
  const [panelData, setPanelData] = useState(null);

  // Demo staff information
  const staffInfo = {
    name: 'Emma Davis',
    staffId: 'emma_davis',
    position: 'Barista',
    business: 'The Daily Grind Cafe',
    avatar: 'ED',
  };

  // Handle panel updates from chat interactions
  const handlePanelUpdate = (panelType, data = null) => {
    setActivePanel(panelType);
    setPanelData(data);
  };

  return (
    <ThemeProvider theme={staffTheme}>
      <CssBaseline />
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        height: '100vh',
        overflow: 'hidden'
      }}>
        {/* Header */}
        <AppBar 
          position="static" 
          elevation={0} 
          sx={{ 
            backgroundColor: 'background.paper', 
            borderBottom: 1, 
            borderColor: 'divider',
            flexShrink: 0,
            zIndex: 1200
          }}
        >
          <Toolbar>
            <Avatar
              sx={{ 
                bgcolor: 'primary.main', 
                width: 40, 
                height: 40, 
                mr: 2,
                fontSize: '0.9rem',
                fontWeight: 600
              }}
            >
              {staffInfo.avatar}
            </Avatar>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h6" sx={{ color: 'text.primary', mb: 0.5 }}>
                StaffCast Assistant
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  icon={<Person />}
                  label={staffInfo.name}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.75rem' }}
                />
                <Chip
                  icon={<Schedule />}
                  label={staffInfo.position}
                  size="small"
                  color="primary"
                  variant="outlined"
                  sx={{ fontSize: '0.75rem' }}
                />
                <Chip
                  icon={<BusinessCenter />}
                  label={staffInfo.business}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: '0.75rem' }}
                />
              </Box>
            </Box>
          </Toolbar>
        </AppBar>

        {/* Main Content Area */}
        <Box sx={{ 
          flexGrow: 1, 
          overflow: 'hidden',
          minHeight: 0
        }}>
          <Grid container sx={{ 
            height: '100%',
            overflow: 'hidden'
          }}>
            {/* Left Panel - Chat Interface */}
            <Grid size={{ xs: 12, md: 4 }}>
              <Paper 
                elevation={0} 
                sx={{ 
                  height: '100%', 
                  borderRadius: 0,
                  borderRight: { md: 1 },
                  borderColor: 'rgba(0, 0, 0, 0.06)',
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden'
                }}
              >
                <ChatPanel 
                  onPanelUpdate={handlePanelUpdate}
                  staffInfo={staffInfo}
                />
              </Paper>
            </Grid>

            {/* Right Panel - Dynamic Data Display */}
            <Grid size={{ xs: 12, md: 8 }}>
              <Paper 
                elevation={0} 
                sx={{ 
                  height: '100%', 
                  borderRadius: 0,
                  backgroundColor: 'background.default',
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden'
                }}
              >
                <DataPanel 
                  activePanel={activePanel}
                  panelData={panelData}
                  staffInfo={staffInfo}
                  onPanelChange={setActivePanel}
                />
              </Paper>
            </Grid>
          </Grid>
        </Box>
      </Box>
    </ThemeProvider>
  );
};

export default SplitScreenLayout;