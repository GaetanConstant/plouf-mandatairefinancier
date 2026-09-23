import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Check, X, Inbox, MessageSquare } from 'lucide-react';
import { Button, Modal, Input } from './ui/Components';
import { API_URL } from '../lib/api';

const quand = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');

export function ValidationPage() {
    const queryClient = useQueryClient();
    const [refus, setRefus] = useState(null);
    const [motif, setMotif] = useState('');

    const { data: file, isLoading } = useQuery({
        queryKey: ['validation-file'],
        queryFn: async () => (await axios.get(`${API_URL}/validation/file`)).data,
    });
    const { data: demandes } = useQuery({
        queryKey: ['demandes-pieces'],
        queryFn: async () => (await axios.get(`${API_URL}/demandes-pieces`)).data,
    });

    // Une validation change les chiffres du compte : tout ce qui en dépend
    // doit être réinterrogé, pas seulement la file.
    const rafraichir = () => {
        ['validation-file', 'stats', 'depenses', 'recettes', 'evenements', 'conformite',
            'completude', 'documents', 'demandes-pieces', 'calendrier', 'frise'].forEach(
            k => queryClient.invalidateQueries([k]));
    };

    const validerMutation = useMutation({
        mutationFn: async (el) => axios.post(`${API_URL}/validation/${el.entite}/${el.id}/valider`),
        onSuccess: rafraichir,
    });
    const refuserMutation = useMutation({
        mutationFn: async ({ el, motif }) =>
            axios.post(`${API_URL}/validation/${el.entite}/${el.id}/refuser`, { motif }),
        onSuccess: () => { rafraichir(); setRefus(null); setMotif(''); },
    });
    const cloreMutation = useMutation({
        mutationFn: async (id) => axios.post(`${API_URL}/demandes-pieces/${id}/clore`),
        onSuccess: rafraichir,
    });

    if (isLoading) return <div>Chargement de la file...</div>;

    const elements = file?.elements || [];
    const ouvertes = (demandes || []).filter(d => d.statut !== 'close');

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header>
                <h2 className="text-2xl font-bold tracking-tight">À valider</h2>
                <p className="text-sm text-muted-foreground">
                    Rien de ce qui figure ici n'entre dans le compte — ni plafond, ni trésorerie,
                    ni dossier de dépôt — tant que vous ne l'avez pas validé.
                </p>
            </header>

            {elements.length === 0 && ouvertes.length === 0 ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center">
                    <Inbox className="mb-3 h-12 w-12 text-muted-foreground opacity-20" />
                    <p className="font-medium text-muted-foreground">Rien en attente.</p>
                </div>
            ) : null}

            {elements.length > 0 && (
                <div className="divide-y divide-border rounded-md border border-border bg-card">
                    {elements.map(el => (
                        <div key={`${el.entite}-${el.id}`} className="flex flex-wrap items-center gap-3 px-5 py-3">
                            <span className="shrink-0 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold uppercase text-secondary-foreground">
                                {el.type_label}
                            </span>
                            <span className="flex-1 text-sm font-medium">{el.libelle}</span>
                            <span className="text-xs text-muted-foreground">
                                par <strong>{el.cree_par || 'inconnu'}</strong> · {quand(el.cree_le)}
                            </span>
                            <div className="flex gap-2">
                                <Button className="gap-1" onClick={() => validerMutation.mutate(el)}>
                                    <Check className="h-4 w-4" /> Valider
                                </Button>
                                <Button variant="outline" className="gap-1"
                                    onClick={() => setRefus(el)}>
                                    <X className="h-4 w-4" /> Refuser
                                </Button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {ouvertes.length > 0 && (
                <div>
                    <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold">
                        <MessageSquare className="h-4 w-4" /> Demandes de pièces
                    </h3>
                    <div className="divide-y divide-border rounded-md border border-border bg-card">
                        {ouvertes.map(d => (
                            <div key={d.id} className="flex flex-wrap items-center gap-3 px-5 py-3">
                                <span className="flex-1 text-sm">{d.message}</span>
                                <span className="text-xs text-muted-foreground">
                                    par <strong>{d.demande_par}</strong> · {quand(d.demande_le)}
                                </span>
                                <Button variant="outline" onClick={() => cloreMutation.mutate(d.id)}>
                                    Clore
                                </Button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <Modal isOpen={Boolean(refus)} onClose={() => setRefus(null)} title="Refuser cet élément">
                <div className="space-y-4">
                    <p className="text-sm text-muted-foreground">
                        L'élément n'est pas supprimé : son auteur le retrouve avec votre motif,
                        le corrige et peut le soumettre à nouveau.
                    </p>
                    <Input label="Motif du refus" placeholder="Ex : facture illisible, montant erroné"
                        value={motif} onChange={e => setMotif(e.target.value)} />
                    <div className="flex justify-end gap-2 pt-2">
                        <Button variant="outline" onClick={() => setRefus(null)}>Annuler</Button>
                        <Button onClick={() => refuserMutation.mutate({ el: refus, motif })}
                            isLoading={refuserMutation.isPending}>
                            Refuser
                        </Button>
                    </div>
                </div>
            </Modal>
        </div>
    );
}
