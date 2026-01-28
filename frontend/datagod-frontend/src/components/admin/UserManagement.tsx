/**
 * UserManagement Component
 * 
 * Full-featured admin user management with search, filters,
 * CRUD operations, role assignment, and bulk actions.
 */

'use client';

import React, { useState, useMemo, useCallback, useEffect } from 'react';

// Types
interface User {
    id: string;
    email: string;
    name: string;
    role: 'admin' | 'user' | 'viewer' | 'api_user';
    status: 'active' | 'inactive' | 'pending' | 'suspended';
    tier: 'free' | 'basic' | 'pro' | 'enterprise';
    createdAt: string;
    lastLogin?: string;
    stripeCustomerId?: string;
    metadata?: Record<string, any>;
}

interface UserFilters {
    search: string;
    role: string;
    status: string;
    tier: string;
}

interface SortConfig {
    key: keyof User;
    direction: 'asc' | 'desc';
}

interface UserManagementProps {
    initialUsers?: User[];
    onUserUpdate?: (user: User) => Promise<void>;
    onUserDelete?: (userId: string) => Promise<void>;
    onUserCreate?: (user: Partial<User>) => Promise<User>;
    onBulkAction?: (action: string, userIds: string[]) => Promise<void>;
}

const ROLES = [
    { value: 'admin', label: 'Admin', color: 'bg-red-100 text-red-800' },
    { value: 'user', label: 'User', color: 'bg-blue-100 text-blue-800' },
    { value: 'viewer', label: 'Viewer', color: 'bg-gray-100 text-gray-800' },
    { value: 'api_user', label: 'API User', color: 'bg-purple-100 text-purple-800' },
];

const STATUSES = [
    { value: 'active', label: 'Active', color: 'bg-green-100 text-green-800' },
    { value: 'inactive', label: 'Inactive', color: 'bg-gray-100 text-gray-800' },
    { value: 'pending', label: 'Pending', color: 'bg-yellow-100 text-yellow-800' },
    { value: 'suspended', label: 'Suspended', color: 'bg-red-100 text-red-800' },
];

const TIERS = [
    { value: 'free', label: 'Free', color: 'bg-gray-100 text-gray-600' },
    { value: 'basic', label: 'Basic', color: 'bg-blue-100 text-blue-700' },
    { value: 'pro', label: 'Pro', color: 'bg-purple-100 text-purple-700' },
    { value: 'enterprise', label: 'Enterprise', color: 'bg-amber-100 text-amber-700' },
];

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api';

// Badge component
const Badge = ({ label, colorClass }: { label: string; colorClass: string }) => (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colorClass}`}>
        {label}
    </span>
);

// Modal component
const Modal = ({
    isOpen,
    onClose,
    title,
    children
}: {
    isOpen: boolean;
    onClose: () => void;
    title: string;
    children: React.ReactNode;
}) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="fixed inset-0 bg-black/50" onClick={onClose} />
            <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex items-center justify-between p-4 border-b dark:border-gray-700">
                    <h3 className="text-lg font-semibold">{title}</h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                <div className="p-4">{children}</div>
            </div>
        </div>
    );
};

export function UserManagement({
    initialUsers = [],
    onUserUpdate,
    onUserDelete,
    onUserCreate,
    onBulkAction,
}: UserManagementProps) {
    // State
    const [users, setUsers] = useState<User[]>(initialUsers);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedUsers, setSelectedUsers] = useState<Set<string>>(new Set());
    const [editingUser, setEditingUser] = useState<User | null>(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [userToDelete, setUserToDelete] = useState<User | null>(null);

    // Filters and sorting
    const [filters, setFilters] = useState<UserFilters>({
        search: '',
        role: '',
        status: '',
        tier: '',
    });
    const [sort, setSort] = useState<SortConfig>({ key: 'createdAt', direction: 'desc' });
    const [page, setPage] = useState(1);
    const pageSize = 10;

    // Fetch users
    const fetchUsers = useCallback(async () => {
        setLoading(true);
        setError(null);

        try {
            const response = await fetch(`${API_BASE_URL}/admin/users`, {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                },
            });

            if (!response.ok) throw new Error('Failed to fetch users');

            const data = await response.json();
            setUsers(data.users || data);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load users');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (!initialUsers.length) {
            fetchUsers();
        }
    }, [initialUsers.length, fetchUsers]);

    // Filter and sort users
    const filteredUsers = useMemo(() => {
        let result = [...users];

        // Apply filters
        if (filters.search) {
            const searchLower = filters.search.toLowerCase();
            result = result.filter(u =>
                u.name.toLowerCase().includes(searchLower) ||
                u.email.toLowerCase().includes(searchLower)
            );
        }

        if (filters.role) {
            result = result.filter(u => u.role === filters.role);
        }

        if (filters.status) {
            result = result.filter(u => u.status === filters.status);
        }

        if (filters.tier) {
            result = result.filter(u => u.tier === filters.tier);
        }

        // Apply sort
        result.sort((a, b) => {
            const aVal = a[sort.key] || '';
            const bVal = b[sort.key] || '';

            if (aVal < bVal) return sort.direction === 'asc' ? -1 : 1;
            if (aVal > bVal) return sort.direction === 'asc' ? 1 : -1;
            return 0;
        });

        return result;
    }, [users, filters, sort]);

    // Paginated users
    const paginatedUsers = useMemo(() => {
        const start = (page - 1) * pageSize;
        return filteredUsers.slice(start, start + pageSize);
    }, [filteredUsers, page]);

    const totalPages = Math.ceil(filteredUsers.length / pageSize);

    // Handlers
    const handleSort = (key: keyof User) => {
        setSort(prev => ({
            key,
            direction: prev.key === key && prev.direction === 'asc' ? 'desc' : 'asc',
        }));
    };

    const handleSelectAll = () => {
        if (selectedUsers.size === paginatedUsers.length) {
            setSelectedUsers(new Set());
        } else {
            setSelectedUsers(new Set(paginatedUsers.map(u => u.id)));
        }
    };

    const handleSelectUser = (userId: string) => {
        setSelectedUsers(prev => {
            const next = new Set(prev);
            if (next.has(userId)) {
                next.delete(userId);
            } else {
                next.add(userId);
            }
            return next;
        });
    };

    const handleBulkAction = async (action: string) => {
        if (selectedUsers.size === 0) return;

        if (onBulkAction) {
            await onBulkAction(action, Array.from(selectedUsers));
        }

        setSelectedUsers(new Set());
        fetchUsers();
    };

    const handleSaveUser = async (user: Partial<User>) => {
        setLoading(true);

        try {
            if (editingUser) {
                // Update existing user
                const response = await fetch(`${API_BASE_URL}/admin/users/${editingUser.id}`, {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(user),
                });

                if (!response.ok) throw new Error('Failed to update user');

                if (onUserUpdate) {
                    await onUserUpdate({ ...editingUser, ...user } as User);
                }
            } else {
                // Create new user
                const response = await fetch(`${API_BASE_URL}/admin/users`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(user),
                });

                if (!response.ok) throw new Error('Failed to create user');

                if (onUserCreate) {
                    await onUserCreate(user);
                }
            }

            fetchUsers();
            setEditingUser(null);
            setIsCreateModalOpen(false);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Operation failed');
        } finally {
            setLoading(false);
        }
    };

    const handleDeleteUser = async () => {
        if (!userToDelete) return;

        setLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/admin/users/${userToDelete.id}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
                },
            });

            if (!response.ok) throw new Error('Failed to delete user');

            if (onUserDelete) {
                await onUserDelete(userToDelete.id);
            }

            fetchUsers();
            setIsDeleteModalOpen(false);
            setUserToDelete(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Delete failed');
        } finally {
            setLoading(false);
        }
    };

    // User form component
    const UserForm = ({ user, onSave, onCancel }: {
        user?: User | null;
        onSave: (data: Partial<User>) => void;
        onCancel: () => void;
    }) => {
        const [formData, setFormData] = useState({
            email: user?.email || '',
            name: user?.name || '',
            role: user?.role || 'user',
            status: user?.status || 'pending',
            tier: user?.tier || 'free',
        });

        return (
            <form onSubmit={(e) => { e.preventDefault(); onSave(formData); }} className="space-y-4">
                <div>
                    <label className="block text-sm font-medium mb-1">Email</label>
                    <input
                        type="email"
                        value={formData.email}
                        onChange={(e) => setFormData(prev => ({ ...prev, email: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                        required
                    />
                </div>

                <div>
                    <label className="block text-sm font-medium mb-1">Name</label>
                    <input
                        type="text"
                        value={formData.name}
                        onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                        className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                        required
                    />
                </div>

                <div className="grid grid-cols-3 gap-4">
                    <div>
                        <label className="block text-sm font-medium mb-1">Role</label>
                        <select
                            value={formData.role}
                            onChange={(e) => setFormData(prev => ({ ...prev, role: e.target.value as any }))}
                            className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                        >
                            {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Status</label>
                        <select
                            value={formData.status}
                            onChange={(e) => setFormData(prev => ({ ...prev, status: e.target.value as any }))}
                            className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                        >
                            {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-1">Tier</label>
                        <select
                            value={formData.tier}
                            onChange={(e) => setFormData(prev => ({ ...prev, tier: e.target.value as any }))}
                            className="w-full px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                        >
                            {TIERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                        </select>
                    </div>
                </div>

                <div className="flex justify-end gap-2 pt-4">
                    <button type="button" onClick={onCancel} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md">
                        Cancel
                    </button>
                    <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
                        {user ? 'Save Changes' : 'Create User'}
                    </button>
                </div>
            </form>
        );
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
            {/* Header */}
            <div className="p-4 border-b dark:border-gray-700">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-semibold">User Management</h2>
                    <button
                        onClick={() => setIsCreateModalOpen(true)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        Add User
                    </button>
                </div>

                {/* Filters */}
                <div className="flex flex-wrap gap-3">
                    <input
                        type="text"
                        placeholder="Search users..."
                        value={filters.search}
                        onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
                        className="px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600 flex-1 min-w-48"
                    />

                    <select
                        value={filters.role}
                        onChange={(e) => setFilters(prev => ({ ...prev, role: e.target.value }))}
                        className="px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                    >
                        <option value="">All Roles</option>
                        {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>

                    <select
                        value={filters.status}
                        onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                        className="px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                    >
                        <option value="">All Status</option>
                        {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                    </select>

                    <select
                        value={filters.tier}
                        onChange={(e) => setFilters(prev => ({ ...prev, tier: e.target.value }))}
                        className="px-3 py-2 border rounded-md dark:bg-gray-700 dark:border-gray-600"
                    >
                        <option value="">All Tiers</option>
                        {TIERS.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                </div>

                {/* Bulk actions */}
                {selectedUsers.size > 0 && (
                    <div className="mt-3 flex items-center gap-3 p-2 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                        <span className="text-sm">{selectedUsers.size} selected</span>
                        <button
                            onClick={() => handleBulkAction('activate')}
                            className="text-sm text-green-600 hover:underline"
                        >
                            Activate
                        </button>
                        <button
                            onClick={() => handleBulkAction('deactivate')}
                            className="text-sm text-yellow-600 hover:underline"
                        >
                            Deactivate
                        </button>
                        <button
                            onClick={() => handleBulkAction('delete')}
                            className="text-sm text-red-600 hover:underline"
                        >
                            Delete
                        </button>
                    </div>
                )}
            </div>

            {/* Error display */}
            {error && (
                <div className="m-4 p-3 bg-red-50 text-red-700 rounded-md">
                    {error}
                </div>
            )}

            {/* Table */}
            <div className="overflow-x-auto">
                <table className="w-full">
                    <thead className="bg-gray-50 dark:bg-gray-900">
                        <tr>
                            <th className="px-4 py-3 text-left">
                                <input
                                    type="checkbox"
                                    checked={selectedUsers.size === paginatedUsers.length && paginatedUsers.length > 0}
                                    onChange={handleSelectAll}
                                    className="rounded"
                                />
                            </th>
                            <th
                                className="px-4 py-3 text-left text-sm font-medium cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('name')}
                            >
                                User {sort.key === 'name' && (sort.direction === 'asc' ? '↑' : '↓')}
                            </th>
                            <th
                                className="px-4 py-3 text-left text-sm font-medium cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('role')}
                            >
                                Role {sort.key === 'role' && (sort.direction === 'asc' ? '↑' : '↓')}
                            </th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Tier</th>
                            <th
                                className="px-4 py-3 text-left text-sm font-medium cursor-pointer hover:bg-gray-100"
                                onClick={() => handleSort('createdAt')}
                            >
                                Created {sort.key === 'createdAt' && (sort.direction === 'asc' ? '↑' : '↓')}
                            </th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y dark:divide-gray-700">
                        {loading && !users.length ? (
                            <tr>
                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">Loading...</td>
                            </tr>
                        ) : paginatedUsers.length === 0 ? (
                            <tr>
                                <td colSpan={7} className="px-4 py-8 text-center text-gray-500">No users found</td>
                            </tr>
                        ) : (
                            paginatedUsers.map(user => {
                                const roleConfig = ROLES.find(r => r.value === user.role);
                                const statusConfig = STATUSES.find(s => s.value === user.status);
                                const tierConfig = TIERS.find(t => t.value === user.tier);

                                return (
                                    <tr key={user.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                                        <td className="px-4 py-3">
                                            <input
                                                type="checkbox"
                                                checked={selectedUsers.has(user.id)}
                                                onChange={() => handleSelectUser(user.id)}
                                                className="rounded"
                                            />
                                        </td>
                                        <td className="px-4 py-3">
                                            <div>
                                                <div className="font-medium">{user.name}</div>
                                                <div className="text-sm text-gray-500">{user.email}</div>
                                            </div>
                                        </td>
                                        <td className="px-4 py-3">
                                            <Badge label={roleConfig?.label || user.role} colorClass={roleConfig?.color || ''} />
                                        </td>
                                        <td className="px-4 py-3">
                                            <Badge label={statusConfig?.label || user.status} colorClass={statusConfig?.color || ''} />
                                        </td>
                                        <td className="px-4 py-3">
                                            <Badge label={tierConfig?.label || user.tier} colorClass={tierConfig?.color || ''} />
                                        </td>
                                        <td className="px-4 py-3 text-sm text-gray-500">
                                            {new Date(user.createdAt).toLocaleDateString()}
                                        </td>
                                        <td className="px-4 py-3">
                                            <div className="flex gap-2">
                                                <button
                                                    onClick={() => setEditingUser(user)}
                                                    className="text-blue-600 hover:underline text-sm"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => { setUserToDelete(user); setIsDeleteModalOpen(true); }}
                                                    className="text-red-600 hover:underline text-sm"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            <div className="p-4 border-t dark:border-gray-700 flex items-center justify-between">
                <span className="text-sm text-gray-500">
                    Showing {((page - 1) * pageSize) + 1}-{Math.min(page * pageSize, filteredUsers.length)} of {filteredUsers.length}
                </span>
                <div className="flex gap-2">
                    <button
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                        Previous
                    </button>
                    <button
                        onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-3 py-1 border rounded disabled:opacity-50"
                    >
                        Next
                    </button>
                </div>
            </div>

            {/* Create/Edit Modal */}
            <Modal
                isOpen={isCreateModalOpen || !!editingUser}
                onClose={() => { setIsCreateModalOpen(false); setEditingUser(null); }}
                title={editingUser ? 'Edit User' : 'Create User'}
            >
                <UserForm
                    user={editingUser}
                    onSave={handleSaveUser}
                    onCancel={() => { setIsCreateModalOpen(false); setEditingUser(null); }}
                />
            </Modal>

            {/* Delete Confirmation Modal */}
            <Modal
                isOpen={isDeleteModalOpen}
                onClose={() => { setIsDeleteModalOpen(false); setUserToDelete(null); }}
                title="Delete User"
            >
                <p className="mb-4">Are you sure you want to delete <strong>{userToDelete?.name}</strong>? This action cannot be undone.</p>
                <div className="flex justify-end gap-2">
                    <button
                        onClick={() => { setIsDeleteModalOpen(false); setUserToDelete(null); }}
                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-md"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleDeleteUser}
                        className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"
                    >
                        Delete
                    </button>
                </div>
            </Modal>
        </div>
    );
}

export default UserManagement;
