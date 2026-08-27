// 'use client';

// import { useState } from 'react';
// import { useRouter } from 'next/navigation';

// export default function HomePage() {
//   const router = useRouter();
//   const [evalMode, setEvalMode] = useState('comparison'); // 'comparison' (Function 2) or 'real_only' (Function 1)
//   const [specPath, setSpecPath] = useState('specs/noaa_winner.yaml');
//   const [realFile, setRealFile] = useState(null);
//   const [syntheticFile, setSyntheticFile] = useState(null);
//   const [loading, setLoading] = useState(false);

//   const handleSubmit = async (e) => {
//     e.preventDefault();
//     if (!realFile) return alert('Please upload the Real Dataset CSV.');
//     if (evalMode === 'comparison' && !syntheticFile) {
//       return alert('Please upload the Synthetic Dataset CSV.');
//     }

//     setLoading(true);
//     try {
//       const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
//       const formData = new FormData();
//       formData.append('real_file', realFile);
//       if (evalMode === 'comparison') formData.append('synthetic_file', syntheticFile);
//       formData.append('spec_path', specPath);
//       formData.append('mode', evalMode);

//       const res = await fetch(`${backendUrl}/api/evaluate`, {
//         method: 'POST',
//         body: formData,
//       });

//       if (!res.ok) throw new Error('Time-series evaluation failed on backend.');
//       const data = await res.json();

//       localStorage.setItem('timeSeriesEvalData', JSON.stringify(data));
//       localStorage.setItem('evalMode', evalMode);
//       localStorage.setItem('selectedSpec', specPath);

//       router.push('/dashboard');
//     } catch (err) {
//       alert(err.message);
//     } finally {
//       setLoading(false);
//     }
//   };

//   return (
//     <div className="flex flex-col items-center justify-center min-h-[75vh] text-center max-w-3xl mx-auto space-y-8 px-4 py-8">
//       <div className="space-y-3">
//         <span className="text-xs font-bold uppercase tracking-widest text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 px-3 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-800">
//           Query Design V3 Engine
//         </span>
//         <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
//           Time-Series Fidelity Dashboard
//         </h1>
//         <p className="text-base sm:text-lg text-slate-500 max-w-2xl dark:text-slate-400">
//           Evaluate synthetic panels using 2-stage grouped collection queries across Distributional, Trend, Seasonality, and Local Pattern taxonomy families.
//         </p>
//       </div>

//       <form onSubmit={handleSubmit} className="w-full max-w-2xl space-y-6 bg-white p-8 rounded-2xl shadow-sm border border-slate-200 dark:bg-slate-900 dark:border-slate-800 text-left">
//         {/* Mode Selector */}
//         <div className="space-y-2">
//           <label className="block text-xs font-bold uppercase tracking-wider text-slate-500">Evaluation Mode</label>
//           <div className="grid grid-cols-2 gap-3 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
//             <button
//               type="button"
//               onClick={() => setEvalMode('comparison')}
//               className={`py-2 px-3 rounded-lg text-sm font-semibold transition-all ${
//                 evalMode === 'comparison' ? 'bg-white dark:bg-slate-900 text-indigo-600 shadow-xs' : 'text-slate-500'
//               }`}
//             >
//               Function 2: Real vs. Synthetic
//             </button>
//             <button
//               type="button"
//               onClick={() => setEvalMode('real_only')}
//               className={`py-2 px-3 rounded-lg text-sm font-semibold transition-all ${
//                 evalMode === 'real_only' ? 'bg-white dark:bg-slate-900 text-indigo-600 shadow-xs' : 'text-slate-500'
//               }`}
//             >
//               Function 1: Profile Real Data
//             </button>
//           </div>
//         </div>

//         {/* Spec Selection */}
//         <div className="space-y-2">
//           <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Spec Configuration (YAML)</label>
//           <select
//             value={specPath}
//             onChange={(e) => setSpecPath(e.target.value)}
//             className="w-full p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50 text-sm"
//           >
//             <option value="specs/demo_small.yaml">demo_small.yaml (~25 query instances)</option>
//             <option value="specs/noaa_winner.yaml">noaa_winner.yaml (Production ~200 instances)</option>
//           </select>
//         </div>

//         {/* File Upload Inputs */}
//         <div className={`grid gap-6 ${evalMode === 'comparison' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
//           <div className="space-y-2">
//             <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Real Dataset CSV</label>
//             <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center dark:border-slate-700">
//               <input type="file" accept=".csv" onChange={(e) => setRealFile(e.target.files?.[0] || null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
//               <span className="text-sm text-slate-500">{realFile ? `✅ ${realFile.name}` : 'Select Real Panel (.csv)'}</span>
//             </div>
//           </div>

//           {evalMode === 'comparison' && (
//             <div className="space-y-2">
//               <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Synthetic Dataset CSV</label>
//               <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center dark:border-slate-700">
//                 <input type="file" accept=".csv" onChange={(e) => setSyntheticFile(e.target.files?.[0] || null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
//                 <span className="text-sm text-slate-500">{syntheticFile ? `✅ ${syntheticFile.name}` : 'Select Synthetic Panel (.csv)'}</span>
//               </div>
//             </div>
//           )}
//         </div>

//         <button
//           type="submit"
//           disabled={loading || !realFile || (evalMode === 'comparison' && !syntheticFile)}
//           className="w-full py-3 px-4 rounded-xl text-white font-medium bg-indigo-600 hover:bg-indigo-700 transition-colors disabled:opacity-50"
//         >
//           {loading ? 'Evaluating Query Battery...' : evalMode === 'comparison' ? 'Run Fidelity Benchmark' : 'Extract Real Query Profiles'}
//         </button>
//       </form>
//     </div>
//   );
// }



'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function HomePage() {
  const router = useRouter();
  const [evalMode, setEvalMode] = useState('comparison'); // 'comparison' (Function 2) or 'real_only' (Function 1)
  const [specPath, setSpecPath] = useState('specs/noaa_winner.yaml');
  const [realFile, setRealFile] = useState(null);
  const [syntheticFile, setSyntheticFile] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!realFile) return alert('Please upload the Real Dataset CSV.');
    if (evalMode === 'comparison' && !syntheticFile) {
      return alert('Please upload the Synthetic Dataset CSV.');
    }

    setLoading(true);

    // Save basic form settings
    localStorage.setItem('evalMode', evalMode);
    localStorage.setItem('selectedSpec', specPath);

    // Redirect directly to dashboard
    router.push('/dashboard');
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center max-w-3xl mx-auto space-y-8 px-4 py-8">
      <div className="space-y-3">
        <span className="text-xs font-bold uppercase tracking-widest text-indigo-600 bg-indigo-50 dark:bg-indigo-950/40 px-3 py-1.5 rounded-full border border-indigo-200 dark:border-indigo-800">
          Query Design V3 Engine
        </span>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Time-Series Fidelity Dashboard
        </h1>
        <p className="text-base sm:text-lg text-slate-500 max-w-2xl dark:text-slate-400">
          Evaluate synthetic panels using 2-stage grouped collection queries across Distributional, Trend, Seasonality, and Local Pattern taxonomy families.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="w-full max-w-2xl space-y-6 bg-white p-8 rounded-2xl shadow-sm border border-slate-200 dark:bg-slate-900 dark:border-slate-800 text-left">
        {/* Mode Selector */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500">Evaluation Mode</label>
          <div className="grid grid-cols-2 gap-3 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
            <button
              type="button"
              onClick={() => setEvalMode('comparison')}
              className={`py-2 px-3 rounded-lg text-sm font-semibold transition-all ${
                evalMode === 'comparison' ? 'bg-white dark:bg-slate-900 text-indigo-600 shadow-xs' : 'text-slate-500'
              }`}
            >
              Function 2: Real vs. Synthetic
            </button>
            <button
              type="button"
              onClick={() => setEvalMode('real_only')}
              className={`py-2 px-3 rounded-lg text-sm font-semibold transition-all ${
                evalMode === 'real_only' ? 'bg-white dark:bg-slate-900 text-indigo-600 shadow-xs' : 'text-slate-500'
              }`}
            >
              Function 1: Profile Real Data
            </button>
          </div>
        </div>

        {/* Spec Selection */}
        <div className="space-y-2">
          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Spec Configuration (YAML)</label>
          <select
            value={specPath}
            onChange={(e) => setSpecPath(e.target.value)}
            className="w-full p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-900/50 text-sm"
          >
            <option value="specs/demo_small.yaml">demo_small.yaml (~25 query instances)</option>
            <option value="specs/noaa_winner.yaml">noaa_winner.yaml (Production ~200 instances)</option>
          </select>
        </div>

        {/* File Upload Inputs */}
        <div className={`grid gap-6 ${evalMode === 'comparison' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Real Dataset CSV</label>
            <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center dark:border-slate-700">
              <input type="file" accept=".csv" onChange={(e) => setRealFile(e.target.files?.[0] || null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
              <span className="text-sm text-slate-500">{realFile ? `✅ ${realFile.name}` : 'Select Real Panel (.csv)'}</span>
            </div>
          </div>

          {evalMode === 'comparison' && (
            <div className="space-y-2">
              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">Synthetic Dataset CSV</label>
              <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center dark:border-slate-700">
                <input type="file" accept=".csv" onChange={(e) => setSyntheticFile(e.target.files?.[0] || null)} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
                <span className="text-sm text-slate-500">{syntheticFile ? `✅ ${syntheticFile.name}` : 'Select Synthetic Panel (.csv)'}</span>
              </div>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !realFile || (evalMode === 'comparison' && !syntheticFile)}
          className="w-full py-3 px-4 rounded-xl text-white font-medium bg-indigo-600 hover:bg-indigo-700 transition-colors disabled:opacity-50"
        >
          {loading ? 'Evaluating Query Battery...' : evalMode === 'comparison' ? 'Run Fidelity Benchmark' : 'Extract Real Query Profiles'}
        </button>
      </form>
    </div>
  );
}