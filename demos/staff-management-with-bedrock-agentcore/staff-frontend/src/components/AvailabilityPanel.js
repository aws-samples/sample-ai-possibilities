import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Grid,
  Switch,
  Button,
  Stack,
  Chip,
  FormControlLabel,
  TextField,
  Skeleton,
  Alert
} from '@mui/material';
import {
  AccessTime,
  Edit,
  Save,
  Cancel,
  CheckCircle,
  Schedule
} from '@mui/icons-material';
import { format, addDays, startOfWeek } from 'date-fns';

const AvailabilityPanel = ({ staffInfo, panelData }) => {
  const [availabilityData, setAvailabilityData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editData, setEditData] = useState({});

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

  // Demo availability data for Emma Davis
  const demoAvailability = [
    {
      date: '2025-08-27',
      dayName: 'Wednesday',
      available: true,
      startTime: '08:00',
      endTime: '18:00',
      notes: 'Available for both morning and afternoon shifts'
    },
    {
      date: '2025-08-28',
      dayName: 'Thursday',
      available: true,
      startTime: '09:00',
      endTime: '17:00',
      notes: ''
    },
    {
      date: '2025-08-29',
      dayName: 'Friday',
      available: true,
      startTime: '08:00',
      endTime: '20:00',
      notes: 'Available for evening shift on Friday'
    },
    {
      date: '2025-08-30',
      dayName: 'Saturday',
      available: true,
      startTime: '08:00',
      endTime: '18:00',
      notes: 'Available for both morning and afternoon shifts on weekends'
    },
    {
      date: '2025-08-31',
      dayName: 'Sunday',
      available: true,
      startTime: '08:00',
      endTime: '16:00',
      notes: 'Prefer shorter shifts on Sunday'
    },
    {
      date: '2025-09-01',
      dayName: 'Monday',
      available: true,
      startTime: '08:00',
      endTime: '18:00',
      notes: ''
    },
    {
      date: '2025-09-02',
      dayName: 'Tuesday',
      available: true,
      startTime: '08:00',
      endTime: '15:00',
      notes: 'Prefers shorter shifts on Tue/Thu'
    }
  ];

  const fetchAvailabilityData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // For demo purposes, we'll use the demo data
      // In production, this would fetch from the API
      
      setTimeout(() => {
        setAvailabilityData(demoAvailability);
        setEditData(
          demoAvailability.reduce((acc, day) => ({
            ...acc,
            [day.date]: {
              available: day.available,
              startTime: day.startTime,
              endTime: day.endTime,
              notes: day.notes
            }
          }), {})
        );
        setLoading(false);
      }, 500);
      
    } catch (err) {
      console.error('Error fetching availability data:', err);
      setError('Failed to load availability data');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAvailabilityData();
  }, []);

  const handleEdit = () => {
    setEditMode(true);
  };

  const handleCancel = () => {
    setEditMode(false);
    // Reset edit data
    setEditData(
      availabilityData.reduce((acc, day) => ({
        ...acc,
        [day.date]: {
          available: day.available,
          startTime: day.startTime,
          endTime: day.endTime,
          notes: day.notes
        }
      }), {})
    );
  };

  const handleSave = async () => {
    try {
      // In production, this would update via the API
      console.log('Saving availability:', editData);
      
      // Update local state
      const updatedData = availabilityData.map(day => ({
        ...day,
        ...editData[day.date]
      }));
      
      setAvailabilityData(updatedData);
      setEditMode(false);
    } catch (err) {
      console.error('Error saving availability:', err);
    }
  };

  const handleAvailabilityChange = (date, field, value) => {
    setEditData(prev => ({
      ...prev,
      [date]: {
        ...prev[date],
        [field]: value
      }
    }));
  };

  const getTotalAvailableHours = () => {
    if (!availabilityData) return 0;
    return availabilityData.reduce((total, day) => {
      if (!day.available) return total;
      const start = new Date(`2000-01-01T${day.startTime}:00`);
      const end = new Date(`2000-01-01T${day.endTime}:00`);
      const hours = (end - start) / (1000 * 60 * 60);
      return total + hours;
    }, 0);
  };

  const getAvailableDays = () => {
    if (!availabilityData) return 0;
    return availabilityData.filter(day => day.available).length;
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="rectangular" height={80} sx={{ mb: 2 }} />
        {[...Array(7)].map((_, i) => (
          <Skeleton key={i} variant="rectangular" height={60} sx={{ mb: 1 }} />
        ))}
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">{error}</Alert>
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
                {getAvailableDays()}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Days Available
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h4" color="primary" sx={{ fontWeight: 600 }}>
                {getTotalAvailableHours()}h
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Hours
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Actions */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Schedule color="primary" />
          Weekly Availability
        </Typography>
        
        {!editMode ? (
          <Button
            variant="contained"
            startIcon={<Edit />}
            onClick={handleEdit}
            sx={{ borderRadius: 2 }}
          >
            Edit Availability
          </Button>
        ) : (
          <Stack direction="row" spacing={1}>
            <Button
              variant="outlined"
              startIcon={<Cancel />}
              onClick={handleCancel}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              startIcon={<Save />}
              onClick={handleSave}
            >
              Save Changes
            </Button>
          </Stack>
        )}
      </Box>

      {/* Availability List */}
      <Stack spacing={2}>
        {availabilityData.map((day, index) => {
          const dayData = editMode ? editData[day.date] : day;
          
          return (
            <Card key={day.date} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justify: 'space-between', alignItems: 'flex-start' }}>
                  <Box sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600, minWidth: 120 }}>
                        {day.dayName}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {day.date}
                      </Typography>
                      
                      {editMode ? (
                        <FormControlLabel
                          control={
                            <Switch
                              checked={dayData.available}
                              onChange={(e) => handleAvailabilityChange(day.date, 'available', e.target.checked)}
                              color="primary"
                            />
                          }
                          label="Available"
                        />
                      ) : (
                        <Chip
                          icon={dayData.available ? <CheckCircle /> : <Cancel />}
                          label={dayData.available ? 'Available' : 'Not Available'}
                          color={dayData.available ? 'success' : 'default'}
                          size="small"
                          variant="outlined"
                        />
                      )}
                    </Box>
                    
                    {dayData.available && (
                      <Box>
                        {editMode ? (
                          <Grid container spacing={2} sx={{ mb: 2 }}>
                            <Grid size={{ xs: 6 }}>
                              <TextField
                                label="Start Time"
                                type="time"
                                size="small"
                                value={dayData.startTime}
                                onChange={(e) => handleAvailabilityChange(day.date, 'startTime', e.target.value)}
                                InputLabelProps={{ shrink: true }}
                                fullWidth
                              />
                            </Grid>
                            <Grid size={{ xs: 6 }}>
                              <TextField
                                label="End Time"
                                type="time"
                                size="small"
                                value={dayData.endTime}
                                onChange={(e) => handleAvailabilityChange(day.date, 'endTime', e.target.value)}
                                InputLabelProps={{ shrink: true }}
                                fullWidth
                              />
                            </Grid>
                            <Grid size={{ xs: 12 }}>
                              <TextField
                                label="Notes"
                                size="small"
                                value={dayData.notes}
                                onChange={(e) => handleAvailabilityChange(day.date, 'notes', e.target.value)}
                                placeholder="Any specific preferences or notes..."
                                fullWidth
                                multiline
                                rows={2}
                              />
                            </Grid>
                          </Grid>
                        ) : (
                          <Box>
                            <Chip
                              icon={<AccessTime />}
                              label={`${dayData.startTime} - ${dayData.endTime}`}
                              color="primary"
                              variant="outlined"
                              sx={{ mb: 1 }}
                            />
                            {dayData.notes && (
                              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                                {dayData.notes}
                              </Typography>
                            )}
                          </Box>
                        )}
                      </Box>
                    )}
                  </Box>
                </Box>
              </CardContent>
            </Card>
          );
        })}
      </Stack>

      {editMode && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            Changes will be saved and your manager will be notified of your availability updates.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

export default AvailabilityPanel;