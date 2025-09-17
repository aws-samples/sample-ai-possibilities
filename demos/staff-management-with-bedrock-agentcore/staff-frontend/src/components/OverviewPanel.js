import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Grid,
  Chip,
  Stack,
  Avatar,
  LinearProgress,
  Divider,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText
} from '@mui/material';
import {
  Dashboard,
  Schedule,
  BeachAccess,
  AccessTime,
  AccountBalance,
  TrendingUp,
  CheckCircle,
  Warning,
  Info,
  Person
} from '@mui/icons-material';
import { format, addDays, isSameDay } from 'date-fns';

const OverviewPanel = ({ staffInfo }) => {
  const [overviewData, setOverviewData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Demo overview data for Emma Davis
  const demoOverviewData = {
    quickStats: {
      upcomingShifts: 3,
      hoursThisWeek: 32,
      pendingLeave: 1,
      availableDays: 5
    },
    nextShift: {
      date: '2025-08-29',
      startTime: '08:00',
      endTime: '16:00',
      position: 'Barista',
      location: 'Main Counter'
    },
    weeklyProgress: {
      hoursWorked: 24,
      hoursScheduled: 32,
      percentage: 75
    },
    recentActivity: [
      {
        type: 'shift_completed',
        date: '2025-08-27',
        description: 'Completed 8-hour shift (Morning)',
        icon: <CheckCircle color="success" />
      },
      {
        type: 'leave_requested',
        date: '2025-08-25',
        description: 'Requested leave for Sep 7-9',
        icon: <BeachAccess color="warning" />
      },
      {
        type: 'availability_updated',
        date: '2025-08-23',
        description: 'Updated weekend availability',
        icon: <AccessTime color="info" />
      }
    ],
    notifications: [
      {
        type: 'info',
        title: 'Schedule Update',
        message: 'Your Friday shift time has been updated to 8:00 AM - 8:00 PM'
      },
      {
        type: 'warning', 
        title: 'Leave Request Pending',
        message: 'Your leave request for Sep 7-9 is waiting for manager approval'
      }
    ],
    achievements: [
      {
        title: 'Perfect Attendance',
        description: '30 days without absence',
        progress: 87,
        target: 30
      },
      {
        title: 'Customer Service Star',
        description: 'Excellent customer feedback',
        progress: 92,
        target: 90
      }
    ]
  };

  useEffect(() => {
    // Simulate data loading
    setTimeout(() => {
      setOverviewData(demoOverviewData);
      setLoading(false);
    }, 500);
  }, []);

  const getNotificationSeverity = (type) => {
    switch (type) {
      case 'warning': return 'warning';
      case 'error': return 'error'; 
      case 'success': return 'success';
      default: return 'info';
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>Loading dashboard...</Typography>
      </Box>
    );
  }

  const { quickStats, nextShift, weeklyProgress, recentActivity, notifications, achievements } = overviewData;
  const today = new Date();
  const isNextShiftToday = nextShift && isSameDay(new Date(nextShift.date), today);

  return (
    <Box sx={{ p: 3 }}>
      {/* Welcome Section */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
          Welcome back, {staffInfo.name}! 👋
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Here's your overview for {format(today, 'EEEE, MMMM dd, yyyy')}
        </Typography>
      </Box>

      {/* Quick Stats */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6, sm: 3 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Schedule color="primary" />
                <Typography variant="subtitle2">Upcoming</Typography>
              </Box>
              <Typography variant="h4" color="primary" sx={{ fontWeight: 600 }}>
                {quickStats.upcomingShifts}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                shifts this week
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 6, sm: 3 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <AccessTime color="info" />
                <Typography variant="subtitle2">Hours</Typography>
              </Box>
              <Typography variant="h4" color="info.main" sx={{ fontWeight: 600 }}>
                {quickStats.hoursThisWeek}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                this week
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 6, sm: 3 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <BeachAccess color="warning" />
                <Typography variant="subtitle2">Leave</Typography>
              </Box>
              <Typography variant="h4" color="warning.main" sx={{ fontWeight: 600 }}>
                {quickStats.pendingLeave}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                pending request
              </Typography>
            </CardContent>
          </Card>
        </Grid>

        <Grid size={{ xs: 6, sm: 3 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <TrendingUp color="success" />
                <Typography variant="subtitle2">Available</Typography>
              </Box>
              <Typography variant="h4" color="success.main" sx={{ fontWeight: 600 }}>
                {quickStats.availableDays}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                days this week
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Left Column */}
        <Grid size={{ xs: 12, md: 8 }}>
          {/* Next Shift */}
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Schedule color="primary" />
                Next Shift
                {isNextShiftToday && (
                  <Chip label="Today" color="primary" size="small" />
                )}
              </Typography>
              
              <Box sx={{ display: 'flex', justify: 'space-between', alignItems: 'center' }}>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 600, mb: 1 }}>
                    {format(new Date(nextShift.date), 'EEEE, MMM dd')}
                  </Typography>
                  <Stack direction="row" spacing={1} sx={{ mb: 1 }}>
                    <Chip
                      icon={<AccessTime />}
                      label={`${nextShift.startTime} - ${nextShift.endTime}`}
                      color="primary"
                      variant="outlined"
                      size="small"
                    />
                    <Chip
                      label={nextShift.position}
                      variant="outlined"
                      size="small"
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {nextShift.location}
                  </Typography>
                </Box>
                
                <Avatar
                  sx={{ 
                    bgcolor: 'primary.light', 
                    width: 60, 
                    height: 60,
                    fontSize: '1.5rem'
                  }}
                >
                  {isNextShiftToday ? '🎯' : '📅'}
                </Avatar>
              </Box>
            </CardContent>
          </Card>

          {/* Weekly Progress */}
          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                This Week's Progress
              </Typography>
              
              <Box sx={{ display: 'flex', justify: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="body1">
                  {weeklyProgress.hoursWorked} of {weeklyProgress.hoursScheduled} hours completed
                </Typography>
                <Typography variant="h6" color="primary">
                  {weeklyProgress.percentage}%
                </Typography>
              </Box>
              
              <LinearProgress
                variant="determinate"
                value={weeklyProgress.percentage}
                sx={{ height: 8, borderRadius: 4, mb: 1 }}
              />
              
              <Typography variant="caption" color="text.secondary">
                {weeklyProgress.hoursScheduled - weeklyProgress.hoursWorked} hours remaining
              </Typography>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Recent Activity
              </Typography>
              
              <List disablePadding>
                {recentActivity.map((activity, index) => (
                  <React.Fragment key={index}>
                    <ListItem disablePadding>
                      <ListItemIcon sx={{ minWidth: 36 }}>
                        {activity.icon}
                      </ListItemIcon>
                      <ListItemText
                        primary={activity.description}
                        secondary={format(new Date(activity.date), 'MMM dd, yyyy')}
                      />
                    </ListItem>
                    {index < recentActivity.length - 1 && <Divider sx={{ my: 1 }} />}
                  </React.Fragment>
                ))}
              </List>
            </CardContent>
          </Card>
        </Grid>

        {/* Right Column */}
        <Grid size={{ xs: 12, md: 4 }}>
          {/* Notifications */}
          <Stack spacing={2} sx={{ mb: 3 }}>
            {notifications.map((notification, index) => (
              <Alert key={index} severity={getNotificationSeverity(notification.type)}>
                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                  {notification.title}
                </Typography>
                <Typography variant="body2">
                  {notification.message}
                </Typography>
              </Alert>
            ))}
          </Stack>

          {/* Achievements */}
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Achievements
              </Typography>
              
              <Stack spacing={3}>
                {achievements.map((achievement, index) => (
                  <Box key={index}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
                      {achievement.title}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {achievement.description}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <LinearProgress
                        variant="determinate"
                        value={achievement.progress}
                        sx={{ flexGrow: 1, height: 6, borderRadius: 3 }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        {achievement.progress}%
                      </Typography>
                    </Box>
                  </Box>
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default OverviewPanel;