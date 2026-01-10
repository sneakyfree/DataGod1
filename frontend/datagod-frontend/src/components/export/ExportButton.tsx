'use client';

import { useState } from 'react';
import { Button, Badge } from '@mui/material';
import FileDownloadIcon from '@mui/icons-material/FileDownload';
import { ExportModal } from './ExportModal';

interface ExportButtonProps {
  searchQuery: string;
  filters: Record<string, any>;
  resultCount: number;
  disabled?: boolean;
}

export const ExportButton = ({ searchQuery, filters, resultCount, disabled = false }: ExportButtonProps) => {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <>
      <Button
        variant="outlined"
        color="primary"
        startIcon={<FileDownloadIcon />}
        onClick={() => setModalOpen(true)}
        disabled={disabled || resultCount === 0}
        sx={{
          minWidth: 'auto',
          whiteSpace: 'nowrap',
        }}
      >
        Export {resultCount > 0 && `(${resultCount.toLocaleString()})`}
      </Button>

      <ExportModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        searchQuery={searchQuery}
        filters={filters}
        resultCount={resultCount}
      />
    </>
  );
};
