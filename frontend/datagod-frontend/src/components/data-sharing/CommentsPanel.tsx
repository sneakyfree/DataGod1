'use client';

import { useState, useCallback } from 'react';
import {
    Box,
    Typography,
    Paper,
    TextField,
    Button,
    Avatar,
    IconButton,
    CircularProgress,
    Divider,
    Collapse,
} from '@mui/material';
import {
    Send,
    Reply,
    Delete,
    ExpandMore,
    ExpandLess,
    Comment as CommentIcon,
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { useAuth } from '../../context/AuthContext';

interface Comment {
    id: number;
    user_id: number;
    username: string;
    full_name?: string;
    content: string;
    parent_id?: number;
    record_id: number;
    created_at: string;
    children?: Comment[];
}

interface CommentsPanelProps {
    recordId: number;
    entityId?: number;
}

function SingleComment({
    comment,
    depth = 0,
    onReply,
    onDelete,
    currentUsername,
}: {
    comment: Comment;
    depth?: number;
    onReply: (parentId: number) => void;
    onDelete: (commentId: number) => void;
    currentUsername?: string;
}) {
    const [showReplies, setShowReplies] = useState(true);
    const displayName = comment.full_name || comment.username || 'User';
    const initial = displayName.charAt(0).toUpperCase();
    const timeAgo = getTimeAgo(comment.created_at);
    const isOwner = comment.username === currentUsername;

    return (
        <Box sx={{ ml: depth * 3, mt: depth > 0 ? 1 : 2 }}>
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start' }}>
                <Avatar
                    sx={{
                        width: 32,
                        height: 32,
                        fontSize: '0.875rem',
                        bgcolor: depth === 0 ? 'primary.main' : 'secondary.main',
                    }}
                >
                    {initial}
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography variant="subtitle2">{displayName}</Typography>
                        <Typography variant="caption" color="text.secondary">
                            {timeAgo}
                        </Typography>
                    </Box>
                    <Typography variant="body2" sx={{ mt: 0.5, whiteSpace: 'pre-wrap' }}>
                        {comment.content}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 1, mt: 0.5 }}>
                        <Button
                            size="small"
                            startIcon={<Reply sx={{ fontSize: 14 }} />}
                            onClick={() => onReply(comment.id)}
                            sx={{ textTransform: 'none', fontSize: '0.75rem', minWidth: 0 }}
                        >
                            Reply
                        </Button>
                        {isOwner && (
                            <IconButton
                                size="small"
                                onClick={() => onDelete(comment.id)}
                                sx={{ fontSize: '0.75rem' }}
                            >
                                <Delete sx={{ fontSize: 16 }} />
                            </IconButton>
                        )}
                    </Box>
                </Box>
            </Box>

            {/* Replies */}
            {comment.children && comment.children.length > 0 && (
                <>
                    <Button
                        size="small"
                        onClick={() => setShowReplies(!showReplies)}
                        startIcon={showReplies ? <ExpandLess /> : <ExpandMore />}
                        sx={{ ml: 5, mt: 0.5, textTransform: 'none', fontSize: '0.75rem' }}
                    >
                        {showReplies ? 'Hide' : 'Show'} {comment.children.length}{' '}
                        {comment.children.length === 1 ? 'reply' : 'replies'}
                    </Button>
                    <Collapse in={showReplies}>
                        {comment.children.map((child) => (
                            <SingleComment
                                key={child.id}
                                comment={child}
                                depth={depth + 1}
                                onReply={onReply}
                                onDelete={onDelete}
                                currentUsername={currentUsername}
                            />
                        ))}
                    </Collapse>
                </>
            )}
        </Box>
    );
}

function getTimeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    if (days < 30) return `${days}d ago`;
    return new Date(dateStr).toLocaleDateString();
}

function buildCommentTree(comments: Comment[]): Comment[] {
    const map = new Map<number, Comment>();
    const roots: Comment[] = [];

    comments.forEach((c) => {
        map.set(c.id, { ...c, children: [] });
    });

    comments.forEach((c) => {
        const node = map.get(c.id)!;
        if (c.parent_id && map.has(c.parent_id)) {
            map.get(c.parent_id)!.children!.push(node);
        } else {
            roots.push(node);
        }
    });

    return roots;
}

export default function CommentsPanel({ recordId, entityId }: CommentsPanelProps) {
    const { user } = useAuth();
    const queryClient = useQueryClient();
    const [newComment, setNewComment] = useState('');
    const [replyTo, setReplyTo] = useState<number | null>(null);

    const { data: comments = [], isLoading } = useQuery({
        queryKey: ['comments', recordId],
        queryFn: async () => {
            const res = await apiService.getComments(recordId, { limit: 100 });
            return res.data?.comments || res.data || [];
        },
        enabled: !!recordId,
    });

    const createMutation = useMutation({
        mutationFn: (data: { record_id: number; content: string; parent_id?: number }) =>
            apiService.createComment(data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['comments', recordId] });
            setNewComment('');
            setReplyTo(null);
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (commentId: number) => apiService.deleteComment(commentId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['comments', recordId] });
        },
    });

    const handleSubmit = useCallback(() => {
        if (!newComment.trim()) return;
        createMutation.mutate({
            record_id: recordId,
            content: newComment.trim(),
            ...(replyTo ? { parent_id: replyTo } : {}),
        });
    }, [newComment, recordId, replyTo, createMutation]);

    const commentTree = buildCommentTree(comments);

    return (
        <Paper sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
                <CommentIcon color="primary" />
                <Typography variant="h6">
                    Comments{comments.length > 0 ? ` (${comments.length})` : ''}
                </Typography>
            </Box>

            {/* New comment input */}
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <TextField
                    fullWidth
                    size="small"
                    placeholder={replyTo ? 'Write a reply...' : 'Add a comment...'}
                    value={newComment}
                    onChange={(e) => setNewComment(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit();
                        }
                    }}
                    multiline
                    maxRows={4}
                    disabled={createMutation.isPending}
                />
                <Button
                    variant="contained"
                    onClick={handleSubmit}
                    disabled={!newComment.trim() || createMutation.isPending}
                    sx={{ minWidth: 48, px: 1 }}
                >
                    {createMutation.isPending ? (
                        <CircularProgress size={20} />
                    ) : (
                        <Send />
                    )}
                </Button>
            </Box>

            {replyTo && (
                <Box sx={{ mb: 1 }}>
                    <Button
                        size="small"
                        onClick={() => setReplyTo(null)}
                        sx={{ textTransform: 'none' }}
                    >
                        Cancel reply
                    </Button>
                </Box>
            )}

            <Divider />

            {/* Comments list */}
            {isLoading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <CircularProgress size={24} />
                </Box>
            ) : commentTree.length === 0 ? (
                <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ py: 3, textAlign: 'center' }}
                >
                    No comments yet. Be the first to comment!
                </Typography>
            ) : (
                commentTree.map((comment) => (
                    <SingleComment
                        key={comment.id}
                        comment={comment}
                        onReply={(parentId) => setReplyTo(parentId)}
                        onDelete={(id) => deleteMutation.mutate(id)}
                        currentUsername={user?.username}
                    />
                ))
            )}
        </Paper>
    );
}
