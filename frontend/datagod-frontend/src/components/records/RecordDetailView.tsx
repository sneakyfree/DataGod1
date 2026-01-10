'use client';

import {
  Box,
  Paper,
  Typography,
  Divider,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Chip,
  Link as MuiLink,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';

interface DataRecord {
  id: number;
  title: string;
  description?: string;
  record_type?: string;
  type?: string;
  amount?: number;
  date?: string;
  url?: string;
  status?: string;
  jurisdiction?: any;
  jurisdiction_id?: number;
  data_source?: any;
  data_source_id?: number;
  data?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

interface RecordDetailViewProps {
  record: DataRecord;
}

export const RecordDetailView = ({ record }: RecordDetailViewProps) => {
  const formatValue = (value: any): string => {
    if (value === null || value === undefined) return 'N/A';
    if (typeof value === 'boolean') return value ? 'Yes' : 'No';
    if (typeof value === 'number') {
      // Check if it looks like currency
      if (value > 100) {
        return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
      }
      return value.toString();
    }
    if (typeof value === 'object') return JSON.stringify(value, null, 2);
    return String(value);
  };

  const formatKey = (key: string): string => {
    return key
      .replace(/_/g, ' ')
      .replace(/([A-Z])/g, ' $1')
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
      .trim();
  };

  // Core fields that should always be shown first
  const coreFields = [
    { key: 'title', label: 'Title' },
    { key: 'record_type', label: 'Document Type' },
    { key: 'description', label: 'Description' },
    { key: 'amount', label: 'Amount' },
    { key: 'date', label: 'Date' },
    { key: 'status', label: 'Status' },
  ];

  // Additional structured data from the 'data' JSON field
  const additionalData = record.data || {};
  const additionalKeys = Object.keys(additionalData).filter(
    key => !['id', 'title', 'description', 'amount', 'date', 'status', 'record_type'].includes(key)
  );

  return (
    <Paper sx={{ p: 0, overflow: 'hidden' }}>
      {/* Core Information */}
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Record Details
        </Typography>
        <Table size="small">
          <TableBody>
            {coreFields.map(({ key, label }) => {
              const value = (record as any)[key];
              if (value === null || value === undefined) return null;
              return (
                <TableRow key={key}>
                  <TableCell
                    component="th"
                    sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
                  >
                    {label}
                  </TableCell>
                  <TableCell sx={{ border: 'none', py: 1.5 }}>
                    {key === 'status' ? (
                      <Chip
                        label={value}
                        size="small"
                        color={value === 'active' ? 'success' : 'default'}
                        variant="outlined"
                      />
                    ) : key === 'amount' ? (
                      new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
                    ) : key === 'date' ? (
                      new Date(value).toLocaleDateString('en-US', {
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                      })
                    ) : key === 'record_type' ? (
                      <Chip
                        label={String(value).charAt(0).toUpperCase() + String(value).slice(1)}
                        size="small"
                        color="primary"
                        variant="outlined"
                      />
                    ) : (
                      formatValue(value)
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </Box>

      <Divider />

      {/* Source Information */}
      <Box sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
          Source Information
        </Typography>
        <Table size="small">
          <TableBody>
            <TableRow>
              <TableCell
                component="th"
                sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
              >
                Jurisdiction
              </TableCell>
              <TableCell sx={{ border: 'none', py: 1.5 }}>
                {record.jurisdiction
                  ? typeof record.jurisdiction === 'object'
                    ? `${record.jurisdiction.name || 'Unknown'}, ${record.jurisdiction.state || ''}`
                    : record.jurisdiction
                  : `ID: ${record.jurisdiction_id || 'N/A'}`}
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell
                component="th"
                sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
              >
                Data Source
              </TableCell>
              <TableCell sx={{ border: 'none', py: 1.5 }}>
                {record.data_source
                  ? typeof record.data_source === 'object'
                    ? record.data_source.name || 'Unknown'
                    : record.data_source
                  : `ID: ${record.data_source_id || 'N/A'}`}
              </TableCell>
            </TableRow>
            {record.url && (
              <TableRow>
                <TableCell
                  component="th"
                  sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
                >
                  Original Source
                </TableCell>
                <TableCell sx={{ border: 'none', py: 1.5 }}>
                  <MuiLink
                    href={record.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5 }}
                  >
                    View Original Document
                    <OpenInNewIcon fontSize="small" />
                  </MuiLink>
                </TableCell>
              </TableRow>
            )}
            <TableRow>
              <TableCell
                component="th"
                sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
              >
                Record ID
              </TableCell>
              <TableCell sx={{ border: 'none', py: 1.5 }}>
                <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                  {record.id}
                </Typography>
              </TableCell>
            </TableRow>
            {record.created_at && (
              <TableRow>
                <TableCell
                  component="th"
                  sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
                >
                  Added to DataGod
                </TableCell>
                <TableCell sx={{ border: 'none', py: 1.5 }}>
                  {new Date(record.created_at).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'long',
                    day: 'numeric',
                  })}
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </Box>

      {/* Additional Data (if exists) */}
      {additionalKeys.length > 0 && (
        <>
          <Divider />
          <Accordion defaultExpanded sx={{ boxShadow: 'none', '&:before': { display: 'none' } }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ px: 3 }}>
              <Typography variant="h6" sx={{ fontWeight: 600 }}>
                Additional Details
              </Typography>
            </AccordionSummary>
            <AccordionDetails sx={{ px: 3, pb: 3 }}>
              <Table size="small">
                <TableBody>
                  {additionalKeys.map(key => (
                    <TableRow key={key}>
                      <TableCell
                        component="th"
                        sx={{ fontWeight: 500, width: '30%', color: 'text.secondary', border: 'none', py: 1.5 }}
                      >
                        {formatKey(key)}
                      </TableCell>
                      <TableCell sx={{ border: 'none', py: 1.5 }}>
                        {typeof additionalData[key] === 'object' ? (
                          <Box
                            component="pre"
                            sx={{
                              fontFamily: 'monospace',
                              fontSize: '0.85rem',
                              backgroundColor: 'grey.100',
                              p: 1,
                              borderRadius: 1,
                              overflow: 'auto',
                              maxHeight: 200,
                            }}
                          >
                            {JSON.stringify(additionalData[key], null, 2)}
                          </Box>
                        ) : (
                          formatValue(additionalData[key])
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </AccordionDetails>
          </Accordion>
        </>
      )}
    </Paper>
  );
};
