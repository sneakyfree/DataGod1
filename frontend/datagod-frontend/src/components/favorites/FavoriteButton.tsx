'use client';

import { useState, useEffect } from 'react';
import { IconButton, Tooltip, CircularProgress } from '@mui/material';
import FavoriteIcon from '@mui/icons-material/Favorite';
import FavoriteBorderIcon from '@mui/icons-material/FavoriteBorder';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';

interface FavoriteButtonProps {
  type: 'record' | 'entity';
  itemId: number;
  size?: 'small' | 'medium' | 'large';
  showTooltip?: boolean;
}

export const FavoriteButton = ({
  type,
  itemId,
  size = 'medium',
  showTooltip = true,
}: FavoriteButtonProps) => {
  const queryClient = useQueryClient();
  const [favoriteId, setFavoriteId] = useState<number | null>(null);

  // Check if item is favorited
  const { data: favoriteData, isLoading: checkLoading } = useQuery({
    queryKey: ['favoriteCheck', type, itemId],
    queryFn: () => apiService.checkFavorite(type, itemId).then(res => res.data),
    staleTime: 30 * 1000,
  });

  useEffect(() => {
    if (favoriteData?.is_favorited) {
      setFavoriteId(favoriteData.favorite_id);
    } else {
      setFavoriteId(null);
    }
  }, [favoriteData]);

  const isFavorited = !!favoriteId;

  // Add to favorites mutation
  const addMutation = useMutation({
    mutationFn: () =>
      apiService.addFavorite({
        record_id: type === 'record' ? itemId : undefined,
        entity_id: type === 'entity' ? itemId : undefined,
        favorite_type: type,
      }),
    onSuccess: (response) => {
      setFavoriteId(response.data.id);
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
      queryClient.invalidateQueries({ queryKey: ['favoriteCheck', type, itemId] });
    },
  });

  // Remove from favorites mutation
  const removeMutation = useMutation({
    mutationFn: () => apiService.removeFavorite(favoriteId!),
    onSuccess: () => {
      setFavoriteId(null);
      queryClient.invalidateQueries({ queryKey: ['favorites'] });
      queryClient.invalidateQueries({ queryKey: ['favoriteCheck', type, itemId] });
    },
  });

  const isLoading = checkLoading || addMutation.isPending || removeMutation.isPending;

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    if (isFavorited) {
      removeMutation.mutate();
    } else {
      addMutation.mutate();
    }
  };

  const tooltipText = isFavorited ? 'Remove from favorites' : 'Add to favorites';

  const button = (
    <IconButton
      onClick={handleToggle}
      disabled={isLoading}
      size={size}
      sx={{
        color: isFavorited ? 'error.main' : 'action.active',
        '&:hover': {
          color: isFavorited ? 'error.dark' : 'error.main',
        },
      }}
    >
      {isLoading ? (
        <CircularProgress size={size === 'small' ? 16 : size === 'large' ? 28 : 20} />
      ) : isFavorited ? (
        <FavoriteIcon fontSize={size} />
      ) : (
        <FavoriteBorderIcon fontSize={size} />
      )}
    </IconButton>
  );

  if (showTooltip) {
    return <Tooltip title={tooltipText}>{button}</Tooltip>;
  }

  return button;
};
