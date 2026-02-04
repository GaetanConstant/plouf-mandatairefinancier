
import React, { useState } from 'react';
import axios from 'axios';
import { Button, Input } from '../components/ui/Components';
import { Wallet, Lock, User } from 'lucide-react';

const API_URL = 'http://localhost:8000';

export function LoginPage({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            // Include credentials to receive cookies
            const response = await axios.post(
                `${API_URL}/login`,
                { username, password },
                { withCredentials: true }
            );

            if (response.status === 200) {
                onLogin(response.data.user);
            }
        } catch (err) {
            console.error("Login Error", err);
            setError(err.response?.data?.detail || "Erreur de connexion");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
            <div className="w-full max-w-md bg-card border border-border rounded-xl shadow-2xl p-8 animate-in fade-in zoom-in-95 duration-300">
                <div className="flex flex-col items-center mb-8">
                    <div className="p-4 bg-primary/10 rounded-full mb-4">
                        <Wallet className="w-12 h-12 text-primary" />
                    </div>
                    <h1 className="text-2xl font-bold tracking-tight">Campagne 2026</h1>
                    <p className="text-muted-foreground text-center mt-2">
                        Connectez-vous pour accéder au compte mandataire.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Identifiant</label>
                        <div className="relative">
                            <User className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                            <input
                                type="text"
                                className="pl-10 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                placeholder="gconstant"
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    <div className="space-y-2">
                        <label className="text-sm font-medium">Mot de passe</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-2.5 h-5 w-5 text-muted-foreground" />
                            <input
                                type="password"
                                className="pl-10 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                                placeholder="••••••••"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>
                    </div>

                    {error && (
                        <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md text-sm text-destructive font-medium flex items-center justify-center">
                            {error}
                        </div>
                    )}

                    <Button type="submit" className="w-full" isLoading={loading}>
                        Se connecter
                    </Button>
                </form>
            </div>

            <p className="mt-8 text-sm text-muted-foreground">
                © 2026 Campagne Municipale. Accès sécurisé.
            </p>
        </div>
    );
}
