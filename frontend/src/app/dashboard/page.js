// 'use client';

// import { useEffect, useState } from 'react';
// import { useRouter } from 'next/navigation';
// import { formatScore, getScoreColor } from '@/utils/helpers';

// const SETTINGS = [
//   {
//     id: 'A',
//     name: 'Setting A',
//     title: 'Single Time-Series',
//     desc: 'One grouped series & one measurement — shape of a single curve, persistence, seasonality, and local patterns.',
//   },
//   {
//     id: 'B',
//     name: 'Setting B',
//     title: 'Cross-Measurement Structure',
//     desc: 'Cross-measurement structure and correlation drift within the same grouped series.',
//   },
//   {
//     id: 'C',
//     name: 'Setting C',
//     title: 'Population of Series',
//     desc: 'Population-level distributions, shared trajectories, and phase-sharing across series.',
//   },
// ];

// const FAMILIES = [
//   {
//     id: 'distributional',
//     name: 'Distributional',
//     shortName: 'Distributional',
//     desc: 'Order-invariant summaries & covariance',
//   },
//   {
//     id: 'trend',
//     name: 'Trend & Drift',
//     shortName: 'Trend',
//     desc: 'Slope, drift, and persistence',
//   },
//   {
//     id: 'seasonality',
//     name: 'Seasonality & Recurrence',
//     shortName: 'Seasonality',
//     desc: 'Cycles, spectral energy & coherence',
//   },
//   {
//     id: 'local',
//     name: 'Local Patterns',
//     shortName: 'Local',
//     desc: 'Matrix profile motifs & discords',
//   },
// ];

// /* ---------------------------------------------------------
//    Helpers
//    --------------------------------------------------------- */

// function getDistance(instance) {
//   const value = instance?.distance;

//   return typeof value === 'number' && Number.isFinite(value)
//     ? value
//     : null;
// }

// function average(values) {
//   const valid = values.filter(
//     (value) =>
//       typeof value === 'number' &&
//       Number.isFinite(value)
//   );

//   if (valid.length === 0) {
//     return null;
//   }

//   return (
//     valid.reduce((sum, value) => sum + value, 0) /
//     valid.length
//   );
// }

// function getSettingInstances(instances, settingId) {
//   return instances.filter(
//     (instance) =>
//       String(instance?.setting || '').toUpperCase() ===
//       settingId
//   );
// }

// function getFamilyInstances(instances, familyId) {
//   return instances.filter(
//     (instance) =>
//       String(instance?.family || '').toLowerCase() ===
//       familyId
//   );
// }

// function calculateSettingScore(instances, settingId) {
//   const settingInstances = getSettingInstances(
//     instances,
//     settingId
//   );

//   return average(
//     settingInstances.map(getDistance)
//   );
// }

// function calculateFamilyScore(instances, familyId) {
//   const familyInstances = getFamilyInstances(
//     instances,
//     familyId
//   );

//   return average(
//     familyInstances.map(getDistance)
//   );
// }

// function getScoreLabel(score) {
//   if (
//     score === null ||
//     score === undefined ||
//     !Number.isFinite(score)
//   ) {
//     return 'No Data';
//   }

//   if (score <= 0.05) {
//     return 'Excellent Match';
//   }

//   if (score <= 0.15) {
//     return 'Good Match';
//   }

//   if (score <= 0.30) {
//     return 'Moderate Match';
//   }

//   return 'Low Fidelity';
// }

// function getSimilarityPercent(score) {
//   if (
//     score === null ||
//     score === undefined ||
//     !Number.isFinite(score)
//   ) {
//     return 0;
//   }

//   return Math.max(
//     0,
//     Math.min(
//       100,
//       Math.round((1 - score) * 100)
//     )
//   );
// }

// /* ---------------------------------------------------------
//    Score badge
//    --------------------------------------------------------- */

// function ScoreBadge({ score }) {
//   if (
//     score === null ||
//     score === undefined ||
//     !Number.isFinite(score)
//   ) {
//     return (
//       <span className="inline-flex px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
//         No Data
//       </span>
//     );
//   }

//   const colors = getScoreColor(score);

//   return (
//     <span
//       className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}
//     >
//       {getScoreLabel(score)}
//     </span>
//   );
// }

// /* ---------------------------------------------------------
//    Main Dashboard
//    --------------------------------------------------------- */

// export default function DashboardPage() {
//   const router = useRouter();

//   const [data, setData] = useState(null);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState('');

//   /*
//    * IMPORTANT:
//    * All hooks are declared before any conditional return.
//    * This prevents:
//    *
//    * "Rendered more hooks than during the previous render."
//    */
//   useEffect(() => {
//     try {
//       const raw =
//         localStorage.getItem('evaluationResult') ||
//         localStorage.getItem('syntheticEvalData') ||
//         localStorage.getItem('timeSeriesEvalData');

//       if (!raw) {
//         setError(
//           'No evaluation result found. Please run an evaluation from the home page.'
//         );
//         return;
//       }

//       const parsed = JSON.parse(raw);

//       if (
//         !parsed ||
//         !Array.isArray(parsed.instances)
//       ) {
//         setError(
//           'The evaluation result is invalid or does not contain query instances.'
//         );
//         return;
//       }

//       setData(parsed);
//     } catch (err) {
//       console.error(
//         'Failed to load evaluation result:',
//         err
//       );

//       setError(
//         'Failed to read the evaluation result. Please run the evaluation again.'
//       );
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   /*
//    * -------------------------------------------------------
//    * Loading
//    * -------------------------------------------------------
//    */

//   if (loading) {
//     return (
//       <div className="min-h-[60vh] flex items-center justify-center">
//         <div className="text-center">

//           <div className="mx-auto h-8 w-8 rounded-full border-4 border-slate-200 border-t-indigo-600 animate-spin" />

//           <p className="mt-4 text-sm text-slate-500">
//             Loading evaluation results...
//           </p>

//         </div>
//       </div>
//     );
//   }

//   /*
//    * -------------------------------------------------------
//    * Error
//    * -------------------------------------------------------
//    */

//   if (error || !data) {
//     return (
//       <div className="max-w-3xl mx-auto py-16 px-4">

//         <div className="rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 p-8 text-center">

//           <h2 className="text-xl font-bold text-rose-800 dark:text-rose-300">
//             Evaluation Result Unavailable
//           </h2>

//           <p className="mt-3 text-sm text-rose-700 dark:text-rose-400">
//             {error ||
//               'No evaluation result was found.'}
//           </p>

//           <button
//             type="button"
//             onClick={() => router.push('/')}
//             className="mt-6 inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
//           >
//             Run New Evaluation
//           </button>

//         </div>

//       </div>
//     );
//   }

//   /*
//    * -------------------------------------------------------
//    * Actual backend instances
//    * -------------------------------------------------------
//    */

//   const instances = Array.isArray(data.instances)
//     ? data.instances
//     : [];

//   /*
//    * -------------------------------------------------------
//    * Overall score
//    *
//    * Backend:
//    *
//    * metadata.distance_mean
//    * -------------------------------------------------------
//    */

//   const meanDistance =
//     typeof data.metadata?.distance_mean === 'number'
//       ? data.metadata.distance_mean
//       : average(
//           instances.map(getDistance)
//         );

//   const medianDistance =
//     typeof data.metadata?.distance_median === 'number'
//       ? data.metadata.distance_median
//       : null;

//   const maximumDistance =
//     typeof data.metadata?.distance_max === 'number'
//       ? data.metadata.distance_max
//       : null;

//   const minimumDistance =
//     typeof data.metadata?.distance_min === 'number'
//       ? data.metadata.distance_min
//       : null;

//   const instanceCount =
//     typeof data.metadata?.instance_count === 'number'
//       ? data.metadata.instance_count
//       : instances.length;

//   /*
//    * -------------------------------------------------------
//    * Self check
//    * -------------------------------------------------------
//    *
//    * Your backend currently returns:
//    *
//    * self_check: null
//    *
//    * Therefore we correctly display:
//    *
//    * Self-Check: NOT RUN
//    *
//    * instead of incorrectly showing PASSED.
//    */

//   const selfCheck = data.self_check;

//   /*
//    * -------------------------------------------------------
//    * Setting scores
//    * -------------------------------------------------------
//    */

//   const settingScores = {
//     A: calculateSettingScore(
//       instances,
//       'A'
//     ),

//     B: calculateSettingScore(
//       instances,
//       'B'
//     ),

//     C: calculateSettingScore(
//       instances,
//       'C'
//     ),
//   };

//   /*
//    * -------------------------------------------------------
//    * Family scores
//    * -------------------------------------------------------
//    */

//   const familyScores = {
//     distributional:
//       calculateFamilyScore(
//         instances,
//         'distributional'
//       ),

//     trend:
//       calculateFamilyScore(
//         instances,
//         'trend'
//       ),

//     seasonality:
//       calculateFamilyScore(
//         instances,
//         'seasonality'
//       ),

//     local:
//       calculateFamilyScore(
//         instances,
//         'local'
//       ),
//   };

//   /*
//    * -------------------------------------------------------
//    * Setting query counts
//    * -------------------------------------------------------
//    */

//   const settingCounts = {
//     A: getSettingInstances(
//       instances,
//       'A'
//     ).length,

//     B: getSettingInstances(
//       instances,
//       'B'
//     ).length,

//     C: getSettingInstances(
//       instances,
//       'C'
//     ).length,
//   };

//   /*
//    * -------------------------------------------------------
//    * Family query counts
//    * -------------------------------------------------------
//    */

//   const familyCounts = {
//     distributional:
//       getFamilyInstances(
//         instances,
//         'distributional'
//       ).length,

//     trend:
//       getFamilyInstances(
//         instances,
//         'trend'
//       ).length,

//     seasonality:
//       getFamilyInstances(
//         instances,
//         'seasonality'
//       ).length,

//     local:
//       getFamilyInstances(
//         instances,
//         'local'
//       ).length,
//   };

//   /*
//    * -------------------------------------------------------
//    * Overall score color
//    * -------------------------------------------------------
//    */

//   const overallColors =
//     meanDistance !== null
//       ? getScoreColor(meanDistance)
//       : {
//           border: 'border-slate-300',
//           bg: 'bg-slate-50',
//           text: 'text-slate-500',
//         };

//   return (
//     <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">

//       {/* ===================================================
//           OVERALL FIDELITY
//           =================================================== */}

//       <section
//         className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm p-7"
//       >

//         <div className="flex flex-col md:flex-row items-center justify-between gap-8">

//           {/* Left */}
//           <div className="flex-1">

//             <div className="flex items-center gap-2 flex-wrap">

//               <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
//                 Mean Fidelity Distance
//               </h1>

//               {selfCheck === null ||
//               selfCheck === undefined ? (
//                 <span className="text-xs px-3 py-1 rounded-full font-mono font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
//                   Self-Check: NOT RUN
//                 </span>
//               ) : (
//                 <span className="text-xs px-3 py-1 rounded-full font-mono font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
//                   Self-Check: AVAILABLE
//                 </span>
//               )}

//             </div>

//             <p className="mt-3 text-base text-slate-500 dark:text-slate-400 max-w-2xl">
//               Normalized fidelity distance across all
//               evaluated query instances. Lower values
//               represent higher fidelity to ground-truth
//               time series.
//             </p>

//             <div className="flex flex-wrap gap-x-6 gap-y-2 mt-5 text-sm text-slate-500">

//               <span>
//                 Instances:{' '}
//                 <strong className="text-slate-700 dark:text-slate-300">
//                   {instanceCount}
//                 </strong>
//               </span>

//               <span>
//                 Median:{' '}
//                 <strong className="text-slate-700 dark:text-slate-300">
//                   {formatScore(
//                     medianDistance ?? 0
//                   )}
//                 </strong>
//               </span>

//               <span>
//                 Min:{' '}
//                 <strong className="text-slate-700 dark:text-slate-300">
//                   {formatScore(
//                     minimumDistance ?? 0
//                   )}
//                 </strong>
//               </span>

//               <span>
//                 Max:{' '}
//                 <strong className="text-slate-700 dark:text-slate-300">
//                   {formatScore(
//                     maximumDistance ?? 0
//                   )}
//                 </strong>
//               </span>

//             </div>

//           </div>


//           {/* Overall score */}
//           <div
//             className={`shrink-0 flex flex-col items-center justify-center h-32 w-32 rounded-full border-2 ${overallColors.border} ${overallColors.bg}`}
//           >

//             <span
//               className={`text-3xl font-black ${overallColors.text}`}
//             >
//               {formatScore(
//                 meanDistance ?? 0
//               )}
//             </span>

//             <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
//               Distance
//             </span>

//           </div>

//         </div>

//       </section>


//       {/* ===================================================
//           SETTINGS
//           =================================================== */}

//       <section className="space-y-4">

//         <div>

//           <h2 className="text-xl font-bold text-slate-900 dark:text-white">
//             Evaluation Lenses (Settings A / B / C)
//           </h2>

//           <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
//             Click any setting to view its query battery
//             organized across the four taxonomy families.
//           </p>

//         </div>


//         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

//           {SETTINGS.map((setting) => {

//             const score =
//               settingScores[setting.id];

//             const similarity =
//               getSimilarityPercent(score);

//             const colors =
//               score !== null
//                 ? getScoreColor(score)
//                 : {
//                     border:
//                       'border-slate-200',
//                     bg:
//                       'bg-white dark:bg-slate-900',
//                     text:
//                       'text-slate-500',
//                   };

//             return (
//               <button
//                 key={setting.id}
//                 type="button"
//                 onClick={() =>
//                   router.push(
//                     `/dashboard/${setting.id}`
//                   )
//                 }
//                 className={`group text-left rounded-2xl border-2 ${colors.border} ${colors.bg} p-6 hover:shadow-lg hover:-translate-y-1 transition-all cursor-pointer`}
//               >

//                 {/* Header */}
//                 <div className="flex items-start justify-between gap-3">

//                   <div>

//                     <h3 className="text-xl font-bold text-slate-900 dark:text-white">
//                       {setting.name}
//                     </h3>

//                     <p className="mt-1 text-xs font-medium text-slate-500">
//                       {setting.title}
//                     </p>

//                   </div>

//                   <ScoreBadge score={score} />

//                 </div>


//                 {/* Score */}
//                 <div className="mt-6">

//                   <p className="text-xs uppercase tracking-wider font-bold text-slate-400">
//                     Distance Score
//                   </p>

//                   <p
//                     className={`mt-1 text-4xl font-black ${colors.text}`}
//                   >
//                     {formatScore(
//                       score ?? 0
//                     )}
//                   </p>

//                 </div>


//                 {/* Similarity */}
//                 <div className="mt-6">

//                   <div className="flex items-center justify-between mb-2">

//                     <span className="text-xs text-slate-500">
//                       Data Similarity Profile
//                     </span>

//                     <span className="text-xs font-semibold text-slate-500">
//                       {score === null
//                         ? '—'
//                         : `${similarity}%`}
//                     </span>

//                   </div>

//                   <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">

//                     <div
//                       className="h-full rounded-full bg-emerald-500 transition-all duration-500"
//                       style={{
//                         width:
//                           score === null
//                             ? '0%'
//                             : `${similarity}%`,
//                       }}
//                     />

//                   </div>

//                 </div>


//                 {/* Description */}
//                 <p className="mt-5 text-xs leading-5 text-slate-500 dark:text-slate-400">
//                   {setting.desc}
//                 </p>


//                 {/* Navigation */}
//                 <div className="mt-5 flex items-center justify-between">

//                   <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 group-hover:underline">
//                     View Setting {setting.id} →
//                   </span>

//                   <span className="text-xs text-slate-400">
//                     {settingCounts[setting.id]} queries
//                   </span>

//                 </div>

//               </button>
//             );
//           })}

//         </div>

//       </section>


//       {/* ===================================================
//           FAMILY OVERVIEW
//           =================================================== */}

//       <section className="space-y-4">

//         <div>

//           <h2 className="text-xl font-bold text-slate-900 dark:text-white">
//             Taxonomy V3 Families Overview
//           </h2>

//           <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
//             Aggregated fidelity distance across the actual
//             query instances returned by the backend.
//           </p>

//         </div>


//         <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">

//           {FAMILIES.map((family) => {

//             const score =
//               familyScores[family.id];

//             const count =
//               familyCounts[family.id];

//             const colors =
//               score !== null
//                 ? getScoreColor(score)
//                 : {
//                     border:
//                       'border-slate-200',
//                     bg:
//                       'bg-white dark:bg-slate-900',
//                     text:
//                       'text-slate-500',
//                   };

//             return (
//               <div
//                 key={family.id}
//                 className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-sm"
//               >

//                 <div className="flex items-start justify-between gap-3">

//                   <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
//                     {family.name}
//                   </h3>

//                   <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
//                     {count}
//                   </span>

//                 </div>

//                 <p
//                   className={`mt-3 text-3xl font-black ${colors.text}`}
//                 >
//                   {formatScore(
//                     score ?? 0
//                   )}
//                 </p>

//                 <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
//                   {family.desc}
//                 </p>

//               </div>
//             );

//           })}

//         </div>

//       </section>


//       {/* ===================================================
//           BACKEND RESULT INFORMATION
//           =================================================== */}

//       <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-5">

//         <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">

//           <div>

//             <p className="text-xs uppercase tracking-wider font-bold text-slate-400">
//               Evaluation Summary
//             </p>

//             <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">

//               {instanceCount} query instances evaluated
//               across{' '}

//               {Array.isArray(
//                 data.overview?.settings
//               )
//                 ? data.overview.settings.length
//                 : 3}{' '}

//               settings and{' '}

//               {Array.isArray(
//                 data.overview?.families
//               )
//                 ? data.overview.families.length
//                 : 4}{' '}

//               taxonomy families.

//             </p>

//           </div>


//           <div className="flex items-center gap-3">

//             <span className="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500">
//               Mode:{' '}
//               <strong className="text-slate-700 dark:text-slate-300">
//                 {data.mode ||
//                   'real_synthetic'}
//               </strong>
//             </span>

//             <button
//               type="button"
//               onClick={() =>
//                 router.push('/')
//               }
//               className="inline-flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-indigo-600 transition-colors"
//             >
//               New Evaluation
//             </button>

//           </div>

//         </div>

//       </section>

//     </div>
//   );
// }




'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  formatScore,
  getScoreColor,
} from '@/utils/helpers';

/* =========================================================
   SETTINGS
   ========================================================= */

const SETTINGS = [
  {
    id: 'A',
    name: 'Setting A',
    title: 'Single Time-Series',
    desc: 'One grouped series & one measurement — shape of a single curve, persistence, seasonality, and local patterns.',
  },
  {
    id: 'B',
    name: 'Setting B',
    title: 'Cross-Measurement Structure',
    desc: 'Cross-measurement structure and correlation drift within the same grouped series.',
  },
  {
    id: 'C',
    name: 'Setting C',
    title: 'Population of Series',
    desc: 'Population-level distributions, shared trajectories, and phase-sharing across series.',
  },
];

/* =========================================================
   FAMILIES
   ========================================================= */

const FAMILIES = [
  {
    id: 'distributional',
    name: 'Distributional',
    shortName: 'Distributional',
    desc: 'Order-invariant summaries & covariance',
  },
  {
    id: 'trend',
    name: 'Trend & Drift',
    shortName: 'Trend',
    desc: 'Slope, drift, and persistence',
  },
  {
    id: 'seasonality',
    name: 'Seasonality & Recurrence',
    shortName: 'Seasonality',
    desc: 'Cycles, spectral energy & coherence',
  },
  {
    id: 'local',
    name: 'Local Patterns',
    shortName: 'Local',
    desc: 'Matrix profile motifs & discords',
  },
];

/* =========================================================
   HELPERS
   ========================================================= */

function getDistance(instance) {
  const value = instance?.distance;

  return typeof value === 'number' &&
    Number.isFinite(value)
    ? value
    : null;
}

function average(values) {
  const valid = values.filter(
    (value) =>
      typeof value === 'number' &&
      Number.isFinite(value)
  );

  if (valid.length === 0) {
    return null;
  }

  return (
    valid.reduce(
      (sum, value) => sum + value,
      0
    ) / valid.length
  );
}

function getSettingInstances(
  instances,
  settingId
) {
  return instances.filter(
    (instance) =>
      String(
        instance?.setting || ''
      ).toUpperCase() === settingId
  );
}

function getFamilyInstances(
  instances,
  familyId
) {
  return instances.filter(
    (instance) =>
      String(
        instance?.family || ''
      ).toLowerCase() === familyId
  );
}

function calculateSettingScore(
  instances,
  settingId
) {
  const settingInstances =
    getSettingInstances(
      instances,
      settingId
    );

  return average(
    settingInstances.map(getDistance)
  );
}

function calculateFamilyScore(
  instances,
  familyId
) {
  const familyInstances =
    getFamilyInstances(
      instances,
      familyId
    );

  return average(
    familyInstances.map(getDistance)
  );
}

function getScoreLabel(score) {
  if (
    score === null ||
    score === undefined ||
    !Number.isFinite(score)
  ) {
    return 'No Data';
  }

  if (score <= 0.05) {
    return 'Excellent Match';
  }

  if (score <= 0.15) {
    return 'Good Match';
  }

  if (score <= 0.30) {
    return 'Moderate Match';
  }

  return 'Low Fidelity';
}

function getSimilarityPercent(score) {
  if (
    score === null ||
    score === undefined ||
    !Number.isFinite(score)
  ) {
    return 0;
  }

  return Math.max(
    0,
    Math.min(
      100,
      Math.round((1 - score) * 100)
    )
  );
}

/* =========================================================
   SCORE BADGE
   ========================================================= */

function ScoreBadge({ score }) {
  if (
    score === null ||
    score === undefined ||
    !Number.isFinite(score)
  ) {
    return (
      <span className="inline-flex px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
        No Score
      </span>
    );
  }

  const colors =
    getScoreColor(score);

  return (
    <span
      className={`inline-flex px-3 py-1 rounded-full text-xs font-semibold border ${colors.bg} ${colors.text} ${colors.border}`}
    >
      {getScoreLabel(score)}
    </span>
  );
}

/* =========================================================
   MAIN DASHBOARD
   ========================================================= */

export default function DashboardPage() {
  const router = useRouter();

  const [data, setData] =
    useState(null);

  const [loading, setLoading] =
    useState(true);

  const [error, setError] =
    useState('');

  /* =======================================================
     LOAD RESULT
     ======================================================= */

  useEffect(() => {
    try {
      const raw =
        localStorage.getItem(
          'evaluationResult'
        ) ||
        localStorage.getItem(
          'syntheticEvalData'
        ) ||
        localStorage.getItem(
          'timeSeriesEvalData'
        );

      if (!raw) {
        setError(
          'No evaluation result found. Please run an evaluation from the home page.'
        );

        return;
      }

      const parsed =
        JSON.parse(raw);

      if (
        !parsed ||
        !Array.isArray(
          parsed.instances
        )
      ) {
        setError(
          'The evaluation result is invalid or does not contain query instances.'
        );

        return;
      }

      setData(parsed);
    } catch (err) {
      console.error(
        'Failed to load evaluation result:',
        err
      );

      setError(
        'Failed to read the evaluation result. Please run the evaluation again.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  /* =======================================================
     LOADING
     ======================================================= */

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center">

          <div className="mx-auto h-8 w-8 rounded-full border-4 border-slate-200 border-t-indigo-600 animate-spin" />

          <p className="mt-4 text-sm text-slate-500">
            Loading evaluation results...
          </p>

        </div>
      </div>
    );
  }

  /* =======================================================
     ERROR
     ======================================================= */

  if (error || !data) {
    return (
      <div className="max-w-3xl mx-auto py-16 px-4">

        <div className="rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 p-8 text-center">

          <h2 className="text-xl font-bold text-rose-800 dark:text-rose-300">
            Evaluation Result Unavailable
          </h2>

          <p className="mt-3 text-sm text-rose-700 dark:text-rose-400">
            {error ||
              'No evaluation result was found.'}
          </p>

          <button
            type="button"
            onClick={() =>
              router.push('/')
            }
            className="mt-6 inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
          >
            Run New Evaluation
          </button>

        </div>

      </div>
    );
  }

  /* =======================================================
     ACTUAL INSTANCES
     ======================================================= */

  const instances =
    Array.isArray(data.instances)
      ? data.instances
      : [];

  /*
   * IMPORTANT:
   *
   * Backend modes:
   *
   * real_only
   * real_synthetic
   */

  const isRealOnly =
    data.mode === 'real_only';

  const isRealSynthetic =
    data.mode === 'real_synthetic';

  /*
   * If mode is missing for an old stored result,
   * treat it as comparison mode because that is
   * how the old dashboard behaved.
   */

  const comparisonMode =
    isRealSynthetic ||
    (!isRealOnly &&
      data.mode !== 'real_only');

  /* =======================================================
     COUNTS
     ======================================================= */

  const instanceCount =
    typeof data.metadata?.instance_count ===
      'number'
      ? data.metadata.instance_count
      : instances.length;

  const settingCounts = {
    A: getSettingInstances(
      instances,
      'A'
    ).length,

    B: getSettingInstances(
      instances,
      'B'
    ).length,

    C: getSettingInstances(
      instances,
      'C'
    ).length,
  };

  const familyCounts = {
    distributional:
      getFamilyInstances(
        instances,
        'distributional'
      ).length,

    trend:
      getFamilyInstances(
        instances,
        'trend'
      ).length,

    seasonality:
      getFamilyInstances(
        instances,
        'seasonality'
      ).length,

    local:
      getFamilyInstances(
        instances,
        'local'
      ).length,
  };

  /* =======================================================
     COMPARISON-ONLY CALCULATIONS
     ======================================================= */

  const meanDistance =
    comparisonMode
      ? (
          typeof data.metadata
            ?.distance_mean ===
            'number'
            ? data.metadata.distance_mean
            : average(
                instances.map(
                  getDistance
                )
              )
        )
      : null;

  const medianDistance =
    comparisonMode
      ? (
          typeof data.metadata
            ?.distance_median ===
            'number'
            ? data.metadata.distance_median
            : null
        )
      : null;

  const maximumDistance =
    comparisonMode
      ? (
          typeof data.metadata
            ?.distance_max ===
            'number'
            ? data.metadata.distance_max
            : null
        )
      : null;

  const minimumDistance =
    comparisonMode
      ? (
          typeof data.metadata
            ?.distance_min ===
            'number'
            ? data.metadata.distance_min
            : null
        )
      : null;

  /* =======================================================
     SETTING SCORES
     ======================================================= */

  const settingScores = {
    A: comparisonMode
      ? calculateSettingScore(
          instances,
          'A'
        )
      : null,

    B: comparisonMode
      ? calculateSettingScore(
          instances,
          'B'
        )
      : null,

    C: comparisonMode
      ? calculateSettingScore(
          instances,
          'C'
        )
      : null,
  };

  /* =======================================================
     FAMILY SCORES
     ======================================================= */

  const familyScores = {
    distributional:
      comparisonMode
        ? calculateFamilyScore(
            instances,
            'distributional'
          )
        : null,

    trend:
      comparisonMode
        ? calculateFamilyScore(
            instances,
            'trend'
          )
        : null,

    seasonality:
      comparisonMode
        ? calculateFamilyScore(
            instances,
            'seasonality'
          )
        : null,

    local:
      comparisonMode
        ? calculateFamilyScore(
            instances,
            'local'
          )
        : null,
  };

  const selfCheck =
    data.self_check;

  /* =======================================================
     REAL-ONLY DASHBOARD
     ======================================================= */

  if (isRealOnly) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">

        {/* =================================================
            HEADER
            ================================================= */}

        <section className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm p-7">

          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">

            <div>

              <div className="flex items-center gap-3 flex-wrap">

                <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                  Real Data Query Profiles
                </h1>

                <span className="text-xs px-3 py-1 rounded-full font-mono font-semibold bg-indigo-50 text-indigo-600 border border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-400 dark:border-indigo-800">
                  REAL ONLY
                </span>

              </div>

              <p className="mt-3 text-base text-slate-500 dark:text-slate-400 max-w-3xl">
                Query profiles extracted from the
                uploaded real dataset using the
                selected Taxonomy V3 specification.
              </p>

            </div>

            <div className="shrink-0 text-center px-6 py-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900">

              <div className="text-3xl font-black text-indigo-600 dark:text-indigo-400">
                {instanceCount}
              </div>

              <div className="text-xs uppercase tracking-wider font-semibold text-slate-500">
                Query Instances
              </div>

            </div>

          </div>

        </section>


        {/* =================================================
            SETTINGS
            ================================================= */}

        <section className="space-y-4">

          <div>

            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              Evaluation Lenses
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Select a setting to view its query
              profiles organized across the four
              taxonomy families.
            </p>

          </div>


          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

            {SETTINGS.map(
              (setting) => {

                const count =
                  settingCounts[
                    setting.id
                  ];

                return (
                  <button
                    key={setting.id}
                    type="button"
                    onClick={() =>
                      router.push(
                        `/dashboard/${setting.id}`
                      )
                    }
                    className="group text-left rounded-2xl border-2 border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-7 hover:border-indigo-300 dark:hover:border-indigo-700 hover:shadow-lg hover:-translate-y-1 transition-all cursor-pointer"
                  >

                    {/* Header */}

                    <div className="flex items-start justify-between gap-3">

                      <div>

                        <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                          {setting.name}
                        </h3>

                        <p className="mt-1 text-xs font-medium text-slate-500 dark:text-slate-400">
                          {setting.title}
                        </p>

                      </div>

                      <span className="inline-flex px-3 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-600 border border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-400 dark:border-indigo-800">
                        Profiled
                      </span>

                    </div>


                    {/* Query Count */}

                    <div className="mt-7">

                      <p className="text-xs uppercase tracking-wider font-bold text-slate-400">
                        Query Profiles
                      </p>

                      <p className="mt-1 text-4xl font-black text-indigo-600 dark:text-indigo-400">
                        {count}
                      </p>

                      <p className="mt-1 text-sm text-slate-500">
                        {count === 1
                          ? 'query'
                          : 'queries'}{' '}
                        available
                      </p>

                    </div>


                    {/* Description */}

                    <p className="mt-6 text-xs leading-5 text-slate-500 dark:text-slate-400">
                      {setting.desc}
                    </p>


                    {/* Navigation */}

                    <div className="mt-6 flex items-center justify-between">

                      <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 group-hover:underline">
                        View Setting{' '}
                        {setting.id} →
                      </span>

                      <span className="text-xs text-slate-400">
                        {count} queries
                      </span>

                    </div>

                  </button>
                );
              }
            )}

          </div>

        </section>


        {/* =================================================
            FAMILY OVERVIEW
            ================================================= */}

        <section className="space-y-4">

          <div>

            <h2 className="text-xl font-bold text-slate-900 dark:text-white">
              Taxonomy V3 Families Overview
            </h2>

            <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
              Number of real-data query profiles
              available in each taxonomy family.
            </p>

          </div>


          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">

            {FAMILIES.map(
              (family) => {

                const count =
                  familyCounts[
                    family.id
                  ];

                return (
                  <div
                    key={family.id}
                    className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-sm"
                  >

                    <div className="flex items-start justify-between gap-3">

                      <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                        {family.name}
                      </h3>

                      <span className="text-xs px-2 py-1 rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-950/40 dark:text-indigo-400">
                        {count}
                      </span>

                    </div>

                    <p className="mt-3 text-3xl font-black text-indigo-600 dark:text-indigo-400">
                      {count}
                    </p>

                    <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
                      {family.desc}
                    </p>

                  </div>
                );
              }
            )}

          </div>

        </section>


        {/* =================================================
            SUMMARY
            ================================================= */}

        <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-5">

          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">

            <div>

              <p className="text-xs uppercase tracking-wider font-bold text-slate-400">
                Evaluation Summary
              </p>

              <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
                {instanceCount} query profiles
                extracted from the real dataset
                across 3 settings and 4 taxonomy
                families.
              </p>

            </div>

            <div className="flex items-center gap-3">

              <span className="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500">
                Mode:{' '}
                <strong className="text-slate-700 dark:text-slate-300">
                  real_only
                </strong>
              </span>

              <button
                type="button"
                onClick={() =>
                  router.push('/')
                }
                className="inline-flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-indigo-600 transition-colors"
              >
                New Evaluation
              </button>

            </div>

          </div>

        </section>

      </div>
    );
  }

  /* =======================================================
     REAL + SYNTHETIC DASHBOARD
     ======================================================= */

  const overallColors =
    meanDistance !== null
      ? getScoreColor(
          meanDistance
        )
      : {
          border:
            'border-slate-300',
          bg: 'bg-slate-50',
          text: 'text-slate-500',
        };

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">

      {/* =================================================
          OVERALL FIDELITY
          ================================================= */}

      <section className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-sm p-7">

        <div className="flex flex-col md:flex-row items-center justify-between gap-8">

          <div className="flex-1">

            <div className="flex items-center gap-2 flex-wrap">

              <h1 className="text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                Mean Fidelity Distance
              </h1>

              {selfCheck === null ||
              selfCheck === undefined ? (
                <span className="text-xs px-3 py-1 rounded-full font-mono font-semibold bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400">
                  Self-Check: NOT RUN
                </span>
              ) : (
                <span className="text-xs px-3 py-1 rounded-full font-mono font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
                  Self-Check: AVAILABLE
                </span>
              )}

            </div>

            <p className="mt-3 text-base text-slate-500 dark:text-slate-400 max-w-2xl">
              Normalized fidelity distance
              across all evaluated query
              instances. Lower values represent
              higher fidelity to the real
              time-series data.
            </p>

            <div className="flex flex-wrap gap-x-6 gap-y-2 mt-5 text-sm text-slate-500">

              <span>
                Instances:{' '}
                <strong className="text-slate-700 dark:text-slate-300">
                  {instanceCount}
                </strong>
              </span>

              <span>
                Median:{' '}
                <strong className="text-slate-700 dark:text-slate-300">
                  {formatScore(
                    medianDistance ??
                      0
                  )}
                </strong>
              </span>

              <span>
                Min:{' '}
                <strong className="text-slate-700 dark:text-slate-300">
                  {formatScore(
                    minimumDistance ??
                      0
                  )}
                </strong>
              </span>

              <span>
                Max:{' '}
                <strong className="text-slate-700 dark:text-slate-300">
                  {formatScore(
                    maximumDistance ??
                      0
                  )}
                </strong>
              </span>

            </div>

          </div>


          {/* Overall score */}

          <div
            className={`shrink-0 flex flex-col items-center justify-center h-32 w-32 rounded-full border-2 ${overallColors.border} ${overallColors.bg}`}
          >

            <span
              className={`text-3xl font-black ${overallColors.text}`}
            >
              {formatScore(
                meanDistance ??
                  0
              )}
            </span>

            <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
              Distance
            </span>

          </div>

        </div>

      </section>


      {/* =================================================
          SETTINGS
          ================================================= */}

      <section className="space-y-4">

        <div>

          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Evaluation Lenses
            {' '}
            (Settings A / B / C)
          </h2>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Click any setting to view its query
            battery organized across the four
            taxonomy families.
          </p>

        </div>


        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

          {SETTINGS.map(
            (setting) => {

              const score =
                settingScores[
                  setting.id
                ];

              const similarity =
                getSimilarityPercent(
                  score
                );

              const colors =
                score !== null
                  ? getScoreColor(
                      score
                    )
                  : {
                      border:
                        'border-slate-200',
                      bg:
                        'bg-white dark:bg-slate-900',
                      text:
                        'text-slate-500',
                    };

              return (
                <button
                  key={setting.id}
                  type="button"
                  onClick={() =>
                    router.push(
                      `/dashboard/${setting.id}`
                    )
                  }
                  className={`group text-left rounded-2xl border-2 ${colors.border} ${colors.bg} p-6 hover:shadow-lg hover:-translate-y-1 transition-all cursor-pointer`}
                >

                  <div className="flex items-start justify-between gap-3">

                    <div>

                      <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                        {setting.name}
                      </h3>

                      <p className="mt-1 text-xs font-medium text-slate-500">
                        {setting.title}
                      </p>

                    </div>

                    <ScoreBadge
                      score={score}
                    />

                  </div>


                  <div className="mt-6">

                    <p className="text-xs uppercase tracking-wider font-bold text-slate-400">
                      Distance Score
                    </p>

                    <p
                      className={`mt-1 text-4xl font-black ${colors.text}`}
                    >
                      {formatScore(
                        score ?? 0
                      )}
                    </p>

                  </div>


                  <div className="mt-6">

                    <div className="flex items-center justify-between mb-2">

                      <span className="text-xs text-slate-500">
                        Data Similarity
                      </span>

                      <span className="text-xs font-semibold text-slate-500">
                        {score === null
                          ? '—'
                          : `${similarity}%`}
                      </span>

                    </div>

                    <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">

                      <div
                        className="h-full rounded-full bg-emerald-500 transition-all duration-500"
                        style={{
                          width:
                            score ===
                            null
                              ? '0%'
                              : `${similarity}%`,
                        }}
                      />

                    </div>

                  </div>


                  <p className="mt-5 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    {setting.desc}
                  </p>


                  <div className="mt-5 flex items-center justify-between">

                    <span className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 group-hover:underline">
                      View Setting{' '}
                      {setting.id} →
                    </span>

                    <span className="text-xs text-slate-400">
                      {
                        settingCounts[
                          setting.id
                        ]
                      }{' '}
                      queries
                    </span>

                  </div>

                </button>
              );
            }
          )}

        </div>

      </section>


      {/* =================================================
          FAMILY OVERVIEW
          ================================================= */}

      <section className="space-y-4">

        <div>

          <h2 className="text-xl font-bold text-slate-900 dark:text-white">
            Taxonomy V3 Families Overview
          </h2>

          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
            Aggregated fidelity distance across
            the actual query instances returned
            by the backend.
          </p>

        </div>


        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">

          {FAMILIES.map(
            (family) => {

              const score =
                familyScores[
                  family.id
                ];

              const count =
                familyCounts[
                  family.id
                ];

              const colors =
                score !== null
                  ? getScoreColor(
                      score
                    )
                  : {
                      border:
                        'border-slate-200',
                      bg:
                        'bg-white dark:bg-slate-900',
                      text:
                        'text-slate-500',
                    };

              return (
                <div
                  key={family.id}
                  className="rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-sm"
                >

                  <div className="flex items-start justify-between gap-3">

                    <h3 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                      {family.name}
                    </h3>

                    <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
                      {count}
                    </span>

                  </div>

                  <p
                    className={`mt-3 text-3xl font-black ${colors.text}`}
                  >
                    {formatScore(
                      score ?? 0
                    )}
                  </p>

                  <p className="mt-2 text-xs leading-5 text-slate-500 dark:text-slate-400">
                    {family.desc}
                  </p>

                </div>
              );
            }
          )}

        </div>

      </section>


      {/* =================================================
          SUMMARY
          ================================================= */}

      <section className="rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-5">

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">

          <div>

            <p className="text-xs uppercase tracking-wider font-bold text-slate-400">
              Evaluation Summary
            </p>

            <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
              {instanceCount} query instances
              evaluated across 3 settings and
              4 taxonomy families.
            </p>

          </div>


          <div className="flex items-center gap-3">

            <span className="text-xs px-3 py-1.5 rounded-full bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-500">
              Mode:{' '}
              <strong className="text-slate-700 dark:text-slate-300">
                real_synthetic
              </strong>
            </span>

            <button
              type="button"
              onClick={() =>
                router.push('/')
              }
              className="inline-flex items-center justify-center rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2 text-xs font-semibold text-slate-700 dark:text-slate-300 hover:text-indigo-600 transition-colors"
            >
              New Evaluation
            </button>

          </div>

        </div>

      </section>

    </div>
  );
}