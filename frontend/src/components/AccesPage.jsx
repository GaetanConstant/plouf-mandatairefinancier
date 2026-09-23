import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { UserPlus, Trash2, ShieldCheck } from 'lucide-react';
import { Button, Input, Select } from './ui/Components';
import { API_URL } from '../lib/api';

const ROLES = [
    { value: 'mandataire', label: 'Mandataire — accès complet' },
    { value: 'expert_comptable', label: 'Expert-comptable — lit le compte, demande des pièces' },
    { value: 'equipe', label: "Équipe — dépose, soumis à validation" },
];

const LIBELLE_ROLE = Object.fromEntries(ROLES.map(r => [r.value, r.label.split(' — ')[0]]));

export function AccesPage({ campaignId, moi }) {
    const queryClient = useQueryClient();
    const [username, setUsername] = useState('');
    const [role, setRole] = useState('equipe');

    const { data: acces, isLoading } = useQuery({
        queryKey: ['acces', campaignId],
        queryFn: async () => (await axios.get(`${API_URL}/campaigns/${campaignId}/acces`)).data,
    });

    const rafraichir = () => queryClient.invalidateQueries(['acces', campaignId]);

    const donner = useMutation({
        mutationFn: async () => axios.post(`${API_URL}/campaigns/${campaignId}/acces`, { username, role }),
        onSuccess: () => { rafraichir(); setUsername(''); },
        onError: (err) => alert(err.response?.data?.detail || 'Erreur'),
    });
    const retirer = useMutation({
        mutationFn: async (u) => axios.delete(`${API_URL}/campaigns/${campaignId}/acces/${u}`),
        onSuccess: rafraichir,
        onError: (err) => alert(err.response?.data?.detail || 'Erreur'),
    });

    if (isLoading) return <div>Chargement des accès...</div>;

    return (
        <div className="space-y-5 animate-in fade-in duration-500">
            <header>
                <h2 className="text-2xl font-bold tracking-tight">Accès à la campagne</h2>
                <p className="text-sm text-muted-foreground">
                    Qui peut voir et alimenter cette campagne. Le rôle vaut pour cette campagne seulement.
                </p>
            </header>

            <div className="space-y-3 rounded-md border border-border bg-card p-4">
                <div className="grid gap-3 md:grid-cols-2">
                    <Input label="Identifiant du compte" placeholder="ex : mgarabedian"
                        value={username} onChange={e => setUsername(e.target.value)} />
                    <Select label="Rôle" options={ROLES} value={role} onChange={e => setRole(e.target.value)} />
                </div>
                <p className="text-xs text-muted-foreground">
                    Le compte doit déjà exister. Sa création se fait dans Paramètres.
                </p>
                <div className="flex justify-end">
                    <Button className="gap-2" isLoading={donner.isPending}
                        onClick={() => username.trim() && donner.mutate()}>
                        <UserPlus className="h-4 w-4" /> Donner l'accès
                    </Button>
                </div>
            </div>

            <div className="divide-y divide-border rounded-md border border-border bg-card">
                {acces?.map(a => (
                    <div key={a.username} className="flex items-center gap-3 px-5 py-3">
                        <ShieldCheck className={`h-4 w-4 ${a.role === 'mandataire' ? 'text-primary' : 'text-muted-foreground'}`} />
                        <span className="flex-1 text-sm">
                            <strong>{a.full_name || a.username}</strong>
                            <span className="text-muted-foreground"> — {a.username}</span>
                        </span>
                        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold uppercase text-secondary-foreground">
                            {LIBELLE_ROLE[a.role] || a.role}
                        </span>
                        {a.username !== moi?.username && (
                            <button onClick={() => retirer.mutate(a.username)}
                                title="Retirer l'accès"
                                className="text-muted-foreground transition-colors hover:text-destructive">
                                <Trash2 className="h-4 w-4" />
                            </button>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}
