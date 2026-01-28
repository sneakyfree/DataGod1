'use client';

import React, { useState } from 'react';
import {
    Box,
    Paper,
    Typography,
    Grid,
    Card,
    CardContent,
    Chip,
    IconButton,
    Tooltip,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TablePagination,
    Avatar,
    Button,
    TextField,
    InputAdornment,
    Select,
    MenuItem,
    FormControl,
    InputLabel,
    Dialog,
    DialogTitle,
    DialogContent,
    DialogActions,
    useTheme,
    alpha,
    Menu,
    ListItemIcon,
    ListItemText,
    Switch,
    FormControlLabel,
} from '@mui/material';
import {
    Person as UserIcon,
    AdminPanelSettings as AdminIcon,
    SupervisorAccount as ManagerIcon,
    Visibility as ViewIcon,
    Edit as EditIcon,
    Delete as DeleteIcon,
    MoreVert as MoreIcon,
    Search as SearchIcon,
    Add as AddIcon,
    Refresh as RefreshIcon,
    Block as BlockIcon,
    CheckCircle as ActiveIcon,
    Schedule as PendingIcon,
    Email as EmailIcon,
    Key as KeyIcon,
} from '@mui/icons-material';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';

// =============================================================================
// TYPES
// =============================================================================

export type UserRole = 'admin' | 'manager' | 'analyst' | 'viewer';
export type UserStatus = 'active' | 'inactive' | 'pending' | 'suspended';

export interface UserInfo {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    role: UserRole;
    status: UserStatus;
    avatar?: string;
    lastLogin?: string;
    createdAt: string;
    mfaEnabled: boolean;
    permissions: string[];
}

interface UserManagementDashboardProps {
    onUserSelect?: (user: UserInfo) => void;
}

// =============================================================================
// HELPERS
// =============================================================================

const roleConfig: Record<UserRole, { color: string; label: string; icon: React.ReactNode }> = {
    admin: { color: '#f44336', label: 'Admin', icon: <AdminIcon /> },
    manager: { color: '#9c27b0', label: 'Manager', icon: <ManagerIcon /> },
    analyst: { color: '#2196f3', label: 'Analyst', icon: <UserIcon /> },
    viewer: { color: '#4caf50', label: 'Viewer', icon: <ViewIcon /> },
};

const statusConfig: Record<UserStatus, { color: string; label: string }> = {
    active: { color: '#4caf50', label: 'Active' },
    inactive: { color: '#9e9e9e', label: 'Inactive' },
    pending: { color: '#ff9800', label: 'Pending' },
    suspended: { color: '#f44336', label: 'Suspended' },
};

// =============================================================================
// MOCK DATA
// =============================================================================

const mockUsers: UserInfo[] = [
    { id: '1', email: 'john.admin@company.com', firstName: 'John', lastName: 'Smith', role: 'admin', status: 'active', lastLogin: new Date(Date.now() - 3600000).toISOString(), createdAt: new Date(Date.now() - 86400000 * 365).toISOString(), mfaEnabled: true, permissions: ['all'] },
    { id: '2', email: 'sarah.manager@company.com', firstName: 'Sarah', lastName: 'Johnson', role: 'manager', status: 'active', lastLogin: new Date(Date.now() - 7200000).toISOString(), createdAt: new Date(Date.now() - 86400000 * 180).toISOString(), mfaEnabled: true, permissions: ['read', 'write', 'manage_users'] },
    { id: '3', email: 'mike.analyst@company.com', firstName: 'Mike', lastName: 'Williams', role: 'analyst', status: 'active', lastLogin: new Date(Date.now() - 86400000).toISOString(), createdAt: new Date(Date.now() - 86400000 * 90).toISOString(), mfaEnabled: false, permissions: ['read', 'write'] },
    { id: '4', email: 'emma.viewer@company.com', firstName: 'Emma', lastName: 'Brown', role: 'viewer', status: 'active', lastLogin: new Date(Date.now() - 172800000).toISOString(), createdAt: new Date(Date.now() - 86400000 * 30).toISOString(), mfaEnabled: false, permissions: ['read'] },
    { id: '5', email: 'david.new@company.com', firstName: 'David', lastName: 'Davis', role: 'analyst', status: 'pending', createdAt: new Date(Date.now() - 86400000).toISOString(), mfaEnabled: false, permissions: ['read'] },
    { id: '6', email: 'lisa.inactive@company.com', firstName: 'Lisa', lastName: 'Miller', role: 'viewer', status: 'inactive', lastLogin: new Date(Date.now() - 86400000 * 60).toISOString(), createdAt: new Date(Date.now() - 86400000 * 200).toISOString(), mfaEnabled: false, permissions: ['read'] },
    { id: '7', email: 'chris.suspended@company.com', firstName: 'Chris', lastName: 'Wilson', role: 'analyst', status: 'suspended', lastLogin: new Date(Date.now() - 86400000 * 14).toISOString(), createdAt: new Date(Date.now() - 86400000 * 120).toISOString(), mfaEnabled: true, permissions: [] },
];

// =============================================================================
// USER ROW ACTIONS MENU
// =============================================================================

interface UserActionsMenuProps {
    user: UserInfo;
    anchorEl: HTMLElement | null;
    onClose: () => void;
    onAction: (action: string, user: UserInfo) => void;
}

function UserActionsMenu({ user, anchorEl, onClose, onAction }: UserActionsMenuProps) {
    return (
        <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={onClose}>
            <MenuItem onClick={() => { onAction('view', user); onClose(); }}>
                <ListItemIcon><ViewIcon fontSize="small" /></ListItemIcon>
                <ListItemText>View Details</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => { onAction('edit', user); onClose(); }}>
                <ListItemIcon><EditIcon fontSize="small" /></ListItemIcon>
                <ListItemText>Edit User</ListItemText>
            </MenuItem>
            <MenuItem onClick={() => { onAction('reset-password', user); onClose(); }}>
                <ListItemIcon><KeyIcon fontSize="small" /></ListItemIcon>
                <ListItemText>Reset Password</ListItemText>
            </MenuItem>
            {user.status === 'active' ? (
                <MenuItem onClick={() => { onAction('suspend', user); onClose(); }}>
                    <ListItemIcon><BlockIcon fontSize="small" color="error" /></ListItemIcon>
                    <ListItemText>Suspend User</ListItemText>
                </MenuItem>
            ) : user.status === 'suspended' ? (
                <MenuItem onClick={() => { onAction('activate', user); onClose(); }}>
                    <ListItemIcon><ActiveIcon fontSize="small" color="success" /></ListItemIcon>
                    <ListItemText>Activate User</ListItemText>
                </MenuItem>
            ) : null}
            <MenuItem onClick={() => { onAction('delete', user); onClose(); }} sx={{ color: 'error.main' }}>
                <ListItemIcon><DeleteIcon fontSize="small" color="error" /></ListItemIcon>
                <ListItemText>Delete User</ListItemText>
            </MenuItem>
        </Menu>
    );
}

// =============================================================================
// USER DETAIL DIALOG
// =============================================================================

interface UserDetailDialogProps {
    user: UserInfo | null;
    open: boolean;
    onClose: () => void;
}

function UserDetailDialog({ user, open, onClose }: UserDetailDialogProps) {
    const theme = useTheme();
    if (!user) return null;

    const role = roleConfig[user.role];
    const status = statusConfig[user.status];

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>User Details</DialogTitle>
            <DialogContent>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3, pt: 1 }}>
                    <Avatar
                        sx={{
                            width: 64,
                            height: 64,
                            bgcolor: alpha(role.color, 0.1),
                            color: role.color,
                            fontSize: 24,
                        }}
                    >
                        {user.firstName[0]}{user.lastName[0]}
                    </Avatar>
                    <Box>
                        <Typography variant="h6" fontWeight={600}>
                            {user.firstName} {user.lastName}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                            {user.email}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, mt: 0.5 }}>
                            <Chip size="small" label={role.label} sx={{ bgcolor: alpha(role.color, 0.1), color: role.color }} />
                            <Chip size="small" label={status.label} sx={{ bgcolor: alpha(status.color, 0.1), color: status.color }} />
                        </Box>
                    </Box>
                </Box>

                <Grid container spacing={2}>
                    <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Created</Typography>
                        <Typography variant="body2">{new Date(user.createdAt).toLocaleDateString()}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Last Login</Typography>
                        <Typography variant="body2">{user.lastLogin ? new Date(user.lastLogin).toLocaleString() : 'Never'}</Typography>
                    </Grid>
                    <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">MFA Status</Typography>
                        <Typography variant="body2">
                            <Chip size="small" label={user.mfaEnabled ? 'Enabled' : 'Disabled'} color={user.mfaEnabled ? 'success' : 'default'} />
                        </Typography>
                    </Grid>
                    <Grid item xs={6}>
                        <Typography variant="caption" color="text.secondary">Permissions</Typography>
                        <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                            {user.permissions.map((p) => (
                                <Chip key={p} size="small" label={p} variant="outlined" />
                            ))}
                        </Box>
                    </Grid>
                </Grid>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Close</Button>
                <Button variant="contained" startIcon={<EditIcon />}>Edit User</Button>
            </DialogActions>
        </Dialog>
    );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function UserManagementDashboard({
    onUserSelect,
}: UserManagementDashboardProps) {
    const theme = useTheme();
    const [search, setSearch] = useState('');
    const [roleFilter, setRoleFilter] = useState<string>('all');
    const [statusFilter, setStatusFilter] = useState<string>('all');
    const [page, setPage] = useState(0);
    const [rowsPerPage, setRowsPerPage] = useState(10);
    const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);
    const [selectedUser, setSelectedUser] = useState<UserInfo | null>(null);
    const [detailOpen, setDetailOpen] = useState(false);

    // Fetch users
    const { data: users = mockUsers, refetch, isLoading } = useQuery<UserInfo[]>({
        queryKey: ['users'],
        queryFn: async () => {
            try {
                const response = await apiService.get('/users');
                return response.data;
            } catch {
                return mockUsers;
            }
        },
    });

    // Filter users
    const filteredUsers = users.filter((u) => {
        if (roleFilter !== 'all' && u.role !== roleFilter) return false;
        if (statusFilter !== 'all' && u.status !== statusFilter) return false;
        if (search) {
            const searchLower = search.toLowerCase();
            return (
                u.email.toLowerCase().includes(searchLower) ||
                u.firstName.toLowerCase().includes(searchLower) ||
                u.lastName.toLowerCase().includes(searchLower)
            );
        }
        return true;
    });

    const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, user: UserInfo) => {
        setMenuAnchor(event.currentTarget);
        setSelectedUser(user);
    };

    const handleAction = (action: string, user: UserInfo) => {
        if (action === 'view') {
            setDetailOpen(true);
        }
        // Handle other actions...
    };

    // Calculate stats
    const activeCount = users.filter((u) => u.status === 'active').length;
    const pendingCount = users.filter((u) => u.status === 'pending').length;
    const mfaCount = users.filter((u) => u.mfaEnabled).length;

    return (
        <Paper
            elevation={0}
            sx={{
                p: 3,
                backgroundColor: theme.palette.mode === 'dark'
                    ? alpha(theme.palette.background.paper, 0.8)
                    : theme.palette.background.paper,
                borderRadius: 2,
            }}
        >
            {/* Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
                <Box>
                    <Typography variant="h5" fontWeight={700}>
                        User Management
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                        Manage users, roles, and permissions
                    </Typography>
                </Box>
                <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button variant="contained" startIcon={<AddIcon />}>
                        Add User
                    </Button>
                    <Tooltip title="Refresh">
                        <IconButton onClick={() => refetch()} disabled={isLoading}>
                            <RefreshIcon />
                        </IconButton>
                    </Tooltip>
                </Box>
            </Box>

            {/* Quick stats */}
            <Grid container spacing={2} sx={{ mb: 3 }}>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha(theme.palette.primary.main, 0.05) }}>
                        <Typography variant="h4" fontWeight={700} color="primary">
                            {users.length}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Total Users
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#4caf50', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#4caf50' }}>
                            {activeCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Active
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#ff9800', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#ff9800' }}>
                            {pendingCount}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            Pending
                        </Typography>
                    </Box>
                </Grid>
                <Grid item xs={6} sm={3}>
                    <Box sx={{ textAlign: 'center', p: 2, borderRadius: 2, backgroundColor: alpha('#2196f3', 0.05) }}>
                        <Typography variant="h4" fontWeight={700} sx={{ color: '#2196f3' }}>
                            {Math.round((mfaCount / users.length) * 100)}%
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                            MFA Enabled
                        </Typography>
                    </Box>
                </Grid>
            </Grid>

            {/* Filters */}
            <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
                <TextField
                    size="small"
                    placeholder="Search users..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    InputProps={{
                        startAdornment: (
                            <InputAdornment position="start">
                                <SearchIcon />
                            </InputAdornment>
                        ),
                    }}
                    sx={{ minWidth: 250 }}
                />
                <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>Role</InputLabel>
                    <Select value={roleFilter} label="Role" onChange={(e) => setRoleFilter(e.target.value)}>
                        <MenuItem value="all">All Roles</MenuItem>
                        <MenuItem value="admin">Admin</MenuItem>
                        <MenuItem value="manager">Manager</MenuItem>
                        <MenuItem value="analyst">Analyst</MenuItem>
                        <MenuItem value="viewer">Viewer</MenuItem>
                    </Select>
                </FormControl>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>Status</InputLabel>
                    <Select value={statusFilter} label="Status" onChange={(e) => setStatusFilter(e.target.value)}>
                        <MenuItem value="all">All Status</MenuItem>
                        <MenuItem value="active">Active</MenuItem>
                        <MenuItem value="inactive">Inactive</MenuItem>
                        <MenuItem value="pending">Pending</MenuItem>
                        <MenuItem value="suspended">Suspended</MenuItem>
                    </Select>
                </FormControl>
            </Box>

            {/* Users table */}
            <TableContainer>
                <Table>
                    <TableHead>
                        <TableRow>
                            <TableCell>User</TableCell>
                            <TableCell>Role</TableCell>
                            <TableCell>Status</TableCell>
                            <TableCell>Last Login</TableCell>
                            <TableCell>MFA</TableCell>
                            <TableCell align="right">Actions</TableCell>
                        </TableRow>
                    </TableHead>
                    <TableBody>
                        {filteredUsers.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage).map((user) => {
                            const role = roleConfig[user.role];
                            const status = statusConfig[user.status];
                            return (
                                <TableRow key={user.id} hover>
                                    <TableCell>
                                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                            <Avatar sx={{ width: 36, height: 36, bgcolor: alpha(role.color, 0.1), color: role.color, fontSize: 14 }}>
                                                {user.firstName[0]}{user.lastName[0]}
                                            </Avatar>
                                            <Box>
                                                <Typography variant="body2" fontWeight={500}>
                                                    {user.firstName} {user.lastName}
                                                </Typography>
                                                <Typography variant="caption" color="text.secondary">
                                                    {user.email}
                                                </Typography>
                                            </Box>
                                        </Box>
                                    </TableCell>
                                    <TableCell>
                                        <Chip size="small" icon={role.icon as React.ReactElement} label={role.label} sx={{ bgcolor: alpha(role.color, 0.1), color: role.color }} />
                                    </TableCell>
                                    <TableCell>
                                        <Chip size="small" label={status.label} sx={{ bgcolor: alpha(status.color, 0.1), color: status.color }} />
                                    </TableCell>
                                    <TableCell>
                                        <Typography variant="body2">
                                            {user.lastLogin ? new Date(user.lastLogin).toLocaleDateString() : 'Never'}
                                        </Typography>
                                    </TableCell>
                                    <TableCell>
                                        <Chip size="small" label={user.mfaEnabled ? 'On' : 'Off'} color={user.mfaEnabled ? 'success' : 'default'} />
                                    </TableCell>
                                    <TableCell align="right">
                                        <IconButton size="small" onClick={(e) => handleMenuOpen(e, user)}>
                                            <MoreIcon />
                                        </IconButton>
                                    </TableCell>
                                </TableRow>
                            );
                        })}
                    </TableBody>
                </Table>
            </TableContainer>
            <TablePagination
                component="div"
                count={filteredUsers.length}
                page={page}
                onPageChange={(_, p) => setPage(p)}
                rowsPerPage={rowsPerPage}
                onRowsPerPageChange={(e) => { setRowsPerPage(parseInt(e.target.value, 10)); setPage(0); }}
            />

            {/* Actions menu */}
            <UserActionsMenu
                user={selectedUser!}
                anchorEl={menuAnchor}
                onClose={() => setMenuAnchor(null)}
                onAction={handleAction}
            />

            {/* Detail dialog */}
            <UserDetailDialog
                user={selectedUser}
                open={detailOpen}
                onClose={() => setDetailOpen(false)}
            />
        </Paper>
    );
}
