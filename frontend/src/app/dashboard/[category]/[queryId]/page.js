// 'use client';

// import Link from 'next/link';
// import { useParams } from 'next/navigation';
// import { useEffect, useState } from 'react';

// import ComparisonChart from '@/components/ComparisonChart';
// import {
//   formatScore,
//   getScoreColor,
// } from '@/utils/helpers';

// /* =========================================================
//    Helpers
//    ========================================================= */

// function normalizeSetting(value) {
//   return String(value || '')
//     .trim()
//     .toUpperCase();
// }

// function normalizeQueryId(value) {
//   return decodeURIComponent(
//     String(value || '')
//   ).trim();
// }

// function getInstanceScore(instance) {
//   if (
//     typeof instance?.distance === 'number' &&
//     Number.isFinite(instance.distance)
//   ) {
//     return instance.distance;
//   }

//   return 0;
// }

// function prettyFamilyName(family) {
//   if (!family) {
//     return 'Unknown';
//   }

//   const names = {
//     distributional: 'Distributional',
//     trend: 'Trend & Drift',
//     seasonality: 'Seasonality & Recurrence',
//     local: 'Local Patterns',
//   };

//   return (
//     names[String(family).toLowerCase()] ||
//     String(family)
//       .replace(/_/g, ' ')
//       .replace(/\b\w/g, (char) =>
//         char.toUpperCase()
//       )
//   );
// }

// function formatValue(value) {
//   if (
//     value === null ||
//     value === undefined
//   ) {
//     return '—';
//   }

//   if (typeof value === 'number') {
//     return Number.isFinite(value)
//       ? String(value)
//       : '—';
//   }

//   if (typeof value === 'string') {
//     return value;
//   }

//   try {
//     return JSON.stringify(value);
//   } catch {
//     return String(value);
//   }
// }

// /* =========================================================
//    Page
//    ========================================================= */

// export default function QueryDetailPage() {
//   const params = useParams();

//   /*
//    * URL structure:
//    *
//    * /dashboard/[category]/[queryId]
//    *
//    * Example:
//    *
//    * /dashboard/A/mean
//    */

//   const rawCategory = params?.category;

//   const category = normalizeSetting(
//     Array.isArray(rawCategory)
//       ? rawCategory[0]
//       : rawCategory
//   );

//   /*
//    * Support both queryId and query so this page remains
//    * compatible with any existing links.
//    */

//   const rawQueryParam =
//     params?.queryId ??
//     params?.query ??
//     '';

//   const rawQueryId = normalizeQueryId(
//     Array.isArray(rawQueryParam)
//       ? rawQueryParam[0]
//       : rawQueryParam
//   );

//   const [instance, setInstance] =
//     useState(null);

//   const [loading, setLoading] =
//     useState(true);

//   const [error, setError] =
//     useState('');

//   /* =======================================================
//      Load actual backend result
//      ======================================================= */

//   useEffect(() => {
//     setLoading(true);
//     setError('');
//     setInstance(null);

//     try {
//       /*
//        * New evaluation result.
//        *
//        * Keep old keys as fallbacks.
//        */

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
//           'The evaluation result does not contain a valid instances array.'
//         );

//         return;
//       }

//       const instances =
//         parsed.instances;

//       /*
//        * First try exact instance_id.
//        *
//        * Example:
//        *
//        * (single)::A::mean::LATITUDE[55,90)/TMAX
//        */

//       let found =
//         instances.find(
//           (item) =>
//             String(
//               item?.instance_id || ''
//             ) === rawQueryId
//         );

//       /*
//        * If instance_id isn't found, try qid.
//        *
//        * This is useful when the URL is:
//        *
//        * /dashboard/A/mean
//        */

//       if (!found) {
//         const matchingQueries =
//           instances.filter(
//             (item) =>
//               normalizeSetting(
//                 item?.setting
//               ) === category &&
//               String(
//                 item?.qid || ''
//               ) === rawQueryId
//           );

//         /*
//          * If multiple instances have the same qid,
//          * use the first one belonging to the selected
//          * setting.
//          */

//         found =
//           matchingQueries.length > 0
//             ? matchingQueries[0]
//             : null;
//       }

//       /*
//        * Last fallback:
//        *
//        * If the query ID is URL encoded and differs only
//        * in representation, try decoded instance_id.
//        */

//       if (!found) {
//         found =
//           instances.find(
//             (item) =>
//               decodeURIComponent(
//                 String(
//                   item?.instance_id || ''
//                 )
//               ) === rawQueryId
//           );
//       }

//       if (!found) {
//         setError(
//           `Query "${rawQueryId}" was not found in the evaluation result.`
//         );

//         return;
//       }

//       /*
//        * Make sure the query belongs to the
//        * Setting selected in the URL.
//        */

//       const instanceSetting =
//         normalizeSetting(
//           found.setting
//         );

//       if (
//         category &&
//         instanceSetting &&
//         instanceSetting !== category
//       ) {
//         setError(
//           `Query "${rawQueryId}" belongs to Setting ${instanceSetting}, not Setting ${category}.`
//         );

//         return;
//       }

//       setInstance(found);
//     } catch (err) {
//       console.error(
//         'Error reading evaluation result:',
//         err
//       );

//       setError(
//         'Failed to load the query evaluation result.'
//       );
//     } finally {
//       setLoading(false);
//     }
//   }, [category, rawQueryId]);

//   /* =======================================================
//      Loading
//      ======================================================= */

//   if (loading) {
//     return (
//       <div className="max-w-7xl mx-auto px-4 py-16">

//         <div className="flex justify-center">

//           <div className="text-center">

//             <div className="mx-auto h-8 w-8 rounded-full border-4 border-slate-200 border-t-indigo-600 animate-spin" />

//             <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
//               Loading query details...
//             </p>

//           </div>

//         </div>

//       </div>
//     );
//   }

//   /* =======================================================
//      Error
//      ======================================================= */

//   if (error || !instance) {
//     return (
//       <div className="max-w-7xl mx-auto px-4 py-10">

//         <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">

//           <Link
//             href="/dashboard"
//             className="hover:text-indigo-600 transition-colors"
//           >
//             Dashboard
//           </Link>

//           <span>&gt;</span>

//           <Link
//             href={`/dashboard/${category}`}
//             className="hover:text-indigo-600 transition-colors"
//           >
//             Setting {category}
//           </Link>

//           <span>&gt;</span>

//           <span className="text-slate-900 dark:text-white font-semibold">
//             Query
//           </span>

//         </nav>


//         <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 p-8 text-center">

//           <h2 className="text-xl font-bold text-rose-800 dark:text-rose-300">
//             Analytical Query Missing
//           </h2>

//           <p className="mt-2 text-sm text-rose-700 dark:text-rose-400">
//             {error ||
//               'The requested query could not be found.'}
//           </p>

//           <Link
//             href={`/dashboard/${category}`}
//             className="inline-flex mt-6 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
//           >
//             Return to Setting {category}
//           </Link>

//         </div>

//       </div>
//     );
//   }

//   /* =======================================================
//      Query information
//      ======================================================= */

//   const score =
//     getInstanceScore(instance);

//   const colorProfile =
//     getScoreColor(score);

//   const familyName =
//     prettyFamilyName(
//       instance.family
//     );

//   const realValue =
//     instance.real_value;

//   const syntheticValue =
//     instance.synth_value;

//   const queryId =
//     instance.qid ||
//     rawQueryId;

//   const focus =
//     instance.focus ||
//     'Whole Collection';

//   const kind =
//     instance.kind ||
//     'unknown';

//   const view =
//     instance.view ||
//     'Default View';

//   const instanceId =
//     instance.instance_id ||
//     rawQueryId;

//   /* =======================================================
//      Render
//      ======================================================= */

//   return (
//     <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">

//       {/* =====================================================
//           BREADCRUMB
//           ===================================================== */}

//       <nav className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2 flex-wrap">

//         <Link
//           href="/dashboard"
//           className="hover:text-indigo-600 transition-colors"
//         >
//           Dashboard
//         </Link>

//         <span>&gt;</span>

//         <Link
//           href={`/dashboard/${category}`}
//           className="hover:text-indigo-600 transition-colors font-semibold"
//         >
//           Setting {category}
//         </Link>

//         <span>&gt;</span>

//         <span className="text-slate-900 dark:text-white font-semibold font-mono">
//           {queryId}
//         </span>

//       </nav>


//       {/* =====================================================
//           HERO HEADER
//           ===================================================== */}

//       <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 bg-white border border-slate-200 rounded-2xl gap-5 dark:bg-slate-900 dark:border-slate-800 shadow-sm">

//         <div className="min-w-0">

//           <div className="flex items-center gap-2 flex-wrap">

//             <span className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
//               Setting {instance.setting || category}
//               {' • '}
//               {view}
//             </span>

//             {instance.mode && (
//               <span className="px-2 py-0.5 text-xs font-mono bg-slate-100 dark:bg-slate-800 rounded text-slate-600 dark:text-slate-300">
//                 Mode: {instance.mode}
//               </span>
//             )}

//           </div>


//           <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-2 break-words">
//             {queryId}
//           </h1>


//           <p className="text-xs font-mono text-slate-400 mt-2 break-all">
//             Focus: {focus}
//           </p>

//         </div>


//         {/* Score */}
//         <div className="text-left sm:text-right shrink-0">

//           <span className="text-xs font-semibold text-slate-400 block uppercase tracking-wider">
//             Fidelity Distance
//           </span>

//           <span
//             className={`text-3xl font-black ${colorProfile.text}`}
//           >
//             {formatScore(score)}
//           </span>

//           <span
//             className={`block mt-1 text-xs font-semibold ${colorProfile.text}`}
//           >
//             {colorProfile.label}
//           </span>

//         </div>

//       </div>


//       {/* =====================================================
//           MAIN GRID
//           ===================================================== */}

//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

//         {/* ===================================================
//             LEFT
//             =================================================== */}

//         <div className="space-y-6">


//           {/* Query Parameters */}
//           <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 space-y-4 shadow-sm">

//             <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
//               Query Execution Parameters
//             </h2>


//             <div className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">

//               {/* Family */}
//               <div className="py-3 flex justify-between gap-4">

//                 <span className="text-slate-500">
//                   Taxonomy Family
//                 </span>

//                 <span className="font-semibold text-slate-800 dark:text-slate-200 text-right">
//                   {familyName}
//                 </span>

//               </div>


//               {/* Setting */}
//               <div className="py-3 flex justify-between gap-4">

//                 <span className="text-slate-500">
//                   Evaluation Setting
//                 </span>

//                 <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
//                   Setting {instance.setting || category}
//                 </span>

//               </div>


//               {/* Query ID */}
//               <div className="py-3 flex justify-between gap-4">

//                 <span className="text-slate-500">
//                   Query ID
//                 </span>

//                 <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 text-right break-all">
//                   {queryId}
//                 </span>

//               </div>


//               {/* Kind */}
//               <div className="py-3 flex justify-between gap-4">

//                 <span className="text-slate-500">
//                   Return Type
//                 </span>

//                 <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase text-xs text-right">
//                   {kind}
//                 </span>

//               </div>


//               {/* Focus */}
//               <div className="py-3 flex justify-between gap-4">

//                 <span className="text-slate-500">
//                   Focus
//                 </span>

//                 <span className="font-mono text-xs text-slate-700 dark:text-slate-300 text-right max-w-[65%] break-all">
//                   {focus}
//                 </span>

//               </div>


//               {/* View */}
//               <div className="py-3 flex justify-between gap-4">

//                 <span className="text-slate-500">
//                   View
//                 </span>

//                 <span className="font-mono text-xs text-slate-700 dark:text-slate-300 text-right">
//                   {view}
//                 </span>

//               </div>


//               {/* Instance ID */}
//               <div className="py-3">

//                 <div className="flex justify-between gap-4">

//                   <span className="text-slate-500 shrink-0">
//                     Instance ID
//                   </span>

//                   <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400 text-right break-all max-w-[70%]">
//                     {instanceId}
//                   </span>

//                 </div>

//               </div>

//             </div>

//           </div>


//           {/* =================================================
//               REAL OUTPUT
//               ================================================= */}

//           <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 shadow-sm">

//             <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
//               Real Output
//             </h2>

//             <div className="mt-4 p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900">

//               <pre className="text-xs font-mono text-indigo-700 dark:text-indigo-300 whitespace-pre-wrap break-words overflow-x-auto">
//                 {formatValue(realValue)}
//               </pre>

//             </div>

//           </div>


//           {/* =================================================
//               SYNTHETIC OUTPUT
//               ================================================= */}

//           <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 shadow-sm">

//             <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
//               Synthetic Output
//             </h2>

//             <div className="mt-4 p-4 rounded-xl bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-100 dark:border-cyan-900">

//               <pre className="text-xs font-mono text-cyan-700 dark:text-cyan-300 whitespace-pre-wrap break-words overflow-x-auto">
//                 {formatValue(syntheticValue)}
//               </pre>

//             </div>

//           </div>


//           {/* =================================================
//               FIDELITY VERDICT
//               ================================================= */}

//           <div
//             className={`p-6 rounded-2xl border ${colorProfile.border} ${colorProfile.bg} text-sm space-y-2`}
//           >

//             <span className="font-bold text-slate-900 dark:text-slate-200 block">
//               Fidelity Benchmark Verdict
//             </span>

//             <p className="text-slate-600 dark:text-slate-300">

//               This query reports a normalized fidelity
//               distance of{' '}

//               <span className="font-bold font-mono">
//                 {formatScore(score)}
//               </span>
//               .

//             </p>

//             <p className="text-slate-600 dark:text-slate-300">

//               Fidelity rating:{' '}

//               <span className="font-bold uppercase tracking-wider">
//                 {colorProfile.label}
//               </span>

//             </p>

//             <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
//               Lower distance values indicate greater
//               similarity between the real and synthetic
//               query outputs.
//             </p>

//           </div>

//         </div>


//         {/* ===================================================
//             RIGHT — VISUALIZATION
//             =================================================== */}

//         <div className="space-y-3">

//           <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 pl-1">
//             Side-by-Side Fidelity Visualization
//           </h2>


//           <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">

//             <ComparisonChart
//               kind={kind}
//               realValue={realValue}
//               synthValue={syntheticValue}
//               qid={queryId}
//             />

//           </div>

//         </div>

//       </div>


//       {/* =====================================================
//           BOTTOM NAVIGATION
//           ===================================================== */}

//       <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">

//         <Link
//           href={`/dashboard/${category}`}
//           className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-indigo-600 hover:border-indigo-300 transition-colors"
//         >
//           ← Back to Setting {category}
//         </Link>


//         <Link
//           href="/dashboard"
//           className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
//         >
//           Dashboard
//         </Link>

//       </div>

//     </div>
//   );
// }


'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import ComparisonChart from '@/components/ComparisonChart';
import RealOnlyChart from '@/components/RealOnlyChart';

import {
  formatScore,
  getScoreColor,
} from '@/utils/helpers';

/* =========================================================
   Helpers
   ========================================================= */

function normalizeSetting(value) {
  return String(value || '').trim().toUpperCase();
}

function normalizeQueryId(value) {
  return decodeURIComponent(String(value || '')).trim();
}

function getScore(instance) {
  if (
    typeof instance?.distance === 'number' &&
    Number.isFinite(instance.distance)
  ) {
    return instance.distance;
  }

  return 0;
}

function getFamilyName(family) {
  const names = {
    distributional: 'Distributional',
    trend: 'Trend & Drift',
    seasonality: 'Seasonality & Recurrence',
    local: 'Local Patterns',
  };

  return (
    names[String(family || '').toLowerCase()] ||
    String(family || 'Unknown')
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())
  );
}

function formatOutput(value) {
  if (value === null || value === undefined) {
    return '—';
  }

  if (typeof value === 'number') {
    return Number.isFinite(value)
      ? String(value)
      : '—';
  }

  if (typeof value === 'string') {
    return value;
  }

  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

/*
 * IMPORTANT:
 *
 * real_only:
 *     value
 *
 * real_synthetic:
 *     real_value
 *     synth_value
 *
 * This helper keeps the mapping in one place.
 */
function getRealValue(instance, mode) {
  if (!instance) {
    return null;
  }

  if (mode === 'real_only') {
    return instance.value ?? null;
  }

  return instance.real_value ?? null;
}

function getSyntheticValue(instance, mode) {
  if (!instance || mode === 'real_only') {
    return null;
  }

  return instance.synth_value ?? null;
}

/* =========================================================
   Page
   ========================================================= */

export default function QueryDetailPage() {
  const params = useParams();

  /*
   * URL structure:
   *
   * /dashboard/[category]/[queryId]
   *
   * Example:
   *
   * /dashboard/A/mean
   */

  const category = normalizeSetting(
    Array.isArray(params?.category)
      ? params.category[0]
      : params?.category
  );

  const rawQueryParam =
    params?.queryId ??
    params?.query ??
    '';

  const rawQueryId = normalizeQueryId(
    Array.isArray(rawQueryParam)
      ? rawQueryParam[0]
      : rawQueryParam
  );

  /* =======================================================
     State
     ======================================================= */

  const [instance, setInstance] = useState(null);

  const [evaluationMode, setEvaluationMode] =
    useState('real_synthetic');

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState('');

  /* =======================================================
     Load evaluation result
     ======================================================= */

  useEffect(() => {
    setLoading(true);
    setError('');
    setInstance(null);

    try {
      /*
       * Try the newest storage key first.
       *
       * Keep the older keys as fallbacks so existing
       * evaluations continue to work.
       */

      const raw =
        localStorage.getItem('timeSeriesEvalData') ||
        localStorage.getItem('evaluationResult') ||
        localStorage.getItem('syntheticEvalData');

      if (!raw) {
        setError(
          'No evaluation result found. Please run an evaluation first.'
        );

        setLoading(false);
        return;
      }

      const parsed = JSON.parse(raw);

      console.log('Evaluation result:', parsed);

      if (
        !parsed ||
        !Array.isArray(parsed.instances)
      ) {
        setError(
          'Evaluation result does not contain a valid instances array.'
        );

        setLoading(false);
        return;
      }

      /*
       * Backend modes:
       *
       * real_only
       * real_synthetic
       */

      const mode =
        parsed.mode === 'real_only'
          ? 'real_only'
          : 'real_synthetic';

      setEvaluationMode(mode);

      console.log('Evaluation mode:', mode);

      const sourceInstances = parsed.instances;

      /* ===================================================
         Find query by instance_id first
         =================================================== */

      let found = sourceInstances.find(
        (item) =>
          String(item?.instance_id || '') ===
          rawQueryId
      );

      /* ===================================================
         Find query by setting + qid
         =================================================== */

      if (!found) {
        found = sourceInstances.find(
          (item) =>
            normalizeSetting(item?.setting) ===
              category &&
            String(item?.qid || '') ===
              rawQueryId
        );
      }

      /* ===================================================
         Decode instance_id and try again
         =================================================== */

      if (!found) {
        found = sourceInstances.find(
          (item) => {
            const instanceId =
              String(item?.instance_id || '');

            try {
              return (
                decodeURIComponent(instanceId) ===
                rawQueryId
              );
            } catch {
              return false;
            }
          }
        );
      }

      /* ===================================================
         Query not found
         =================================================== */

      if (!found) {
        setError(
          `Query "${rawQueryId}" was not found in the evaluation result.`
        );

        setLoading(false);
        return;
      }

      console.log(
        'Found query instance:',
        found
      );

      /* ===================================================
         Make sure query belongs to selected setting
         =================================================== */

      const instanceSetting =
        normalizeSetting(found.setting);

      if (
        category &&
        instanceSetting &&
        instanceSetting !== category
      ) {
        setError(
          `Query "${rawQueryId}" belongs to Setting ${instanceSetting}, not Setting ${category}.`
        );

        setLoading(false);
        return;
      }

      setInstance(found);
    } catch (err) {
      console.error(
        'Error loading query detail:',
        err
      );

      setError(
        'Failed to load the evaluation result.'
      );
    } finally {
      setLoading(false);
    }
  }, [category, rawQueryId]);

  /* =======================================================
     Loading UI
     ======================================================= */

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20">
        <div className="flex justify-center">
          <div className="text-center">

            <div className="mx-auto h-8 w-8 rounded-full border-4 border-slate-200 border-t-indigo-600 animate-spin" />

            <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
              Loading query details...
            </p>

          </div>
        </div>
      </div>
    );
  }

  /* =======================================================
     Error UI
     ======================================================= */

  if (!instance || error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-10">

        <nav className="text-sm font-medium text-slate-500 flex items-center gap-2">

          <Link
            href="/dashboard"
            className="hover:text-indigo-600 transition-colors"
          >
            Dashboard
          </Link>

          <span>&gt;</span>

          <Link
            href={`/dashboard/${category}`}
            className="hover:text-indigo-600 transition-colors"
          >
            Setting {category}
          </Link>

          <span>&gt;</span>

          <span className="text-slate-900 dark:text-white font-semibold">
            Query
          </span>

        </nav>

        <div className="mt-8 rounded-2xl border border-rose-200 bg-rose-50 dark:bg-rose-950/20 dark:border-rose-900 p-8 text-center">

          <h2 className="text-xl font-bold text-rose-800 dark:text-rose-300">
            Analytical Query Missing
          </h2>

          <p className="mt-2 text-sm text-rose-700 dark:text-rose-400">
            {error || 'The requested query could not be found.'}
          </p>

          <Link
            href={`/dashboard/${category}`}
            className="inline-flex mt-6 rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700"
          >
            Return to Setting {category}
          </Link>

        </div>

      </div>
    );
  }

  /* =======================================================
     Determine mode
     ======================================================= */

  const isRealOnly =
    evaluationMode === 'real_only';

  /*
   * REAL-ONLY:
   *
   * instance.value
   *
   * REAL + SYNTHETIC:
   *
   * instance.real_value
   * instance.synth_value
   */

  const realValue =
    getRealValue(
      instance,
      evaluationMode
    );

  const syntheticValue =
    getSyntheticValue(
      instance,
      evaluationMode
    );

  const score =
    getScore(instance);

  const colorProfile =
    getScoreColor(score);

  /* =======================================================
     Query information
     ======================================================= */

  const queryId =
    instance.qid ||
    rawQueryId;

  const familyName =
    getFamilyName(instance.family);

  const focus =
    instance.focus ||
    'Whole Collection';

  const kind =
    instance.kind ||
    instance.return_type ||
    'unknown';

  const view =
    instance.view ||
    'Default View';

  const setting =
    instance.setting ||
    category;

  const instanceId =
    instance.instance_id ||
    rawQueryId;

  /* =======================================================
     Render
     ======================================================= */

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">

      {/* =====================================================
          BREADCRUMB
          ===================================================== */}

      <nav className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2 flex-wrap">

        <Link
          href="/dashboard"
          className="hover:text-indigo-600 transition-colors"
        >
          Dashboard
        </Link>

        <span>&gt;</span>

        <Link
          href={`/dashboard/${category}`}
          className="hover:text-indigo-600 transition-colors font-semibold"
        >
          Setting {category}
        </Link>

        <span>&gt;</span>

        <span className="text-slate-900 dark:text-white font-semibold font-mono">
          {queryId}
        </span>

      </nav>


      {/* =====================================================
          HERO HEADER
          ===================================================== */}

      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 bg-white border border-slate-200 rounded-2xl gap-5 dark:bg-slate-900 dark:border-slate-800 shadow-sm">

        <div className="min-w-0">

          <div className="flex items-center gap-2 flex-wrap">

            <span className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
              Setting {setting}
              {' • '}
              {view}
            </span>

            {instance.mode && (
              <span className="px-2 py-0.5 text-xs font-mono bg-slate-100 dark:bg-slate-800 rounded text-slate-600 dark:text-slate-300">
                Mode: {instance.mode}
              </span>
            )}

          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-2 break-words">
            {queryId}
          </h1>

          <p className="text-xs font-mono text-slate-400 mt-2 break-all">
            Focus: {focus}
          </p>

        </div>


        {/* ===================================================
            FIDELITY DISTANCE
            ONLY FOR REAL + SYNTHETIC
            =================================================== */}

        {!isRealOnly && (
          <div className="text-left sm:text-right shrink-0">

            <span className="text-xs font-semibold text-slate-400 block uppercase tracking-wider">
              Fidelity Distance
            </span>

            <span
              className={`text-3xl font-black ${colorProfile.text}`}
            >
              {formatScore(score)}
            </span>

            <span
              className={`block mt-1 text-xs font-semibold ${colorProfile.text}`}
            >
              {colorProfile.label}
            </span>

          </div>
        )}

      </div>


      {/* =====================================================
          MAIN CONTENT
          ===================================================== */}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

        {/* ===================================================
            LEFT COLUMN
            =================================================== */}

        <div className="space-y-6">


          {/* =================================================
              QUERY EXECUTION PARAMETERS
              ================================================= */}

          <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 space-y-4 shadow-sm">

            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Query Execution Parameters
            </h2>

            <div className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">

              {/* Family */}

              <div className="py-3 flex justify-between gap-4">

                <span className="text-slate-500">
                  Taxonomy Family
                </span>

                <span className="font-semibold text-slate-800 dark:text-slate-200 text-right">
                  {familyName}
                </span>

              </div>


              {/* Setting */}

              <div className="py-3 flex justify-between gap-4">

                <span className="text-slate-500">
                  Evaluation Setting
                </span>

                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  Setting {setting}
                </span>

              </div>


              {/* Query ID */}

              <div className="py-3 flex justify-between gap-4">

                <span className="text-slate-500">
                  Query ID
                </span>

                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 text-right break-all">
                  {queryId}
                </span>

              </div>


              {/* Return Type */}

              <div className="py-3 flex justify-between gap-4">

                <span className="text-slate-500">
                  Return Type
                </span>

                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase text-xs text-right">
                  {instance.return_type || kind}
                </span>

              </div>


              {/* Focus */}

              <div className="py-3 flex justify-between gap-4">

                <span className="text-slate-500">
                  Focus
                </span>

                <span className="font-mono text-xs text-slate-700 dark:text-slate-300 text-right max-w-[65%] break-all">
                  {focus}
                </span>

              </div>


              {/* View */}

              <div className="py-3 flex justify-between gap-4">

                <span className="text-slate-500">
                  View
                </span>

                <span className="font-mono text-xs text-slate-700 dark:text-slate-300 text-right">
                  {view}
                </span>

              </div>


              {/* Instance ID */}

              <div className="py-3">

                <div className="flex justify-between gap-4">

                  <span className="text-slate-500 shrink-0">
                    Instance ID
                  </span>

                  <span className="font-mono text-[11px] text-slate-500 dark:text-slate-400 text-right break-all max-w-[70%]">
                    {instanceId}
                  </span>

                </div>

              </div>

            </div>

          </div>


          {/* =================================================
              REAL OUTPUT
              BOTH MODES
              ================================================= */}

          <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 shadow-sm">

            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Real Output
            </h2>

            <div className="mt-4 p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-100 dark:border-indigo-900">

              <pre className="text-xs font-mono text-indigo-700 dark:text-indigo-300 whitespace-pre-wrap break-words overflow-x-auto">
                {formatOutput(realValue)}
              </pre>

            </div>

          </div>


          {/* =================================================
              SYNTHETIC OUTPUT
              REAL + SYNTHETIC ONLY
              ================================================= */}

          {!isRealOnly && (
            <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 shadow-sm">

              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Synthetic Output
              </h2>

              <div className="mt-4 p-4 rounded-xl bg-cyan-50 dark:bg-cyan-950/30 border border-cyan-100 dark:border-cyan-900">

                <pre className="text-xs font-mono text-cyan-700 dark:text-cyan-300 whitespace-pre-wrap break-words overflow-x-auto">
                  {formatOutput(syntheticValue)}
                </pre>

              </div>

            </div>
          )}


          {/* =================================================
              FIDELITY VERDICT
              REAL + SYNTHETIC ONLY
              ================================================= */}

          {!isRealOnly && (
            <div
              className={`p-6 rounded-2xl border ${colorProfile.border} ${colorProfile.bg} text-sm space-y-2`}
            >

              <span className="font-bold text-slate-900 dark:text-slate-200 block">
                Fidelity Benchmark Verdict
              </span>

              <p className="text-slate-600 dark:text-slate-300">

                This query reports a normalized
                fidelity distance of{' '}

                <span className="font-bold font-mono">
                  {formatScore(score)}
                </span>.

              </p>

              <p className="text-slate-600 dark:text-slate-300">

                Fidelity rating:{' '}

                <span className="font-bold uppercase tracking-wider">
                  {colorProfile.label}
                </span>

              </p>

              <p className="text-xs text-slate-500 dark:text-slate-400 pt-1">
                Lower distance values indicate greater
                similarity between the real and synthetic
                query outputs.
              </p>

            </div>
          )}

        </div>


        {/* ===================================================
            RIGHT COLUMN — VISUALIZATION
            =================================================== */}

        <div className="space-y-3">

          {/* =================================================
              REAL-ONLY VISUALIZATION
              ================================================= */}

          {isRealOnly ? (
            <>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 pl-1">
                Real Data Visualization
              </h2>

              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">

                <RealOnlyChart
                  kind={kind}
                  realValue={realValue}
                  qid={queryId}
                />

              </div>
            </>

          ) : (

            /* ===============================================
               REAL + SYNTHETIC VISUALIZATION
               =============================================== */

            <>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 pl-1">
                Side-by-Side Fidelity Visualization
              </h2>

              <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl p-4 shadow-sm">

                <ComparisonChart
                  kind={kind}
                  realValue={realValue}
                  synthValue={syntheticValue}
                  qid={queryId}
                />

              </div>
            </>
          )}

        </div>

      </div>


      {/* =====================================================
          BOTTOM NAVIGATION
          ===================================================== */}

      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">

        <Link
          href={`/dashboard/${category}`}
          className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-5 py-2.5 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:text-indigo-600 hover:border-indigo-300 transition-colors"
        >
          ← Back to Setting {category}
        </Link>

        <Link
          href="/dashboard"
          className="w-full sm:w-auto inline-flex items-center justify-center rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 transition-colors"
        >
          Dashboard
        </Link>

      </div>

    </div>
  );
}