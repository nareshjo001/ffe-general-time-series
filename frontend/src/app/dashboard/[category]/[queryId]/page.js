// 'use client';

// import Link from 'next/link';
// import { useParams } from 'next/navigation';
// import { useEffect, useState } from 'react';
// import ComparisonChart from '@/components/ComparisonChart';
// import { formatScore, getScoreColor } from '@/utils/helpers';
// import { DEMO_EVALUATION_RESULTS } from '@/services/demoData';

// export default function QueryDetailPage() {
//   const params = useParams();
//   const category = params.category;
//   const rawQueryId = decodeURIComponent(params.queryId);

//   const [instance, setInstance] = useState(null);

//   useEffect(() => {
//     let sourceInstances = DEMO_EVALUATION_RESULTS.instances;
//     const raw = localStorage.getItem('timeSeriesEvalData') || localStorage.getItem('syntheticEvalData');

//     if (raw) {
//       try {
//         const parsed = JSON.parse(raw);
//         if (parsed.instances && parsed.instances.length > 0) {
//           sourceInstances = parsed.instances;
//         }
//       } catch (err) {
//         console.error('Error reading storage data:', err);
//       }
//     }

//     // Match instance by unique ID or qid
//     const found = sourceInstances.find(
//       (item) => item.instance_id === rawQueryId || item.qid === rawQueryId
//     );

//     setInstance(found || sourceInstances[0]);
//   }, [rawQueryId]);

//   if (!instance) {
//     return (
//       <div className="text-center py-20 space-y-4 max-w-7xl mx-auto px-4">
//         <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200">
//           Analytical Query Missing
//         </h2>
//         <Link
//           href={`/dashboard/${category}`}
//           className="text-indigo-600 hover:text-indigo-700 underline text-sm"
//         >
//           Return to {category} list
//         </Link>
//       </div>
//     );
//   }

//   const score = instance.distance ?? 0;
//   const colorProfile = getScoreColor(score);

//   return (
//     <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
//       {/* Navigation Breadcrumb */}
//       <nav className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
//         <Link
//           href="/dashboard"
//           className="hover:text-indigo-600 transition-colors"
//         >
//           Dashboard
//         </Link>
//         <span>&gt;</span>
//         <Link
//           href={`/dashboard/${category}`}
//           className="capitalize hover:text-indigo-600 transition-colors"
//         >
//           {category.replace(/_/g, ' ')} Family
//         </Link>
//         <span>&gt;</span>
//         <span className="text-slate-900 font-semibold dark:text-white font-mono">
//           {instance.qid}
//         </span>
//       </nav>

//       {/* Hero Header */}
//       <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 bg-white border border-slate-200 rounded-2xl gap-4 dark:bg-slate-900 dark:border-slate-800 shadow-xs">
//         <div>
//           <div className="flex items-center gap-2">
//             <span className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
//               Setting {instance.setting} • {instance.view || 'Default View'}
//             </span>
//             {instance.mode && (
//               <span className="px-2 py-0.5 text-xs font-mono bg-slate-100 dark:bg-slate-800 rounded text-slate-600 dark:text-slate-300">
//                 Mode: {instance.mode}
//               </span>
//             )}
//           </div>

//           <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
//             {instance.qid}
//           </h2>
//           <p className="text-xs font-mono text-slate-400 mt-1">
//             Focus: {instance.focus || 'Whole Collection'}
//           </p>
//         </div>

//         <div className="text-left sm:text-right">
//           <span className="text-xs font-semibold text-slate-400 block uppercase tracking-wider">
//             Fidelity Distance
//           </span>
//           <span className={`text-3xl font-black ${colorProfile.text}`}>
//             {formatScore(score)}
//           </span>
//         </div>
//       </div>

//       {/* Main Full-Width Desktop Grid */}
//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
//         {/* Left Side: Parameters & Summary Details */}
//         <div className="space-y-6">
//           {/* Metadata Specs */}
//           <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 space-y-4 shadow-xs">
//             <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
//               Query Execution Parameters
//             </h4>
//             <div className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
//               <div className="py-2.5 flex justify-between">
//                 <span className="text-slate-500">Taxonomy Family</span>
//                 <span className="font-semibold capitalize text-slate-800 dark:text-slate-200">
//                   {instance.family}
//                 </span>
//               </div>
//               <div className="py-2.5 flex justify-between">
//                 <span className="text-slate-500">Return Type (Kind)</span>
//                 <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase text-xs">
//                   {instance.kind}
//                 </span>
//               </div>
//               <div className="py-2.5 flex justify-between items-center">
//                 <span className="text-slate-500">Real Output Value</span>
//                 <span className="font-mono text-xs text-indigo-600 dark:text-indigo-400 max-w-[260px] truncate text-right">
//                   {JSON.stringify(instance.real_value)}
//                 </span>
//               </div>
//               <div className="py-2.5 flex justify-between items-center">
//                 <span className="text-slate-500">Synthetic Output Value</span>
//                 <span className="font-mono text-xs text-cyan-600 dark:text-cyan-400 max-w-[260px] truncate text-right">
//                   {JSON.stringify(instance.synth_value)}
//                 </span>
//               </div>
//             </div>
//           </div>

//           {/* Quality Analysis Verdict Card */}
//           <div
//             className={`p-6 rounded-2xl border ${colorProfile.border} ${colorProfile.bg} text-sm space-y-1.5`}
//           >
//             <span className="font-bold text-slate-900 dark:text-slate-200 block">
//               Fidelity Benchmark Verdict:
//             </span>
//             <p className="text-slate-600 dark:text-slate-300">
//               This query reports a normalized fidelity distance of{' '}
//               <span className="font-bold font-mono">
//                 {formatScore(score)}
//               </span>
//               . The synthetic generator is functioning with a{' '}
//               <span className="font-bold uppercase tracking-wider">
//                 {colorProfile.label}
//               </span>{' '}
//               fidelity rating against real baseline sequences.
//             </p>
//           </div>
//         </div>

//         {/* Right Side: Visualization Card */}
//         <div className="space-y-3">
//           <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 pl-1">
//             Side-by-Side Fidelity Visualization
//           </h4>

//           <ComparisonChart
//             kind={instance.kind}
//             realValue={instance.real_value}
//             synthValue={instance.synth_value}
//             qid={instance.qid}
//           />
//         </div>
//       </div>
//     </div>
//   );
// }




'use client';

import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import ComparisonChart from '@/components/ComparisonChart';
import { formatScore, getScoreColor } from '@/utils/helpers';
import { DEMO_EVALUATION_RESULTS } from '@/services/demoData';

export default function QueryDetailPage() {
  const params = useParams();
  const category = (params.category || 'A').toUpperCase(); // Setting: 'A' | 'B' | 'C'
  const rawQueryParam = params.query || params.queryId || '';
  const rawQueryId = decodeURIComponent(rawQueryParam);

  const [instance, setInstance] = useState(null);

  useEffect(() => {
    let sourceInstances = DEMO_EVALUATION_RESULTS.instances;
    const raw = localStorage.getItem('timeSeriesEvalData') || localStorage.getItem('syntheticEvalData');

    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        if (parsed.instances && parsed.instances.length > 0) {
          sourceInstances = parsed.instances;
        }
      } catch (err) {
        console.error('Error reading storage data:', err);
      }
    }

    // Match instance by unique ID or qid
    const found = sourceInstances.find(
      (item) => item.instance_id === rawQueryId || item.qid === rawQueryId
    );

    setInstance(found || sourceInstances[0]);
  }, [rawQueryId]);

  if (!instance) {
    return (
      <div className="text-center py-20 space-y-4 max-w-7xl mx-auto px-4">
        <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-200">
          Analytical Query Missing
        </h2>
        <Link
          href={`/dashboard/${category}`}
          className="text-indigo-600 hover:text-indigo-700 underline text-sm"
        >
          Return to Setting {category} list
        </Link>
      </div>
    );
  }

  const score = instance.distance ?? 0;
  const colorProfile = getScoreColor(score);

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
      {/* Navigation Breadcrumb */}
      <nav className="text-sm font-medium text-slate-500 dark:text-slate-400 flex items-center gap-2">
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
        <span className="text-slate-900 font-semibold dark:text-white font-mono">
          {instance.qid}
        </span>
      </nav>

      {/* Hero Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-6 bg-white border border-slate-200 rounded-2xl gap-4 dark:bg-slate-900 dark:border-slate-800 shadow-xs">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold text-indigo-600 dark:text-indigo-400 uppercase tracking-wider">
              Setting {instance.setting} • {instance.view || 'Default View'}
            </span>
            {instance.mode && (
              <span className="px-2 py-0.5 text-xs font-mono bg-slate-100 dark:bg-slate-800 rounded text-slate-600 dark:text-slate-300">
                Mode: {instance.mode}
              </span>
            )}
          </div>

          <h2 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white mt-1">
            {instance.qid}
          </h2>
          <p className="text-xs font-mono text-slate-400 mt-1">
            Focus: {instance.focus || 'Whole Collection'}
          </p>
        </div>

        <div className="text-left sm:text-right">
          <span className="text-xs font-semibold text-slate-400 block uppercase tracking-wider">
            Fidelity Distance
          </span>
          <span className={`text-3xl font-black ${colorProfile.text}`}>
            {formatScore(score)}
          </span>
        </div>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Left Side: Parameters & Summary Details */}
        <div className="space-y-6">
          <div className="bg-white border border-slate-200 p-6 rounded-2xl dark:bg-slate-900 dark:border-slate-800 space-y-4 shadow-xs">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              Query Execution Parameters
            </h4>
            <div className="divide-y divide-slate-100 dark:divide-slate-800 text-sm">
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-500">Taxonomy Family</span>
                <span className="font-semibold capitalize text-slate-800 dark:text-slate-200">
                  {instance.family}
                </span>
              </div>
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-500">Evaluation Setting</span>
                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200">
                  Setting {instance.setting}
                </span>
              </div>
              <div className="py-2.5 flex justify-between">
                <span className="text-slate-500">Return Type (Kind)</span>
                <span className="font-mono font-semibold text-slate-800 dark:text-slate-200 uppercase text-xs">
                  {instance.kind}
                </span>
              </div>
              <div className="py-2.5 flex justify-between items-center">
                <span className="text-slate-500">Real Output Value</span>
                <span className="font-mono text-xs text-indigo-600 dark:text-indigo-400 max-w-[260px] truncate text-right">
                  {JSON.stringify(instance.real_value)}
                </span>
              </div>
              <div className="py-2.5 flex justify-between items-center">
                <span className="text-slate-500">Synthetic Output Value</span>
                <span className="font-mono text-xs text-cyan-600 dark:text-cyan-400 max-w-[260px] truncate text-right">
                  {JSON.stringify(instance.synth_value)}
                </span>
              </div>
            </div>
          </div>

          {/* Fidelity Verdict Card */}
          <div
            className={`p-6 rounded-2xl border ${colorProfile.border} ${colorProfile.bg} text-sm space-y-1.5`}
          >
            <span className="font-bold text-slate-900 dark:text-slate-200 block">
              Fidelity Benchmark Verdict:
            </span>
            <p className="text-slate-600 dark:text-slate-300">
              This query reports a normalized fidelity distance of{' '}
              <span className="font-bold font-mono">
                {formatScore(score)}
              </span>
              . The synthetic generator is functioning with an{' '}
              <span className="font-bold uppercase tracking-wider">
                {colorProfile.label}
              </span>{' '}
              fidelity rating against real baseline sequences.
            </p>
          </div>
        </div>

        {/* Right Side: Visualization Card */}
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 pl-1">
            Side-by-Side Fidelity Visualization
          </h4>

          <ComparisonChart
            kind={instance.kind}
            realValue={instance.real_value}
            synthValue={instance.synth_value}
            qid={instance.qid}
          />
        </div>
      </div>
    </div>
  );
}