import React from 'react';
import { Box, Typography, Grid, Card, CardContent, CardHeader, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Button } from '@mui/material';
import { Link } from 'react-router-dom';

const Jurisdictions: React.FC = () => {
  // Mock data for jurisdictions
  const jurisdictions = [
    { id: '1', name: 'New York County, NY', state: 'NY', county: 'New York', api_available: true, scraper_needed: false },
    { id: '2', name: 'Los Angeles County, CA', state: 'CA', county: 'Los Angeles', api_available: true, scraper_needed: false },
    { id: '3', name: 'Cook County, IL', state: 'IL', county: 'Cook', api_available: true, scraper_needed: false },
    { id: '4', name: 'Maricopa County, AZ', state: 'AZ', county: 'Maricopa', api_available: false, scraper_needed: true },
    { id: '5', name: 'Harris County, TX', state: 'TX', county: 'Harris', api_available: false, scraper_needed: true },
  ];

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Jurisdictions
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>State</TableCell>
              <TableCell>County</TableCell>
              <TableCell>API Available</TableCell>
              <TableCell>Scraper Needed</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {jurisdictions.map((jurisdiction) => (
              <TableRow key={jurisdiction.id}>
                <TableCell>{jurisdiction.name}</TableCell>
                <TableCell>{jurisdiction.state}</TableCell>
                <TableCell>{jurisdiction.county}</TableCell>
                <TableCell>{jurisdiction.api_available ? 'Yes' : 'No'}</TableCell>
                <TableCell>{jurisdiction.scraper_needed ? 'Yes' : 'No'}</TableCell>
                <TableCell>
                  <Button variant="contained" size="small" component={Link} to={`/jurisdictions/${jurisdiction.id}`}>
                    View Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default Jurisdictions;
