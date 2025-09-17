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
  Skeleton,
  Alert,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress
} from '@mui/material';
import {
  AccountBalance,
  TrendingUp,
  Schedule,
  AttachMoney
} from '@mui/icons-material';
import { format, parseISO } from 'date-fns';

const PayrollPanel = ({ staffInfo, panelData }) => {
  const [payrollData, setPayrollData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

  // Demo payroll data for Emma Davis
  const demoPayrollData = {
    currentPeriod: {
      payPeriod: '2025-08-19 to 2025-08-25',
      hoursWorked: 32.0,
      hourlyRate: 26.5,
      grossPay: 848.0,
      deductions: {
        tax: 169.6,
        super: 84.8,
        other: 0
      },
      netPay: 593.6,
      status: 'processed',
      paymentDate: '2025-08-28'
    },
    yearToDate: {
      grossPay: 12720.0,
      tax: 2544.0,
      super: 1272.0,
      netPay: 8904.0,
      hoursWorked: 480
    },
    recentPayslips: [
      {
        id: 'PAY-2025-08-25',
        payPeriod: '2025-08-19 to 2025-08-25',
        hoursWorked: 32.0,
        grossPay: 848.0,
        netPay: 593.6,
        paymentDate: '2025-08-28',
        status: 'processed'
      },
      {
        id: 'PAY-2025-08-18',
        payPeriod: '2025-08-12 to 2025-08-18',
        hoursWorked: 36.0,
        grossPay: 954.0,
        netPay: 667.8,
        paymentDate: '2025-08-21',
        status: 'paid'
      },
      {
        id: 'PAY-2025-08-11',
        payPeriod: '2025-08-05 to 2025-08-11',
        hoursWorked: 30.0,
        grossPay: 795.0,
        netPay: 556.5,
        paymentDate: '2025-08-14',
        status: 'paid'
      },
      {
        id: 'PAY-2025-08-04',
        payPeriod: '2025-07-29 to 2025-08-04',
        hoursWorked: 34.0,
        grossPay: 901.0,
        netPay: 630.7,
        paymentDate: '2025-08-07',
        status: 'paid'
      }
    ]
  };

  const fetchPayrollData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // For demo purposes, we'll use the demo data
      // In production, this would fetch from the API
      
      setTimeout(() => {
        setPayrollData(demoPayrollData);
        setLoading(false);
      }, 700);
      
    } catch (err) {
      console.error('Error fetching payroll data:', err);
      setError('Failed to load payroll data');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPayrollData();
  }, []);

  const getStatusColor = (status) => {
    switch (status) {
      case 'paid': return 'success';
      case 'processed': return 'info';
      case 'pending': return 'warning';
      default: return 'default';
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-AU', {
      style: 'currency',
      currency: 'AUD'
    }).format(amount);
  };

  if (loading) {
    return (
      <Box sx={{ p: 3 }}>
        <Grid container spacing={2} sx={{ mb: 3 }}>
          {[...Array(4)].map((_, i) => (
            <Grid size={{ xs: 6 }} key={i}>
              <Skeleton variant="rectangular" height={80} />
            </Grid>
          ))}
        </Grid>
        <Skeleton variant="rectangular" height={300} />
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

  const { currentPeriod, yearToDate, recentPayslips } = payrollData;

  return (
    <Box sx={{ p: 3 }}>
      {/* Current Pay Period */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        Current Pay Period
      </Typography>
      
      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justify: 'space-between', alignItems: 'flex-start', mb: 2 }}>
            <Box>
              <Typography variant="h5" color="primary" sx={{ fontWeight: 600, mb: 1 }}>
                {formatCurrency(currentPeriod.netPay)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Net Pay • {currentPeriod.payPeriod}
              </Typography>
            </Box>
            <Chip
              label={currentPeriod.status}
              color={getStatusColor(currentPeriod.status)}
              variant="outlined"
              sx={{ textTransform: 'capitalize' }}
            />
          </Box>
          
          <Grid container spacing={2}>
            <Grid size={{ xs: 6 }}>
              <Typography variant="body2" color="text.secondary">Hours Worked</Typography>
              <Typography variant="h6">{currentPeriod.hoursWorked}h</Typography>
            </Grid>
            <Grid size={{ xs: 6 }}>
              <Typography variant="body2" color="text.secondary">Hourly Rate</Typography>
              <Typography variant="h6">{formatCurrency(currentPeriod.hourlyRate)}</Typography>
            </Grid>
            <Grid size={{ xs: 6 }}>
              <Typography variant="body2" color="text.secondary">Gross Pay</Typography>
              <Typography variant="h6">{formatCurrency(currentPeriod.grossPay)}</Typography>
            </Grid>
            <Grid size={{ xs: 6 }}>
              <Typography variant="body2" color="text.secondary">Payment Date</Typography>
              <Typography variant="h6">{currentPeriod.paymentDate}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Year to Date Summary */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        Year to Date Summary
      </Typography>
      
      <Grid container spacing={2} sx={{ mb: 3 }}>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h5" color="primary" sx={{ fontWeight: 600 }}>
                {formatCurrency(yearToDate.netPay)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Net Pay YTD
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h5" color="primary" sx={{ fontWeight: 600 }}>
                {yearToDate.hoursWorked}h
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Total Hours
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h5" color="success.main" sx={{ fontWeight: 600 }}>
                {formatCurrency(yearToDate.grossPay)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Gross Pay
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 6 }}>
          <Card variant="outlined">
            <CardContent sx={{ py: 2 }}>
              <Typography variant="h5" color="warning.main" sx={{ fontWeight: 600 }}>
                {formatCurrency(yearToDate.tax)}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Tax Deducted
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Recent Payslips */}
      <Typography variant="h6" sx={{ mb: 2 }}>
        Recent Payslips
      </Typography>
      
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Pay Period</TableCell>
              <TableCell align="right">Hours</TableCell>
              <TableCell align="right">Gross Pay</TableCell>
              <TableCell align="right">Net Pay</TableCell>
              <TableCell align="center">Status</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {recentPayslips.map((payslip) => (
              <TableRow key={payslip.id} hover>
                <TableCell>
                  <Typography variant="body2" sx={{ fontWeight: 500 }}>
                    {payslip.payPeriod}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Paid: {payslip.paymentDate}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 1 }}>
                    <Schedule sx={{ fontSize: 16, color: 'text.secondary' }} />
                    {payslip.hoursWorked}h
                  </Box>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" color="success.main" sx={{ fontWeight: 500 }}>
                    {formatCurrency(payslip.grossPay)}
                  </Typography>
                </TableCell>
                <TableCell align="right">
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {formatCurrency(payslip.netPay)}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Chip
                    label={payslip.status}
                    color={getStatusColor(payslip.status)}
                    size="small"
                    variant="outlined"
                    sx={{ textTransform: 'capitalize' }}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Tax Information */}
      <Alert severity="info" sx={{ mt: 3 }}>
        <Typography variant="body2">
          <strong>Tax Information:</strong> Your payslips and tax statements are available through your employee portal. 
          Contact HR if you need assistance with tax declarations.
        </Typography>
      </Alert>
    </Box>
  );
};

export default PayrollPanel;