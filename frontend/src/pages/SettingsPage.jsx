
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button, Input, Select, Modal } from '../components/ui/Components';
import { User, Shield, Key, Plus, Trash2, KeyRound, RefreshCw, CloudUpload } from 'lucide-react';
import { API_URL } from '../lib/api';


export function SettingsPage({ currentUser }) {
    return (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <header className="mb-8">
                <h1 className="text-3xl font-bold tracking-tight">Paramètres</h1>
                <p className="text-muted-foreground">Gestion de votre profil et des utilisateurs.</p>
            </header>

            <ChangePasswordSection />

            {currentUser.role === 'admin' && (
                <>
                    <DataSynchronizationSection />
                    <UserManagementSection />
                </>
            )}
        </div>
    );
}

function ChangePasswordSection() {
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage(null);
        setError(null);

        if (password !== confirm) {
            setError("Les mots de passe ne correspondent pas");
            return;
        }

        setLoading(true);
        try {
            await axios.put(
                `${API_URL}/users/me/password`,
                { password },
                { withCredentials: true }
            );
            setMessage("Mot de passe modifié avec succès");
            setPassword('');
            setConfirm('');
        } catch (err) {
            setError("Erreur lors de la modification");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm max-w-2xl">
            <div className="flex items-center gap-2 mb-6">
                <div className="p-2 bg-primary/10 rounded-full">
                    <Key className="w-5 h-5 text-primary" />
                </div>
                <h2 className="text-lg font-semibold">Sécurité du compte</h2>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                    <Input
                        label="Nouveau mot de passe"
                        type="password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        required
                    />
                    <Input
                        label="Confirmer le mot de passe"
                        type="password"
                        value={confirm}
                        onChange={e => setConfirm(e.target.value)}
                        required
                    />
                </div>

                {message && <p className="text-sm text-green-600 bg-green-50 p-2 rounded">{message}</p>}
                {error && <p className="text-sm text-red-600 bg-red-50 p-2 rounded">{error}</p>}

                <div className="flex justify-end">
                    <Button type="submit" isLoading={loading}>
                        Mettre à jour
                    </Button>
                </div>
            </form>
        </div>
    );
}

function DataSynchronizationSection() {
    const [loading, setLoading] = useState(false);
    const [pushLoading, setPushLoading] = useState(false);
    const [message, setMessage] = useState(null);
    const [error, setError] = useState(null);

    const handleSync = async () => {
        setLoading(true);
        setMessage(null);
        setError(null);
        try {
            const res = await axios.post(`${API_URL}/sync-budget`, {}, { withCredentials: true });
            setMessage(res.data.message);
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur lors de la synchronisation");
        } finally {
            setLoading(false);
        }
    };

    const handlePush = async () => {
        setPushLoading(true);
        setMessage(null);
        setError(null);
        try {
            const res = await axios.post(`${API_URL}/push-budget`, {}, { withCredentials: true });
            setMessage(res.data.message);
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur lors de la sauvegarde sur le cloud");
        } finally {
            setPushLoading(false);
        }
    };

    return (
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm max-w-2xl">
            <div className="flex items-center gap-2 mb-6">
                <div className="p-2 bg-blue-100 rounded-full">
                    <RefreshCw className={`w-5 h-5 text-blue-600 ${loading ? 'animate-spin' : ''}`} />
                </div>
                <h2 className="text-lg font-semibold">Synchronisation des données</h2>
            </div>

            <p className="text-sm text-muted-foreground mb-6">
                Mettre à jour la base de données avec les dernières données du fichier <strong>Budget 2026.xlsx</strong>.
                Toutes les dépenses existantes seront remplacées par celles contenues dans l'Excel.
            </p>

            {message && <p className="text-sm text-green-600 bg-green-50 p-3 rounded-lg border border-green-100 mb-4">{message}</p>}
            {error && <p className="text-sm text-red-600 bg-red-50 p-3 rounded-lg border border-red-100 mb-4">{error}</p>}

            <div className="flex justify-end gap-3">
                <Button
                    onClick={handleSync}
                    isLoading={loading}
                    variant="outline"
                    className="gap-2 border-primary/20 hover:bg-primary/5"
                >
                    <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                    Importer du Cloud
                </Button>
                <Button
                    onClick={handlePush}
                    isLoading={pushLoading}
                    className="gap-2"
                >
                    <CloudUpload className="w-4 h-4" />
                    Sauvegarder vers Cloud
                </Button>
            </div>
        </div>
    );
}

function UserManagementSection() {
    const [users, setUsers] = useState([]);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    // Reset Password State
    const [isResetModalOpen, setIsResetModalOpen] = useState(false);
    const [selectedUserForReset, setSelectedUserForReset] = useState(null);

    const fetchUsers = async () => {
        try {
            const res = await axios.get(`${API_URL}/users`, { withCredentials: true });
            setUsers(res.data);
        } catch (err) {
            console.error(err);
        }
    };

    useEffect(() => {
        fetchUsers();
    }, []);

    const handleRoleChange = async (username, newRole) => {
        try {
            await axios.put(
                `${API_URL}/users/${username}/role`,
                { role: newRole },
                { withCredentials: true }
            );
            fetchUsers();
        } catch (err) {
            alert(err.response?.data?.detail || "Erreur lors du changement de rôle");
        }
    };

    const handleDeleteUser = async (username) => {
        if (!window.confirm(`Êtes-vous sûr de vouloir supprimer l'utilisateur ${username} ?`)) return;

        try {
            await axios.delete(
                `${API_URL}/users/${username}`,
                { withCredentials: true }
            );
            fetchUsers();
        } catch (err) {
            alert(err.response?.data?.detail || "Erreur lors de la suppression");
        }
    };

    const openResetModal = (user) => {
        setSelectedUserForReset(user);
        setIsResetModalOpen(true);
    };

    return (
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
            <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-2">
                    <div className="p-2 bg-secondary rounded-full">
                        <Shield className="w-5 h-5 text-secondary-foreground" />
                    </div>
                    <h2 className="text-lg font-semibold">Gestion des Utilisateurs</h2>
                </div>
                <Button onClick={() => setIsCreateModalOpen(true)} size="sm" className="gap-2">
                    <Plus className="w-4 h-4" /> Ajouter un utilisateur
                </Button>
            </div>

            <div className="overflow-x-auto">
                <table className="w-full text-sm">
                    <thead>
                        <tr className="border-b border-border">
                            <th className="text-left py-3 px-4 font-medium text-muted-foreground">Utilisateur</th>
                            <th className="text-left py-3 px-4 font-medium text-muted-foreground">Nom Complet</th>
                            <th className="text-left py-3 px-4 font-medium text-muted-foreground">Rôle</th>
                            <th className="text-left py-3 px-4 font-medium text-muted-foreground">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {users.map(u => (
                            <tr key={u.username} className="border-b border-border last:border-0 hover:bg-muted/50">
                                <td className="py-3 px-4 font-medium">{u.username}</td>
                                <td className="py-3 px-4">{u.full_name}</td>
                                <td className="py-3 px-4">
                                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${u.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'
                                        }`}>
                                        {u.role === 'admin' ? 'Administrateur' : 'Utilisateur'}
                                    </span>
                                </td>
                                <td className="py-3 px-4">
                                    {u.username !== 'gconstant' && (
                                        <div className="flex items-center gap-2">
                                            <select
                                                className="text-xs border rounded p-1 bg-background mr-2"
                                                value={u.role}
                                                onChange={(e) => handleRoleChange(u.username, e.target.value)}
                                            >
                                                <option value="user">Utilisateur</option>
                                                <option value="admin">Administrateur</option>
                                            </select>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="h-8 w-8 p-0 border-orange-200 text-orange-600 hover:bg-orange-50 mr-1"
                                                title="Réinitialiser le mot de passe"
                                                onClick={() => openResetModal(u)}
                                            >
                                                <KeyRound className="w-4 h-4" />
                                            </Button>

                                            <Button
                                                variant="outline"
                                                size="sm"
                                                className="h-8 w-8 p-0 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700"
                                                title="Supprimer l'utilisateur"
                                                onClick={() => handleDeleteUser(u.username)}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </div>
                                    )}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            <Modal
                isOpen={isCreateModalOpen}
                onClose={() => setIsCreateModalOpen(false)}
                title="Créer un nouvel utilisateur"
            >
                <CreateUserForm onClose={() => { setIsCreateModalOpen(false); fetchUsers(); }} />
            </Modal>

            <Modal
                isOpen={isResetModalOpen}
                onClose={() => setIsResetModalOpen(false)}
                title={`Réinitialiser le mot de passe de ${selectedUserForReset?.username}`}
            >
                <ResetPasswordForm
                    username={selectedUserForReset?.username}
                    onClose={() => setIsResetModalOpen(false)}
                />
            </Modal>
        </div>
    );
}

function CreateUserForm({ onClose }) {
    const [formData, setFormData] = useState({
        username: '',
        full_name: '',
        password: '',
        role: 'user'
    });
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await axios.post(`${API_URL}/users`, formData, { withCredentials: true });
            onClose();
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur lors de la création");
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <Input
                label="Identifiant"
                value={formData.username}
                onChange={e => setFormData({ ...formData, username: e.target.value })}
                placeholder="Ex: mgarabedian"
                required
            />
            <Input
                label="Nom Complet"
                value={formData.full_name}
                onChange={e => setFormData({ ...formData, full_name: e.target.value })}
                placeholder="Ex: Michel Garabedian"
                required
            />
            <Input
                label="Mot de passe initial"
                type="password"
                value={formData.password}
                onChange={e => setFormData({ ...formData, password: e.target.value })}
                required
            />
            <Select
                label="Rôle"
                value={formData.role}
                onChange={e => setFormData({ ...formData, role: e.target.value })}
                options={[
                    { value: 'user', label: 'Utilisateur Standard' },
                    { value: 'admin', label: 'Administrateur' }
                ]}
            />

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onClose}>Annuler</Button>
                <Button type="submit" isLoading={loading}>Créer l'utilisateur</Button>
            </div>
        </form>
    );
}

function ResetPasswordForm({ username, onClose }) {
    const [password, setPassword] = useState('');
    const [error, setError] = useState(null);
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);
        setLoading(true);

        try {
            await axios.put(
                `${API_URL}/users/${username}/password`,
                { password },
                { withCredentials: true }
            );
            setSuccess(true);
            setTimeout(() => {
                onClose();
            }, 1000);
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur lors de la réinitialisation");
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="py-8 text-center text-green-600">
                <p className="font-medium">Mot de passe réinitialisé avec succès !</p>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <p className="text-sm text-muted-foreground mb-4">
                Entrez le nouveau mot de passe pour l'utilisateur <strong>{username}</strong>.
            </p>

            <Input
                label="Nouveau mot de passe"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                autoFocus
            />

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex justify-end gap-2 pt-4">
                <Button type="button" variant="outline" onClick={onClose}>Annuler</Button>
                <Button type="submit" isLoading={loading}>Enregistrer</Button>
            </div>
        </form>
    );
}
