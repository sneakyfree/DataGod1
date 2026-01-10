import React from 'react';
import { Box, Typography, Grid, Card, CardContent, CardHeader, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Button } from '@mui/material';
import { Link } from 'react-router-dom';

const Records: React.FC = () => {
  // Mock data for records
  const records = [
    { id: '1', title: 'Mortgage for 123 Main St', jurisdiction: { name: 'New York County, NY' }, data_source: { name: 'NYC Open Data' }, amount: 500000, date: '2025-01-15', record_type: 'Mortgage' },
    { id: '2', title: 'Deed for 456 Oak Ave', jurisdiction: { name: 'Los Angeles County, CA' }, data_source: { name: 'LA County Records' }, amount: 750000, date: '2025-02-20', record_type: 'Deed' },
    { id: '3', title: 'Lien for 789 Pine Rd', jurisdiction: { name: 'Cook County, IL' }, data_source: { name: 'Chicago Public Records' }, amount: 25000, date: '2025-03-10', record_type: 'Lien' },
    { id: '4', title: 'Foreclosure for 101 Elm St', jurisdiction: { name: 'Maricopa County, AZ' }, data_source: { name: 'Phoenix Public Records' }, amount: 300000, date: '2025-04-05', record_type: 'Foreclosure' },
    { id: '5', title: 'Tax Lien for 202 Maple Dr', jurisdiction: { name: 'Harris County, TX' }, data_source: { name: 'Houston Public Records' }, amount: 15000, date: '2025-05-12', record_type: 'Tax Lien' },
  ];

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h4" gutterBottom>
        Records
      </Typography>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Title</TableCell>
              <TableCell>Jurisdiction</TableCell>
              <TableCell>Data Source</TableCell>
              <TableCell>Amount</TableCell>
              <TableCell>Date</TableCell>
              <TableCell>Record Type</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {records.map((record) => (
              <TableRow key={record.id}>
                <TableCell>{record.title}</TableCell>
                <TableCell>{record.jurisdiction.name}</TableCell>
                <TableCell>{record.data_source.name}</TableCell>
                <TableCell>{record.amount ? `$${record.amount.toLocaleString()}` : 'N/A'}</TableCell>
                <TableCell>{record.date}</TableCell>
                <TableCell>{record.record_type}</TableCell>
                <TableCell>
                  <Button variant="contained" size="small" component={Link} to={`/records/${record.id}`}>
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

export default Records;
