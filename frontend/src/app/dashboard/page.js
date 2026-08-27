// // 'use client';

// // import { useEffect, useState } from 'react';
// // import { useRouter } from 'next/navigation';
// // import ScoreCard from '@/components/ScoreCard';
// // import { formatScore, getScoreColor } from '@/utils/helpers';

// // const FAMILIES = [
// //   { id: 'distributional', name: 'Distributional', desc: 'Order-invariant value distributions & covariance matrices' },
// //   { id: 'trend', name: 'Trend & Drift', desc: 'Slope, CUSUM changepoints, & lag-1 autocorrelation persistence' },
// //   { id: 'seasonality', name: 'Seasonality & Recurrence', desc: 'Spectral concentration, dominant period, & coherence' },
// //   { id: 'local', name: 'Local Patterns', desc: 'Matrix profile motifs & discords (shape & amp modes)' },
// // ];

// // export default function DashboardPage() {
// //   const router = useRouter();
// //   const [data, setData] = useState(null);

// //   useEffect(() => {
// //     const raw = localStorage.getItem('timeSeriesEvalData');
// //     if (raw) setData(JSON.parse(raw));
// //   }, []);

// //   if (!data) {
// //     return (
// //       <div className="flex h-[60vh] items-center justify-center text-slate-500">
// //         No active evaluation data found. Please run an evaluation from the home page.
// //       </div>
// //     );
// //   }

// //   const meanDistance = data.mean_distance ?? 0.0;
// //   const overallColors = getScoreColor(meanDistance);
// //   const selfCheckMax = data.self_check_max ?? 0.0;

// //   return (
// //     <div className="space-y-8 max-w-7xl mx-auto py-6">
// //       {/* Overview Hero */}
// //       <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-sm">
// //         <div className="space-y-1">
// //           <div className="flex items-center gap-2">
// //             <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Mean Fidelity Distance</h2>
// //             <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-medium ${selfCheckMax < 1e-6 ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}`}>
// //               Self-Check: {selfCheckMax < 1e-6 ? 'PASSED (0.0)' : 'FAILED'}
// //             </span>
// //           </div>
// //           <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xl">
// //             Normalized fidelity distance across all evaluated query instances. Lower values represent higher fidelity to ground-truth time series.
// //           </p>
// //         </div>
// //         <div className={`flex flex-col items-center justify-center h-28 w-28 rounded-full border-2 ${overallColors.border} ${overallColors.bg}`}>
// //           <span className={`text-3xl font-black ${overallColors.text}`}>{formatScore(meanDistance)}</span>
// //           <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Distance</span>
// //         </div>
// //       </div>

// //       {/* 4 Taxonomy Families */}
// //       <div className="space-y-4">
// //         <h3 className="text-lg font-bold text-slate-900 dark:text-white">Taxonomy V3 Families</h3>
// //         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
// //           {FAMILIES.map((fam) => {
// //             const famScore = data.family_scores?.[fam.id] ?? 0.0;
// //             return (
// //               <ScoreCard
// //                 key={fam.id}
// //                 title={fam.name}
// //                 subtitle={fam.desc}
// //                 score={famScore}
// //                 onClick={() => router.push(`/dashboard/${fam.id}`)}
// //               />
// //             );
// //           })}
// //         </div>
// //       </div>

// //       {/* Settings Breakdown (A, B, C) */}
// //       <div className="space-y-4">
// //         <h3 className="text-lg font-bold text-slate-900 dark:text-white">Evaluation Lenses (Settings A / B / C)</h3>
// //         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
// //           <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
// //             <h4 className="text-sm font-semibold text-slate-500">Setting A (Single Series, 1 Measurement)</h4>
// //             <p className="text-2xl font-bold mt-1">{formatScore(data.setting_scores?.A ?? 0.0)}</p>
// //           </div>
// //           <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
// //             <h4 className="text-sm font-semibold text-slate-500">Setting B (1 Series, All Measurements Jointly)</h4>
// //             <p className="text-2xl font-bold mt-1">{formatScore(data.setting_scores?.B ?? 0.0)}</p>
// //           </div>
// //           <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
// //             <h4 className="text-sm font-semibold text-slate-500">Setting C (Collection Population, 1 Measurement)</h4>
// //             <p className="text-2xl font-bold mt-1">{formatScore(data.setting_scores?.C ?? 0.0)}</p>
// //           </div>
// //         </div>
// //       </div>
// //     </div>
// //   );
// // }


// 'use client';

// import { useEffect, useState } from 'react';
// import { useRouter } from 'next/navigation';
// import ScoreCard from '@/components/ScoreCard';
// import { formatScore, getScoreColor } from '@/utils/helpers';

// // 1. Define demo fallback data matching the expected schema
// const DEMO_DATA = {
//   mean_distance: 0.1842,
//   self_check_max: 0.0,
//   family_scores: {
//     distributional: 0.1245,
//     trend: 0.1983,
//     seasonality: 0.1421,
//     local: 0.2720,
//   },
//   setting_scores: {
//     A: 0.1124,
//     B: 0.1845,
//     C: 0.2558,
//   },
// };

// const FAMILIES = [
//   { id: 'distributional', name: 'Distributional', desc: 'Order-invariant value distributions & covariance matrices' },
//   { id: 'trend', name: 'Trend & Drift', desc: 'Slope, CUSUM changepoints, & lag-1 autocorrelation persistence' },
//   { id: 'seasonality', name: 'Seasonality & Recurrence', desc: 'Spectral concentration, dominant period, & coherence' },
//   { id: 'local', name: 'Local Patterns', desc: 'Matrix profile motifs & discords (shape & amp modes)' },
// ];

// export default function DashboardPage() {
//   const router = useRouter();
//   // 2. Initialize with DEMO_DATA as the default
//   const [data, setData] = useState(DEMO_DATA);
//   const [isDemo, setIsDemo] = useState(true);

//   useEffect(() => {
//     const raw = localStorage.getItem('timeSeriesEvalData');
//     if (raw) {
//       try {
//         setData(JSON.parse(raw));
//         setIsDemo(false);
//       } catch (err) {
//         console.error('Failed to parse evaluation data:', err);
//       }
//     }
//   }, []);

//   const meanDistance = data.mean_distance ?? 0.0;
//   const overallColors = getScoreColor(meanDistance);
//   const selfCheckMax = data.self_check_max ?? 0.0;

//   return (
//     <div className="space-y-8 max-w-7xl mx-auto py-6">
//       {/* Demo Banner Indicator */}
//       {/* {isDemo && (
//         <div className="px-4 py-2 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-xl text-xs font-medium text-amber-800 dark:text-amber-300 flex items-center justify-between">
//           <span>Displaying Demo Evaluation Data. Run an evaluation from the home page for live metrics.</span>
//           <span className="uppercase tracking-wider font-bold">Demo Mode</span>
//         </div>
//       )} */}

//       {/* Overview Hero */}
//       <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-sm">
//         <div className="space-y-1">
//           <div className="flex items-center gap-2">
//             <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Mean Fidelity Distance</h2>
//             <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-medium ${selfCheckMax < 1e-6 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300' : 'bg-rose-100 text-rose-800'}`}>
//               Self-Check: {selfCheckMax < 1e-6 ? 'PASSED (0.0)' : 'FAILED'}
//             </span>
//           </div>
//           <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xl">
//             Normalized fidelity distance across all evaluated query instances. Lower values represent higher fidelity to ground-truth time series.
//           </p>
//         </div>
//         <div className={`flex flex-col items-center justify-center h-28 w-28 rounded-full border-2 ${overallColors.border} ${overallColors.bg}`}>
//           <span className={`text-3xl font-black ${overallColors.text}`}>{formatScore(meanDistance)}</span>
//           <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Distance</span>
//         </div>
//       </div>

//       {/* 4 Taxonomy Families */}
//       <div className="space-y-4">
//         <h3 className="text-lg font-bold text-slate-900 dark:text-white">Taxonomy V3 Families</h3>
//         <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
//           {FAMILIES.map((fam) => {
//             const famScore = data.family_scores?.[fam.id] ?? 0.0;
//             return (
//               <ScoreCard
//                 key={fam.id}
//                 title={fam.name}
//                 subtitle={fam.desc}
//                 score={famScore}
//                 onClick={() => router.push(`/dashboard/${fam.id}`)}
//               />
//             );
//           })}
//         </div>
//       </div>

//       {/* Settings Breakdown (A, B, C) */}
//       <div className="space-y-4">
//         <h3 className="text-lg font-bold text-slate-900 dark:text-white">Evaluation Lenses (Settings A / B / C)</h3>
//         <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
//           <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
//             <h4 className="text-sm font-semibold text-slate-500">Setting A (Single Series, 1 Measurement)</h4>
//             <p className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">{formatScore(data.setting_scores?.A ?? 0.0)}</p>
//           </div>
//           <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
//             <h4 className="text-sm font-semibold text-slate-500">Setting B (1 Series, All Measurements Jointly)</h4>
//             <p className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">{formatScore(data.setting_scores?.B ?? 0.0)}</p>
//           </div>
//           <div className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl">
//             <h4 className="text-sm font-semibold text-slate-500">Setting C (Collection Population, 1 Measurement)</h4>
//             <p className="text-2xl font-bold mt-1 text-slate-900 dark:text-white">{formatScore(data.setting_scores?.C ?? 0.0)}</p>
//           </div>
//         </div>
//       </div>
//     </div>
//   );
// }



'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import ScoreCard from '@/components/ScoreCard';
import { formatScore, getScoreColor } from '@/utils/helpers';

const DEMO_DATA = {
  mean_distance: 0.1842,
  self_check_max: 0.0,
  family_scores: {
    distributional: 0.1245,
    trend: 0.1983,
    seasonality: 0.1421,
    local: 0.2720,
  },
  setting_scores: {
    A: 0.1124,
    B: 0.1845,
    C: 0.2558,
  },
};

const SETTINGS = [
  {
    id: 'A',
    name: 'Setting A',
    desc: 'Single Series, 1 Measurement — Univariate shape, trend & local patterns',
  },
  {
    id: 'B',
    name: 'Setting B',
    desc: '1 Series, All Measurements Jointly — Cross-measurement co-movement & correlation drift',
  },
  {
    id: 'C',
    name: 'Setting C',
    desc: 'Collection Population, 1 Measurement — Cross-series population distributions & trajectories',
  },
];

const FAMILIES = [
  { id: 'distributional', name: 'Distributional' },
  { id: 'trend', name: 'Trend & Drift' },
  { id: 'seasonality', name: 'Seasonality & Recurrence' },
  { id: 'local', name: 'Local Patterns' },
];

export default function DashboardPage() {
  const router = useRouter();
  const [data, setData] = useState(DEMO_DATA);

  useEffect(() => {
    const raw = localStorage.getItem('timeSeriesEvalData') || localStorage.getItem('syntheticEvalData');
    if (raw) {
      try {
        setData(JSON.parse(raw));
      } catch (err) {
        console.error('Failed to parse evaluation data:', err);
      }
    }
  }, []);

  const meanDistance = data.mean_distance ?? 0.0;
  const overallColors = getScoreColor(meanDistance);
  const selfCheckMax = data.self_check_max ?? 0.0;

  return (
    <div className="space-y-8 max-w-7xl mx-auto py-6">
      {/* Overview Hero */}
      <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Mean Fidelity Distance</h2>
            <span className={`text-xs px-2 py-0.5 rounded-full font-mono font-medium ${selfCheckMax < 1e-6 ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-300' : 'bg-rose-100 text-rose-800'}`}>
              Self-Check: {selfCheckMax < 1e-6 ? 'PASSED (0.0)' : 'FAILED'}
            </span>
          </div>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-xl">
            Normalized fidelity distance across all evaluated query instances. Lower values represent higher fidelity to ground-truth time series.
          </p>
        </div>
        <div className={`flex flex-col items-center justify-center h-28 w-28 rounded-full border-2 ${overallColors.border} ${overallColors.bg}`}>
          <span className={`text-3xl font-black ${overallColors.text}`}>{formatScore(meanDistance)}</span>
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">Distance</span>
        </div>
      </div>

      {/* Primary Section: 3 Settings (Clickable Cards) */}
      <div className="space-y-4">
        <div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white">Evaluation Lenses (Settings A / B / C)</h3>
          <p className="text-xs text-slate-500 dark:text-slate-400">Click any setting to view its query battery organized across the 4 families.</p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {SETTINGS.map((setting) => {
            const settingScore = data.setting_scores?.[setting.id] ?? 0.0;
            return (
              <ScoreCard
                key={setting.id}
                title={setting.name}
                subtitle={setting.desc}
                score={settingScore}
                onClick={() => router.push(`/dashboard/${setting.id}`)}
              />
            );
          })}
        </div>
      </div>

      {/* Secondary Section: 4 Taxonomy Families (Overview Metrics) */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Taxonomy V3 Families Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FAMILIES.map((fam) => {
            const famScore = data.family_scores?.[fam.id] ?? 0.0;
            const scoreColor = getScoreColor(famScore);
            return (
              <div key={fam.id} className="p-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-xs">
                <h4 className="text-sm font-semibold text-slate-500 dark:text-slate-400">{fam.name}</h4>
                <p className={`text-2xl font-bold mt-1 ${scoreColor.text}`}>{formatScore(famScore)}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}