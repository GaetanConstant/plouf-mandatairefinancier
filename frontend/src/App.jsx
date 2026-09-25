
import React, { useState, useEffect, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import {
  LayoutDashboard,
  Wallet,
  Receipt,
  FileText,
  AlertCircle,
  TrendingDown,
  TrendingUp,


  Users,
  Plus,
  LogOut,
  BellRing,
  Inbox,
  Gift,
  Info,
  Menu,
  MessageSquare,
  Settings,
  Shield,
  ShieldCheck,
  FileCheck,
  BookOpen,
  BookText,
  ClipboardList,
  Archive,
  CalendarDays,
  CalendarRange,
  GitCommitHorizontal,
  Flag,
  Users2,
  UsersRound,
  Landmark,
  Droplets,
  ChevronRight,
  ChevronDown,
  Sun,
  Moon
} from 'lucide-react';
import { cn } from './lib/utils'; // Keep this relative import!
import { Modal, Button } from './components/ui/Components';
import { ExpenseForm } from './components/ExpenseForm';

import { RevenueForm } from './components/RevenueForm';
import { DepensesList } from './components/DepensesList';
import { RevenueList } from './components/RevenueList';
import { JustificatifsList } from './components/JustificatifsList';
import { LoginPage } from './pages/LoginPage';
import { SettingsPage } from './pages/SettingsPage';
import { AProposPage } from './pages/AProposPage';
import { CampaignPage } from './pages/CampaignPage';
import { AttestationsPage } from './components/AttestationsPage';
import { CarnetsPage } from './components/CarnetsPage';
import { ConformitePage } from './components/ConformitePage';
import { CalendrierPage } from './components/CalendrierPage';
import { ValidationPage } from './components/ValidationPage';
import { SoumissionsPage } from './components/SoumissionsPage';
import { DemandesPiecesPage } from './components/DemandesPiecesPage';
import { AccesPage } from './components/AccesPage';
import { RelevesPage } from './components/RelevesPage';
import { ConcoursNaturePage } from './components/ConcoursNaturePage';
import { MainCourantePage } from './components/MainCourantePage';
import { IdentitePage } from './components/IdentitePage';
import { DepotPage } from './components/DepotPage';
import { EvenementsPage } from './components/EvenementsPage';
import { FrisePage } from './components/FrisePage';
import { EcheancierPage } from './components/EcheancierPage';
import { MutualisationPage } from './components/MutualisationPage';
import { ListeEquipePage } from './components/ListeEquipePage';
import { EmpruntsPage } from './components/EmpruntsPage';
import { API_URL, surSessionExpiree } from './lib/api';

axios.defaults.withCredentials = true;

const ACCES_ECRAN = {
  identite: ['mandataire'],
  listeequipe: ['mandataire'],
  echeancier: ['mandataire', 'expert_comptable', 'direction'],
  maincourante: ['mandataire', 'expert_comptable', 'direction'],
  releves: ['mandataire', 'expert_comptable'],
  concours: ['mandataire', 'expert_comptable', 'direction'],
  recettes: ['mandataire', 'expert_comptable'],
  depenses: ['mandataire', 'expert_comptable', 'direction'],
  emprunts: ['mandataire'],
  justificatifs: ['mandataire', 'expert_comptable', 'direction'],
  attestations: ['mandataire'],
  carnets: ['mandataire'],
  evenements: ['mandataire', 'expert_comptable', 'direction', 'equipe'],
  frise: ['mandataire', 'expert_comptable', 'direction'],
  calendrier: ['mandataire', 'expert_comptable', 'direction', 'equipe'],
  mutualisation: ['mandataire'],
  conformite: ['mandataire', 'expert_comptable', 'direction'],
  depot: ['mandataire'],
  demandes: ['mandataire', 'expert_comptable'],
  validation: ['mandataire'],
  soumissions: ['mandataire', 'expert_comptable', 'direction', 'equipe'],
  acces: ['mandataire'],
  dashboard: ['mandataire', 'expert_comptable', 'direction'],
  settings: ['mandataire', 'expert_comptable', 'direction', 'equipe'],
  apropos: ['mandataire', 'expert_comptable', 'direction', 'equipe'],
};

// Écran d'arrivée selon le rôle : l'équipe n'a pas de tableau de bord, elle
// atterrirait sur une page vide.
const ongletParDefaut = (role) => (role === 'equipe' ? 'soumissions' : 'dashboard');

const peutVoir = (tab, role) => (ACCES_ECRAN[tab] ?? ['mandataire']).includes(role);

const GROUPES_NAV = [
  { label: 'Administratif', icon: ClipboardList, items: [
    { key: 'identite', label: 'Identité', icon: ClipboardList },
    { key: 'listeequipe', label: 'Liste & équipe', icon: UsersRound },
    { key: 'echeancier', label: 'Échéancier', icon: Flag },
  ]},
  { label: 'Comptabilité', icon: BookText, items: [
    { key: 'maincourante', label: 'Main courante', icon: BookText },
    { key: 'releves', label: 'Relevés bancaires', icon: Landmark },
    { key: 'recettes', label: 'Recettes / Dons', icon: TrendingUp },
    { key: 'depenses', label: 'Dépenses', icon: Receipt },
    { key: 'emprunts', label: 'Emprunts', icon: Landmark },
    { key: 'concours', label: 'Concours en nature', icon: Gift },
    { key: 'justificatifs', label: 'Justificatifs', icon: FileText },
  ]},
  { label: 'Dons & reçus', icon: BookOpen, items: [
    { key: 'attestations', label: 'Attestations', icon: FileCheck },
    { key: 'carnets', label: 'Reçus-dons', icon: BookOpen },
  ]},
  { label: 'Campagne', icon: CalendarDays, items: [
    { key: 'evenements', label: 'Événements', icon: CalendarDays },
    { key: 'frise', label: 'Frise', icon: GitCommitHorizontal },
    { key: 'calendrier', label: 'Calendrier', icon: CalendarRange },
    { key: 'mutualisation', label: 'Mutualisation', icon: Users2 },
  ]},
  { label: 'Conformité & dépôt', icon: ShieldCheck, items: [
    { key: 'conformite', label: 'Conformité', icon: ShieldCheck },
    { key: 'depot', label: 'Dépôt', icon: Archive },
    { key: 'demandes', label: 'Demandes de pièces', icon: MessageSquare },
  ]},
];

const groupeDe = (tab) => GROUPES_NAV.find(g => g.items.some(i => i.key === tab))?.label ?? null;

function App() {
  const queryClient = useQueryClient();

  const [user, setUser] = useState(null);
  const [campaign, setCampaign] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  const [activeTab, setActiveTab] = useState('dashboard');
  const [isExpenseModalOpen, setIsExpenseModalOpen] = useState(false);
  // Cible désignée par une alerte de conformité : l'écran d'arrivée s'en sert
  // pour ouvrir ou surligner la ligne à corriger, puis la consomme.
  const [cible, setCible] = useState(null);
  const consommerCible = useCallback(() => setCible(null), []);

  // Accordéon : un seul groupe ouvert à la fois. Navigation centralisée pour
  // que le groupe suive l'onglet, même quand l'appel vient d'ailleurs.
  const { data: moi } = useQuery({
    queryKey: ['me', campaign?.id],
    queryFn: async () => (await axios.get(`${API_URL}/me`, { withCredentials: true })).data,
    enabled: Boolean(user),
  });
  const roleCampagne = moi?.role_campagne ?? null;
  const estMandataire = roleCampagne === 'mandataire';
  const estExpert = roleCampagne === 'expert_comptable';
  const estEquipe = roleCampagne === 'equipe';
  const estDirection = roleCampagne === 'direction';

  // File d'attente : la pastille du menu et le bandeau du tableau de bord.
  const { data: fileValidation } = useQuery({
    queryKey: ['validation-file', campaign?.id],
    queryFn: async () => (await axios.get(`${API_URL}/validation/file`)).data,
    enabled: Boolean(campaign) && estMandataire,
    refetchInterval: 30000,
  });

  const onglet = peutVoir(activeTab, roleCampagne) ? activeTab : ongletParDefaut(roleCampagne);

  const [groupeOuvert, setGroupeOuvert] = useState(() => groupeDe(activeTab));
  const allerA = useCallback((tab) => {
    setActiveTab(tab);
    setGroupeOuvert(groupeDe(tab));
    setMenuOuvert(false);
  }, []);
  const [menuOuvert, setMenuOuvert] = useState(false);
  const [isRevenueModalOpen, setIsRevenueModalOpen] = useState(false);
  const [prefilledData, setPrefilledData] = useState(null);
  const [isScanning, setIsScanning] = useState(false);

  // Theme management
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('theme') || 'light';
    }
    return 'light';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Session expirée côté serveur : on revient à la connexion plutôt que de
  // laisser chaque écran afficher son propre échec.
  useEffect(() => {
    surSessionExpiree(() => {
      setUser(null);
      setCampaign(null);
      queryClient.clear();
    });
  }, [queryClient]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  // Check auth status on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await axios.get(`${API_URL}/me`, { withCredentials: true });
        setUser(res.data);
      } catch (e) {
        // Not logged in
        setUser(null);
      } finally {
        setAuthLoading(false);
      }
    };
    checkAuth();
  }, []);

  const handleLogout = async () => {
    try {
      await axios.post(`${API_URL}/logout`, {}, { withCredentials: true });
      setUser(null);
    } catch (e) {
      console.error("Logout failed", e);
    }
  };

  const handleScan = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsScanning(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API_URL}/analyze-document`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setPrefilledData({
        ...response.data,
        file: file // pass the file to the form so user doesn't have to select it again
      });
      setIsExpenseModalOpen(true);
    } catch (err) {
      console.error("Scan failed", err);
      alert("Erreur lors de l'analyse du document");
    } finally {
      setIsScanning(false);
      e.target.value = null; // reset input
    }
  };


  const { data: completude } = useQuery({
    queryKey: ['completude'],
    queryFn: async () => (await axios.get(`${API_URL}/identite/completude`)).data,
    enabled: Boolean(campaign) && peutVoir('dashboard', roleCampagne),
  });

  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery({
    queryKey: ['stats', campaign?.id],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/stats`);
      return response.data;
    },
    refetchInterval: 5000,
    enabled: !!user && !!campaign && peutVoir('dashboard', roleCampagne),
  });

  const { data: depenses } = useQuery({
    queryKey: ['depenses', campaign?.id],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/depenses`);
      return response.data;
    },
    enabled: !!user && !!campaign && peutVoir('depenses', roleCampagne),
  });

  const { data: recettes } = useQuery({
    queryKey: ['recettes', campaign?.id],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/recettes`);
      return response.data;
    },
    enabled: !!user && !!campaign && peutVoir('recettes', roleCampagne),
  });

  if (authLoading) {
    return <div className="flex items-center justify-center h-screen bg-background text-foreground">Chargement...</div>;
  }

  if (!user) {
    return <LoginPage onLogin={(u) => { setUser(u); setCampaign(null); setActiveTab('dashboard'); }} />;
  }

  if (!campaign) {
    return <CampaignPage onSelect={setCampaign} user={user} />;
  }

  // Ce voile ne couvre que le tableau de bord : les autres écrans gèrent leur
  // propre chargement, et un rôle sans accès aux chiffres ne doit pas rester
  // bloqué derrière des données qu'il n'aura jamais.
  if (onglet === 'dashboard' && statsLoading && !stats && !statsError) {
    return <div className="flex items-center justify-center h-screen bg-background text-foreground">Chargement des données...</div>;
  }

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <Modal
        isOpen={isExpenseModalOpen}
        onClose={() => { setIsExpenseModalOpen(false); setPrefilledData(null); }}
        title={prefilledData ? "Nouvelle Dépense (Pré-remplie)" : "Nouvelle Dépense"}
      >
        <ExpenseForm
          onClose={() => { setIsExpenseModalOpen(false); setPrefilledData(null); }}
          prefilledData={prefilledData}
        />
      </Modal>

      <Modal
        isOpen={isRevenueModalOpen}
        onClose={() => setIsRevenueModalOpen(false)}
        title="Nouveau Don / Recette"
      >
        <RevenueForm onClose={() => setIsRevenueModalOpen(false)} />
      </Modal>

      <div className="flex h-screen overflow-hidden">
        {/* Voile du tiroir : ferme le menu au clic hors de lui. */}
        {menuOuvert && (
          <button
            type="button"
            aria-label="Fermer le menu"
            onClick={() => setMenuOuvert(false)}
            className="fixed inset-0 z-30 bg-black/40 md:hidden"
          />
        )}
        {/* Sidebar */}
        <aside className={cn(
          "w-64 shrink-0 border-r border-border p-4 flex flex-col bg-card",
          // Hors mobile : colonne fixe. Sur mobile : tiroir glissant au-dessus.
          "max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-40 max-md:transition-transform",
          menuOuvert ? "max-md:translate-x-0" : "max-md:-translate-x-full",
        )}>
          <div className="mb-3 flex items-center gap-2">
            <Droplets className="w-8 h-8 text-primary" />
            <div className="flex flex-col">
              <span className="font-bold text-xl tracking-tight leading-none">Plouf</span>
              <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">{campaign.name}</span>
            </div>
          </div>


          <nav className="flex-1 space-y-0.5 overflow-y-auto -mr-3 pr-3">
            {peutVoir('dashboard', roleCampagne) && (
              <NavItem icon={LayoutDashboard} label="Tableau de bord" active={onglet === 'dashboard'} onClick={() => allerA('dashboard')} />
            )}

            {estMandataire && (
              <NavItem icon={BellRing} label="À valider" active={onglet === 'validation'}
                onClick={() => allerA('validation')} badge={fileValidation?.total || 0} />
            )}

            {(estExpert || estEquipe || estDirection) && (
              <NavItem icon={Inbox} label="Mes soumissions" active={onglet === 'soumissions'}
                onClick={() => allerA('soumissions')} />
            )}

            {GROUPES_NAV.map(g => ({ ...g, items: g.items.filter(i => peutVoir(i.key, roleCampagne)) }))
              .filter(g => g.items.length > 0)
              .map(g => (
                <NavGroup key={g.label} icon={g.icon} label={g.label} items={g.items}
                  activeTab={onglet} setActiveTab={allerA}
                  open={groupeOuvert === g.label}
                  onToggle={() => setGroupeOuvert(groupeOuvert === g.label ? null : g.label)} />
              ))}

          </nav>

          <div className="mt-auto space-y-0.5 rounded-lg bg-muted/50 p-2">
            <div className="mb-1 flex items-center gap-2 px-1 text-sm font-medium text-foreground">
              <Users className="h-4 w-4 shrink-0" />
              <span className="truncate">{user.full_name}</span>
            </div>

            <div>
              {estMandataire && (
                <button
                  onClick={() => allerA('acces')}
                  className={cn("w-full flex items-center gap-2 px-3 py-0.5 text-xs font-medium transition-colors",
                    onglet === 'acces' ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
                >
                  <Users className="w-3 h-3" /> Accès à la campagne
                </button>
              )}
              <button
                onClick={() => allerA('settings')}
                className={cn("w-full flex items-center gap-2 px-3 py-0.5 text-xs font-medium transition-colors",
                  onglet === 'settings' ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                <Settings className="w-3 h-3" /> Paramètres
              </button>
              <button
                onClick={() => allerA('apropos')}
                className={cn("w-full flex items-center gap-2 px-3 py-0.5 text-xs font-medium transition-colors",
                  onglet === 'apropos' ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                <Info className="w-3 h-3" /> À propos
              </button>
            </div>
            <button
              onClick={toggleTheme}
              className="w-full flex items-center gap-2 px-3 py-0.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {theme === 'light' ? <Moon className="w-3 h-3" /> : <Sun className="w-3 h-3" />}
              {theme === 'light' ? 'Mode Sombre' : 'Mode Clair'}
            </button>


            <button
              onClick={() => setCampaign(null)}
              className="w-full flex items-center gap-2 px-3 py-0.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors mb-2"
            >
              <ChevronRight className="w-3 h-3 rotate-180" /> Changer de campagne
            </button>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-1 text-xs font-medium text-destructive hover:bg-destructive/10 rounded-md transition-colors"
            >
              <LogOut className="w-3 h-3" /> Se déconnecter
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          {/* Barre mobile : ouvre le tiroir, la navigation étant hors écran. */}
          <div className="mb-4 flex items-center gap-3 md:hidden">
            <button
              type="button"
              onClick={() => setMenuOuvert(true)}
              aria-label="Ouvrir le menu"
              className="rounded-md border border-border p-2 text-muted-foreground transition-colors hover:text-foreground"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="truncate text-sm font-semibold">{campaign?.name}</span>
            {estMandataire && fileValidation?.total > 0 && (
              <span className="ml-auto rounded-full bg-red-500 px-2 py-0.5 text-[11px] font-bold text-white">
                {fileValidation.total}
              </span>
            )}
          </div>
          {onglet === 'dashboard' && statsError && (
            <div className="rounded-xl border border-red-300 bg-red-50/60 p-6">
              <h2 className="font-bold text-red-700">Les chiffres du compte n'ont pas pu être chargés.</h2>
              <p className="mt-1 text-sm text-red-700/80">
                {statsError.response?.status === 400
                  ? "Aucune campagne n'est sélectionnée. Repassez par « Changer de campagne »."
                  : statsError.response?.data?.detail || statsError.message}
              </p>
            </div>
          )}

          {onglet === 'dashboard' && stats && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

              <header className="mb-8 flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight md:text-3xl">Vue d'ensemble</h1>
                  <p className="text-muted-foreground">Suivi en temps réel de la consommation du plafond.</p>
                </div>
                {estMandataire && (
                  <div className="flex w-full flex-wrap gap-3 sm:w-auto sm:gap-4">
                    <Button onClick={() => setIsExpenseModalOpen(true)} className="gap-2">
                      <Plus className="w-4 h-4" /> Nouvelle Dépense
                    </Button>

                    <Button variant="secondary" onClick={() => setIsRevenueModalOpen(true)} className="gap-2">
                      <Plus className="w-4 h-4" /> Nouveau Don
                    </Button>

                    <input
                      type="file"
                      id="scan-input"
                      className="hidden"
                      accept=".pdf,.png,.jpg,.jpeg"
                      onChange={handleScan}
                    />
                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => document.getElementById('scan-input').click()}
                      isLoading={isScanning}
                    >
                      <FileText className="w-4 h-4" /> Scanner Justificatif
                    </Button>

                    <a href={`${API_URL}/export`} target="_blank" rel="noopener noreferrer">
                      <Button variant="outline" className="gap-2 border-primary/20 text-primary hover:bg-primary/5">
                        <FileText className="w-4 h-4" /> Exporter
                      </Button>
                    </a>
                  </div>
                )}
              </header>



              {/* Ce qui attend un arbitrage passe avant tout le reste. */}
              {estMandataire && fileValidation?.total > 0 && (
                <button
                  type="button"
                  onClick={() => allerA('validation')}
                  className="w-full rounded-xl border border-amber-300 bg-amber-50/60 p-4 text-left transition-colors hover:bg-amber-50"
                >
                  <span className="font-semibold text-amber-800">
                    {fileValidation.total} élément{fileValidation.total > 1 ? 's' : ''} en attente de votre validation
                  </span>
                  <p className="mt-1 text-xs text-amber-800/80">
                    {fileValidation.nb_elements} dépôt{fileValidation.nb_elements > 1 ? 's' : ''} de l'équipe ou de
                    l'expert-comptable
                    {fileValidation.nb_demandes_pieces > 0 && `, ${fileValidation.nb_demandes_pieces} demande(s) de pièces`}.
                    Rien n'entre dans le compte avant arbitrage.
                  </p>
                </button>
              )}

              {/* Complétude du dossier : ce qui bloque le dépôt, avant les chiffres. */}
              {completude && !completude.complet && (
                <button
                  type="button"
                  onClick={() => allerA('identite')}
                  className="w-full rounded-xl border border-red-300 bg-red-50/60 p-4 text-left transition-colors hover:bg-red-50"
                >
                  <div className="flex items-center justify-between gap-4">
                    <span className="font-semibold text-red-700">
                      Dossier de dépôt incomplet — {completude.manquants.length} élément
                      {completude.manquants.length > 1 ? 's' : ''} à renseigner
                    </span>
                    <span className="text-xl font-black text-red-600">{completude.pct}%</span>
                  </div>
                  <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-secondary">
                    <div className="h-full bg-red-500 transition-all duration-700" style={{ width: `${completude.pct}%` }} />
                  </div>
                  <p className="mt-2 text-xs text-red-700/80">
                    {completude.manquants.slice(0, 3).join(' · ')}
                    {completude.manquants.length > 3 && ` · +${completude.manquants.length - 3} autres`}
                  </p>
                </button>
              )}

              {/* Stats Cards */}
              <div className="grid gap-4 md:grid-cols-1 lg:grid-cols-2 xl:grid-cols-3">
                <Card title="Recettes Totales" value={`${stats.total_recettes.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`} icon={TrendingUp} description={`${stats.nombre_donateurs} donateurs`} className="border-l-4 border-l-green-500" />
                <Card title="Dépenses Payées" value={`${stats.total_depenses_payees.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`} icon={TrendingDown} description={`Dépenses réelles décaissées`} className="border-l-4 border-l-orange-500" />
                <Card title="Concours en Nature" value={`${stats.total_nature_hors_tresorerie.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`} icon={Shield} description="Inclus dans le plafond (Gratuité)" className="border-l-4 border-l-purple-400" />
                <Card title="Solde Trésorerie" value={`${stats.solde_tresorerie.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`} icon={Wallet} description="Reliquat actuel en banque" className={cn("border-l-4", stats.solde_tresorerie < 0 ? "border-l-red-600" : "border-l-blue-500")} />
                <Card title="Solde Prévisionnel" value={`${stats.solde_previsionnel?.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`} icon={AlertCircle} description="Reliquat final après paiements" className={cn("border-l-4", stats.solde_previsionnel < 0 ? "border-l-red-500" : "border-l-purple-500")} />
                <Card title="Marge Plafond Légal" value={`${stats.reste_a_depenser.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}`} icon={Shield} description={`Plafond restant (incluant nature)`} className={cn("border-l-4", stats.reste_a_depenser < 10000 ? "border-l-red-500" : "border-l-gray-500")} />
              </div>

              {/* Progress Bars - Split View */}
              <div className="grid gap-6 md:grid-cols-2">
                {/* Plafond Légal */}
                <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold text-lg">Consommation Plafond Légal</h3>
                    <span className="text-sm font-medium text-muted-foreground">{stats.consommation_plafond.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-secondary h-4 rounded-full overflow-hidden">
                    <div
                      className={cn("h-full transition-all duration-1000 ease-out",
                        stats.consommation_plafond > 90 ? "bg-red-500" :
                          stats.consommation_plafond > 75 ? "bg-orange-500" : "bg-primary"
                      )}
                      style={{ width: `${Math.min(stats.consommation_plafond, 100)}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">Limite légale absolue ({stats.plafond.toLocaleString('fr-FR')} €, propre à cette élection). Ne jamais dépasser 100%.</p>
                </div>

                {/* Budget Réel/Trésorerie */}
                <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
                  <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                    <h3 className="font-semibold text-lg">Consommation Budget Réel</h3>
                    <span className="text-sm font-medium text-muted-foreground">{stats.consommation_budget_actuel ? stats.consommation_budget_actuel.toFixed(1) : '0'}%</span>
                  </div>
                  <div className="w-full bg-secondary h-4 rounded-full overflow-hidden">
                    <div
                      className={cn("h-full transition-all duration-1000 ease-out",
                        stats.consommation_budget_actuel > 100 ? "bg-red-600" :
                          stats.consommation_budget_actuel > 90 ? "bg-orange-500" : "bg-green-500"
                      )}
                      style={{ width: `${Math.min(stats.consommation_budget_actuel || 0, 100)}%` }}
                    />
                  </div>
                  <p className="mt-2 text-xs text-muted-foreground">Dépenses engagées vs Recettes encaissées. Si &gt; 100%, le compte est à découvert.</p>
                </div>
              </div>

              {/* Recent Activity */}
              <div className="grid gap-8 md:grid-cols-2">
                <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
                  <h3 className="font-semibold text-lg mb-4">Dernières Dépenses</h3>
                  {depenses && depenses.slice(0, 5).map((d, i) => (
                    <div key={i} className="flex justify-between items-center py-3 border-b border-border last:border-0 hover:bg-muted/50 px-2 rounded-md transition-colors cursor-default">
                      <div>
                        <p className="font-medium text-sm">{d.libelle}</p>
                        <p className="text-xs text-muted-foreground">{d.date} • {d.fournisseur}</p>
                      </div>
                      <span className={cn("font-semibold text-sm", d.is_nature ? "text-purple-600" : "text-orange-600")}>
                        {d.is_nature ? "" : "- "} {d.montant_ttc.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </span>
                    </div>
                  ))}
                  {!depenses?.length && <p className="text-muted-foreground text-sm italic">Aucune dépense enregistrée.</p>}
                </div>

                <div className="bg-card rounded-xl border border-border p-6 shadow-sm">
                  <h3 className="font-semibold text-lg mb-4">Derniers Dons</h3>
                  {recettes && recettes.slice(0, 5).map((r, i) => (
                    <div key={i} className="flex justify-between items-center py-3 border-b border-border last:border-0 hover:bg-muted/50 px-2 rounded-md transition-colors cursor-default">
                      <div>
                        <p className="font-medium text-sm">{r.nom_donateur}</p>
                        <p className="text-xs text-muted-foreground">{r.date}</p>
                      </div>
                      <span className="font-semibold text-sm text-green-600">
                        + {r.montant.toLocaleString('fr-FR', { style: 'currency', currency: 'EUR' })}
                      </span>
                    </div>
                  ))}
                  {!recettes?.length && <p className="text-muted-foreground text-sm italic">Aucune recette enregistrée.</p>}
                </div>
              </div>
            </div>
          )}

          {onglet === 'depenses' && peutVoir('depenses', roleCampagne) && (
            <DepensesList cible={cible?.entite === 'depense' ? cible.id : null}
              onCibleConsommee={consommerCible} role={roleCampagne} />
          )}
          {onglet === 'recettes' && peutVoir('recettes', roleCampagne) && (
            <RevenueList cible={cible?.entite === 'recette' ? cible.id : null}
              onCibleConsommee={consommerCible} />
          )}
          {onglet === 'justificatifs' && peutVoir('justificatifs', roleCampagne) && <JustificatifsList />}
          {onglet === 'attestations' && peutVoir('attestations', roleCampagne) && <AttestationsPage campaignId={campaign.id} />}
          {onglet === 'carnets' && peutVoir('carnets', roleCampagne) && <CarnetsPage />}
          {onglet === 'conformite' && peutVoir('conformite', roleCampagne) && (
            <ConformitePage onNavigate={(tab, c) => { setCible(c); allerA(tab); }} />
          )}
          {onglet === 'maincourante' && peutVoir('maincourante', roleCampagne) && <MainCourantePage />}
          {onglet === 'identite' && peutVoir('identite', roleCampagne) && (
            <IdentitePage cible={cible?.entite} onCibleConsommee={consommerCible} />
          )}
          {onglet === 'depot' && peutVoir('depot', roleCampagne) && <DepotPage />}
          {onglet === 'evenements' && peutVoir('evenements', roleCampagne) && <EvenementsPage />}
          {onglet === 'frise' && peutVoir('frise', roleCampagne) && <FrisePage />}
          {onglet === 'calendrier' && peutVoir('calendrier', roleCampagne) && <CalendrierPage />}
          {onglet === 'echeancier' && peutVoir('echeancier', roleCampagne) && <EcheancierPage />}
          {onglet === 'mutualisation' && peutVoir('mutualisation', roleCampagne) && <MutualisationPage />}
          {onglet === 'listeequipe' && peutVoir('listeequipe', roleCampagne) && <ListeEquipePage />}
          {onglet === 'emprunts' && peutVoir('emprunts', roleCampagne) && <EmpruntsPage />}

          {onglet === 'settings' && <SettingsPage currentUser={user} />}
          {onglet === 'apropos' && <AProposPage />}
          {onglet === 'validation' && peutVoir('validation', roleCampagne) && <ValidationPage />}
          {onglet === 'soumissions' && peutVoir('soumissions', roleCampagne) && <SoumissionsPage />}
          {onglet === 'demandes' && peutVoir('demandes', roleCampagne) && <DemandesPiecesPage />}
          {onglet === 'releves' && peutVoir('releves', roleCampagne) && <RelevesPage />}
          {onglet === 'concours' && peutVoir('concours', roleCampagne) && <ConcoursNaturePage />}
          {onglet === 'acces' && peutVoir('acces', roleCampagne) && (
            <AccesPage campaignId={campaign?.id} moi={moi} />
          )}
        </main>

      </div>
    </div >
  );
}

function NavGroup({ icon: Icon, label, items, activeTab, setActiveTab, open, onToggle }) {
  const hasActive = items.some(i => i.key === activeTab);
  return (
    <div>
      <button
        onClick={onToggle}
        className={cn(
          // Typo resserrée : « Conformité & dépôt » doit tenir sur une ligne dans
          // une barre de 256 px, sinon le libellé se coupe ou passe à la ligne.
          "w-full flex items-center justify-between gap-1 rounded-md px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide transition-colors",
          hasActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
        )}
      >
        <span className="flex min-w-0 items-center gap-2 text-left leading-tight">
          <Icon className="w-4 h-4 shrink-0" />
          <span className="truncate whitespace-nowrap">{label}</span>
        </span>
        <ChevronDown className={cn("w-4 h-4 shrink-0 transition-transform duration-200", open ? "" : "-rotate-90")} />
      </button>
      {open && (
        <div className="mt-1 ml-2 pl-2 border-l border-border space-y-1">
          {items.map(it => (
            <NavItem key={it.key} icon={it.icon} label={it.label} active={activeTab === it.key} onClick={() => setActiveTab(it.key)} />
          ))}
        </div>
      )}
    </div>
  );
}

function NavItem({ icon: Icon, label, active, onClick, badge = 0 }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 rounded-md px-4 py-1.5 text-sm font-medium transition-all duration-200",
        active
          ? "bg-primary/10 text-primary shadow-sm"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      <Icon className="w-5 h-5" />
      <span className="flex-1 text-left">{label}</span>
      {badge > 0 && (
        <span className="rounded-full bg-red-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
          {badge}
        </span>
      )}
    </button>
  );
}

function Card({ title, value, icon: Icon, description, className }) {
  return (
    <div className={cn("bg-card rounded-xl border border-border p-6 shadow-sm hover:shadow-md transition-shadow", className)}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
        <div className="p-2 bg-muted rounded-full">
          <Icon className="w-4 h-4 text-primary" />
        </div>
      </div>
      <div className="text-2xl font-bold tracking-tight">{value}</div>
      <p className="text-xs text-muted-foreground mt-1">{description}</p>
    </div>
  );
}

export default App;
