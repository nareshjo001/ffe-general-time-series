// 'use client';

// import { useEffect, useState, useMemo } from 'react';
// import Link from 'next/link';
// import { useParams } from 'next/navigation';
// import QueryTable from '@/components/QueryTable';
// import { DEMO_EVALUATION_RESULTS } from '@/services/demoData';

// const FAMILY_TITLES = {
//   distributional: 'Distributional Family',
//   trend: 'Trend & Drift Family',
//   seasonality: 'Seasonality & Recurrence Family',
//   local: 'Local Patterns Family',
// };

// const SETTINGS = [
//   { id: 'ALL', label: 'All Settings', desc: 'View all queries for this family' },
//   { id: 'A', label: 'Setting A', desc: 'Single Series, 1 Measurement' },
//   { id: 'B', label: 'Setting B', desc: '1 Series, All Measurements Jointly' },
//   { id: 'C', label: 'Setting C', desc: 'Collection Population, 1 Measurement' },
// ];

// export default function FamilyCategoryPage() {
//   const params = useParams();
//   const categoryKey = params.category; // 'distributional' | 'trend' | 'seasonality' | 'local'

//   const [instances, setInstances] = useState([]);
//   const [selectedSetting, setSelectedSetting] = useState('ALL'); // 'ALL' | 'A' | 'B' | 'C'
//   const [isDemo, setIsDemo] = useState(true);

//   useEffect(() => {
//     const raw = localStorage.getItem('timeSeriesEvalData');
//     let dataSource = DEMO_EVALUATION_RESULTS.instances;

//     if (raw) {
//       try {
//         const parsed = JSON.parse(raw);
//         if (parsed.instances && parsed.instances.length > 0) {
//           dataSource = parsed.instances;
//           setIsDemo(false);
//         }
//       } catch (err) {
//         console.error('Error parsing evaluation data from storage:', err);
//       }
//     }

//     // Filter queries for this specific taxonomy family first
//     const familyQueries = dataSource.filter((item) => item.family === categoryKey);
//     setInstances(familyQueries);
//   }, [categoryKey]);

//   // Compute filtered queries based on the active setting selection
//   const displayedQueries = useMemo(() => {
//     if (selectedSetting === 'ALL') {
//       return instances;
//     }
//     return instances.filter((item) => item.setting === selectedSetting);
//   }, [instances, selectedSetting]);

//   const familyName = FAMILY_TITLES[categoryKey] || `${categoryKey} Family`;

//   return (
//     <div className="space-y-6 max-w-7xl mx-auto py-6">
//       {/* Breadcrumb Navigation */}
//       <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">
//         <Link href="/dashboard" className="hover:text-indigo-600 transition-colors">Dashboard</Link>
//         <span>&gt;</span>
//         <span className="capitalize text-slate-900 dark:text-white font-semibold">{familyName}</span>
//       </nav>

//       {/* Demo Mode Notice */}
//       {/* {isDemo && (
//         <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-xs font-medium text-amber-800 dark:text-amber-300">
//           Showing Demo Evaluation Data for <b>{familyName}</b>.
//         </div>
//       )} */}

//       {/* Page Header */}
//       <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
//         <h2 className="text-3xl font-extrabold capitalize text-slate-900 dark:text-white">{familyName}</h2>
//         <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
//           Select an evaluation lens setting (A, B, C) to filter query instances.
//         </p>
//       </div>

//       {/* Setting Selector Tabs */}
//       <div className="space-y-2">
//         <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
//           Evaluation Lens (Setting Filter)
//         </label>
//         <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
//           {SETTINGS.map((setting) => {
//             const count = setting.id === 'ALL'
//               ? instances.length
//               : instances.filter((item) => item.setting === setting.id).length;

//             const isSelected = selectedSetting === setting.id;

//             return (
//               <button
//                 key={setting.id}
//                 type="button"
//                 onClick={() => setSelectedSetting(setting.id)}
//                 className={`p-3.5 rounded-xl border text-left transition-all ${
//                   isSelected
//                     ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 dark:border-indigo-500 shadow-xs'
//                     : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
//                 }`}
//               >
//                 <div className="flex items-center justify-between">
//                   <span className={`text-sm font-bold ${isSelected ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-900 dark:text-white'}`}>
//                     {setting.label}
//                   </span>
//                   <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-semibold ${
//                     isSelected
//                       ? 'bg-indigo-600 text-white dark:bg-indigo-500'
//                       : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
//                   }`}>
//                     {count}
//                   </span>
//                 </div>
//                 <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
//                   {setting.desc}
//                 </p>
//               </button>
//             );
//           })}
//         </div>
//       </div>

//       {/* Query List Table */}
//       {displayedQueries.length === 0 ? (
//         <div className="p-10 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500">
//           No query instances found for <b>{selectedSetting === 'ALL' ? familyName : `Setting ${selectedSetting}`}</b> in this family.
//         </div>
//       ) : (
//         <QueryTable queries={displayedQueries} familyKey={categoryKey} />
//       )}
//     </div>
//   );
// }



'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import QueryTable from '@/components/QueryTable';
import { DEMO_EVALUATION_RESULTS } from '@/services/demoData';

const SETTING_INFO = {
  A: {
    title: 'Setting A: Single Time-Series',
    desc: 'One grouped series & one measurement (shape of a single curve, persistence, seasonality, and local patterns).',
  },
  B: {
    title: 'Setting B: Single Series, Joint Measurements',
    desc: 'One grouped series across all measurements jointly (cross-measurement couplings and correlation drift).',
  },
  C: {
    title: 'Setting C: Population of Series',
    desc: 'All grouped series for one measurement (population-wide distributions, trajectories, and synchrony).',
  },
};

const FAMILIES = [
  { id: 'ALL', label: 'All Families', desc: 'All queries in this setting' },
  { id: 'distributional', label: 'Distributional', desc: 'Order-invariant summaries & covariance' },
  { id: 'trend', label: 'Trend & Drift', desc: 'Slope, drift, and persistence' },
  { id: 'seasonality', label: 'Seasonality & Recurrence', desc: 'Cycles, spectral energy & coherence' },
  { id: 'local', label: 'Local Patterns', desc: 'Matrix profile motifs & discords' },
];

export default function SettingCategoryPage() {
  const params = useParams();
  const settingKey = (params.category || 'A').toUpperCase(); // 'A' | 'B' | 'C'

  const [instances, setInstances] = useState([]);
  const [selectedFamily, setSelectedFamily] = useState('ALL'); // 'ALL' | 'distributional' | 'trend' | 'seasonality' | 'local'
  const [isDemo, setIsDemo] = useState(true);

  useEffect(() => {
    let dataSource = DEMO_EVALUATION_RESULTS.instances;
    const raw = localStorage.getItem('timeSeriesEvalData') || localStorage.getItem('syntheticEvalData');

    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed.instances && parsed.instances.length > 0) {
          dataSource = parsed.instances;
          setIsDemo(false);
        }
      } catch (err) {
        console.error('Error parsing evaluation data from storage:', err);
      }
    }

    // Filter queries specifically belonging to this Setting (A, B, or C)
    const settingQueries = dataSource.filter(
      (item) => (item.setting || '').toUpperCase() === settingKey
    );
    setInstances(settingQueries);
  }, [settingKey]);

  // Dynamic filter by taxonomy family
  const displayedQueries = useMemo(() => {
    if (selectedFamily === 'ALL') {
      return instances;
    }
    return instances.filter((item) => item.family === selectedFamily);
  }, [instances, selectedFamily]);

  const currentSetting = SETTING_INFO[settingKey] || {
    title: `Setting ${settingKey}`,
    desc: 'Query instance battery for this evaluation lens.',
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-6">
      {/* Breadcrumb Navigation */}
      <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">
        <Link href="/dashboard" className="hover:text-indigo-600 transition-colors">
          Dashboard
        </Link>
        <span>&gt;</span>
        <span className="text-slate-900 dark:text-white font-semibold">
          Setting {settingKey}
        </span>
      </nav>

      {/* Demo Mode Notice */}
      {/* {isDemo && (
        <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-xs font-medium text-amber-800 dark:text-amber-300">
          Showing Demo Evaluation Data for <b>Setting {settingKey}</b>.
        </div>
      )} */}

      {/* Page Header */}
      <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
        <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
          {currentSetting.title}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {currentSetting.desc}
        </p>
      </div>

      {/* 4 Taxonomy Families Filter Tabs */}
      <div className="space-y-2">
        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
          Taxonomy V3 Families Filter
        </label>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {FAMILIES.map((fam) => {
            const count =
              fam.id === 'ALL'
                ? instances.length
                : instances.filter((item) => item.family === fam.id).length;

            const isSelected = selectedFamily === fam.id;

            return (
              <button
                key={fam.id}
                type="button"
                onClick={() => setSelectedFamily(fam.id)}
                className={`p-3.5 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 dark:border-indigo-500 shadow-xs'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`text-sm font-bold ${
                      isSelected
                        ? 'text-indigo-600 dark:text-indigo-400'
                        : 'text-slate-900 dark:text-white'
                    }`}
                  >
                    {fam.label}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full font-mono font-semibold ${
                      isSelected
                        ? 'bg-indigo-600 text-white dark:bg-indigo-500'
                        : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                    }`}
                  >
                    {count}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
                  {fam.desc}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* Query List Table */}
      {displayedQueries.length === 0 ? (
        <div className="p-10 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500">
          No queries found for <b>{selectedFamily === 'ALL' ? 'this setting' : `${selectedFamily} family`}</b> under Setting {settingKey}.
        </div>
      ) : (
        <QueryTable queries={displayedQueries} familyKey={settingKey} />
      )}
    </div>
  );
}