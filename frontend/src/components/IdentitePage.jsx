import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Save, User, Briefcase, Landmark, Calculator, Vote } from 'lucide-react';
import { Button, Input, Select } from './ui/Components';
import { API_URL } from '../lib/api';


const TYPES_ELECTION = ['municipale', 'metropole', 'secteur', 'legislative', 'departementale', 'regionale', 'europeenne', 'autre']
    .map(v => ({ value: v, label: v.charAt(0).toUpperCase() + v.slice(1) }));

const SECTIONS = [
    {
        key: 'election', endpoint: 'election', title: 'Élection', icon: Vote,
        fields: [
            { key: 'type', label: 'Type de scrutin', type: 'select', options: TYPES_ELECTION },
            { key: 'libelle', label: 'Libellé' },
            { key: 'circonscription', label: 'Circonscription' },
            { key: 'population', label: 'Population', type: 'number' },
            { key: 'nom_liste', label: 'Nom de la liste' },
            { key: 'nuance_politique', label: 'Nuance politique / Parti' },
            { key: 'date_tour1', label: '1er tour', type: 'date' },
            { key: 'date_tour2', label: '2e tour', type: 'date' },
            { key: 'plafond_depenses', label: 'Plafond de dépenses (€)', type: 'number' },
            { key: 'date_depot_surcharge', label: 'Date de dépôt officielle (surcharge)', type: 'date' },
        ],
        readonly: [
            { key: 'date_limite_depot', label: 'Date limite de dépôt (calculée)' },
            { key: 'date_cloture_compte', label: 'Clôture du compte (calculée)' },
        ],
    },
    {
        key: 'candidat', endpoint: 'candidat', title: 'Candidat', icon: User,
        fields: [
            { key: 'civilite', label: 'Civilité' },
            { key: 'nom', label: 'Nom' },
            { key: 'nom_usage', label: "Nom d'usage" },
            { key: 'prenom', label: 'Prénom' },
            { key: 'date_naissance', label: 'Date de naissance', type: 'date' },
            { key: 'lieu_naissance', label: 'Lieu de naissance' },
            { key: 'mandat_parlementaire', label: 'Mandat parlementaire' },
            { key: 'tete_de_liste', label: 'Tête de liste', type: 'checkbox' },
            { key: 'adresse_postale', label: 'Adresse postale' },
            { key: 'code_postal', label: 'Code postal' },
            { key: 'ville', label: 'Ville' },
            { key: 'email', label: 'Email' },
            { key: 'tel', label: 'Téléphone' },
            { key: 'adresse_post_campagne', label: 'Adresse joignable après le scrutin' },
            { key: 'remplacant_identite', label: 'Identité du remplaçant (législatives)' },
        ],
    },
    {
        key: 'mandataire', endpoint: 'mandataire', title: 'Mandataire', icon: Briefcase,
        fields: [
            { key: 'type', label: 'Type', type: 'select', options: [{ value: 'physique', label: 'Personne physique' }, { value: 'afe', label: 'Association de financement' }] },
            { key: 'civilite', label: 'Civilité' },
            { key: 'nom', label: 'Nom' },
            { key: 'prenom', label: 'Prénom' },
            { key: 'date_naissance', label: 'Date de naissance', type: 'date' },
            { key: 'adresse_postale', label: 'Adresse postale' },
            { key: 'code_postal', label: 'Code postal' },
            { key: 'ville', label: 'Ville' },
            { key: 'email', label: 'Email' },
            { key: 'tel', label: 'Téléphone' },
            { key: 'date_declaration_prefecture', label: 'Date de déclaration en préfecture', type: 'date' },
            { key: 'prefecture', label: 'Préfecture' },
            { key: 'incompatibilites_verifiees', label: 'Incompatibilités vérifiées', type: 'checkbox' },
            { key: 'capacite_civile_ok', label: 'Capacité civile OK', type: 'checkbox' },
            { key: 'interdiction_bancaire', label: 'Interdiction bancaire', type: 'checkbox' },
        ],
    },
    {
        key: 'expert_comptable', endpoint: 'expert-comptable', title: 'Expert-comptable', icon: Calculator,
        fields: [
            { key: 'dispense', label: 'Compte dispensé d\'expert-comptable', type: 'checkbox' },
            { key: 'cabinet', label: 'Cabinet' },
            { key: 'nom', label: 'Nom' },
            { key: 'prenom', label: 'Prénom' },
            { key: 'adresse_postale', label: 'Adresse postale' },
            { key: 'email', label: 'Email' },
            { key: 'tel', label: 'Téléphone' },
            { key: 'date_designation', label: 'Date de désignation', type: 'date' },
            { key: 'mission_etendue', label: 'Mission étendue (conseil)', type: 'checkbox' },
        ],
    },
    {
        key: 'compte_bancaire', endpoint: 'compte-bancaire', title: 'Compte bancaire dédié', icon: Landmark,
        fields: [
            { key: 'banque', label: 'Banque' },
            { key: 'libelle', label: 'Libellé du compte' },
            { key: 'iban', label: 'IBAN' },
            { key: 'date_ouverture', label: 'Date d\'ouverture', type: 'date' },
            { key: 'date_cloture', label: 'Date de clôture', type: 'date' },
            { key: 'droit_au_compte_active', label: 'Droit au compte activé', type: 'checkbox' },
        ],
    },
];

export function IdentitePage() {
    const { data, isLoading } = useQuery({
        queryKey: ['identite'],
        queryFn: async () => (await axios.get(`${API_URL}/identite`)).data,
    });

    if (isLoading) return <div>Chargement de l'identité...</div>;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            <header>
                <h1 className="text-3xl font-bold tracking-tight">Identité administrative</h1>
                <p className="text-muted-foreground">Socle à compléter en premier : il alimente la checklist de conformité et le dépôt.</p>
            </header>
            {SECTIONS.map(section => (
                <IdentitySection key={section.key} section={section} initial={data?.[section.key] || {}} />
            ))}
        </div>
    );
}

function IdentitySection({ section, initial }) {
    const queryClient = useQueryClient();
    const [form, setForm] = useState({});
    const [saved, setSaved] = useState(false);

    useEffect(() => { setForm(initial || {}); }, [JSON.stringify(initial)]);

    const mutation = useMutation({
        mutationFn: async (payload) => axios.put(`${API_URL}/identite/${section.endpoint}`, payload),
        onSuccess: () => {
            queryClient.invalidateQueries(['identite']);
            queryClient.invalidateQueries(['conformite']);
            setSaved(true);
            setTimeout(() => setSaved(false), 2000);
        },
    });

    const handleSave = () => {
        const payload = {};
        section.fields.forEach(f => {
            let v = form[f.key];
            if (f.type === 'number') v = v === '' || v === null || v === undefined ? null : Number(v);
            payload[f.key] = v ?? null;
        });
        mutation.mutate(payload);
    };

    const Icon = section.icon;

    return (
        <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
            <div className="flex items-center gap-2 mb-4">
                <Icon className="w-5 h-5 text-primary" />
                <h2 className="font-bold text-lg">{section.title}</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {section.fields.map(f => (
                    <div key={f.key}>
                        {f.type === 'checkbox' ? (
                            <label className="flex items-center gap-2 cursor-pointer pt-6">
                                <input type="checkbox" className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                                    checked={!!form[f.key]}
                                    onChange={e => setForm({ ...form, [f.key]: e.target.checked })} />
                                <span className="text-sm font-medium">{f.label}</span>
                            </label>
                        ) : f.type === 'select' ? (
                            <Select label={f.label} options={f.options} value={form[f.key] || ''}
                                onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
                        ) : (
                            <Input label={f.label} type={f.type || 'text'} value={form[f.key] ?? ''}
                                onChange={e => setForm({ ...form, [f.key]: e.target.value })} />
                        )}
                    </div>
                ))}
                {section.readonly?.map(f => (
                    <div key={f.key}>
                        <label className="text-sm font-medium leading-none mb-1.5 block text-muted-foreground">{f.label}</label>
                        <div className="h-10 flex items-center px-3 rounded-md border border-dashed border-border bg-muted/30 text-sm">
                            {initial?.[f.key] || '—'}
                        </div>
                    </div>
                ))}
            </div>
            <div className="flex justify-end mt-4">
                <Button onClick={handleSave} isLoading={mutation.isPending} className="gap-2">
                    <Save className="w-4 h-4" /> {saved ? 'Enregistré ✓' : 'Enregistrer'}
                </Button>
            </div>
        </div>
    );
}
