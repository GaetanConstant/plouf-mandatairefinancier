import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Landmark, Upload, ClipboardPaste, ScanLine, Link2, X, Trash2, Check } from 'lucide-react';
import { Button, Input, Modal, Select } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';

const eur = (v) => (v ?? 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

const VOIES = [
    { cle: 'csv', label: 'Fichier CSV', icon: Upload },
    { cle: 'texte', label: 'Copier-coller', icon: ClipboardPaste },
    { cle: 'ocr', label: 'PDF ou photo', icon: ScanLine },
];

export function RelevesPage() {
    const queryClient = useQueryClient();
    const [importOuvert, setImportOuvert] = useState(false);
    const [transactionCiblee, setTransactionCiblee] = useState(null);

    const { data: releves, isLoading } = useQuery({
        queryKey: ['releves'],
        queryFn: async () => (await axios.get(`${API_URL}/releves`)).data,
    });

    const supprimer = useMutation({
        mutationFn: async (id) => axios.delete(`${API_URL}/releves/${id}`),
        onSuccess: () => queryClient.invalidateQueries(['releves']),
    });

    if (isLoading) return <div>Chargement des relevés...</div>;

    return (
        <div className="space-y-5 animate-in fade-in duration-500">
            <header className="flex flex-wrap items-start justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold tracking-tight">Relevés bancaires</h2>
                    <p className="text-sm text-muted-foreground">
                        Rapprochez chaque ligne du compte avec les dépenses qu'elle règle.
                        Une ligne peut en régler plusieurs, une dépense peut être payée en plusieurs fois.
                    </p>
                </div>
                <Button className="gap-2" onClick={() => setImportOuvert(true)}>
                    <Upload className="h-4 w-4" /> Importer un relevé
                </Button>
            </header>

            {!releves?.length ? (
                <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border p-12 text-center">
                    <Landmark className="mb-3 h-12 w-12 text-muted-foreground opacity-20" />
                    <p className="font-medium text-muted-foreground">Aucun relevé importé.</p>
                </div>
            ) : releves.map(r => (
                <div key={r.id} className="rounded-md border border-border bg-card">
                    <div className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-3">
                        <h3 className="font-semibold">{r.libelle}</h3>
                        <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] font-bold uppercase text-secondary-foreground">
                            {r.source}
                        </span>
                        <span className="text-xs text-muted-foreground">
                            {r.date_debut} → {r.date_fin} · {r.nb_transactions} ligne(s) ·
                            débits {eur(r.total_debit)}
                        </span>
                        {r.nb_orphelines > 0 ? (
                            <span className="rounded-full bg-amber-100 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-700">
                                {r.nb_orphelines} à rapprocher
                            </span>
                        ) : (
                            <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-bold uppercase text-emerald-700">
                                tout rapproché
                            </span>
                        )}
                        <button
                            onClick={() => window.confirm(`Supprimer le relevé « ${r.libelle} » et ses rapprochements ?`) && supprimer.mutate(r.id)}
                            title="Supprimer ce relevé"
                            className="ml-auto text-muted-foreground transition-colors hover:text-destructive"
                        >
                            <Trash2 className="h-4 w-4" />
                        </button>
                    </div>

                    <div className="divide-y divide-border">
                        {r.transactions.map(t => (
                            <div key={t.id} className="px-5 py-3">
                                <div className="flex flex-wrap items-center gap-3">
                                    <span className="w-24 shrink-0 text-xs text-muted-foreground">{t.date_operation}</span>
                                    <span className="flex-1 text-sm font-medium">{t.libelle}</span>
                                    <span className={cn('text-sm font-semibold',
                                        t.sens === 'debit' ? 'text-foreground' : 'text-emerald-600')}>
                                        {t.sens === 'debit' ? '−' : '+'}{eur(t.montant)}
                                    </span>
                                    {t.rapprochee ? (
                                        <span className="flex items-center gap-1 text-xs font-medium text-emerald-600">
                                            <Check className="h-3.5 w-3.5" /> rapprochée
                                        </span>
                                    ) : (
                                        <Button variant="outline" className="gap-1"
                                            onClick={() => setTransactionCiblee(t)}>
                                            <Link2 className="h-3.5 w-3.5" /> Rapprocher
                                            <span className="text-xs text-muted-foreground">reste {eur(t.reste)}</span>
                                        </Button>
                                    )}
                                </div>

                                {t.imputations.length > 0 && (
                                    <ul className="ml-24 mt-2 space-y-1">
                                        {t.imputations.map(i => (
                                            <li key={i.id} className="flex items-center gap-2 text-xs text-muted-foreground">
                                                <span className="flex-1">
                                                    {i.libelle_depense}
                                                    {i.fournisseur && <span className="opacity-70"> · {i.fournisseur}</span>}
                                                </span>
                                                <span className="font-mono">{eur(i.montant)}</span>
                                                <DesimputerBouton imputationId={i.id} />
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            ))}

            <Modal isOpen={importOuvert} onClose={() => setImportOuvert(false)} title="Importer un relevé">
                <ImportReleve onClose={() => setImportOuvert(false)} />
            </Modal>

            <Modal isOpen={Boolean(transactionCiblee)} onClose={() => setTransactionCiblee(null)}
                title="Rapprocher une transaction">
                {transactionCiblee && (
                    <Rapprochement transaction={transactionCiblee} onClose={() => setTransactionCiblee(null)} />
                )}
            </Modal>
        </div>
    );
}


function DesimputerBouton({ imputationId }) {
    const queryClient = useQueryClient();
    const retirer = useMutation({
        mutationFn: async () => axios.delete(`${API_URL}/imputations/${imputationId}`),
        onSuccess: () => {
            queryClient.invalidateQueries(['releves']);
            queryClient.invalidateQueries(['rapprochement-depenses']);
            queryClient.invalidateQueries(['main-courante']);
            queryClient.invalidateQueries(['depenses']);
        },
    });
    return (
        <button onClick={() => retirer.mutate()} title="Retirer ce rapprochement"
            className="transition-colors hover:text-destructive">
            <X className="h-3 w-3" />
        </button>
    );
}


/** Import en deux temps : on lit, on relit à l'écran, puis on valide. */
function ImportReleve({ onClose }) {
    const queryClient = useQueryClient();
    const [voie, setVoie] = useState('csv');
    const [libelle, setLibelle] = useState('');
    const [texte, setTexte] = useState('');
    const [apercu, setApercu] = useState(null);
    const [erreur, setErreur] = useState('');

    const echoue = (err) => setErreur(err.response?.data?.detail || 'Lecture impossible.');

    const [fichierDepose, setFichierDepose] = useState(null);

    const lireFichier = useMutation({
        mutationFn: async ({ fichier, route }) => {
            const body = new FormData();
            body.append('file', fichier);
            const { data } = await axios.post(`${API_URL}/releves/${route}`, body, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            // Le relevé lui-même part en enveloppe B du dossier de dépôt.
            const conserve = new FormData();
            conserve.append('file', fichier);
            const { data: piece } = await axios.post(`${API_URL}/upload`, conserve, {
                headers: { 'Content-Type': 'multipart/form-data' },
            });
            return { ...data, chemin: piece.path };
        },
        onSuccess: (data) => { setApercu(data.transactions); setFichierDepose(data.chemin); setErreur(''); },
        onError: echoue,
    });

    const lireTexte = useMutation({
        mutationFn: async () => (await axios.post(`${API_URL}/releves/lire-texte`, { texte })).data,
        onSuccess: (data) => { setApercu(data.transactions); setErreur(''); },
        onError: echoue,
    });

    const enregistrer = useMutation({
        mutationFn: async () => axios.post(`${API_URL}/releves`, {
            libelle, source: voie === 'texte' ? 'manuel' : voie,
            fichier: fichierDepose, transactions: apercu,
        }),
        onSuccess: () => {
            ['releves', 'rapprochement-depenses', 'documents', 'completude']
                .forEach(k => queryClient.invalidateQueries([k]));
            onClose();
        },
        onError: echoue,
    });

    return (
        <div className="space-y-4">
            <div className="flex gap-2">
                {VOIES.map(({ cle, label, icon: Icon }) => (
                    <button key={cle} type="button" onClick={() => { setVoie(cle); setApercu(null); }}
                        className={cn('flex flex-1 items-center justify-center gap-2 rounded-md border px-3 py-2 text-xs font-medium transition-colors',
                            voie === cle ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:text-foreground')}>
                        <Icon className="h-4 w-4" /> {label}
                    </button>
                ))}
            </div>

            <Input label="Nom du relevé" placeholder="Ex : Septembre 2026"
                value={libelle} onChange={e => setLibelle(e.target.value)} />

            {voie === 'texte' ? (
                <div className="space-y-2">
                    <label className="text-sm font-medium">Lignes du relevé</label>
                    <textarea
                        rows={6}
                        className="w-full rounded-md border border-input bg-background p-3 font-mono text-xs"
                        placeholder="08/09/2026  VIR IMPRIMERIE GRENIER   -4 037,21"
                        value={texte}
                        onChange={e => setTexte(e.target.value)}
                    />
                    <Button variant="outline" isLoading={lireTexte.isPending}
                        onClick={() => texte.trim() && lireTexte.mutate()}>
                        Lire les lignes
                    </Button>
                </div>
            ) : (
                <div className="space-y-1">
                    <label className="text-sm font-medium">
                        {voie === 'csv' ? 'Fichier CSV de la banque' : 'PDF ou photo du relevé'}
                    </label>
                    <input
                        type="file"
                        accept={voie === 'csv' ? '.csv,text/csv' : '.pdf,image/*'}
                        className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm file:border-0 file:bg-transparent file:text-sm file:font-medium hover:file:cursor-pointer"
                        onChange={e => e.target.files[0] && lireFichier.mutate({
                            fichier: e.target.files[0],
                            route: voie === 'csv' ? 'lire-csv' : 'lire-image',
                        })}
                    />
                    <p className="text-[11px] text-muted-foreground">
                        Le fichier est conservé comme pièce du dossier : le relevé bancaire
                        est exigé en enveloppe B.
                    </p>
                    {voie === 'ocr' && (
                        <p className="text-[11px] text-muted-foreground">
                            La reconnaissance se trompe : relisez l'aperçu avant d'enregistrer.
                        </p>
                    )}
                </div>
            )}

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}
            {(lireFichier.isPending) && <p className="text-sm text-muted-foreground">Lecture en cours…</p>}

            {apercu && (
                <div className="space-y-2">
                    <p className="text-sm font-medium">{apercu.length} transaction(s) lues</p>
                    <div className="max-h-56 overflow-y-auto rounded-md border border-border">
                        {apercu.map((t, i) => (
                            <div key={i} className="flex items-center gap-2 border-b border-border px-3 py-1.5 text-xs last:border-0">
                                <span className="w-20 shrink-0 text-muted-foreground">{t.date_operation}</span>
                                <span className="flex-1 truncate">{t.libelle}</span>
                                <span className={t.sens === 'debit' ? '' : 'text-emerald-600'}>
                                    {t.sens === 'debit' ? '−' : '+'}{eur(t.montant)}
                                </span>
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-end gap-2">
                        <Button variant="outline" onClick={onClose}>Annuler</Button>
                        <Button isLoading={enregistrer.isPending}
                            onClick={() => libelle.trim() && enregistrer.mutate()}>
                            Enregistrer le relevé
                        </Button>
                    </div>
                    {!libelle.trim() && <p className="text-right text-xs text-muted-foreground">Donnez un nom au relevé.</p>}
                </div>
            )}
        </div>
    );
}


function Rapprochement({ transaction, onClose }) {
    const queryClient = useQueryClient();
    const [depenseId, setDepenseId] = useState('');
    const [montant, setMontant] = useState('');
    const [erreur, setErreur] = useState('');

    const { data: candidates } = useQuery({
        queryKey: ['rapprochement-depenses'],
        queryFn: async () => (await axios.get(`${API_URL}/rapprochement/depenses`)).data,
    });

    const imputer = useMutation({
        mutationFn: async () => axios.post(`${API_URL}/transactions/${transaction.id}/imputations`, {
            depense_id: Number(depenseId),
            montant: montant === '' ? null : Number(montant),
        }),
        onSuccess: () => {
            ['releves', 'rapprochement-depenses', 'main-courante', 'depenses', 'stats', 'conformite']
                .forEach(k => queryClient.invalidateQueries([k]));
            setDepenseId(''); setMontant(''); setErreur('');
            onClose();
        },
        onError: (err) => setErreur(err.response?.data?.detail || 'Rapprochement impossible.'),
    });

    const choisie = (candidates || []).find(c => String(c.id) === depenseId);

    return (
        <div className="space-y-4">
            <div className="rounded-md bg-muted/40 p-3 text-sm">
                <div className="font-medium">{transaction.libelle}</div>
                <div className="text-muted-foreground">
                    {transaction.date_operation} · {eur(transaction.montant)} ·
                    reste à imputer <strong>{eur(transaction.reste)}</strong>
                </div>
            </div>

            <Select
                label="Dépense à régler"
                value={depenseId}
                onChange={e => { setDepenseId(e.target.value); setMontant(''); setErreur(''); }}
                options={[
                    { value: '', label: '— choisir une dépense —' },
                    ...(candidates || []).map(c => ({
                        value: String(c.id),
                        label: `${c.date_facture} · ${c.libelle} · ${c.fournisseur || ''} — reste ${c.reste.toFixed(2)} €`,
                    })),
                ]}
            />

            {choisie && (
                <Input
                    label={`Montant imputé (laisser vide pour ${Math.min(choisie.reste, transaction.reste).toFixed(2)} €)`}
                    type="number" step="0.01" placeholder={Math.min(choisie.reste, transaction.reste).toFixed(2)}
                    value={montant} onChange={e => setMontant(e.target.value)}
                />
            )}

            <p className="text-xs text-muted-foreground">
                Seules les dépenses qu'il reste à régler apparaissent. Un montant partiel laisse
                la dépense ouverte pour un second versement.
            </p>

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}

            <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={onClose}>Fermer</Button>
                <Button isLoading={imputer.isPending} onClick={() => depenseId && imputer.mutate()}>
                    Rapprocher
                </Button>
            </div>
        </div>
    );
}
