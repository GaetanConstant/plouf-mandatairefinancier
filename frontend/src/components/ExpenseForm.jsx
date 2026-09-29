import React, { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CATEGORIES_CNCCFP, PRISES_EN_CHARGE, STATUTS_DEPENSE, TYPES_PIECE } from '../lib/constants';
import { Button, Input, Select } from './ui/Components';
import { CalendarDays, Plus, X } from 'lucide-react';
import { API_URL } from '../lib/api';



// Valeur sentinelle de l'option « nouveau fournisseur » du menu déroulant.
const NOUVEAU_FOURNISSEUR = '__nouveau__';

// Une quote-part vide vaut la totalité de la dépense, comme côté serveur.
const QUOTE_PART_TOTALE = 100;
const part = (q) => (q === '' || q === null || q === undefined ? QUOTE_PART_TOTALE : Number(q));

export function ExpenseForm({ onClose, prefilledData, expense }) {
    const queryClient = useQueryClient();
    const isEdit = Boolean(expense?.id);
    const [formData, setFormData] = useState({
        date: expense?.date || new Date().toISOString().split('T')[0],
        libelle: expense?.libelle || '',
        fournisseur: expense?.fournisseur || '',
        montant_ttc: expense?.montant_ttc ?? '',
        tva: expense?.tva ?? '',
        categorie_cnccfp: expense?.categorie_cnccfp || CATEGORIES_CNCCFP[0].code,
        prise_en_charge: expense?.prise_en_charge || PRISES_EN_CHARGE[0].value,
        statut: expense?.statut || STATUTS_DEPENSE[0].value,
        justificatif_path: expense?.justificatif_path || null,
        type_piece: expense?.type_piece || TYPES_PIECE[1].value,
        is_nature: expense?.is_nature || false
    });
    // Le fournisseur se choisit dans la liste des fournisseurs déjà saisis ;
    // `newSupplier` bascule le champ en saisie libre pour en créer un nouveau.
    const [newSupplier, setNewSupplier] = useState(false);

    // Rattachements à des événements. Une dépense peut être ventilée sur
    // plusieurs (Σ des quote-parts ≤ 100 %), d'où une liste et non un champ.
    const [liaisons, setLiaisons] = useState(
        (expense?.evenements || []).map(l => ({
            evenement_id: l.evenement_id,
            quote_part: l.quote_part ?? '',
        })));

    const { data: evenements } = useQuery({
        queryKey: ['evenements'],
        queryFn: async () => (await axios.get(`${API_URL}/evenements`)).data,
    });

    const totalQuotePart = liaisons.reduce((t, l) => t + part(l.quote_part), 0);
    const quotePartExcessive = totalQuotePart > QUOTE_PART_TOTALE;

    const ajouterLiaison = () => {
        const libres = (evenements || []).filter(
            e => !liaisons.some(l => l.evenement_id === e.id));
        if (!libres.length) return;
        setLiaisons([...liaisons, { evenement_id: libres[0].id, quote_part: '' }]);
    };
    const modifierLiaison = (i, champ, valeur) =>
        setLiaisons(liaisons.map((l, j) => (j === i ? { ...l, [champ]: valeur } : l)));
    const retirerLiaison = (i) => setLiaisons(liaisons.filter((_, j) => j !== i));

    const [file, setFile] = useState(null);
    const [errors, setErrors] = useState({});
    const [suppliers, setSuppliers] = useState([]);

    // Fetch suppliers on mount
    useEffect(() => {
        axios.get(`${API_URL}/fournisseurs`)
            .then(res => setSuppliers(res.data))
            .catch(err => console.error("Failed to fetch suppliers", err));
    }, []);

    // Effect to populate form with scanned data
    useEffect(() => {
        if (prefilledData) {
            setFormData(prev => ({
                ...prev,
                date: prefilledData.date || prev.date,
                montant_ttc: prefilledData.montant || prev.montant_ttc,
                fournisseur: prefilledData.fournisseur !== "Inconnu" ? prefilledData.fournisseur : prev.fournisseur,
                libelle: prefilledData.libelle !== "Dépense détectée" ? prefilledData.libelle : prev.libelle,
            }));
            if (prefilledData.file) {
                setFile(prefilledData.file);
            }
        }
    }, [prefilledData]);

    const uploadMutation = useMutation({
        mutationFn: async (fileToUpload) => {
            const formData = new FormData();
            formData.append('file', fileToUpload);
            // ... (rest of logic)
            const res = await axios.post(`${API_URL}/upload`, formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            });
            return res.data.path;
        }
    });

    const saveMutation = useMutation({
        mutationFn: async (payload) => {
            if (isEdit) {
                await axios.put(`${API_URL}/depenses/${expense.id}`, payload);
            } else {
                await axios.post(`${API_URL}/depenses`, payload);
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['depenses']);
            queryClient.invalidateQueries(['stats']);
            queryClient.invalidateQueries(['completude']);
            // Le coût d'un événement dépend de ces liaisons.
            queryClient.invalidateQueries(['evenements']);
            queryClient.invalidateQueries(['frise']);
            // Re-fetch suppliers to include the newly added one if it's new
            axios.get(`${API_URL}/fournisseurs`).then(res => setSuppliers(res.data));
            onClose();
        }
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        const newErrors = {};
        if (!formData.libelle) newErrors.libelle = "Le libellé est requis";
        if (!formData.fournisseur) newErrors.fournisseur = "Le fournisseur est requis";
        if (!formData.montant_ttc || Number(formData.montant_ttc) <= 0) newErrors.montant_ttc = "Montant invalide";
        if (quotePartExcessive) newErrors.liaisons = `Quote-part totale : ${totalQuotePart} % (maximum 100 %)`;

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        let justificatifPath = null;
        if (file) {
            try {
                justificatifPath = await uploadMutation.mutateAsync(file);
            } catch (err) {
                console.error("Upload failed", err);
                setErrors({ ...newErrors, file: "Erreur lors de l'upload du fichier" });
                return;
            }
        }

        saveMutation.mutate({
            ...formData,
            montant_ttc: Number(formData.montant_ttc),
            tva: Number(formData.tva || 0),
            // En édition sans nouveau fichier, on ne renvoie rien : le service
            // conserve alors le justificatif déjà rattaché.
            justificatif_path: justificatifPath,
            // Liste explicite : le serveur détache ce qui n'y figure plus.
            evenements: liaisons.map(l => ({
                evenement_id: Number(l.evenement_id),
                quote_part: l.quote_part === '' ? null : Number(l.quote_part),
            })),
        });
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                    label="Date"
                    type="date"
                    value={formData.date}
                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                    required
                />
                <Select
                    label="Statut"
                    options={STATUTS_DEPENSE}
                    value={formData.statut}
                    onChange={e => setFormData({ ...formData, statut: e.target.value })}
                />
            </div>

            <Input
                label="Libellé"
                placeholder="Ex: Impression tracts semaine 1"
                value={formData.libelle}
                onChange={e => setFormData({ ...formData, libelle: e.target.value })}
                error={errors.libelle}
            />

            {newSupplier || (formData.fournisseur && !suppliers.includes(formData.fournisseur)) ? (
                <div className="space-y-2">
                    <Input
                        label="Nouveau fournisseur"
                        placeholder="Ex: Imprimerie Villeurbanne"
                        value={formData.fournisseur}
                        onChange={e => setFormData({ ...formData, fournisseur: e.target.value })}
                        error={errors.fournisseur}
                        autoFocus
                    />
                    {suppliers.length > 0 && (
                        <button
                            type="button"
                            className="text-xs text-primary hover:underline"
                            onClick={() => { setNewSupplier(false); setFormData({ ...formData, fournisseur: '' }); }}
                        >
                            ← Choisir un fournisseur existant
                        </button>
                    )}
                </div>
            ) : (
                <Select
                    label="Fournisseur"
                    options={[
                        { value: '', label: '— Choisir un fournisseur —' },
                        ...suppliers.map(s => ({ value: s, label: s })),
                        { value: NOUVEAU_FOURNISSEUR, label: '＋ Nouveau fournisseur…' },
                    ]}
                    value={formData.fournisseur}
                    onChange={e => {
                        if (e.target.value === NOUVEAU_FOURNISSEUR) {
                            setNewSupplier(true);
                            setFormData({ ...formData, fournisseur: '' });
                        } else {
                            setFormData({ ...formData, fournisseur: e.target.value });
                        }
                    }}
                    error={errors.fournisseur}
                />
            )}

            <Select
                label="Prise en charge"
                options={PRISES_EN_CHARGE}
                value={formData.prise_en_charge}
                onChange={e => setFormData({ ...formData, prise_en_charge: e.target.value })}
            />

            <Select
                label="Catégorie CNCCFP"
                options={CATEGORIES_CNCCFP.map(c => ({ value: c.code, label: `${c.code} - ${c.label}` }))}
                value={formData.categorie_cnccfp}
                onChange={e => setFormData({ ...formData, categorie_cnccfp: e.target.value })}
            />

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input
                    label="Montant TTC (€)"
                    type="number"
                    step="0.01"
                    value={formData.montant_ttc}
                    onChange={e => setFormData({ ...formData, montant_ttc: e.target.value })}
                    error={errors.montant_ttc}
                />
                <Input
                    label="Dont TVA (€)"
                    type="number"
                    step="0.01"
                    value={formData.tva}
                    onChange={e => setFormData({ ...formData, tva: e.target.value })}
                />
            </div>

            <div className="flex items-center gap-2 p-3 bg-muted/40 rounded-lg border border-border/50">
                <input
                    type="checkbox"
                    id="is_nature"
                    className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                    checked={formData.is_nature}
                    onChange={e => setFormData({ ...formData, is_nature: e.target.checked })}
                />
                <label htmlFor="is_nature" className="text-sm font-medium cursor-pointer">
                    C'est un concours en nature (Don de prestation/matériel)
                </label>
            </div>

            <div className="space-y-3 rounded-lg border border-border/50 bg-muted/40 p-3">
                <div className="flex items-center justify-between gap-2">
                    <label className="flex items-center gap-2 text-sm font-medium">
                        <CalendarDays className="w-4 h-4 text-primary" />
                        Rattachement à un événement
                    </label>
                    {Boolean(evenements?.length) && (
                        <button type="button" onClick={ajouterLiaison}
                            disabled={liaisons.length >= evenements.length}
                            className="inline-flex items-center gap-1 text-xs text-primary hover:underline disabled:opacity-40 disabled:no-underline">
                            <Plus className="w-3 h-3" /> Rattacher un événement
                        </button>
                    )}
                </div>

                {!evenements?.length && (
                    <p className="text-xs text-muted-foreground italic">
                        Aucun événement enregistré — créez-en un depuis l'onglet Événements.
                    </p>
                )}
                {Boolean(evenements?.length) && !liaisons.length && (
                    <p className="text-xs text-muted-foreground italic">
                        Cette dépense n'est rattachée à aucun événement.
                    </p>
                )}

                {liaisons.map((liaison, i) => (
                    <div key={i} className="flex items-end gap-2">
                        <div className="flex-1 min-w-0">
                            <Select
                                label={i === 0 ? 'Événement' : ''}
                                options={(evenements || [])
                                    .filter(e => e.id === Number(liaison.evenement_id)
                                        || !liaisons.some(l => Number(l.evenement_id) === e.id))
                                    .map(e => ({ value: e.id, label: e.titre }))}
                                value={liaison.evenement_id}
                                onChange={e => modifierLiaison(i, 'evenement_id', e.target.value)}
                            />
                        </div>
                        <div className="w-28 shrink-0">
                            <Input
                                label={i === 0 ? 'Quote-part %' : ''}
                                type="number" min="0" max="100" placeholder="100"
                                value={liaison.quote_part}
                                onChange={e => modifierLiaison(i, 'quote_part', e.target.value)}
                            />
                        </div>
                        <button type="button" onClick={() => retirerLiaison(i)}
                            title="Détacher cet événement"
                            className="mb-2 text-muted-foreground hover:text-red-600 transition-colors">
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                ))}

                {liaisons.length > 0 && (
                    <p className={`text-[11px] ${quotePartExcessive ? 'text-destructive font-medium' : 'text-muted-foreground'}`}>
                        {quotePartExcessive
                            ? `Quote-part totale : ${totalQuotePart} % — le maximum est 100 %.`
                            : `Quote-part totale : ${totalQuotePart} %. Vide = 100 %, le reste est hors événement.`}
                    </p>
                )}
                {errors.liaisons && <p className="text-sm text-destructive">{errors.liaisons}</p>}
            </div>

            <div className="space-y-2 rounded-lg border border-border/50 bg-muted/40 p-3">
                <Select
                    label="Nature de la pièce"
                    options={TYPES_PIECE}
                    value={formData.type_piece}
                    onChange={e => setFormData({ ...formData, type_piece: e.target.value })}
                />

                {formData.justificatif_path && (
                    <p className="text-xs text-muted-foreground">
                        Pièce actuelle :{' '}
                        <a
                            href={`${API_URL}/docs/${formData.justificatif_path.split('/').pop()}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                        >
                            {formData.justificatif_path.split('/').pop()}
                        </a>
                    </p>
                )}

                <div className="space-y-1">
                    <label className="text-sm font-medium">
                        {formData.justificatif_path ? 'Remplacer la pièce' : 'Justificatif (devis ou facture)'}
                    </label>
                    <input
                        type="file"
                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium hover:file:cursor-pointer"
                        onChange={e => setFile(e.target.files[0])}
                    />
                    {formData.justificatif_path && (
                        <p className="text-[11px] text-muted-foreground">
                            Sans nouveau fichier, seule la nature de la pièce est mise à jour.
                        </p>
                    )}
                    {errors.file && <p className="text-sm text-destructive">{errors.file}</p>}
                </div>
            </div>

            <div className="pt-4 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={onClose}>Annuler</Button>
                <Button type="submit" isLoading={saveMutation.isPending || uploadMutation.isPending}>
                    {isEdit ? 'Mettre à jour la dépense' : 'Enregistrer la dépense'}
                </Button>
            </div>
        </form>
    );
}
