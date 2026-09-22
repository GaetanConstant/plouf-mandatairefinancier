import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { TYPES_RECETTE } from '../lib/constants';
import { Button, Input, Select } from './ui/Components';
import { API_URL } from '../lib/api';


export function RevenueForm({ onClose }) {
    const queryClient = useQueryClient();
    const [formData, setFormData] = useState({
        date: new Date().toISOString().split('T')[0],
        nom_donateur: '',
        adresse: '',
        montant: '',
        type: TYPES_RECETTE[0].value,
        recu_genere: false
    });
    const [error, setError] = useState(null);

    const createMutation = useMutation({
        mutationFn: async (newRevenue) => {
            await axios.post(`${API_URL}/recettes`, newRevenue);
        },
        onSuccess: () => {
            queryClient.invalidateQueries(['recettes']);
            queryClient.invalidateQueries(['stats']);
            onClose();
        },
        onError: (err) => {
            setError(err.response?.data?.detail || "Une erreur est survenue");
        }
    });

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError(null);

        if (!formData.nom_donateur) {
            setError("Le nom du donateur est requis");
            return;
        }
        if (!formData.montant || Number(formData.montant) <= 0) {
            setError("Montant invalide");
            return;
        }

        createMutation.mutate({
            ...formData,
            montant: Number(formData.montant)
        });
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
                <div className="p-3 text-sm bg-destructive/10 text-destructive rounded-md border border-destructive/20">
                    {error}
                </div>
            )}

            <div className="grid grid-cols-2 gap-4">
                <Input
                    label="Date"
                    type="date"
                    value={formData.date}
                    onChange={e => setFormData({ ...formData, date: e.target.value })}
                    required
                />
                <Select
                    label="Type de recette"
                    options={TYPES_RECETTE}
                    value={formData.type}
                    onChange={e => setFormData({ ...formData, type: e.target.value })}
                />
            </div>

            <Input
                label="Nom du donateur / Organisme"
                placeholder="Prénom Nom"
                value={formData.nom_donateur}
                onChange={e => setFormData({ ...formData, nom_donateur: e.target.value })}
            />

            <Input
                label="Adresse complète"
                placeholder="123 rue de la République, 69100 Villeurbanne"
                value={formData.adresse}
                onChange={e => setFormData({ ...formData, adresse: e.target.value })}
            />

            <Input
                label="Montant (€)"
                type="number"
                step="0.01"
                value={formData.montant}
                onChange={e => setFormData({ ...formData, montant: e.target.value })}
            />

            <div className="flex items-center gap-2 pt-2">
                <input
                    type="checkbox"
                    id="recu"
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
                    checked={formData.recu_genere}
                    onChange={e => setFormData({ ...formData, recu_genere: e.target.checked })}
                />
                <label htmlFor="recu" className="text-sm font-medium leading-none">
                    Reçu-don généré et envoyé
                </label>
            </div>

            <div className="pt-4 flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={onClose}>Annuler</Button>
                <Button type="submit" isLoading={createMutation.isPending}>
                    Enregistrer la recette
                </Button>
            </div>
        </form>
    );
}
