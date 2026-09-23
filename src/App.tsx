import { useState, useEffect } from 'react';
import { PageId, BusinessProfile, ClimateAssessmentData, ClimateFingerprint, TransformationPhaseItem, ImpactVerificationMetric, UserPreferences, ToastMessage } from './types';
import {
  getBusinessProfile,
  saveBusinessProfile,
  getClimateAssessment,
  saveClimateAssessment,
  getClimateFingerprint,
  getTransformationPlan,
  updateTransformationItemStatus,
  getImpactVerification,
  getUserPreferences,
  saveUserPreferences,
} from './services/api';

import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';

import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { BusinessProfilePage } from './pages/BusinessProfilePage';
import { ClimateAssessmentPage } from './pages/ClimateAssessmentPage';
import { ClimateFingerprintPage } from './pages/ClimateFingerprintPage';
import { EnergyPage } from './pages/EnergyPage';
import { WaterPage } from './pages/WaterPage';
import { WastePage } from './pages/WastePage';
import { EmissionsPage } from './pages/EmissionsPage';
import { MobilityPage } from './pages/MobilityPage';
import { GreenSolutionsPage } from './pages/GreenSolutionsPage';
import { ScenarioSimulatorPage } from './pages/ScenarioSimulatorPage';
import { TransformationPlanPage } from './pages/TransformationPlanPage';
import { ImpactVerificationPage } from './pages/ImpactVerificationPage';
import { ClimateImpactReportPage } from './pages/ClimateImpactReportPage';
import { SettingsPage } from './pages/SettingsPage';

import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

export function App() {
  const [currentPage, setCurrentPage] = useState<PageId>('landing');
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  // App-level state (ready for Phase 2 API replacement)
  const [profile, setProfile] = useState<BusinessProfile | null>(null);
  const [assessment, setAssessment] = useState<ClimateAssessmentData | null>(null);
  const [fingerprint, setFingerprint] = useState<ClimateFingerprint | null>(null);
  const [plan, setPlan] = useState<TransformationPhaseItem[]>([]);
  const [verification, setVerification] = useState<ImpactVerificationMetric[]>([]);
  const [preferences, setPreferences] = useState<UserPreferences | null>(null);

  // Cross-page state: selected solution for simulator jump
  const [selectedSolutionForSimulator, setSelectedSolutionForSimulator] = useState<string[]>(['sol-solar', 'sol-water-ro']);

  // Toast system
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (type: 'success' | 'info' | 'warning' | 'error', title: string, message?: string) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3500);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Initial data loading
  useEffect(() => {
    async function initData() {
      try {
        const [profData, assessData, fpData, planData, verifData, prefData] = await Promise.all([
          getBusinessProfile(),
          getClimateAssessment(),
          getClimateFingerprint(),
          getTransformationPlan(),
          getImpactVerification(),
          getUserPreferences(),
        ]);

        setProfile(profData);
        setAssessment(assessData);
        setFingerprint(fpData);
        setPlan(planData);
        setVerification(verifData);
        setPreferences(prefData);
      } catch (err) {
        console.error('Failed to load initial mock data', err);
        addToast('error', 'Data Load Error', 'Could not load enterprise profile.');
      } finally {
        setLoading(false);
      }
    }

    initData();
  }, []);

  const handleNavigate = (page: PageId) => {
    setCurrentPage(page);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSaveProfile = async (updated: BusinessProfile) => {
    try {
      const res = await saveBusinessProfile(updated);
      setProfile(res);
      addToast('success', 'Profile Updated', 'Business operational baseline saved successfully.');
    } catch {
      addToast('error', 'Error', 'Failed to update business profile.');
    }
  };

  const handleSaveAssessment = async (data: ClimateAssessmentData) => {
    try {
      const res = await saveClimateAssessment(data);
      setAssessment(data);
      if (res.fingerprint) {
        setFingerprint(res.fingerprint);
      }
      addToast('success', 'Assessment Analyzed', 'Climate Fingerprint diagnostic updated.');
      return res;
    } catch {
      addToast('error', 'Error', 'Failed to process climate assessment.');
    }
  };

  const handleUpdatePlanStatus = async (id: string, status: 'Pending' | 'In Progress' | 'Completed') => {
    try {
      const updated = await updateTransformationItemStatus(id, status);
      setPlan(updated);
      addToast('info', 'Roadmap Action Updated', `Status set to "${status}"`);
    } catch {
      addToast('error', 'Error', 'Failed to update action status.');
    }
  };

  const handleSavePreferences = async (updated: Partial<UserPreferences>) => {
    try {
      const res = await saveUserPreferences(updated);
      setPreferences(res);
      addToast('success', 'Settings Saved', 'User preferences updated.');
    } catch {
      addToast('error', 'Error', 'Failed to save preferences.');
    }
  };

  const handleSelectSolutionForSimulator = (solutionId: string) => {
    setSelectedSolutionForSimulator((prev) =>
      prev.includes(solutionId) ? prev : [...prev, solutionId]
    );
  };

  if (loading || !profile || !assessment || !fingerprint || !preferences) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
        <div className="w-12 h-12 rounded-2xl bg-emerald-600 flex items-center justify-center text-white font-black text-2xl animate-bounce">
          C
        </div>
        <h2 className="mt-4 text-base font-extrabold text-slate-800 tracking-tight">
          ClimaCred AI
        </h2>
        <p className="text-xs text-slate-600 mt-1 animate-pulse">
          Initializing Climate Intelligence Workspace...
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-800 flex flex-col lg:flex-row antialiased">
      {/* Sidebar Navigation */}
      <Sidebar
        currentPage={currentPage}
        onNavigate={handleNavigate}
        mobileOpen={mobileMenuOpen}
        onCloseMobile={() => setMobileMenuOpen(false)}
      />

      {/* Main Content Area */}
      <div className="flex-1 lg:pl-72 flex flex-col min-w-0 min-h-screen">
        <Header
          currentPage={currentPage}
          onOpenMobile={() => setMobileMenuOpen(true)}
          onNavigate={handleNavigate}
        />

        <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 max-w-7xl w-full mx-auto">
          {currentPage === 'landing' && <LandingPage onNavigate={handleNavigate} />}

          {currentPage === 'dashboard' && <DashboardPage onNavigate={handleNavigate} />}

          {currentPage === 'profile' && (
            <BusinessProfilePage
              profile={profile}
              onSave={handleSaveProfile}
              onNavigate={handleNavigate}
            />
          )}

          {currentPage === 'assessment' && (
            <ClimateAssessmentPage
              initialData={assessment}
              onSaveAssessment={handleSaveAssessment}
              onNavigate={handleNavigate}
            />
          )}

          {currentPage === 'fingerprint' && (
            <ClimateFingerprintPage
              fingerprint={fingerprint}
              onNavigate={handleNavigate}
            />
          )}

          {currentPage === 'energy' && <EnergyPage onNavigate={handleNavigate} />}

          {currentPage === 'water' && <WaterPage onNavigate={handleNavigate} />}

          {currentPage === 'waste' && <WastePage onNavigate={handleNavigate} />}

          {currentPage === 'emissions' && <EmissionsPage onNavigate={handleNavigate} />}

          {currentPage === 'mobility' && <MobilityPage onNavigate={handleNavigate} />}

          {currentPage === 'solutions' && (
            <GreenSolutionsPage
              onNavigate={handleNavigate}
              onSelectSolutionForSimulator={handleSelectSolutionForSimulator}
            />
          )}

          {currentPage === 'simulator' && (
            <ScenarioSimulatorPage
              onNavigate={handleNavigate}
              initialSelectedSolutionIds={selectedSolutionForSimulator}
            />
          )}

          {currentPage === 'transformation' && (
            <TransformationPlanPage
              planItems={plan}
              onUpdateStatus={handleUpdatePlanStatus}
              onNavigate={handleNavigate}
            />
          )}

          {currentPage === 'verification' && (
            <ImpactVerificationPage
              metrics={verification}
              onNavigate={handleNavigate}
            />
          )}

          {currentPage === 'report' && (
            <ClimateImpactReportPage
              profile={profile}
              fingerprint={fingerprint}
              verificationMetrics={verification}
            />
          )}

          {currentPage === 'settings' && (
            <SettingsPage
              preferences={preferences}
              onSavePreferences={handleSavePreferences}
            />
          )}
        </main>
      </div>

      {/* Floating Toast Container */}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto p-4 rounded-2xl shadow-xl border flex items-start gap-3 animate-slide-up transition-all ${
              toast.type === 'success'
                ? 'bg-slate-900 text-white border-slate-800'
                : toast.type === 'error'
                ? 'bg-rose-900 text-white border-rose-800'
                : 'bg-white text-slate-900 border-slate-200'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
            ) : toast.type === 'error' ? (
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            ) : (
              <Info className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
            )}

            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold leading-tight">{toast.title}</p>
              {toast.message && <p className="text-[11px] text-slate-300 mt-0.5">{toast.message}</p>}
            </div>

            <button
              onClick={() => removeToast(toast.id)}
              className="p-1 text-slate-400 hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;
