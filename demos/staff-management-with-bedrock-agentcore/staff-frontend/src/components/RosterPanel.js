import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Grid,
  Avatar,
  Skeleton,
  Alert,
  Button,
  Stack
} from '@mui/material';
import {
  Schedule,
  Person,
  AccessTime,
  CalendarToday,
  Refresh
} from '@mui/icons-material';
import { format, startOfWeek, addDays, isSameDay, parseISO } from 'date-fns';

const RosterPanel = ({ staffInfo, panelData }) => {
  const [rosterData, setRosterData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentWeek, setCurrentWeek] = useState(new Date());

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

  // Demo data for Emma Davis - would normally come from API
  const demoShifts = [
    {
      date: '2025-08-27',
      startTime: '08:00',
      endTime: '16:00',
      position: 'Barista',
      coWorkers: ['James Davidson', 'Sarah Mitchell']
    },
    {
      date: '2025-08-28',
      startTime: '09:00',
      endTime: '17:00',
      position: 'Barista',
      coWorkers: ['Emma Chen', 'Michael Wilson']
    },
    {
      date: '2025-08-30',
      startTime: '08:00',
      endTime: '14:00',
      position: 'Barista',
      coWorkers: ['Sarah Mitchell']
    },
    {
      date: '2025-09-01',
      startTime: '10:00',
      endTime: '18:00',
      position: 'Barista',
      coWorkers: ['James Davidson', 'Lucy Thompson']
    },
    {
      date: '2025-09-03',
      startTime: '08:00',
      endTime: '16:00',
      position: 'Barista',
      coWorkers: ['Emma Chen']
    }
  ];

  const fetchRosterData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // For demo purposes, we'll use the demo data
      // In production, this would fetch from the API:
      // const response = await fetch(`${API_URL}/api/my-roster`);
      // const data = await response.json();
      
      setTimeout(() => {
        setRosterData(demoShifts);
        setLoading(false);
      }, 800);
      
    } catch (err) {
      console.error('Error fetching roster data:', err);
      setError('Failed to load schedule data');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRosterData();
  }, []);

  const getWeekDays = (weekStart) => {
    const days = [];
    for (let i = 0; i < 7; i++) {
      days.push(addDays(weekStart, i));
    }
    return days;
  };

  const getShiftForDate = (date) => {
    if (!rosterData) return null;
    const dateStr = format(date, 'yyyy-MM-dd');
    return rosterData.find(shift => shift.date === dateStr);
  };

  const weekStart = startOfWeek(currentWeek, { weekStartsOn: 1 }); // Start on Monday
  const weekDays = getWeekDays(weekStart);

  const nextWeek = () => {
    setCurrentWeek(addDays(currentWeek, 7));
  };

  const prevWeek = () => {
    setCurrentWeek(addDays(currentWeek, -7));
  };

  const goToToday = () => {
    setCurrentWeek(new Date());
  };

  const getTotalHours = () => {
    if (!rosterData) return 0;
    return rosterData.reduce((total, shift) => {
      const start = new Date(`2000-01-01T${shift.startTime}:00`);
      const end = new Date(`2000-01-01T${shift.endTime}:00`);
      const hours = (end - start) / (1000 * 60 * 60);
      return total + hours;
    }, 0);
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="rectangular" height={60} sx={{ mb: 2 }} />
        <Grid container spacing={1}>
          {[...Array(7)].map((_, i) => (
            <Grid size={{ xs: true }} key={i}>
              <Skeleton variant="rectangular" height={120} />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert 
          severity="error" 
          action={
            <Button color="inherit" size="small" onClick={fetchRosterData}>
              <Refresh sx={{ mr: 0.5 }} />
              Retry
            </Button>
          }
        >
          {error}
        </Alert>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h4" color="primary" sx={{ fontWeight: 600 }}>
                {rosterData ? rosterData.length : 0}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Shifts This Week
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h4" color="primary" sx={{ fontWeight: 600 }}>
                {getTotalHours()}h
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Hours
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Week Navigation */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'between', mb: 3 }}>
        <Typography variant="h6">
          Week of {format(weekStart, 'MMM dd, yyyy')}
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button size="small" onClick={prevWeek}>Previous</Button>
          <Button size="small" onClick={goToToday} variant="outlined">Today</Button>
          <Button size="small" onClick={nextWeek}>Next</Button>
        </Stack>
      </Box>

      {/* Calendar Grid */}
      <Grid container spacing={1} sx={{ mb: 2 }}>
        {weekDays.map((day, index) => {
          const shift = getShiftForDate(day);
          const isToday = isSameDay(day, new Date());
          
          return (
            <Grid size={{ xs: true }} key={index}>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  minHeight: 140,
                  border: 1,
                  borderColor: isToday ? 'primary.main' : 'divider',
                  backgroundColor: shift ? 'primary.light' : 'background.paper',
                  color: shift ? 'white' : 'text.primary'
                }}
              >
                <Typography 
                  variant="subtitle2" 
                  sx={{ 
                    fontWeight: 600,
                    mb: 1,
                    color: isToday ? 'primary.main' : 'inherit'
                  }}
                >
                  {format(day, 'EEE')}
                </Typography>
                <Typography 
                  variant="h6" 
                  sx={{ 
                    mb: 1,
                    color: isToday ? 'primary.main' : 'inherit'
                  }}
                >
                  {format(day, 'd')}
                </Typography>
                
                {shift ? (
                  <Box>
                    <Chip
                      size="small"
                      label={`${shift.startTime} - ${shift.endTime}`}
                      sx={{
                        backgroundColor: 'rgba(255,255,255,0.2)',
                        color: 'white',
                        mb: 1,
                        fontSize: '0.75rem'
                      }}
                    />
                    <Typography variant="caption" display="block">
                      {shift.position}
                    </Typography>
                  </Box>
                ) : (
                  <Typography variant="caption" color="text.secondary">
                    No shift
                  </Typography>
                )}
              </Paper>
            </Grid>
          );
        })}
      </Grid>

      {/* Upcoming Shifts Detail */}
      <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Schedule color="primary" />
        Upcoming Shifts
      </Typography>

      <Stack spacing={2}>
        {rosterData && rosterData.length > 0 ? (
          rosterData.map((shift, index) => (
            <Card key={index} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 0.5 }}>
                      {format(parseISO(shift.date), 'EEEE, MMMM dd')}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
                      <Chip
                        icon={<AccessTime />}
                        label={`${shift.startTime} - ${shift.endTime}`}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                      <Chip
                        label={shift.position}
                        size="small"
                        variant="outlined"
                      />
                    </Box>
                  </Box>
                </Box>
                
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Working with:
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                  {shift.coWorkers.map((coWorker, idx) => (
                    <Chip
                      key={idx}
                      avatar={<Avatar sx={{ width: 24, height: 24, fontSize: '0.75rem' }}>
                        {coWorker.split(' ').map(n => n[0]).join('')}
                      </Avatar>}
                      label={coWorker}
                      size="small"
                      variant="outlined"
                    />
                  ))}
                </Box>
              </CardContent>
            </Card>
          ))
        ) : (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <CalendarToday sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              No shifts scheduled
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Your upcoming shifts will appear here
            </Typography>
          </Paper>
        )}
      </Stack>
    </Box>
  );
};

export default RosterPanel;