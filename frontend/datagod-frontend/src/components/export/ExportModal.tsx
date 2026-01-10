'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  RadioGroup,
  FormControlLabel,
  Radio,
  FormGroup,
  Checkbox,
  Alert,
  LinearProgress,
  Chip,
  Divider,
} from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import TableChartIcon from '@mui/icons-material/TableChart';
import CodeIcon from '@mui/icons-material/Code';
import GridOnIcon from '@mui/icons-material/GridOn';
import { apiService } from '../../services/api';

interface ExportModalProps {
  open: boolean;
  onClose: () => void;
  searchQuery: string;
  filters: Record<string, any>;
  resultCount: number;
}

type ExportFormat = 'csv' | 'excel' | 'json';

interface ExportField {
  key: string;
  label: string;
  default: boolean;
}

const availableFields: ExportField[] = [
  { key: 'title', label: 'Title / Name', default: true },
  { key: 'record_type', label: 'Document Type', default: true },
  { key: 'grantor', label: 'Grantor (From)', default: true },
  { key: 'grantee', label: 'Grantee (To)', default: true },
  { key: 'amount', label: 'Amount', default: true },
  { key: 'date', label: 'Date', default: true },
  { key: 'address', label: 'Address', default: true },
  { key: 'city', label: 'City', default: true },
  { key: 'state', label: 'State', default: true },
  { key: 'zip_code', label: 'ZIP Code', default: false },
  { key: 'document_number', label: 'Document Number', default: false },
  { key: 'book_page', label: 'Book/Page', default: false },
  { key: 'jurisdiction', label: 'Coverage Area', default: true },
];

const formatOptions = [
  { value: 'csv', label: 'CSV', description: 'Comma-separated values, works with any spreadsheet', icon: <TableChartIcon /> },
  { value: 'excel', label: 'Excel', description: 'Native Excel format (.xlsx) with formatting', icon: <GridOnIcon /> },
  { value: 'json', label: 'JSON', description: 'Structured data for developers', icon: <CodeIcon /> },
];

export const ExportModal = ({ open, onClose, searchQuery, filters, resultCount }: ExportModalProps) => {
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [selectedFields, setSelectedFields] = useState<string[]>(
    availableFields.filter(f => f.default).map(f => f.key)
  );
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const handleFieldToggle = (fieldKey: string) => {
    setSelectedFields(prev =>
      prev.includes(fieldKey)
        ? prev.filter(k => k !== fieldKey)
        : [...prev, fieldKey]
    );
  };

  const handleSelectAll = () => {
    setSelectedFields(availableFields.map(f => f.key));
  };

  const handleSelectNone = () => {
    setSelectedFields([]);
  };

  const handleExport = async () => {
    if (selectedFields.length === 0) {
      setError('Please select at least one field to export');
      return;
    }

    setIsExporting(true);
    setError(null);
    setProgress(10);

    try {
      // Simulate progress for UX
      const progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await apiService.exportData(format, searchQuery, {
        ...filters,
        fields: selectedFields,
      });

      clearInterval(progressInterval);
      setProgress(100);

      // Handle the download
      const blob = response.data instanceof Blob
        ? response.data
        : new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `datagod-export-${new Date().toISOString().split('T')[0]}.${format === 'excel' ? 'xlsx' : format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      // Close modal after successful download
      setTimeout(() => {
        onClose();
        setProgress(0);
        setIsExporting(false);
      }, 500);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Export failed. Please try again.');
      setIsExporting(false);
      setProgress(0);
    }
  };

  const handleClose = () => {
    if (!isExporting) {
      setError(null);
      setProgress(0);
      onClose();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <FileDownloadIcon color="primary" />
          <Typography variant="h6">Export Records</Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Download {resultCount.toLocaleString()} records matching your search
        </Typography>
      </DialogTitle>

      <DialogContent>
        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Format Selection */}
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Choose Format
        </Typography>
        <RadioGroup
          value={format}
          onChange={(e) => setFormat(e.target.value as ExportFormat)}
        >
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 2 }}>
            {formatOptions.map((option) => (
              <Box
                key={option.value}
                sx={{
                  flex: 1,
                  minWidth: 120,
                  border: 1,
                  borderColor: format === option.value ? 'primary.main' : 'divider',
                  borderRadius: 1,
                  p: 1.5,
                  cursor: 'pointer',
                  backgroundColor: format === option.value ? 'primary.light' : 'transparent',
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: 'primary.main',
                  },
                }}
                onClick={() => setFormat(option.value as ExportFormat)}
              >
                <FormControlLabel
                  value={option.value}
                  control={<Radio size="small" />}
                  label={
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      {option.icon}
                      <Typography variant="body2" fontWeight={500}>
                        {option.label}
                      </Typography>
                    </Box>
                  }
                  sx={{ m: 0 }}
                />
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', ml: 3.5 }}>
                  {option.description}
                </Typography>
              </Box>
            ))}
          </Box>
        </RadioGroup>

        <Divider sx={{ my: 2 }} />

        {/* Field Selection */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Select Fields
          </Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Chip label="All" size="small" onClick={handleSelectAll} variant="outlined" />
            <Chip label="None" size="small" onClick={handleSelectNone} variant="outlined" />
          </Box>
        </Box>

        <FormGroup sx={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 0.5 }}>
          {availableFields.map((field) => (
            <FormControlLabel
              key={field.key}
              control={
                <Checkbox
                  checked={selectedFields.includes(field.key)}
                  onChange={() => handleFieldToggle(field.key)}
                  size="small"
                />
              }
              label={<Typography variant="body2">{field.label}</Typography>}
              sx={{ m: 0 }}
            />
          ))}
        </FormGroup>

        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
          {selectedFields.length} of {availableFields.length} fields selected
        </Typography>

        {/* Progress */}
        {isExporting && (
          <Box sx={{ mt: 2 }}>
            <LinearProgress variant="determinate" value={progress} />
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              Preparing your download...
            </Typography>
          </Box>
        )}

        {/* Rate limit notice */}
        <Alert severity="info" sx={{ mt: 2 }} icon={false}>
          <Typography variant="caption">
            Exports are limited to 5 per minute. Large exports may take a moment to prepare.
          </Typography>
        </Alert>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={isExporting}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleExport}
          disabled={isExporting || selectedFields.length === 0}
          startIcon={<FileDownloadIcon />}
        >
          {isExporting ? 'Exporting...' : `Export ${format.toUpperCase()}`}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
