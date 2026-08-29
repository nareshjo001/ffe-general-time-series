// 'use client';

// import { useEffect, useState, useMemo } from 'react';
// import Link from 'next/link';
// import { useParams } from 'next/navigation';
// import QueryTable from '@/components/QueryTable';
// import { DEMO_EVALUATION_RESULTS } from '@/services/demoData';

// const SETTING_INFO = {
//   A: {
//     title: 'Setting A: Single Time-Series',
//     desc: 'One grouped series & one measurement (shape of a single curve, persistence, seasonality, and local patterns).',
//   },
//   B: {
//     title: 'Setting B: Single Series, Joint Measurements',
//     desc: 'One grouped series across all measurements jointly (cross-measurement couplings and correlation drift).',
//   },
//   C: {
//     title: 'Setting C: Population of Series',
//     desc: 'All grouped series for one measurement (population-wide distributions, trajectories, and synchrony).',
//   },
// };

// const FAMILIES = [
//   { id: 'ALL', label: 'All Families', desc: 'All queries in this setting' },
//   { id: 'distributional', label: 'Distributional', desc: 'Order-invariant summaries & covariance' },
//   { id: 'trend', label: 'Trend & Drift', desc: 'Slope, drift, and persistence' },
//   { id: 'seasonality', label: 'Seasonality & Recurrence', desc: 'Cycles, spectral energy & coherence' },
//   { id: 'local', label: 'Local Patterns', desc: 'Matrix profile motifs & discords' },
// ];

// export default function SettingCategoryPage() {
//   const params = useParams();
//   const settingKey = (params.category || 'A').toUpperCase(); // 'A' | 'B' | 'C'

//   const [instances, setInstances] = useState([]);
//   const [selectedFamily, setSelectedFamily] = useState('ALL'); // 'ALL' | 'distributional' | 'trend' | 'seasonality' | 'local'
//   const [isDemo, setIsDemo] = useState(true);

//   useEffect(() => {
//     let dataSource = DEMO_EVALUATION_RESULTS.instances;
//     const raw = localStorage.getItem('timeSeriesEvalData') || localStorage.getItem('syntheticEvalData');

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

//     // Filter queries specifically belonging to this Setting (A, B, or C)
//     const settingQueries = dataSource.filter(
//       (item) => (item.setting || '').toUpperCase() === settingKey
//     );
//     setInstances(settingQueries);
//   }, [settingKey]);

//   // Dynamic filter by taxonomy family
//   const displayedQueries = useMemo(() => {
//     if (selectedFamily === 'ALL') {
//       return instances;
//     }
//     return instances.filter((item) => item.family === selectedFamily);
//   }, [instances, selectedFamily]);

//   const currentSetting = SETTING_INFO[settingKey] || {
//     title: `Setting ${settingKey}`,
//     desc: 'Query instance battery for this evaluation lens.',
//   };

//   return (
//     <div className="space-y-6 max-w-7xl mx-auto py-6">
//       {/* Breadcrumb Navigation */}
//       <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">
//         <Link href="/dashboard" className="hover:text-indigo-600 transition-colors">
//           Dashboard
//         </Link>
//         <span>&gt;</span>
//         <span className="text-slate-900 dark:text-white font-semibold">
//           Setting {settingKey}
//         </span>
//       </nav>

//       {/* Demo Mode Notice */}
//       {/* {isDemo && (
//         <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-xs font-medium text-amber-800 dark:text-amber-300">
//           Showing Demo Evaluation Data for <b>Setting {settingKey}</b>.
//         </div>
//       )} */}

//       {/* Page Header */}
//       <div className="border-b border-slate-200 dark:border-slate-800 pb-4">
//         <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white">
//           {currentSetting.title}
//         </h2>
//         <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
//           {currentSetting.desc}
//         </p>
//       </div>

//       {/* 4 Taxonomy Families Filter Tabs */}
//       <div className="space-y-2">
//         <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
//           Taxonomy V3 Families Filter
//         </label>
//         <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
//           {FAMILIES.map((fam) => {
//             const count =
//               fam.id === 'ALL'
//                 ? instances.length
//                 : instances.filter((item) => item.family === fam.id).length;

//             const isSelected = selectedFamily === fam.id;

//             return (
//               <button
//                 key={fam.id}
//                 type="button"
//                 onClick={() => setSelectedFamily(fam.id)}
//                 className={`p-3.5 rounded-xl border text-left transition-all ${
//                   isSelected
//                     ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 dark:border-indigo-500 shadow-xs'
//                     : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
//                 }`}
//               >
//                 <div className="flex items-center justify-between">
//                   <span
//                     className={`text-sm font-bold ${
//                       isSelected
//                         ? 'text-indigo-600 dark:text-indigo-400'
//                         : 'text-slate-900 dark:text-white'
//                     }`}
//                   >
//                     {fam.label}
//                   </span>
//                   <span
//                     className={`text-xs px-2 py-0.5 rounded-full font-mono font-semibold ${
//                       isSelected
//                         ? 'bg-indigo-600 text-white dark:bg-indigo-500'
//                         : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
//                     }`}
//                   >
//                     {count}
//                   </span>
//                 </div>
//                 <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-1">
//                   {fam.desc}
//                 </p>
//               </button>
//             );
//           })}
//         </div>
//       </div>

//       {/* Query List Table */}
//       {displayedQueries.length === 0 ? (
//         <div className="p-10 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl text-slate-500">
//           No queries found for <b>{selectedFamily === 'ALL' ? 'this setting' : `${selectedFamily} family`}</b> under Setting {settingKey}.
//         </div>
//       ) : (
//         <QueryTable queries={displayedQueries} familyKey={settingKey} />
//       )}
//     </div>
//   );
// }


'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import QueryTable from '@/components/QueryTable';

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
  {
    id: 'ALL',
    label: 'All Families',
    desc: 'All queries in this setting',
  },
  {
    id: 'distributional',
    label: 'Distributional',
    desc: 'Order-invariant summaries & covariance',
  },
  {
    id: 'trend',
    label: 'Trend & Drift',
    desc: 'Slope, drift, and persistence',
  },
  {
    id: 'seasonality',
    label: 'Seasonality & Recurrence',
    desc: 'Cycles, spectral energy & coherence',
  },
  {
    id: 'local',
    label: 'Local Patterns',
    desc: 'Matrix profile motifs & discords',
  },
];

/* =========================================================
   Helpers
   ========================================================= */

function normalizeSetting(value) {
  return String(value || '')
    .trim()
    .toUpperCase();
}

function normalizeFamily(value) {
  return String(value || '')
    .trim()
    .toLowerCase();
}

function getQueryCount(instances, familyId) {
  if (familyId === 'ALL') {
    return instances.length;
  }

  return instances.filter(
    (item) =>
      normalizeFamily(item.family) === familyId
  ).length;
}

/* =========================================================
   Page
   ========================================================= */

export default function SettingCategoryPage() {
  const params = useParams();

  const rawCategory = params?.category;

  const settingKey = normalizeSetting(
    Array.isArray(rawCategory)
      ? rawCategory[0]
      : rawCategory
  );

  const [allInstances, setAllInstances] = useState([]);
  const [selectedFamily, setSelectedFamily] =
    useState('ALL');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [evaluationMode, setEvaluationMode] = useState('real_synthetic');

  /* =======================================================
     Load actual backend evaluation result
     ======================================================= */

//   useEffect(() => {
//     setLoading(true);
//     setError('');

//     try {
//       /*
//        * New evaluation flow stores the backend result in
//        * evaluationResult.
//        *
//        * Older keys are retained as fallbacks.
//        */

//       const raw =
//         localStorage.getItem('evaluationResult') ||
//         localStorage.getItem('syntheticEvalData') ||
//         localStorage.getItem('timeSeriesEvalData');

//       if (!raw) {
//         setError(
//           'No evaluation result found. Please run an evaluation from the home page.'
//         );

//         setAllInstances([]);
//         return;
//       }

//       const parsed = JSON.parse(raw);

//       if (
//         !parsed ||
//         !Array.isArray(parsed.instances)
//       ) {
//         setError(
//           'The evaluation result does not contain a valid instances array.'
//         );

//         setAllInstances([]);
//         return;
//       }
      
// //       if (
// //   parsed.instances &&
// //   parsed.instances.length > 0
// // ) {
// //   dataSource = parsed.instances;
// //   setIsDemo(false);

// //   setEvaluationMode(
// //     parsed.mode || 'real_synthetic'
// //   );
// // }
//       /*
//        * Keep the complete backend result instances.
//        * Setting/family filtering happens below.
//        */

//       setAllInstances(parsed.instances);
//     } catch (err) {
//       console.error(
//         'Error loading evaluation result:',
//         err
//       );

//       setError(
//         'Unable to read the evaluation result. Please run the evaluation again.'
//       );

//       setAllInstances([]);
//     } finally {
//       setLoading(false);
//     }
//   }, [settingKey]);

useEffect(() => {
  setLoading(true);
  setError('');

  try {
    /*
     * New evaluation flow stores the backend result in
     * evaluationResult.
     *
     * Older keys are retained as fallbacks.
     */

    const raw =
      localStorage.getItem('evaluationResult') ||
      localStorage.getItem('syntheticEvalData') ||
      localStorage.getItem('timeSeriesEvalData');

    if (!raw) {
      setError(
        'No evaluation result found. Please run an evaluation from the home page.'
      );

      setAllInstances([]);
      return;
    }

    const parsed = JSON.parse(raw);

    /*
     * IMPORTANT:
     * Backend returns:
     *
     * mode: "real_only"
     *
     * or
     *
     * mode: "real_synthetic"
     *
     * Read it from the ROOT of the response.
     */
    setEvaluationMode(
      parsed.mode === 'real_only'
        ? 'real_only'
        : 'real_synthetic'
    );

    if (
      !parsed ||
      !Array.isArray(parsed.instances)
    ) {
      setError(
        'The evaluation result does not contain a valid instances array.'
      );

      setAllInstances([]);
      return;
    }

    /*
     * Keep the complete backend result instances.
     * Setting/family filtering happens below.
     */
    setAllInstances(parsed.instances);

  } catch (err) {
    console.error(
      'Error loading evaluation result:',
      err
    );

    setError(
      'Unable to read the evaluation result. Please run the evaluation again.'
    );

    setAllInstances([]);

  } finally {
    setLoading(false);
  }
}, [settingKey]);

  /* =======================================================
     Setting information
     ======================================================= */

  const currentSetting =
    SETTING_INFO[settingKey];

  /* =======================================================
     Filter all backend instances by setting
     ======================================================= */

  const settingInstances =
    allInstances.filter(
      (item) =>
        normalizeSetting(item.setting) ===
        settingKey
    );

  /* =======================================================
     Filter by selected family
     ======================================================= */

  const displayedQueries =
    selectedFamily === 'ALL'
      ? settingInstances
      : settingInstances.filter(
          (item) =>
            normalizeFamily(item.family) ===
            selectedFamily
        );

  /* =======================================================
     Loading state
     ======================================================= */

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto py-16 px-4">

        <div className="flex items-center justify-center">

          <div className="text-center">

            <div className="mx-auto h-8 w-8 rounded-full border-4 border-slate-200 border-t-indigo-600 animate-spin" />

            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
              Loading Setting {settingKey} results...
            </p>

          </div>

        </div>

      </div>
    );
  }

  /* =======================================================
     Invalid setting
     ======================================================= */

  if (!currentSetting) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4">

        <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">

          <Link
            href="/dashboard"
            className="hover:text-indigo-600 transition-colors"
          >
            Dashboard
          </Link>

          <span>&gt;</span>

          <span className="text-slate-900 dark:text-white font-semibold">
            Setting {settingKey || 'Unknown'}
          </span>

        </nav>

        <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 p-8 text-center">

          <h2 className="text-xl font-bold text-rose-800 dark:text-rose-300">
            Invalid Setting
          </h2>

          <p className="mt-2 text-sm text-rose-700 dark:text-rose-400">
            Setting "{settingKey}" is not available.
            Please select Setting A, B, or C.
          </p>

          <Link
            href="/dashboard"
            className="inline-flex mt-6 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Back to Dashboard
          </Link>

        </div>

      </div>
    );
  }

  /* =======================================================
     Data error
     ======================================================= */

  if (error) {
    return (
      <div className="max-w-7xl mx-auto py-8 px-4">

        <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">

          <Link
            href="/dashboard"
            className="hover:text-indigo-600 transition-colors"
          >
            Dashboard
          </Link>

          <span>&gt;</span>

          <span className="text-slate-900 dark:text-white font-semibold">
            Setting {settingKey}
          </span>

        </nav>

        <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 p-8 text-center">

          <h2 className="text-xl font-bold text-rose-800 dark:text-rose-300">
            Evaluation Data Unavailable
          </h2>

          <p className="mt-2 text-sm text-rose-700 dark:text-rose-400">
            {error}
          </p>

          <Link
            href="/"
            className="inline-flex mt-6 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Run New Evaluation
          </Link>

        </div>

      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto py-6 px-4">

      {/* =====================================================
          BREADCRUMB
          ===================================================== */}

      <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">

        <Link
          href="/dashboard"
          className="hover:text-indigo-600 transition-colors"
        >
          Dashboard
        </Link>

        <span>&gt;</span>

        <span className="text-slate-900 dark:text-white font-semibold">
          Setting {settingKey}
        </span>

      </nav>


      {/* =====================================================
          PAGE HEADER
          ===================================================== */}

      <div className="border-b border-slate-200 dark:border-slate-800 pb-5">

        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">

          <div>

            <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white">
              {currentSetting.title}
            </h1>

            <p className="text-sm text-slate-500 dark:text-slate-400 mt-2 max-w-3xl">
              {currentSetting.desc}
            </p>

          </div>

          <div className="shrink-0">

            <span className="inline-flex items-center px-3 py-1.5 rounded-full bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold text-indigo-700 dark:text-indigo-300">
              {settingInstances.length}{' '}
              {settingInstances.length === 1
                ? 'query'
                : 'queries'}
            </span>

          </div>

        </div>

      </div>


      {/* =====================================================
          TAXONOMY FAMILY FILTER
          ===================================================== */}

      <div className="space-y-3">

        <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
          Taxonomy V3 Families Filter
        </label>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">

          {FAMILIES.map((family) => {

            const count =
              getQueryCount(
                settingInstances,
                family.id
              );

            const isSelected =
              selectedFamily === family.id;

            return (
              <button
                key={family.id}
                type="button"
                onClick={() =>
                  setSelectedFamily(
                    family.id
                  )
                }
                className={`p-4 rounded-xl border text-left transition-all ${
                  isSelected
                    ? 'border-indigo-600 bg-indigo-50/70 dark:bg-indigo-950/40 dark:border-indigo-500 shadow-sm'
                    : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700 hover:shadow-sm'
                }`}
              >

                <div className="flex items-center justify-between gap-2">

                  <span
                    className={`text-sm font-bold ${
                      isSelected
                        ? 'text-indigo-600 dark:text-indigo-400'
                        : 'text-slate-900 dark:text-white'
                    }`}
                  >
                    {family.label}
                  </span>

                  <span
                    className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-mono font-semibold ${
                      isSelected
                        ? 'bg-indigo-600 text-white dark:bg-indigo-500'
                        : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
                    }`}
                  >
                    {count}
                  </span>

                </div>

                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">
                  {family.desc}
                </p>

              </button>
            );
          })}

        </div>

      </div>


      {/* =====================================================
          ACTIVE FILTER
          ===================================================== */}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">

        <div>

          <h2 className="text-lg font-bold text-slate-900 dark:text-white">

            {selectedFamily === 'ALL'
              ? 'All Queries'
              : FAMILIES.find(
                  (family) =>
                    family.id ===
                    selectedFamily
                )?.label || selectedFamily}

          </h2>

          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">

            Showing{' '}

            <strong>
              {displayedQueries.length}
            </strong>{' '}

            of{' '}

            <strong>
              {settingInstances.length}
            </strong>{' '}

            queries in Setting {settingKey}.

          </p>

        </div>


        {selectedFamily !== 'ALL' && (
          <button
            type="button"
            onClick={() =>
              setSelectedFamily('ALL')
            }
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            Show All Families
          </button>
        )}

      </div>


      {/* =====================================================
          QUERY TABLE
          ===================================================== */}

      {displayedQueries.length === 0 ? (

        <div className="p-10 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">

          <div className="text-3xl mb-3">
            No Queries
          </div>

          <p className="text-sm text-slate-500 dark:text-slate-400">

            No queries found for{' '}

            <strong>
              {selectedFamily === 'ALL'
                ? `Setting ${settingKey}`
                : `${selectedFamily} family`}
            </strong>.

          </p>

        </div>

      ) : (

        <QueryTable
          queries={displayedQueries}
          familyKey={settingKey}
          mode={evaluationMode}
        />

      )}


      {/* =====================================================
          FOOTER
          ===================================================== */}

      <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-4">

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">

          <p className="text-xs text-slate-500 dark:text-slate-400">

            Setting {settingKey} •{' '}

            {displayedQueries.length}{' '}

            {displayedQueries.length === 1
              ? 'query'
              : 'queries'}

          </p>

          <Link
            href="/dashboard"
            className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 hover:underline"
          >
            ← Back to Dashboard
          </Link>

        </div>

      </div>

    </div>
  );
}