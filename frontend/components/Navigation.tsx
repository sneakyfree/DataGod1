import React from 'react';
import { AppBar, Toolbar, Typography, Box, Button, Container, Link } from '@mui/material';
import { Link as RouterLink } from 'react-router-dom';

const Navigation: React.FC = () => {
  return (
    <AppBar position="static" color="primary">
      <Container maxWidth="lg">
        <Toolbar>
          <Typography variant="h6" component={RouterLink} to="/" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }}>
            DataGod - Mortgage Data Gathering Neural Network
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button color="inherit" component={RouterLink} to="/search">
              Search
            </Button>
            <Button color="inherit" component={RouterLink} to="/dashboard">
              Dashboard
            </Button>
            <Button color="inherit" component={RouterLink} to="/records">
              Records
            </Button>
            <Button color="inherit" component={RouterLink} to="/jurisdictions">
              Jurisdictions
            </Button>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navigation;
