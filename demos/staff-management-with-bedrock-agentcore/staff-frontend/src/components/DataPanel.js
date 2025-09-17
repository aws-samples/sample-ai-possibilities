import React from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  useTheme
} from '@mui/material';
import {
  Schedule,
  BeachAccess,
  AccessTime,
  AccountBalance,
  Policy,
  Dashboard
} from '@mui/icons-material';
import RosterPanel from './RosterPanel';
import LeavePanel from './LeavePanel';
import AvailabilityPanel from './AvailabilityPanel';
import PayrollPanel from './PayrollPanel';
import PolicyPanel from './PolicyPanel';
import OverviewPanel from './OverviewPanel';

const DataPanel = ({ activePanel, panelData, staffInfo, onPanelChange }) => {
  const theme = useTheme();

  const panels = [
    {
      id: 'overview',
      label: 'Overview',
      icon: <Dashboard />,
      component: <OverviewPanel staffInfo={staffInfo} />
    },
    {
      id: 'roster',
      label: 'Schedule',
      icon: <Schedule />,
      component: <RosterPanel staffInfo={staffInfo} panelData={panelData} />
    },
    {
      id: 'leave',
      label: 'Leave',
      icon: <BeachAccess />,
      component: <LeavePanel staffInfo={staffInfo} panelData={panelData} />
    },
    {
      id: 'availability',
      label: 'Availability',
      icon: <AccessTime />,
      component: <AvailabilityPanel staffInfo={staffInfo} panelData={panelData} />
    },
    {
      id: 'payroll',
      label: 'Payroll',
      icon: <AccountBalance />,
      component: <PayrollPanel staffInfo={staffInfo} panelData={panelData} />
    },
    {
      id: 'policy',
      label: 'Policies',
      icon: <Policy />,
      component: <PolicyPanel staffInfo={staffInfo} panelData={panelData} />
    }
  ];

  const activeIndex = panels.findIndex(panel => panel.id === activePanel);
  const currentPanel = panels[activeIndex] || panels[0];

  const handleTabChange = (event, newValue) => {
    const selectedPanel = panels[newValue];
    if (selectedPanel) {
      onPanelChange(selectedPanel.id);
    }
  };

  return (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Panel Header */}
      <Box sx={{ 
        borderBottom: 1, 
        borderColor: 'divider', 
        backgroundColor: 'background.paper',
        flexShrink: 0,
        zIndex: 10
      }}>
        <Box sx={{ px: 3, py: 2 }}>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {currentPanel.icon}
            {currentPanel.label}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {staffInfo.name} • {staffInfo.position} • {staffInfo.business}
          </Typography>
        </Box>
        
        {/* Tab Navigation */}
        <Tabs
          value={activeIndex}
          onChange={handleTabChange}
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            minHeight: 48,
            '& .MuiTab-root': {
              minHeight: 48,
              textTransform: 'none',
              fontSize: '0.875rem',
              fontWeight: 500,
            }
          }}
        >
          {panels.map((panel) => (
            <Tab
              key={panel.id}
              icon={panel.icon}
              label={panel.label}
              iconPosition="start"
              sx={{ 
                gap: 1,
                '&.Mui-selected': {
                  color: 'primary.main',
                }
              }}
            />
          ))}
        </Tabs>
      </Box>

      {/* Panel Content */}
      <Box sx={{ 
        flexGrow: 1, 
        overflow: 'auto',
        minHeight: 0,
        maxHeight: 'calc(100vh - 160px)', // Constrain height to force scrolling
        '&::-webkit-scrollbar': {
          width: '8px',
        },
        '&::-webkit-scrollbar-track': {
          backgroundColor: 'rgba(0,0,0,0.05)',
        },
        '&::-webkit-scrollbar-thumb': {
          backgroundColor: 'rgba(0,0,0,0.3)',
          borderRadius: '4px',
          '&:hover': {
            backgroundColor: 'rgba(0,0,0,0.5)',
          }
        }
      }}>
        {currentPanel.component}
      </Box>
    </Box>
  );
};

export default DataPanel;