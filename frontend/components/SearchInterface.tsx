import React, { useState } from 'react';
import { TextField, Button, Box, Typography, Autocomplete, Chip } from '@mui/material';
import { Link } from 'react-router-dom';

const SearchInterface: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filters, setFilters] = useState<{ [key: string]: string }>({});
  const [selectedJurisdiction, setSelectedJurisdiction] = useState('');
  const [selectedDataSource, setSelectedDataSource] = useState('');
  const [selectedRecordType, setSelectedRecordType] = useState('');

  const jurisdictions = [
    { id: '1', name: 'New York County, NY' },
    { id: '2', name: 'Los Angeles County, CA' },
    { id: '3', name: 'Cook County, IL' },
    { id: '4', name: 'Maricopa County, AZ' },
    { id: '5', name: 'Harris County, TX' },
  ];

  const dataSources = [
    { id: '1', name: 'NYC Open Data' },
    { id: '2', name: 'LA County Records' },
    { id: '3', name: 'Chicago Public Records' },
    { id: '4', name: 'Phoenix Public Records' },
    { id: '5', name: 'Houston Public Records' },
  ];

  const recordTypes = [
    { id: '1', name: 'Mortgage' },
    { id: '2', name: 'Deed' },
    { id: '3', name: 'Lien' },
    { id: '4', name: 'Foreclosure' },
    { id: '5', name: 'Tax Lien' },
  ];

  const handleSearch = () => {
    // Implement search functionality
    console.log('Searching for:', searchTerm, 'with filters:', filters);
  };

  const handleFilterChange = (field: string, value: string) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h4" gutterBottom>
        Search Mortgage Records
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
        <TextField
          label="Search Term"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          variant="outlined"
          size="small"
          sx={{ flex: 1, minWidth: 200 }}
        />
        <Button
          variant="contained"
          onClick={handleSearch}
          sx={{ height: '40px' }}
        >
          Search
        </Button>
      </Box>
      
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
        <Autocomplete
          options={jurisdictions}
          getOptionLabel={(option) => option.name}
          value={jurisdictions.find(j => j.id === selectedJurisdiction) || null}
          onChange={(event, value) => setSelectedJurisdiction(value?.id || '')}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Jurisdiction"
              variant="outlined"
              size="small"
              sx={{ flex: 1, minWidth: 200 }}
            />
          )}
        />
        
        <Autocomplete
          options={dataSources}
          getOptionLabel={(option) => option.name}
          value={dataSources.find(ds => ds.id === selectedDataSource) || null}
          onChange={(event, value) => setSelectedDataSource(value?.id || '')}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Data Source"
              variant="outlined"
              size="small"
              sx={{ flex: 1, minWidth: 200 }}
            />
          )}
        />
        
        <Autocomplete
          options={recordTypes}
          getOptionLabel={(option) => option.name}
          value={recordTypes.find(rt => rt.id === selectedRecordType) || null}
          onChange={(event, value) => setSelectedRecordType(value?.id || '')}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Record Type"
              variant="outlined"
              size="small"
              sx={{ flex: 1, minWidth: 200 }}
            />
          )}
        />
      </Box>
      
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          {Object.entries(filters).map(([key, value]) => (
            <Chip
              key={key}
              label={`${key}: ${value}`}
              onDelete={() => handleFilterChange(key, '')}
              variant="outlined"
              size="small"
            />
          ))}
        </Box>
      </Box>
    </Box>
  );
};

export default SearchInterface;
