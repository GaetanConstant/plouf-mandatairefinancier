
import React, { useState } from 'react';
import axios from 'axios';
import { Button } from '../components/ui/Components';
import { Lock, User } from 'lucide-react';
import parrot from '../assets/parrot.webp';

const API_URL = 'http://localhost:8000';

// Palette SCOPA
const SCOPA = { primary: '#6186ea', dark: '#3547af', cream: '#edecea' };

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
            const response = await axios.post(`${API_URL}/login`, { username, password }, { withCredentials: true });
            if (response.status === 200) onLogin(response.data.user);
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur de connexion");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex" style={{ backgroundColor: SCOPA.cream }}>
            {/* Colonne formulaire (encadré + typo conservés) */}
            <div className="flex-1 flex flex-col items-center justify-center p-6">
                <div className="w-full max-w-md bg-card border border-border rounded-2xl shadow-2xl p-8 animate-in fade-in zoom-in-95 duration-300">
                    <div className="flex flex-col items-center mb-8">
                        {/* Vignette perroquet sur mobile (où la colonne de droite est masquée) */}
                        <img src={parrot} alt="Plouf" className="md:hidden w-full h-32 object-cover rounded-xl mb-4" />
                        <h1 className="text-3xl font-extrabold tracking-tight" style={{ color: SCOPA.dark }}>Plouf</h1>
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
                                    className="pl-10 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
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
                                    className="pl-10 flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
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

                        <Button type="submit" className="w-full rounded-full" isLoading={loading}
                            style={{ backgroundColor: SCOPA.primary }}>
                            Se connecter
                        </Button>
                    </form>
                </div>

                <p className="mt-8 text-sm" style={{ color: SCOPA.dark, opacity: 0.6 }}>
                    © 2026 Plouf — Accès sécurisé.
                </p>
            </div>

            {/* Colonne perroquet (image enership) */}
            <div className="hidden md:block flex-1 relative overflow-hidden">
                <img src={parrot} alt="Perroquet Plouf" className="absolute inset-0 w-full h-full object-cover" />
                <div className="absolute inset-0" style={{ background: `linear-gradient(160deg, rgba(53,71,175,0.25) 0%, rgba(53,71,175,0.65) 100%)` }} />
                <div className="absolute bottom-12 left-12 right-12 text-white">
                    <h2 className="text-5xl font-extrabold uppercase tracking-wide drop-shadow-lg">Plouf</h2>
                    <p className="mt-3 text-white/90 text-lg max-w-md drop-shadow">
                        La gestion du mandataire financier, simple et conforme.
                    </p>
                </div>
            </div>
        </div>
    );
}
