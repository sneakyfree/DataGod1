'use client';

/**
 * DataGod SearchTypeahead Component
 * Autocomplete dropdown for the search bar
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    Box,
    TextField,
    Paper,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    CircularProgress,
    Chip,
    Typography,
    InputAdornment,
    Divider,
} from '@mui/material';
import {
    Search,
    Description,
    Person,
    Business,
    History,
} from '@mui/icons-material';
import { apiService } from '../../services/api';

interface Suggestion {
    type: 'record' | 'entity';
    id: number;
    text: string;
    subtype?: string;
}

interface RecentSearch {
    id: number;
    name: string;
    query: any;
    created_at: string;
}

interface SearchTypeaheadProps {
    onSelect: (suggestion: Suggestion | RecentSearch) => void;
    onSearch: (query: string) => void;
    placeholder?: string;
}

export default function SearchTypeahead({
    onSelect,
    onSearch,
    placeholder = 'Search records, entities...',
}: SearchTypeaheadProps) {
    const [query, setQuery] = useState('');
    const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
    const [recentSearches, setRecentSearches] = useState<RecentSearch[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [isOpen, setIsOpen] = useState(false);
    const debounceRef = useRef<ReturnType<typeof setTimeout>>();
    const containerRef = useRef<HTMLDivElement>(null);

    // Load recent searches on focus
    const loadRecentSearches = useCallback(async () => {
        try {
            const res = await apiService.get('/search/recent', { params: { limit: 5 } });
            setRecentSearches(res.data?.recent_searches || []);
        } catch {
            // Silent fail for recent searches
        }
    }, []);

    // Fetch typeahead suggestions
    useEffect(() => {
        if (debounceRef.current) clearTimeout(debounceRef.current);

        if (query.length < 2) {
            setSuggestions([]);
            return;
        }

        debounceRef.current = setTimeout(async () => {
            setIsLoading(true);
            try {
                const res = await apiService.get('/search/typeahead', { params: { q: query, limit: 8 } });
                setSuggestions(res.data?.suggestions || []);
            } catch {
                setSuggestions([]);
            } finally {
                setIsLoading(false);
            }
        }, 250); // 250ms debounce

        return () => {
            if (debounceRef.current) clearTimeout(debounceRef.current);
        };
    }, [query]);

    // Close dropdown on outside click
    useEffect(() => {
        const handle = (e: MouseEvent) => {
            if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };
        document.addEventListener('mousedown', handle);
        return () => document.removeEventListener('mousedown', handle);
    }, []);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter') {
            onSearch(query);
            setIsOpen(false);
        }
        if (e.key === 'Escape') {
            setIsOpen(false);
        }
    };

    const iconForType = (type: string) => {
        switch (type) {
            case 'record': return <Description fontSize="small" />;
            case 'entity': return <Person fontSize="small" />;
            default: return <Search fontSize="small" />;
        }
    };

    return (
        <Box ref={containerRef} sx={{ position: 'relative', width: '100%' }}>
            <TextField
                fullWidth
                placeholder={placeholder}
                value={query}
                onChange={(e) => {
                    setQuery(e.target.value);
                    setIsOpen(true);
                }}
                onFocus={() => {
                    setIsOpen(true);
                    loadRecentSearches();
                }}
                onKeyDown={handleKeyDown}
                InputProps={{
                    startAdornment: (
                        <InputAdornment position="start">
                            <Search />
                        </InputAdornment>
                    ),
                    endAdornment: isLoading ? (
                        <InputAdornment position="end">
                            <CircularProgress size={20} />
                        </InputAdornment>
                    ) : undefined,
                }}
            />

            {isOpen && (suggestions.length > 0 || (query.length === 0 && recentSearches.length > 0)) && (
                <Paper
                    elevation={8}
                    sx={{
                        position: 'absolute',
                        top: '100%',
                        left: 0,
                        right: 0,
                        zIndex: 1300,
                        maxHeight: 400,
                        overflow: 'auto',
                        mt: 0.5,
                    }}
                >
                    <List dense disablePadding>
                        {/* Recent searches when no query */}
                        {query.length === 0 && recentSearches.length > 0 && (
                            <>
                                <ListItem sx={{ py: 0.5 }}>
                                    <Typography variant="caption" color="text.disabled" fontWeight={600}>
                                        Recent Searches
                                    </Typography>
                                </ListItem>
                                {recentSearches.map((rs) => (
                                    <ListItem
                                        key={rs.id}
                                        onClick={() => {
                                            onSelect(rs);
                                            setIsOpen(false);
                                        }}
                                        sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                                    >
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            <History fontSize="small" color="action" />
                                        </ListItemIcon>
                                        <ListItemText primary={rs.name} />
                                    </ListItem>
                                ))}
                            </>
                        )}

                        {/* Typeahead suggestions */}
                        {suggestions.length > 0 && (
                            <>
                                {query.length === 0 && recentSearches.length > 0 && <Divider />}
                                {suggestions.map((s, i) => (
                                    <ListItem
                                        key={`${s.type}-${s.id}-${i}`}
                                        onClick={() => {
                                            onSelect(s);
                                            setIsOpen(false);
                                            setQuery(s.text);
                                        }}
                                        sx={{ cursor: 'pointer', '&:hover': { bgcolor: 'action.hover' } }}
                                    >
                                        <ListItemIcon sx={{ minWidth: 32 }}>
                                            {iconForType(s.type)}
                                        </ListItemIcon>
                                        <ListItemText
                                            primary={s.text}
                                            secondary={s.subtype?.replace(/_/g, ' ')}
                                        />
                                        <Chip label={s.type} size="small" variant="outlined" sx={{ textTransform: 'capitalize' }} />
                                    </ListItem>
                                ))}
                            </>
                        )}
                    </List>
                </Paper>
            )}
        </Box>
    );
}
