import React, { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { FileText, Pencil, Paperclip } from 'lucide-react';
import { API_URL } from '../lib/api';
import { Modal, Button, Select } from './ui/Components';
import { TYPES_PIECE } from '../lib/constants';
import { ExpenseForm } from './ExpenseForm';


export function DepensesList({ cible = null, onCibleConsommee, role = 'mandataire' }) {
    const [editing, setEditing] = useState(null);
    // Hors mandataire, une dépense n'est pas modifiable : on peut seulement y
    // verser un justificatif, qui passera par la file de validation.
    const peutModifier = role === 'mandataire';
    const [depotPiece, setDepotPiece] = useState(null);
    const { data: depenses, isLoading } = useQuery({
        queryKey: ['depenses'],
        queryFn: async () => {
            const response = await axios.get(`${API_URL}/depenses`);
            return response.data;
        }
    });

    // Une alerte de conformité a désigné une dépense : on l'ouvre en modification,
    // puis on libère la cible pour ne pas la rouvrir au prochain rendu.
    useEffect(() => {
        if (!cible || !depenses) return;
        const trouvee = depenses.find(d => d.id === cible);
        // Ouverture volontaire depuis une alerte de conformité. La cible est
        // consommée dans la foulée, donc l'effet ne se rejoue pas en cascade.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        if (trouvee) setEditing(trouvee);
        onCibleConsommee?.();
    }, [cible, depenses, onCibleConsommee]);

    if (isLoading) return <div>Chargement des dépenses...</div>;

    return (
        <div className="space-y-4 animate-in fade-in duration-500">
            <h2 className="text-2xl font-bold tracking-tight">Dépenses</h2>
            <div className="rounded-md border border-border bg-card">
                <div className="relative w-full overflow-auto">
                    <table className="w-full caption-bottom text-sm">
                        <thead className="[&_tr]:border-b">
                            <tr className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Date</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Libellé</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Fournisseur</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Catégorie</th>
                                <th className="h-12 px-4 text-left align-middle font-medium text-muted-foreground">Statut</th>
                                <th className="h-12 px-4 text-right align-middle font-medium text-muted-foreground">Montant TTC</th>
                                <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">Justificatif</th>
                                <th className="h-12 px-4 text-center align-middle font-medium text-muted-foreground">{peutModifier ? 'Modifier' : 'Justificatif'}</th>
                            </tr>
                        </thead>
                        <tbody className="[&_tr:last-child]:border-0">
                            {depenses?.map((depense, i) => (
                                <tr key={i} className="border-b transition-colors hover:bg-muted/50 data-[state=selected]:bg-muted">
                                    <td className="p-4 align-middle whitespace-nowrap">{depense.date}</td>
                                    <td className="p-4 align-middle font-medium">
                                        {depense.libelle}
                                        {depense.is_nature && (
                                            <span className="ml-2 inline-flex items-center rounded-full bg-purple-100 px-2 py-0.5 text-[10px] font-bold text-purple-700 border border-purple-200">
                                                NATURE
                                            </span>
                                        )}
                                    </td>
                                    <td className="p-4 align-middle">{depense.fournisseur}</td>
                                    <td className="p-4 align-middle"><span className="inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80">{depense.categorie_cnccfp}</span></td>
                                    <td className="p-4 align-middle">{depense.statut}</td>
                                    <td className="p-4 align-middle text-right">{depense.montant_ttc.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}</td>
                                    <td className="p-4 align-middle text-center">
                                        {depense.justificatif_path ? (
                                            <>
                                                <a
                                                    href={`${API_URL}/docs/${depense.justificatif_path.split('/').pop()}`}
                                                    target="_blank"
                                                    rel="noopener noreferrer"
                                                    className="text-primary hover:text-primary/80 flex justify-center transition-colors"
                                                >
                                                    <FileText className="w-5 h-5" />
                                                </a>
                                                {/* Un devis reste à remplacer par la facture définitive. */}
                                                {depense.type_piece === 'devis' && (
                                                    <span className="mt-1 block text-[10px] font-bold text-amber-600">DEVIS</span>
                                                )}
                                            </>
                                        ) : (
                                            <span className="text-muted-foreground text-xs">-</span>
                                        )}
                                    </td>
                                    <td className="p-4 align-middle text-center">
                                        {peutModifier ? (
                                            <button
                                                type="button"
                                                onClick={() => setEditing(depense)}
                                                title="Modifier cette dépense"
                                                className="text-muted-foreground hover:text-primary transition-colors"
                                            >
                                                <Pencil className="w-4 h-4" />
                                            </button>
                                        ) : (
                                            <button
                                                type="button"
                                                onClick={() => setDepotPiece(depense)}
                                                title="Déposer un justificatif"
                                                className="text-muted-foreground hover:text-primary transition-colors"
                                            >
                                                <Paperclip className="w-4 h-4" />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            <Modal
                isOpen={Boolean(editing)}
                onClose={() => setEditing(null)}
                title="Modifier la dépense"
            >
                {editing && (
                    <ExpenseForm expense={editing} onClose={() => setEditing(null)} />
                )}
            </Modal>

            <Modal
                isOpen={Boolean(depotPiece)}
                onClose={() => setDepotPiece(null)}
                title="Déposer un justificatif"
            >
                {depotPiece && (
                    <DepotJustificatif depense={depotPiece} onClose={() => setDepotPiece(null)} />
                )}
            </Modal>
        </div>
    );
}


/**
 * Dépôt d'un justificatif sur une dépense existante.
 *
 * Seul geste ouvert à la direction de campagne et à l'équipe : aucun champ de
 * la dépense n'est modifiable ici, la pièce part à la validation du mandataire.
 */
function DepotJustificatif({ depense, onClose }) {
    const queryClient = useQueryClient();
    const [fichier, setFichier] = useState(null);
    const [typePiece, setTypePiece] = useState(TYPES_PIECE[1].value);
    const [erreur, setErreur] = useState('');

    const deposer = useMutation({
        mutationFn: async () => {
            const body = new FormData();
            body.append('file', fichier);
            const { data } = await axios.post(`${API_URL}/upload`, body, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            await axios.post(`${API_URL}/depenses/${depense.id}/piece`, {
                fichier: data.path, type_piece: typePiece,
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['depenses']);
            queryClient.invalidateQueries(['mes-soumissions']);
            onClose();
        },
        onError: (err) => setErreur(err.response?.data?.detail || "Le dépôt a échoué."),
    });

    return (
        <div className="space-y-4">
            <div className="rounded-md bg-muted/40 p-3 text-sm">
                <div className="font-medium">{depense.libelle}</div>
                <div className="text-muted-foreground">
                    {depense.fournisseur} · {depense.date} ·{' '}
                    {depense.montant_ttc.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                </div>
            </div>

            <p className="text-sm text-muted-foreground">
                Vous ne pouvez pas modifier cette dépense : seul le dépôt d'un justificatif
                vous est ouvert. Il sera soumis au mandataire financier.
            </p>

            <Select label="Nature de la pièce" options={TYPES_PIECE} value={typePiece}
                onChange={e => setTypePiece(e.target.value)} />

            <div className="space-y-1">
                <label className="text-sm font-medium">Fichier</label>
                <input
                    type="file"
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium hover:file:cursor-pointer"
                    onChange={e => { setFichier(e.target.files[0]); setErreur(''); }}
                />
            </div>

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}

            <div className="flex justify-end gap-2 pt-2">
                <Button variant="outline" onClick={onClose}>Annuler</Button>
                <Button onClick={() => fichier && deposer.mutate()} isLoading={deposer.isPending}>
                    Déposer
                </Button>
            </div>
        </div>
    );
}
