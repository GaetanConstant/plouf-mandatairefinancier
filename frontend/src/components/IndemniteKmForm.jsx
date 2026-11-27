import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Button, Input, Select } from './ui/Components';
import { API_URL, messageErreur } from '../lib/api';

const eur = (v) => (v ?? 0).toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' });

/**
 * Saisie d'un trajet en voiture personnelle.
 *
 * Le serveur crée la dépense D1 avancée par la personne et génère son
 * justificatif : l'état de frais kilométriques, carte grise en annexe. Le
 * montant affiché ici n'est qu'un aperçu, le serveur refait le calcul.
 */
export function IndemniteKmForm({ onClose, beneficiaire = '' }) {
    const queryClient = useQueryClient();
    const [erreur, setErreur] = useState('');
    const [carteGrise, setCarteGrise] = useState(null);
    const [f, setF] = useState({
        beneficiaire, qualite: '', adresse: '',
        vehicule: '', immatriculation: '', puissance_cv: 4, electrique: false,
        date: new Date().toISOString().split('T')[0],
        depart: '', arrivee: '', aller_retour: true, km_aller: '',
        objet: '', evenement_id: '', visa_mandataire: true,
    });
    const maj = (champ) => (e) => setF({
        ...f, [champ]: e.target.type === 'checkbox' ? e.target.checked : e.target.value,
    });

    const { data: bareme } = useQuery({
        queryKey: ['bareme-km'],
        queryFn: async () => (await axios.get(`${API_URL}/indemnites-km/bareme`)).data,
    });
    const { data: evenements } = useQuery({
        queryKey: ['evenements'],
        queryFn: async () => (await axios.get(`${API_URL}/evenements`)).data,
    });

    const taux = (bareme || []).find(b => b.puissance_cv === Math.min(Math.max(Number(f.puissance_cv), 3), 7))?.taux;
    const kmTotal = (Number(f.km_aller) || 0) * (f.aller_retour ? 2 : 1);
    const apercu = taux ? kmTotal * taux * (f.electrique ? 1.2 : 1) : null;

    const enregistrer = useMutation({
        mutationFn: async () => {
            let carte_grise_path = null;
            if (carteGrise) {
                const body = new FormData();
                body.append('file', carteGrise);
                carte_grise_path = (await axios.post(`${API_URL}/upload`, body, {
                    headers: { 'Content-Type': 'multipart/form-data' },
                })).data.path;
            }
            return (await axios.post(`${API_URL}/indemnites-km`, {
                ...f,
                puissance_cv: Number(f.puissance_cv),
                km_aller: Number(f.km_aller),
                evenement_id: f.evenement_id ? Number(f.evenement_id) : null,
                carte_grise_path,
            })).data;
        },
        onSuccess: () => {
            ['notes-frais', 'avances', 'depenses', 'completude', 'stats']
                .forEach(k => queryClient.invalidateQueries([k]));
            onClose();
        },
        onError: (err) => setErreur(messageErreur(err)),
    });

    const soumettre = (e) => {
        e.preventDefault();
        setErreur('');
        enregistrer.mutate();
    };

    return (
        <form onSubmit={soumettre} className="space-y-4">
            <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Bénéficiaire" value={f.beneficiaire} onChange={maj('beneficiaire')} required
                    placeholder="Ex : Gabriel AMARD" />
                <Input label="Qualité" value={f.qualite} onChange={maj('qualite')}
                    placeholder="Ex : candidat, membre de l'équipe" />
            </fieldset>
            <Input label="Adresse du bénéficiaire" value={f.adresse} onChange={maj('adresse')} />

            <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                <Input label="Véhicule" value={f.vehicule} onChange={maj('vehicule')} required
                    placeholder="Ex : Fiat 500" />
                <Input label="Immatriculation" value={f.immatriculation} onChange={maj('immatriculation')} required
                    placeholder="AA-123-BB" />
                <Select label="Puissance fiscale" value={f.puissance_cv} onChange={maj('puissance_cv')}
                    options={(bareme || []).map(b => ({ value: b.puissance_cv, label: b.libelle }))} />
            </fieldset>
            <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={f.electrique} onChange={maj('electrique')} />
                Véhicule 100 % électrique (barème majoré de 20 %)
            </label>

            <fieldset className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <Input label="Date" type="date" value={f.date} onChange={maj('date')} required />
                <Select label="Événement" value={f.evenement_id} onChange={maj('evenement_id')}
                    options={[{ value: '', label: '— Aucun —' },
                        ...(evenements || []).map(ev => ({ value: ev.id, label: ev.titre }))]} />
                <Input label="Lieu de départ" value={f.depart} onChange={maj('depart')} required />
                <Input label="Lieu d'arrivée" value={f.arrivee} onChange={maj('arrivee')} required />
                <Input label="Distance aller (km)" type="number" step="0.1" min="0.1"
                    value={f.km_aller} onChange={maj('km_aller')} required />
                <label className="flex items-center gap-2 self-end pb-2 text-sm">
                    <input type="checkbox" checked={f.aller_retour} onChange={maj('aller_retour')} />
                    Aller-retour
                </label>
            </fieldset>
            <Input label="Objet du déplacement" value={f.objet} onChange={maj('objet')} required
                placeholder="Ex : réunion publique de campagne à L'Arbresle" />

            <div className="space-y-2">
                <label className="text-sm font-medium">Carte grise (jointe en annexe)</label>
                <input type="file" accept="image/*,application/pdf" className="block text-sm"
                    onChange={e => setCarteGrise(e.target.files[0] || null)} />
            </div>
            <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={f.visa_mandataire} onChange={maj('visa_mandataire')} />
                Cases de signature et visa du mandataire sur le justificatif
            </label>

            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-muted/40 px-4 py-3 text-sm">
                <span className="text-muted-foreground">
                    {kmTotal ? `${kmTotal.toLocaleString('fr-FR')} km × ${taux?.toLocaleString('fr-FR')} €${f.electrique ? ' × 1,2' : ''}` : 'Distance à saisir'}
                </span>
                <span className="font-bold tabular-nums">{apercu !== null ? eur(Math.round(apercu * 100) / 100) : '—'}</span>
            </div>

            {erreur && <p className="text-sm text-destructive">{erreur}</p>}
            <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={onClose}>Annuler</Button>
                <Button type="submit" isLoading={enregistrer.isPending}>Créer la dépense et le justificatif</Button>
            </div>
        </form>
    );
}
