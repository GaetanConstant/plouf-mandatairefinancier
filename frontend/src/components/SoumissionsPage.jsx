import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Inbox, RotateCcw, Plus } from 'lucide-react';
import { Button, Modal } from './ui/Components';
import { ExpenseForm } from './ExpenseForm';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';

const quand = (iso) => (iso ? new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' }) : '');

const STATUTS = {
    propose: { label: 'En attente', cls: 'bg-amber-100 text-amber-700' },
    valide: { label: 'Validé', cls: 'bg-emerald-100 text-emerald-700' },
    refuse: { label: 'Refusé', cls: 'bg-red-100 text-red-700' },
};

export function SoumissionsPage() {
    const queryClient = useQueryClient();
    const [depotOuvert, setDepotOuvert] = useState(false);

    const { data: soumissions, isLoading } = useQuery({
        queryKey: ['mes-soumissions'],
        queryFn: async () => (await axios.get(`${API_URL}/validation/mes-soumissions`)).data,
    });

    const resoumettre = useMutation({
        mutationFn: async (el) => axios.post(`${API_URL}/validation/${el.entite}/${el.id}/resoumettre`),
        onSuccess: () => queryClient.invalidateQueries(['mes-soumissions']),
    });

    if (isLoading) return <div>Chargement...</div>;

    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Mes soumissions</h2>
                    <p className="text-sm text-muted-foreground">
                        Ce que vous avez déposé et où ça en est. Un élément refusé se corrige et se soumet à nouveau.
                    </p>
                </div>
                <Button className="gap-2" onClick={() => setDepotOuvert(true)}>
                    <Plus className="h-4 w-4" /> Déposer une dépense
                </Button>
            </header>

            {!soumissions?.length ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center">
                    <Inbox className="mb-3 h-12 w-12 text-muted-foreground opacity-20" />
                    <p className="font-medium text-muted-foreground">Vous n'avez encore rien déposé.</p>
                </div>
            ) : (
                <div className="divide-y divide-border rounded-md border border-border bg-card">
                    {soumissions.map(el => {
                        const st = STATUTS[el.statut] || STATUTS.propose;
                        return (
                            <div key={`${el.entite}-${el.id}`} className="px-5 py-3">
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className="shrink-0 rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold uppercase text-secondary-foreground">
                                        {el.type_label}
                                    </span>
                                    <span className="flex-1 text-sm font-medium">{el.libelle}</span>
                                    <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-bold uppercase', st.cls)}>
                                        {st.label}
                                    </span>
                                    <span className="text-xs text-muted-foreground">{quand(el.cree_le)}</span>
                                    {el.statut === 'refuse' && (
                                        <Button variant="outline" className="gap-1"
                                            onClick={() => resoumettre.mutate(el)}>
                                            <RotateCcw className="h-3.5 w-3.5" /> Soumettre à nouveau
                                        </Button>
                                    )}
                                </div>
                                {el.motif_refus && (
                                    <p className="mt-1 text-xs text-red-700">Motif : {el.motif_refus}</p>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            <Modal isOpen={depotOuvert} onClose={() => setDepotOuvert(false)}
                title="Déposer une dépense">
                <p className="mb-4 text-sm text-muted-foreground">
                    Votre dépôt part au mandataire financier. Il n'entre dans le compte qu'une fois validé.
                </p>
                <ExpenseForm onClose={() => {
                    setDepotOuvert(false);
                    queryClient.invalidateQueries(['mes-soumissions']);
                }} />
            </Modal>
        </div>
    );
}
