// 'use client';

// import Link from 'next/link';
// import { getScoreColor, formatScore } from '@/utils/helpers';

// export default function QueryTable({ queries = [], familyKey }) {
//   return (
//     <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
//       <table className="w-full border-collapse text-left text-sm text-slate-500 dark:text-slate-400">
//         <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">
//           <tr>
//             <th className="px-6 py-4">Query ID</th>
//             <th className="px-6 py-4">Setting</th>
//             <th className="px-6 py-4">Focus</th>
//             <th className="px-6 py-4">Kind</th>
//             <th className="px-6 py-4">Fidelity Distance</th>
//             <th className="px-6 py-4 text-right">Action</th>
//           </tr>
//         </thead>
//         <tbody className="divide-y divide-slate-200 dark:divide-slate-800">
//           {queries.map((q, idx) => {
//             const rawId = q.instance_id || q.qid || String(idx);
//             const encodedId = encodeURIComponent(rawId);
//             const colors = getScoreColor(q.distance);

//             return (
//               <tr key={rawId} className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors">
//                 <td className="px-6 py-4 font-semibold text-slate-900 dark:text-white">
//                   {q.qid}
//                   {q.mode && (
//                     <span className="ml-2 px-2 py-0.5 text-[10px] font-mono rounded bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
//                       {q.mode}
//                     </span>
//                   )}
//                 </td>
//                 <td className="px-6 py-4 font-mono font-bold text-xs text-indigo-600 dark:text-indigo-400">
//                   Setting {q.setting}
//                 </td>
//                 <td className="px-6 py-4 font-mono text-xs text-slate-500">
//                   {q.focus || 'Whole Collection'}
//                 </td>
//                 <td className="px-6 py-4 font-mono text-xs uppercase text-slate-400">
//                   {q.kind}
//                 </td>
//                 <td className="px-6 py-4 font-mono font-medium text-slate-900 dark:text-slate-100">
//                   <span className={`inline-flex px-2 py-0.5 rounded text-xs border font-semibold ${colors.border} ${colors.bg} ${colors.text}`}>
//                     {formatScore(q.distance)}
//                   </span>
//                 </td>
//                 <td className="px-6 py-4 text-right">
//                   <Link
//                     href={`/dashboard/${familyKey}/${encodedId}`}
//                     className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 hover:text-indigo-600 transition-all dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
//                   >
//                     View Instance →
//                   </Link>
//                 </td>
//               </tr>
//             );
//           })}
//         </tbody>
//       </table>
//     </div>
//   );
// }



'use client';

import Link from 'next/link';
import { getScoreColor, formatScore } from '@/utils/helpers';

export default function QueryTable({
  queries = [],
  familyKey,
  mode = 'real_synthetic',
}) {
  const isRealOnly = mode === 'real_only';

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
      <table className="w-full border-collapse text-left text-sm text-slate-500 dark:text-slate-400">

        {/* =====================================================
            TABLE HEADER
        ===================================================== */}
        <thead className="bg-slate-50 dark:bg-slate-800/50 text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">
          <tr>
            <th className="px-6 py-4">Query ID</th>

            <th className="px-6 py-4">Setting</th>

            <th className="px-6 py-4">Focus</th>

            <th className="px-6 py-4">Kind</th>

            {/* Only comparison mode has fidelity distance */}
            {!isRealOnly && (
              <th className="px-6 py-4">
                Fidelity Distance
              </th>
            )}

            <th className="px-6 py-4 text-right">
              Action
            </th>
          </tr>
        </thead>

        {/* =====================================================
            TABLE BODY
        ===================================================== */}
        <tbody className="divide-y divide-slate-200 dark:divide-slate-800">

          {queries.map((q, idx) => {

            const rawId =
              q.instance_id ||
              q.qid ||
              String(idx);

            const encodedId =
              encodeURIComponent(rawId);

            const colors =
              getScoreColor(q.distance);

            return (
              <tr
                key={rawId}
                className="hover:bg-slate-50/70 dark:hover:bg-slate-800/30 transition-colors"
              >

                {/* QUERY ID */}
                <td className="px-6 py-4 font-semibold text-slate-900 dark:text-white">

                  {q.qid}

                  {/* Do not show mode badge for real_only */}
                  {!isRealOnly && q.mode && (
                    <span className="ml-2 px-2 py-0.5 text-[10px] font-mono rounded bg-indigo-50 text-indigo-600 dark:bg-indigo-950 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                      {q.mode}
                    </span>
                  )}

                </td>

                {/* SETTING */}
                <td className="px-6 py-4 font-mono font-bold text-xs text-indigo-600 dark:text-indigo-400">
                  Setting {q.setting}
                </td>

                {/* FOCUS */}
                <td className="px-6 py-4 font-mono text-xs text-slate-500">
                  {q.focus || 'Whole Collection'}
                </td>

                {/* KIND */}
                <td className="px-6 py-4 font-mono text-xs uppercase text-slate-400">
                  {q.kind}
                </td>

                {/* =================================================
                    FIDELITY DISTANCE

                    REAL ONLY:
                        Don't render it.

                    REAL + SYNTHETIC:
                        Show distance.
                   ================================================= */}
                {!isRealOnly && (
                  <td className="px-6 py-4 font-mono font-medium text-slate-900 dark:text-slate-100">

                    <span
                      className={`inline-flex px-2 py-0.5 rounded text-xs border font-semibold ${colors.border} ${colors.bg} ${colors.text}`}
                    >
                      {formatScore(q.distance)}
                    </span>

                  </td>
                )}

                {/* ACTION */}
                <td className="px-6 py-4 text-right">

                  <Link
                    href={`/dashboard/${familyKey}/${encodedId}`}
                    className="inline-flex items-center justify-center rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 hover:text-indigo-600 transition-all dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700"
                  >
                    View Instance →
                  </Link>

                </td>

              </tr>
            );
          })}

        </tbody>
      </table>
    </div>
  );
}