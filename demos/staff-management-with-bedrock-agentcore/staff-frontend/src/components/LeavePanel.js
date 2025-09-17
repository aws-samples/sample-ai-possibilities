import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  Chip,
  Grid,
  Button,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  MenuItem,
  Skeleton,
  Alert,
  LinearProgress
} from '@mui/material';
import {
  BeachAccess,
  Add,
  CheckCircle,
  Schedule,
  Cancel,
  LocalHospital
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';

const LeavePanel = ({ staffInfo, panelData }) => {
  const [leaveRequests, setLeaveRequests] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newRequestOpen, setNewRequestOpen] = useState(false);
  const [newRequest, setNewRequest] = useState({
    startDate: '',
    endDate: '',
    type: 'annual_leave',
    reason: ''
  });

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

  // Demo data for Emma Davis leave requests
  const demoLeaveData = {
    requests: [
      {
        id: 'HOL003',
        startDate: '2025-09-07',
        endDate: '2025-09-09',
        days: 3,
        type: 'annual_leave',
        reason: 'Weekend getaway with friends',
        status: 'pending',
        requestedAt: '2025-08-25T10:30:00Z'
      },
      {
        id: 'HOL004',
        startDate: '2025-09-22',
        endDate: '2025-09-22',
        days: 1,
        type: 'personal_leave',
        reason: 'Medical appointment',
        status: 'approved',
        requestedAt: '2025-08-17T14:15:00Z',
        approvedAt: '2025-08-19T09:20:00Z',
        approvedBy: 'Sarah Mitchell'
      }
    ],
    balances: {
      annual_leave: { available: 15, used: 3, total: 18 },
      sick_leave: { available: 8, used: 0, total: 8 },
      personal_leave: { available: 2, used: 1, total: 3 }
    }
  };

  const leaveTypes = [
    { value: 'annual_leave', label: 'Annual Leave', icon: <BeachAccess /> },
    { value: 'sick_leave', label: 'Sick Leave', icon: <LocalHospital /> },
    { value: 'personal_leave', label: 'Personal Leave', icon: <Schedule /> }
  ];

  const fetchLeaveData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // For demo purposes, we'll use the demo data
      // In production, this would fetch from the API:
      // const response = await fetch(`${API_URL}/api/my-holidays`);
      // const data = await response.json();
      
      setTimeout(() => {
        setLeaveRequests(demoLeaveData);
        setLoading(false);
      }, 600);
      
    } catch (err) {
      console.error('Error fetching leave data:', err);
      setError('Failed to load leave data');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaveData();
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'approved': return 'success';
      case 'pending': return 'warning';
      case 'rejected': return 'error';
      default: return 'default';
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'approved': return <CheckCircle />;
      case 'pending': return <Schedule />;
      case 'rejected': return <Cancel />;
      default: return null;
    }
  };

  const handleNewRequest = () => {
    setNewRequestOpen(true);
  };

  const handleCloseNewRequest = () => {
    setNewRequestOpen(false);
    setNewRequest({
      startDate: '',
      endDate: '',
      type: 'annual_leave',
      reason: ''
    });
  };

  const handleSubmitRequest = async () => {
    try {
      // In production, this would submit to the API
      console.log('Submitting leave request:', newRequest);
      
      // For demo, just add to local state
      const newLeaveRequest = {
        id: `HOL${Date.now()}`,
        ...newRequest,
        days: 1, // Calculate based on dates
        status: 'pending',
        requestedAt: new Date().toISOString()
      };

      setLeaveRequests(prev => ({
        ...prev,
        requests: [newLeaveRequest, ...prev.requests]
      }));

      handleCloseNewRequest();
    } catch (err) {
      console.error('Error submitting leave request:', err);
    }
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Skeleton variant="rectangular" height={120} sx={{ mb: 2 }} />
        <Skeleton variant="rectangular" height={60} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" height={60} sx={{ mb: 1 }} />
        <Skeleton variant="rectangular" height={60} />
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

  const { requests, balances } = leaveRequests;

  return (
    <Box sx={{ p: 3 }}>
      {/* Leave Balances */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        Leave Balances
      </Typography>
      
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {Object.entries(balances).map(([type, balance]) => {
          const leaveType = leaveTypes.find(t => t.value === type);
          const usedPercentage = (balance.used / balance.total) * 100;
          
          return (
            <Grid size={{ xs: 12, sm: 4 }} key={type}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    {leaveType?.icon}
                    <Typography variant="subtitle2">
                      {leaveType?.label}
                    </Typography>
                  </Box>
                  <Typography variant="h4" color="primary" sx={{ fontWeight: 600, mb: 1 }}>
                    {balance.available}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                    days available
                  </Typography>
                  <LinearProgress 
                    variant="determinate" 
                    value={usedPercentage} 
                    sx={{ mb: 1 }}
                  />
                  <Typography variant="caption" color="text.secondary">
                    {balance.used} of {balance.total} days used
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          );
        })}
      </Grid>

      {/* Actions */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Leave Requests
        </Typography>
        <Button
          variant="contained"
          startIcon={<Add />}
          onClick={handleNewRequest}
          sx={{ borderRadius: 2 }}
        >
          New Request
        </Button>
      </Box>

      {/* Leave Requests */}
      <Stack spacing={2}>
        {requests && requests.length > 0 ? (
          requests.map((request, index) => (
            <Card key={request.id} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                  <Box>
                    <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1 }}>
                      {leaveTypes.find(t => t.value === request.type)?.label}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                      {format(parseISO(request.startDate), 'MMM dd, yyyy')}
                      {request.startDate !== request.endDate && 
                        ` - ${format(parseISO(request.endDate), 'MMM dd, yyyy')}`
                      }
                      {request.days > 1 && ` (${request.days} days)`}
                    </Typography>
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      {request.reason}
                    </Typography>
                  </Box>
                  <Chip
                    icon={getStatusIcon(request.status)}
                    label={request.status.replace('_', ' ')}
                    color={getStatusColor(request.status)}
                    variant="outlined"
                    sx={{ textTransform: 'capitalize' }}
                  />
                </Box>
                
                <Box sx={{ display: 'flex', justify: 'space-between', alignItems: 'center' }}>
                  <Typography variant="caption" color="text.secondary">
                    Requested {format(parseISO(request.requestedAt), 'MMM dd, yyyy')}
                    {request.approvedAt && request.approvedBy && (
                      ` • Approved by ${request.approvedBy}`
                    )}
                  </Typography>
                  
                  {request.status === 'pending' && (
                    <Button size="small" color="error" variant="outlined">
                      Cancel
                    </Button>
                  )}
                </Box>
              </CardContent>
            </Card>
          ))
        ) : (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <BeachAccess sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              No leave requests
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Your leave requests will appear here
            </Typography>
          </Paper>
        )}
      </Stack>

      {/* New Request Dialog */}
      <Dialog 
        open={newRequestOpen} 
        onClose={handleCloseNewRequest}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>New Leave Request</DialogTitle>
        <DialogContent>
          <Stack spacing={3} sx={{ mt: 1 }}>
            <TextField
              select
              label="Leave Type"
              value={newRequest.type}
              onChange={(e) => setNewRequest(prev => ({ ...prev, type: e.target.value }))}
              fullWidth
            >
              {leaveTypes.map((type) => (
                <MenuItem key={type.value} value={type.value}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    {type.icon}
                    {type.label}
                  </Box>
                </MenuItem>
              ))}
            </TextField>
            
            <TextField
              label="Start Date"
              type="date"
              value={newRequest.startDate}
              onChange={(e) => setNewRequest(prev => ({ ...prev, startDate: e.target.value }))}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            
            <TextField
              label="End Date"
              type="date"
              value={newRequest.endDate}
              onChange={(e) => setNewRequest(prev => ({ ...prev, endDate: e.target.value }))}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            
            <TextField
              label="Reason"
              multiline
              rows={3}
              value={newRequest.reason}
              onChange={(e) => setNewRequest(prev => ({ ...prev, reason: e.target.value }))}
              fullWidth
              placeholder="Please provide a brief reason for your leave request..."
            />
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseNewRequest}>Cancel</Button>
          <Button 
            onClick={handleSubmitRequest} 
            variant="contained"
            disabled={!newRequest.startDate || !newRequest.endDate || !newRequest.reason}
          >
            Submit Request
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LeavePanel;