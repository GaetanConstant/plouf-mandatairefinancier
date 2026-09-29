import React, { useEffect, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { FileText, Upload } from 'lucide-react';
import { Modal, Button, Select } from './ui/Components';
import { TYPES_PIECE_RECETTE } from '../lib/constants';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';


export function RevenueList({ cible = null, onCibleConsommee }) {
    // Recette dont on verse le justificatif : la pièce est exigée au dossier
    // au même titre qu'une facture de dépense.
    const [depot, setDepot] = useState(null);
    // Recette désignée par une alerte : on l'amène à l'écran et on la surligne.
    const ligneCible = useRef(null);
    useEffect(() => {
        if (!cible) return;
        ligneCible.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        const t = setTimeout(() => onCibleConsommee?.(), 4000);
        return () => clearTimeout(t);
    }, [cible, onCibleConsommee]);

    const { data: recettes, isLoading } = useQuery({
        queryKey: ['recettes'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/recettes`);
            return response.data;
        }
    });

    if (isLoading) return <div>Chargement des recettes...</div>;

    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold tracking-tight">Recettes & Dons</h2>
            <div className="rounded-md border border-border bg-card">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">N° pièce</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Donateur</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Type</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Recu fiscal</th>
                                <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Montant</th>
                                <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Justificatif</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {recettes?.map((recette, i) => (
                                <tr key={i}
                                    ref={recette.id === cible ? ligneCible : null}
                                    className={cn("border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted",
                                        recette.id === cible && "bg-amber-50 ring-2 ring-inset ring-amber-400")}>
                                    <td className="p-4 align-middle font-mono text-xs text-muted-foreground whitespace-nowrap">{recette.num_piece || '—'}</td>
                                    <td className="p-4 align-middle whitespace-nowrap">{recette.date}</td>
                                    <td className="p-4 align-middle font-medium">{recette.nom_donateur}</td>
                                    <td className="p-4 align-middle">{recette.type}</td>
                                    <td className="p-4 align-middle">
                                        {recette.recu_genere ? (
                                            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-green-500/10 text-green-500 hover:bg-green-500/20">Oui</span>
                                        ) : (
                                            <span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-yellow-500/10 text-yellow-500 hover:bg-yellow-500/20">Non</span>
                                        )}
                                    </td>
                                    <td className="p-4 align-middle text-right text-green-600 font-medium">+ {recette.montant.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                                    <td className="p-4 align-middle text-center">
                                        {recette.justificatif_path ? (
                                            <a href={`${API_URL}/docs/${recette.justificatif_path.split('/').pop()}`}
                                                target="_blank" rel="noopener noreferrer"
                                                title="Ouvrir le justificatif"
                                                className="text-primary hover:text-primary/80 inline-flex transition-colors">
                                                <FileText className="w-4 h-4" />
                                            </a>
                                        ) : (
                                            <button onClick={() => setDepot(recette)}
                                                title="Déposer un justificatif"
                                                className="text-muted-foreground hover:text-primary inline-flex transition-colors">
                                                <Upload className="w-4 h-4" />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <Modal isOpen={Boolean(depot)} onClose={() => setDepot(null)}
                title="Déposer un justificatif">
                {depot && <DepotJustificatifRecette recette={depot} onClose={() => setDepot(null)} />}
            </Modal>
        </div>
    );
}


/**
 * Dépôt d'une pièce sur une recette existante.
 *
 * Pendant du dépôt côté dépense : aucun champ de la recette n'est modifiable
 * ici, seule la pièce est versée. Sans ce geste, une recette sans justificatif
 * resterait signalée comme manquante sans moyen de la corriger.
 */
function DepotJustificatifRecette({ recette, onClose }) {
    const queryClient = useQueryClient();
    const [fichier, setFichier] = useState(null);
    const [typePiece, setTypePiece] = useState(TYPES_PIECE_RECETTE[0].value);
    const [erreur, setErreur] = useState('');

    const deposer = useMutation({
        mutationFn: async () => {
            const body = new FormData();
            body.append('file', fichier);
            const { data } = await axios.post(`${API_URL}/upload`, body, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            await axios.post(`${API_URL}/recettes/${recette.id}/piece`, {
                fichier: data.path, type_piece: typePiece,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['recettes']);
            queryClient.invalidateQueries(['completude']);
            queryClient.invalidateQueries(['mes-soumissions']);
            onClose();
        },
        onError: (err) => setErreur(err.response?.data?.detail || "Le dépôt a échoué."),
    });

    return (
        <div className="space-y-4">
            <div className="rounded-md bg-muted/40 p-3 text-sm">
                <div className="font-medium">{recette.nom_donateur}</div>
                <div className="text-muted-foreground">
                    {recette.type} · {recette.date} ·{' '}
                    {recette.montant.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </div>
            </div>

            <Select label="Nature de la pièce" options={TYPES_PIECE_RECETTE} value={typePiece}
                onChange={e => setTypePiece(e.target.value)} />

            <div className="space-y-1">
                <label className="text-sm font-medium">Fichier</label>
                <input
                    type="file"
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium hover:file:cursor-pointer"
                    onChange={e => setFichier(e.target.files[0])}
                />
            </div>

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}

            <div className="pt-2 flex justify-end gap-2">
                <Button variant="outline" onClick={onClose}>Annuler</Button>
                <Button onClick={() => deposer.mutate()} disabled={!fichier}
                    isLoading={deposer.isPending}>Déposer</Button>
            </div>
        </div>
    );
}
