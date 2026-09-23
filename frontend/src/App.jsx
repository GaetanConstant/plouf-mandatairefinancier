
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
  Info,
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
import { MainCourantePage } from './components/MainCourantePage';
import { IdentitePage } from './components/IdentitePage';
import { DepotPage } from './components/DepotPage';
import { EvenementsPage } from './components/EvenementsPage';
import { FrisePage } from './components/FrisePage';
import { EcheancierPage } from './components/EcheancierPage';
import { MutualisationPage } from './components/MutualisationPage';
import { ListeEquipePage } from './components/ListeEquipePage';
import { EmpruntsPage } from './components/EmpruntsPage';
import { API_URL } from './lib/api';

axios.defaults.withCredentials = true;

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
    enabled: Boolean(campaign),
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['stats', campaign?.id],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/stats`);
      return response.data;
    },
    refetchInterval: 5000,
    enabled: !!user && !!campaign // Only fetch if user is logged in and campaign selected
  });

  const { data: depenses } = useQuery({
    queryKey: ['depenses', campaign?.id],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/depenses`);
      return response.data;
    },
    enabled: !!user && !!campaign
  });

  const { data: recettes } = useQuery({
    queryKey: ['recettes', campaign?.id],
    queryFn: async () => {
      const response = await axios.get(`${API_URL}/recettes`);
      return response.data;
    },
    enabled: !!user && !!campaign
  });

  if (authLoading) {
    return <div className="flex items-center justify-center h-screen bg-background text-foreground">Chargement...</div>;
  }

  if (!user) {
    return <LoginPage onLogin={setUser} />;
  }

  if (!campaign) {
    return <CampaignPage onSelect={setCampaign} user={user} />;
  }

  if (statsLoading && !stats) { // Check !stats to avoid full page loader on refresh if cache exists
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
        {/* Sidebar */}
        <aside className="w-64 border-r border-border p-6 flex flex-col bg-card">
          <div className="flex items-center gap-2 mb-8">
            <Droplets className="w-8 h-8 text-primary" />
            <div className="flex flex-col">
              <span className="font-bold text-xl tracking-tight leading-none">Plouf</span>
              <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">{campaign.name}</span>
            </div>
          </div>


          <nav className="flex-1 overflow-y-auto -mr-3 pr-3 space-y-1">
            <NavItem icon={LayoutDashboard} label="Tableau de bord" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />

            {user.role === 'admin' && [
              { label: 'Administratif', icon: ClipboardList, items: [
                { key: 'identite', label: 'Identité', icon: ClipboardList },
                { key: 'listeequipe', label: 'Liste & équipe', icon: UsersRound },
                { key: 'echeancier', label: 'Échéancier', icon: Flag },
              ]},
              { label: 'Comptabilité', icon: BookText, items: [
                { key: 'maincourante', label: 'Main courante', icon: BookText },
                { key: 'recettes', label: 'Recettes / Dons', icon: TrendingUp },
                { key: 'depenses', label: 'Dépenses', icon: Receipt },
                { key: 'emprunts', label: 'Emprunts', icon: Landmark },
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
              ]},
            ].map(g => (
              <NavGroup key={g.label} icon={g.icon} label={g.label} items={g.items}
                activeTab={activeTab} setActiveTab={setActiveTab}
                defaultOpen={g.items.some(i => i.key === activeTab)} />
            ))}

          </nav>

          <div className="mt-auto p-4 bg-muted/50 rounded-lg space-y-4">
            <div>
              <div className="flex items-center gap-2 text-sm text-foreground mb-1 font-medium">
                <Users className="w-4 h-4" />
                <span>{user.full_name}</span>
              </div>
              <div className="text-xs text-muted-foreground/80">Villeurbanne</div>
            </div>

            <div className="space-y-1">
              <button
                onClick={() => setActiveTab('settings')}
                className={cn("w-full flex items-center gap-2 px-3 py-1 text-xs font-medium transition-colors",
                  activeTab === 'settings' ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                <Settings className="w-3 h-3" /> Paramètres
              </button>
              <button
                onClick={() => setActiveTab('apropos')}
                className={cn("w-full flex items-center gap-2 px-3 py-1 text-xs font-medium transition-colors",
                  activeTab === 'apropos' ? "text-foreground" : "text-muted-foreground hover:text-foreground")}
              >
                <Info className="w-3 h-3" /> À propos
              </button>
            </div>
            <button
              onClick={toggleTheme}
              className="w-full flex items-center gap-2 px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {theme === 'light' ? <Moon className="w-3 h-3" /> : <Sun className="w-3 h-3" />}
              {theme === 'light' ? 'Mode Sombre' : 'Mode Clair'}
            </button>


            <button
              onClick={() => setCampaign(null)}
              className="w-full flex items-center gap-2 px-3 py-1 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors mb-2"
            >
              <ChevronRight className="w-3 h-3 rotate-180" /> Changer de campagne
            </button>

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-destructive hover:bg-destructive/10 rounded-md transition-colors"
            >
              <LogOut className="w-3 h-3" /> Se déconnecter
            </button>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'dashboard' && (
            <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">

              <header className="flex justify-between items-center mb-8">
                <div>
                  <h1 className="text-3xl font-bold tracking-tight">Vue d'ensemble</h1>
                  <p className="text-muted-foreground">Suivi en temps réel de la consommation du plafond.</p>
                </div>
                {user.role === 'admin' && (
                  <div className="flex gap-4">
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



              {/* Complétude du dossier : ce qui bloque le dépôt, avant les chiffres. */}
              {completude && !completude.complet && (
                <button
                  type="button"
                  onClick={() => setActiveTab('identite')}
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
                  <div className="flex justify-between items-center mb-4">
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
                  <div className="flex justify-between items-center mb-4">
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

          {activeTab === 'depenses' && user.role === 'admin' && (
            <DepensesList cible={cible?.entite === 'depense' ? cible.id : null}
              onCibleConsommee={consommerCible} />
          )}
          {activeTab === 'recettes' && user.role === 'admin' && (
            <RevenueList cible={cible?.entite === 'recette' ? cible.id : null}
              onCibleConsommee={consommerCible} />
          )}
          {activeTab === 'justificatifs' && user.role === 'admin' && <JustificatifsList />}
          {activeTab === 'attestations' && user.role === 'admin' && <AttestationsPage campaignId={campaign.id} />}
          {activeTab === 'carnets' && user.role === 'admin' && <CarnetsPage />}
          {activeTab === 'conformite' && user.role === 'admin' && (
            <ConformitePage onNavigate={(tab, c) => { setCible(c); setActiveTab(tab); }} />
          )}
          {activeTab === 'maincourante' && user.role === 'admin' && <MainCourantePage />}
          {activeTab === 'identite' && user.role === 'admin' && (
            <IdentitePage cible={cible?.entite} onCibleConsommee={consommerCible} />
          )}
          {activeTab === 'depot' && user.role === 'admin' && <DepotPage />}
          {activeTab === 'evenements' && user.role === 'admin' && <EvenementsPage />}
          {activeTab === 'frise' && user.role === 'admin' && <FrisePage />}
          {activeTab === 'calendrier' && user.role === 'admin' && <CalendrierPage />}
          {activeTab === 'echeancier' && user.role === 'admin' && <EcheancierPage />}
          {activeTab === 'mutualisation' && user.role === 'admin' && <MutualisationPage />}
          {activeTab === 'listeequipe' && user.role === 'admin' && <ListeEquipePage />}
          {activeTab === 'emprunts' && user.role === 'admin' && <EmpruntsPage />}

          {activeTab === 'settings' && <SettingsPage currentUser={user} />}
          {activeTab === 'apropos' && <AProposPage />}
        </main>

      </div>
    </div >
  );
}

function NavGroup({ icon: Icon, label, items, activeTab, setActiveTab, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen);
  const hasActive = items.some(i => i.key === activeTab);
  return (
    <div>
      <button
        onClick={() => setOpen(!open)}
        className={cn(
          // Typo resserrée : « Conformité & dépôt » doit tenir sur une ligne dans
          // une barre de 256 px, sinon le libellé se coupe ou passe à la ligne.
          "w-full flex items-center justify-between gap-1 px-3 py-2 rounded-md text-[11px] font-semibold uppercase tracking-wide transition-colors",
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

function NavItem({ icon: Icon, label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "w-full flex items-center gap-3 px-4 py-2.5 text-sm font-medium rounded-md transition-all duration-200",
        active
          ? "bg-primary/10 text-primary shadow-sm"
          : "text-muted-foreground hover:bg-muted hover:text-foreground"
      )}
    >
      <Icon className="w-5 h-5" />
      {label}
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
