import React from 'react';
import { Box, Typography, Grid, Card, CardContent, CardHeader, Divider, Chip, List, ListItem, ListItemText, Avatar, Button } from '@mui/material';
import { Link } from 'react-router-dom';

const RecordDetailView: React.FC<{ record: any }> = ({ record }) => {
  return (
    <Box sx={{ p: 2 }}>
      <Card>
        <CardHeader
          title={record.title}
          subheader={`Record ID: ${record.id} | Date: ${record.date}`}
          avatar={
            <Avatar sx={{ bgcolor: 'primary.main' }}>
              {record.record_type.charAt(0)}
            </Avatar>
          }
        />
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Record Details
              </Typography>
              <List>
                <ListItem>
                  <ListItemText primary="Jurisdiction" secondary={record.jurisdiction.name} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Data Source" secondary={record.data_source.name} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Amount" secondary={record.amount ? `$${record.amount.toLocaleString()}` : 'N/A'} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="URL" secondary={record.url} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Record Type" secondary={record.record_type} />
                </ListItem>
                <ListItem>
                  <ListItemText primary="Status" secondary={record.status} />
                </ListItem>
              </List>
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Description
              </Typography>
              <Typography paragraph>
                {record.description || 'No description available.'}
              </Typography>
              <Typography variant="h6" gutterBottom sx={{ mt: 2 }}>
                Related Entities
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {record.related_entities?.map((entity: any) => (
                  <Chip
                    key={entity.id}
                    label={entity.entity_name}
                    variant="outlined"
                    size="small"
                  />
                ))}
              </Box>
            </Grid>
          </Grid>
          <Divider sx={{ my: 2 }} />
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
            <Button variant="contained" color="primary" component={Link} to="/records">
              Back to Records
            </Button>
            <Button variant="contained" color="secondary" component={Link} to="/search">
              Search Again
            </Button>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default RecordDetailView;
