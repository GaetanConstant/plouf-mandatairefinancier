import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Check, FileText, Trash2, Upload } from 'lucide-react';
import { Button, Input, Select } from './ui/Components';
import { cn } from '../lib/utils';
import { API_URL } from '../lib/api';

const nomDuMois = (periode) => new Date(`${periode}-01T12:00:00`)
    .toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' });

const CLES_A_RAFRAICHIR = ['releves-mensuels', 'completude', 'documents', 'identite'];

async function televerser(fichier) {
    const body = new FormData();
    body.append('file', fichier);
    const { data } = await axios.post(`${API_URL}/upload`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data.path;
}


/**
 * Relevés PDF de la banque, un par mois de vie du compte.
 *
 * C'est la pièce justificative de l'enveloppe B. Les imports (CSV, copier-
 * coller) ne servent qu'au rapprochement : trois exports du jour ne font pas
 * trois relevés.
 */
export function RelevesMensuels() {
    const queryClient = useQueryClient();
    const rafraichir = () => CLES_A_RAFRAICHIR.forEach(k => queryClient.invalidateQueries([k]));
    const [erreur, setErreur] = useState('');
    const echoue = (err) => setErreur(err.response?.data?.detail || 'Opération impossible.');

    const { data: etat, isLoading } = useQuery({
        queryKey: ['releves-mensuels'],
        queryFn: async () => (await axios.get(`${API_URL}/releves-mensuels`)).data,
    });

    const deposer = useMutation({
        mutationFn: async ({ fichier, periode }) =>
            axios.post(`${API_URL}/releves-mensuels`, { fichier: await televerser(fichier), periode }),
        onSuccess: () => { rafraichir(); setErreur(''); },
        onError: echoue,
    });
    const dater = useMutation({
        mutationFn: async ({ id, periode }) =>
            axios.put(`${API_URL}/releves-mensuels/${id}/periode`, { periode }),
        onSuccess: () => { rafraichir(); setErreur(''); },
        onError: echoue,
    });
    const retirer = useMutation({
        mutationFn: async (fichier) => axios.delete(`${API_URL}/justificatifs/${encodeURIComponent(fichier)}`),
        onSuccess: rafraichir,
        onError: echoue,
    });

    if (isLoading || !etat) return null;
    const nbAttendus = etat.mois.filter(m => m.attendu).length;

    return (
        <section className="rounded-md border border-border bg-card p-5 space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                    <h3 className="font-semibold">Relevés PDF de la banque</h3>
                    <p className="text-xs text-muted-foreground">
                        Pièce justificative de l'enveloppe B : un relevé par mois, de l'ouverture à la clôture
                        du compte. Les imports ci-dessous ne servent qu'au rapprochement.
                    </p>
                </div>
                {nbAttendus > 0 && (
                    <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-bold uppercase',
                        etat.manquants.length ? 'bg-amber-100 text-amber-700' : 'bg-emerald-100 text-emerald-700')}>
                        {nbAttendus - etat.manquants.length}/{nbAttendus} mois au dossier
                    </span>
                )}
            </div>

            <PeriodeCompte etat={etat} onEnregistre={rafraichir} onErreur={echoue} />

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}

            {etat.mois.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                    Renseignez la date d'ouverture du compte pour savoir quels relevés fournir.
                </p>
            ) : (
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {etat.mois.map(m => (
                        <div key={m.periode}
                            className={cn('rounded-md border px-3 py-2 text-sm',
                                m.documents.length ? 'border-emerald-200 bg-emerald-50/50'
                                    : 'border-amber-200 bg-amber-50/50')}>
                            <div className="flex items-center justify-between gap-2">
                                <span className="font-medium capitalize">{nomDuMois(m.periode)}</span>
                                {m.documents.length ? <Check className="h-4 w-4 text-emerald-600" /> : (
                                    <label className="inline-flex cursor-pointer items-center gap-1 text-xs text-primary hover:underline">
                                        <Upload className="h-3 w-3" /> Déposer le PDF
                                        <input type="file" accept=".pdf,image/*" className="hidden"
                                            onChange={e => e.target.files[0] &&
                                                deposer.mutate({ fichier: e.target.files[0], periode: m.periode })} />
                                    </label>
                                )}
                            </div>
                            {!m.attendu && (
                                <p className="text-[11px] text-muted-foreground">Hors de la période du compte.</p>
                            )}
                            {m.documents.map(d => (
                                <FichierReleve key={d.id} doc={d}
                                    onRetirer={() => window.confirm(`Retirer ${d.fichier} du dossier ?`)
                                        && retirer.mutate(d.fichier)} />
                            ))}
                        </div>
                    ))}
                </div>
            )}
            {deposer.isPending && <p className="text-xs text-muted-foreground">Envoi du relevé…</p>}

            {etat.a_dater.length > 0 && (
                <div className="space-y-2 rounded-md border border-dashed border-border p-3">
                    <p className="text-xs font-medium">
                        Relevés déjà versés, sans mois indiqué : précisez le mois qu'ils couvrent.
                    </p>
                    {etat.a_dater.map(d => (
                        <ADater key={d.id} doc={d} mois={etat.mois.map(m => m.periode)}
                            onDater={periode => dater.mutate({ id: d.id, periode })} />
                    ))}
                </div>
            )}
        </section>
    );
}


function FichierReleve({ doc, onRetirer }) {
    return (
        <div className="mt-1 flex items-center gap-2 text-xs">
            <a href={`${API_URL}/docs/${doc.fichier}`} target="_blank" rel="noopener noreferrer"
                className="flex min-w-0 flex-1 items-center gap-1 text-primary hover:underline">
                <FileText className="h-3 w-3 shrink-0" /> <span className="truncate">{doc.fichier}</span>
            </a>
            <button onClick={onRetirer} title="Retirer ce relevé du dossier"
                className="text-muted-foreground transition-colors hover:text-destructive">
                <Trash2 className="h-3 w-3" />
            </button>
        </div>
    );
}


function ADater({ doc, mois, onDater }) {
    const [periode, setPeriode] = useState(mois[0] ?? '');
    return (
        <div className="flex flex-wrap items-center gap-2 text-xs">
            <a href={`${API_URL}/docs/${doc.fichier}`} target="_blank" rel="noopener noreferrer"
                className="min-w-0 flex-1 truncate text-primary hover:underline">{doc.fichier}</a>
            <div className="w-44">
                <Select value={periode} onChange={e => setPeriode(e.target.value)}
                    options={mois.map(p => ({ value: p, label: nomDuMois(p) }))} />
            </div>
            <Button variant="outline" disabled={!periode} onClick={() => onDater(periode)}>Classer</Button>
        </div>
    );
}


/** Ouverture et clôture du compte : elles fixent les mois dont on attend un relevé. */
function PeriodeCompte({ etat, onEnregistre, onErreur }) {
    const [ouverture, setOuverture] = useState(etat.date_ouverture ?? '');
    const [cloture, setCloture] = useState(etat.date_cloture ?? '');
    const enregistrer = useMutation({
        mutationFn: async () => axios.put(`${API_URL}/releves-mensuels/compte`, {
            date_ouverture: ouverture || null, date_cloture: cloture || null,
        }),
        onSuccess: onEnregistre,
        onError: onErreur,
    });
    const modifie = ouverture !== (etat.date_ouverture ?? '') || cloture !== (etat.date_cloture ?? '');

    return (
        <div className="flex flex-wrap items-end gap-3">
            <div className="w-full sm:w-44">
                <Input label="Compte ouvert le" type="date" value={ouverture}
                    onChange={e => setOuverture(e.target.value)} />
            </div>
            <div className="w-full sm:w-44">
                <Input label="Clôturé le" type="date" value={cloture}
                    onChange={e => setCloture(e.target.value)} />
            </div>
            <Button variant="outline" disabled={!modifie} isLoading={enregistrer.isPending}
                onClick={() => enregistrer.mutate()}>
                Enregistrer
            </Button>
            {etat.ouverture_deduite && !etat.date_ouverture && (
                <p className="w-full text-[11px] text-muted-foreground">
                    Date d'ouverture inconnue : la première ligne importée sert de point de départ.
                </p>
            )}
        </div>
    );
}
