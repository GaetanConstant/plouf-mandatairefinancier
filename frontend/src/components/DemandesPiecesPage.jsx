import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { MessageSquare, Send } from 'lucide-react';
import { Button, Input, Select } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';

const quand = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');

const STATUTS = {
    ouverte: { label: 'Ouverte', cls: 'bg-amber-100 text-amber-700' },
    repondue: { label: 'Répondue', cls: 'bg-blue-100 text-blue-700' },
    close: { label: 'Close', cls: 'bg-muted text-muted-foreground' },
};

export function DemandesPiecesPage() {
    const queryClient = useQueryClient();
    const [message, setMessage] = useState('');
    const [depenseId, setDepenseId] = useState('');
    const [reponses, setReponses] = useState({});

    const { data: demandes, isLoading } = useQuery({
        queryKey: ['demandes-pieces'],
        queryFn: async () => (await axios.get(`${API_URL}/demandes-pieces`)).data,
    });
    const { data: depenses } = useQuery({
        queryKey: ['depenses'],
        queryFn: async () => (await axios.get(`${API_URL}/depenses`)).data,
    });

    const rafraichir = () => {
        queryClient.invalidateQueries(['demandes-pieces']);
        queryClient.invalidateQueries(['validation-file']);
    };

    const creer = useMutation({
        mutationFn: async () => axios.post(`${API_URL}/demandes-pieces`, {
            message, depense_id: depenseId === '' ? null : Number(depenseId),
        }),
        onSuccess: () => { rafraichir(); setMessage(''); setDepenseId(''); },
    });
    const repondre = useMutation({
        mutationFn: async ({ id, reponse }) =>
            axios.post(`${API_URL}/demandes-pieces/${id}/repondre`, { reponse }),
        onSuccess: rafraichir,
    });

    if (isLoading) return <div>Chargement des demandes...</div>;

    return (
        <div className="space-y-5 animate-in fade-in duration-500">
            <header>
                <h2 className="text-2xl font-bold tracking-tight">Demandes de pièces</h2>
                <p className="text-sm text-muted-foreground">
                    L'expert-comptable réclame ici les justificatifs manquants ; le mandataire répond.
                </p>
            </header>

            <div className="space-y-3 rounded-md border border-border bg-card p-4">
                <Select
                    label="Dépense concernée (facultatif)"
                    value={depenseId}
                    onChange={e => setDepenseId(e.target.value)}
                    options={[{ value: '', label: '— aucune en particulier —' },
                        ...(depenses || []).map(d => ({ value: String(d.id), label: `${d.libelle} (${d.fournisseur})` }))]}
                />
                <Input label="Demande" placeholder="Ex : il manque le relevé bancaire de septembre"
                    value={message} onChange={e => setMessage(e.target.value)} />
                <div className="flex justify-end">
                    <Button className="gap-2" isLoading={creer.isPending}
                        onClick={() => message.trim() && creer.mutate()}>
                        <Send className="h-4 w-4" /> Envoyer la demande
                    </Button>
                </div>
            </div>

            {!demandes?.length ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-10 text-center">
                    <MessageSquare className="mb-3 h-10 w-10 text-muted-foreground opacity-20" />
                    <p className="text-muted-foreground">Aucune demande pour l'instant.</p>
                </div>
            ) : (
                <div className="divide-y divide-border rounded-md border border-border bg-card">
                    {demandes.map(d => {
                        const st = STATUTS[d.statut] || STATUTS.ouverte;
                        return (
                            <div key={d.id} className="space-y-2 px-5 py-3">
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-bold uppercase', st.cls)}>
                                        {st.label}
                                    </span>
                                    <span className="flex-1 text-sm font-medium">{d.message}</span>
                                    <span className="text-xs text-muted-foreground">
                                        {d.demande_par} · {quand(d.demande_le)}
                                    </span>
                                </div>
                                {d.reponse ? (
                                    <p className="ml-2 border-l-2 border-border pl-3 text-sm text-muted-foreground">
                                        {d.reponse} <span className="text-xs">— {d.repondu_par}, {quand(d.repondu_le)}</span>
                                    </p>
                                ) : d.statut !== 'close' && (
                                    <div className="flex items-end gap-2">
                                        <div className="flex-1">
                                            <Input label="Réponse" placeholder="Votre réponse"
                                                value={reponses[d.id] || ''}
                                                onChange={e => setReponses({ ...reponses, [d.id]: e.target.value })} />
                                        </div>
                                        <Button variant="outline"
                                            onClick={() => reponses[d.id]?.trim() &&
                                                repondre.mutate({ id: d.id, reponse: reponses[d.id] })}>
                                            Répondre
                                        </Button>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
