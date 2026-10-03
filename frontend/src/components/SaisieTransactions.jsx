import React from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';
import { API_URL } from '../lib/api';
import { Plus, X } from 'lucide-react';

// Une ligne vierge du tableau de saisie.
export const LIGNE_VIDE = { date_operation: '', libelle: '', montant: '', sens: 'debit', reference: '', cible: '' };

/** Lignes retenues : une date et un montant suffisent à faire une écriture. */
/** Lignes retenues : une date et un montant suffisent à faire une écriture.
 *  `cible` encode l'écriture réglée — « d:12 » une dépense, « r:3 » une recette. */
export const lignesPretes = (lignes) => lignes
    .filter(l => l.date_operation && l.montant !== '')
    .map(({ cible, ...l }) => ({
        ...l,
        montant: Math.abs(Number(l.montant)),
        depense_id: cible?.startsWith('d:') ? Number(cible.slice(2)) : null,
        recette_id: cible?.startsWith('r:') ? Number(cible.slice(2)) : null,
    }));

/** Écritures qu'il reste à rapprocher, pour les proposer à la saisie. */
export function useCibles() {
    const { data: depenses } = useQuery({
        queryKey: ['rapprochement-depenses'],
        queryFn: async () => (await axios.get(`${API_URL}/rapprochement/depenses`)).data,
    });
    const { data: recettes } = useQuery({
        queryKey: ['rapprochement-recettes'],
        queryFn: async () => (await axios.get(`${API_URL}/rapprochement/recettes`)).data,
    });
    return {
        debit: (depenses || []).map(d => ({
            valeur: `d:${d.id}`,
            label: `${d.num_piece || ''} ${d.libelle} — reste ${d.reste.toFixed(2)} €`.trim(),
        })),
        credit: (recettes || []).map(r => ({
            valeur: `r:${r.id}`,
            label: `${r.num_piece || ''} ${r.libelle} — reste ${r.reste.toFixed(2)} €`.trim(),
        })),
    };
}

/** Saisie directe des lignes d'un relevé, quand la banque n'offre pas d'export. */
function AjoutLigne({ releve, onClose }) {
    const queryClient = useQueryClient();
    const [lignes, setLignes] = useState([{ ...LIGNE_VIDE }]);
    const [erreur, setErreur] = useState('');

    const pretes = lignes.filter(l => l.date_operation && l.montant !== '');

    const ajouter = useMutation({
        mutationFn: async () => {
            for (const l of pretes) {
                await axios.post(`${API_URL}/releves/${releve.id}/transactions`,
                                 { ...l, montant: Math.abs(Number(l.montant)) });
            }
        },
        onSuccess: () => {
            ['releves', 'rapprochement-depenses', 'rapprochement-recettes',
             'main-courante', 'completude'].forEach(k => queryClient.invalidateQueries([k]));
            onClose();
        },
        onError: (err) => setErreur(err.response?.data?.detail || "L'ajout a échoué."),
    });

    return (
        <div className="space-y-4">
            <div className="rounded-md bg-muted/40 p-3 text-sm">
                <div className="font-medium">{releve.libelle}</div>
                <div className="text-muted-foreground">{releve.nb_transactions} ligne(s) déjà saisies</div>
            </div>
            <SaisieLignes lignes={lignes} setLignes={setLignes} />
            {erreur && <p className="text-sm text-destructive">{erreur}</p>}
            <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={onClose}>Annuler</Button>
                <Button disabled={!pretes.length} isLoading={ajouter.isPending}
                    onClick={() => ajouter.mutate()}>
                    Ajouter {pretes.length || ''} ligne{pretes.length > 1 ? 's' : ''}
                </Button>
            </div>
        </div>
    );
}


export function SaisieLignes({ lignes, setLignes }) {
    const cibles = useCibles();
    // Changer de sens invalide la cible choisie : un débit ne règle pas une recette.
    const modifier = (i, champ, valeur) =>
        setLignes(lignes.map((l, j) => (j === i
            ? { ...l, [champ]: valeur, ...(champ === 'sens' ? { cible: '' } : {}) }
            : l)));

    return (
        <div className="space-y-2">
            <label className="text-sm font-medium">Lignes du relevé</label>
            <p className="text-[11px] text-muted-foreground">
                Reportez ce que vous lisez sur le relevé. Le montant reste positif :
                c'est le sens qui dit débit ou crédit. Désignez l'écriture réglée pour
                la rapprocher aussitôt — sinon la ligne reste à rapprocher plus tard.
            </p>
            <div className="space-y-2">
                {lignes.map((l, i) => (
                    <div key={i} className="grid grid-cols-12 items-center gap-1.5">
                        <input type="date" value={l.date_operation}
                            onChange={e => modifier(i, 'date_operation', e.target.value)}
                            className="col-span-3 h-9 rounded-md border border-input bg-background px-2 text-xs" />
                        <input placeholder="Libellé" value={l.libelle}
                            onChange={e => modifier(i, 'libelle', e.target.value)}
                            className="col-span-3 h-9 rounded-md border border-input bg-background px-2 text-xs" />
                        <input placeholder="N° chèque / réf." value={l.reference}
                            onChange={e => modifier(i, 'reference', e.target.value)}
                            className="col-span-2 h-9 rounded-md border border-input bg-background px-2 text-xs" />
                        <select value={l.sens} onChange={e => modifier(i, 'sens', e.target.value)}
                            className="col-span-2 h-9 rounded-md border border-input bg-background px-1 text-xs">
                            <option value="debit">Débit</option>
                            <option value="credit">Crédit</option>
                        </select>
                        <input type="number" step="0.01" min="0" placeholder="0,00" value={l.montant}
                            onChange={e => modifier(i, 'montant', e.target.value)}
                            className="col-span-1 h-9 rounded-md border border-input bg-background px-1 text-xs" />
                        <button type="button" onClick={() => setLignes(lignes.filter((_, j) => j !== i))}
                            disabled={lignes.length === 1} title="Retirer la ligne"
                            className="col-span-1 text-muted-foreground hover:text-destructive disabled:opacity-30">
                            <X className="mx-auto h-3.5 w-3.5" />
                        </button>
                        <select value={l.cible || ''} onChange={e => modifier(i, 'cible', e.target.value)}
                            className="col-span-11 h-9 rounded-md border border-input bg-background px-2 text-xs text-muted-foreground">
                            <option value="">
                                {l.sens === 'credit' ? '— recette encaissée (facultatif) —'
                                    : '— dépense réglée par cette ligne (facultatif) —'}
                            </option>
                            {(l.sens === 'credit' ? cibles.credit : cibles.debit).map(c => (
                                <option key={c.valeur} value={c.valeur}>{c.label}</option>
                            ))}
                        </select>
                        <div className="col-span-1" />
                    </div>
                ))}
            </div>
            <button type="button" onClick={() => setLignes([...lignes, { ...LIGNE_VIDE }])}
                className="inline-flex items-center gap-1 text-xs text-primary hover:underline">
                <Plus className="h-3 w-3" /> Ajouter une ligne
            </button>
        </div>
    );
}
