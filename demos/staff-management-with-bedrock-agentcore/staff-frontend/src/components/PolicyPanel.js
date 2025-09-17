import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Stack,
  Chip,
  Skeleton,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  IconButton
} from '@mui/material';
import {
  Policy,
  Search,
  ExpandMore,
  MenuBook,
  Info,
  Warning,
  CheckCircle
} from '@mui/icons-material';

const PolicyPanel = ({ staffInfo, panelData }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [recentSearches, setRecentSearches] = useState([
    'sick leave policy',
    'annual leave entitlements',
    'dress code',
    'break policies'
  ]);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8081';

  // Demo policy data
  const demoPolicies = [
    {
      id: 'leave-policy',
      title: 'Leave and Holiday Policy',
      category: 'Leave Management',
      summary: 'Guidelines for annual leave, sick leave, and personal leave requests',
      content: `**Annual Leave Entitlements**

All full-time employees are entitled to 4 weeks (20 working days) of annual leave per year. Part-time employees receive pro-rata entitlements based on their working hours.

**Sick Leave Policy**

- Full-time employees: 10 days per year
- Part-time employees: Pro-rata based on hours worked
- Medical certificates required for absences over 3 consecutive days

**Personal Leave**

Up to 3 days per year for personal emergencies or appointments that cannot be scheduled outside work hours.

**Leave Request Process**

1. Submit requests at least 2 weeks in advance
2. Requests approved based on business needs and coverage
3. Peak periods (holidays, weekends) may have restrictions`,
      tags: ['leave', 'holidays', 'sick leave', 'annual leave']
    },
    {
      id: 'break-policy',
      title: 'Break and Meal Policy',
      category: 'Working Conditions',
      summary: 'Guidelines for rest breaks and meal periods during shifts',
      content: `**Rest Breaks**

- 15-minute paid break for shifts 4-6 hours
- 30-minute unpaid meal break for shifts over 6 hours
- Additional 15-minute paid break for shifts over 8 hours

**Break Scheduling**

- Breaks scheduled by shift supervisor
- Coverage must be arranged before taking breaks
- Meal breaks typically taken mid-shift

**Break Areas**

- Staff break room available with microwave and refrigerator
- Outdoor seating area available weather permitting`,
      tags: ['breaks', 'meals', 'rest periods', 'shifts']
    },
    {
      id: 'dress-code',
      title: 'Dress Code and Uniform Policy',
      category: 'Workplace Standards',
      summary: 'Professional appearance standards and uniform requirements',
      content: `**Uniform Requirements**

- Company-provided aprons must be worn at all times
- Dark colored pants (black, navy, or dark brown)
- Closed-toe, non-slip shoes required
- Hair longer than shoulder length must be tied back

**Personal Hygiene**

- Clean, well-groomed appearance expected
- Minimal jewelry (wedding rings, small earrings acceptable)
- No strong perfumes or fragrances
- Name tags must be visible

**Uniform Care**

- Aprons laundered by company
- Personal clothing items maintained by employee
- Report damaged uniforms to management immediately`,
      tags: ['dress code', 'uniform', 'appearance', 'safety']
    }
  ];

  const performSearch = async (query) => {
    if (!query.trim()) return;

    setLoading(true);
    try {
      // For demo purposes, filter demo policies
      // In production, this would call the Knowledge Base API
      const results = demoPolicies.filter(policy =>
        policy.title.toLowerCase().includes(query.toLowerCase()) ||
        policy.content.toLowerCase().includes(query.toLowerCase()) ||
        policy.tags.some(tag => tag.toLowerCase().includes(query.toLowerCase()))
      );
      
      setTimeout(() => {
        setSearchResults(results);
        setLoading(false);
        
        // Add to recent searches if not already there
        if (!recentSearches.includes(query)) {
          setRecentSearches(prev => [query, ...prev.slice(0, 4)]);
        }
      }, 800);
      
    } catch (err) {
      console.error('Error searching policies:', err);
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    performSearch(searchQuery);
  };

  const handleRecentSearch = (query) => {
    setSearchQuery(query);
    performSearch(query);
  };

  const getPolicyIcon = (category) => {
    switch (category) {
      case 'Leave Management': return <CheckCircle color="success" />;
      case 'Working Conditions': return <Info color="info" />;
      case 'Workplace Standards': return <Warning color="warning" />;
      default: return <Policy />;
    }
  };

  // Auto-search if panelData contains search query
  useEffect(() => {
    if (panelData?.searchQuery) {
      setSearchQuery(panelData.searchQuery);
      performSearch(panelData.searchQuery);
    }
  }, [panelData]);

  return (
    <Box sx={{ p: 3 }}>
      {/* Search Section */}
      <Typography variant="h6" sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <MenuBook color="primary" />
        Company Policies & Procedures
      </Typography>

      <form onSubmit={handleSearch}>
        <TextField
          fullWidth
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search policies (e.g., 'sick leave', 'dress code', 'break policy')..."
          variant="outlined"
          sx={{ mb: 3 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            )
          }}
        />
      </form>

      {/* Recent Searches */}
      {recentSearches.length > 0 && !searchResults.length && !loading && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
            Recent Searches
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {recentSearches.map((query, index) => (
              <Chip
                key={index}
                label={query}
                size="small"
                variant="outlined"
                clickable
                onClick={() => handleRecentSearch(query)}
                sx={{ mb: 1 }}
              />
            ))}
          </Stack>
        </Box>
      )}

      {/* Loading State */}
      {loading && (
        <Stack spacing={2}>
          <Skeleton variant="rectangular" height={60} />
          <Skeleton variant="rectangular" height={60} />
          <Skeleton variant="rectangular" height={60} />
        </Stack>
      )}

      {/* Search Results */}
      {searchResults.length > 0 && !loading && (
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 2, color: 'primary.main' }}>
            Found {searchResults.length} result{searchResults.length !== 1 ? 's' : ''} for "{searchQuery}"
          </Typography>
          
          <Stack spacing={2}>
            {searchResults.map((policy) => (
              <Accordion key={policy.id} elevation={0} variant="outlined">
                <AccordionSummary expandIcon={<ExpandMore />}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                    {getPolicyIcon(policy.category)}
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                        {policy.title}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {policy.summary}
                      </Typography>
                      <Box sx={{ mt: 1 }}>
                        <Chip
                          label={policy.category}
                          size="small"
                          color="primary"
                          variant="outlined"
                        />
                      </Box>
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" sx={{ whiteSpace: 'pre-line', lineHeight: 1.8 }}>
                    {policy.content}
                  </Typography>
                  
                  <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                      Related Topics:
                    </Typography>
                    <Stack direction="row" spacing={0.5} flexWrap="wrap">
                      {policy.tags.map((tag, index) => (
                        <Chip
                          key={index}
                          label={tag}
                          size="small"
                          variant="outlined"
                          clickable
                          onClick={() => handleRecentSearch(tag)}
                          sx={{ mb: 0.5, fontSize: '0.7rem' }}
                        />
                      ))}
                    </Stack>
                  </Box>
                </AccordionDetails>
              </Accordion>
            ))}
          </Stack>
        </Box>
      )}

      {/* No Results */}
      {searchQuery && searchResults.length === 0 && !loading && (
        <Alert severity="info">
          <Typography variant="body2">
            No policies found for "{searchQuery}". Try searching for terms like "leave", "break", "uniform", or "safety".
          </Typography>
        </Alert>
      )}

      {/* Default State */}
      {!searchQuery && !loading && (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <MenuBook sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
          <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
            Search Company Policies
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Find information about leave policies, workplace procedures, and company guidelines.
          </Typography>
          
          <Stack spacing={2}>
            <Typography variant="subtitle2" color="text.secondary">
              Popular Topics:
            </Typography>
            <Stack direction="row" spacing={1} justifyContent="center" flexWrap="wrap">
              {[
                'Annual Leave Policy',
                'Sick Leave Guidelines', 
                'Break & Meal Policies',
                'Dress Code Requirements',
                'Safety Procedures'
              ].map((topic, index) => (
                <Chip
                  key={index}
                  label={topic}
                  variant="outlined"
                  clickable
                  onClick={() => {
                    setSearchQuery(topic.toLowerCase());
                    performSearch(topic.toLowerCase());
                  }}
                  sx={{ mb: 1 }}
                />
              ))}
            </Stack>
          </Stack>
        </Box>
      )}

      {/* Help Text */}
      <Alert severity="info" sx={{ mt: 3 }}>
        <Typography variant="body2">
          <strong>Can't find what you're looking for?</strong> Ask me in the chat about specific policies 
          or contact HR for additional assistance.
        </Typography>
      </Alert>
    </Box>
  );
};

export default PolicyPanel;