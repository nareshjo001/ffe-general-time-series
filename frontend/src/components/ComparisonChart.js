'use client';

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

export default function ComparisonChart({ kind, realValue, synthValue, qid }) {
  // 1. SCALAR / COUNT / UNIT / CORRELATION -> Side-by-Side Bar Chart
  if (['scalar', 'count', 'unit', 'correlation'].includes(kind)) {
    const data = [
      {
        name: qid || 'Metric Value',
        Real: typeof realValue === 'number' ? realValue : 0,
        Synthetic: typeof synthValue === 'number' ? synthValue : 0,
      },
    ];

    return (
      <div className="w-full h-72 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
            <XAxis dataKey="name" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
            />
            <Legend />
            <Bar dataKey="Real" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Synthetic" fill="#06b6d4" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // 2. VECTOR / PROFILE -> Overlaid Dual Line Chart
  if (kind === 'vector') {
    const realArr = Array.isArray(realValue) ? realValue : [];
    const synthArr = Array.isArray(synthValue) ? synthValue : [];
    const maxLen = Math.max(realArr.length, synthArr.length);

    const data = Array.from({ length: maxLen }, (_, i) => ({
      step: `Step ${i + 1}`,
      Real: realArr[i] ?? null,
      Synthetic: synthArr[i] ?? null,
    }));

    return (
      <div className="w-full h-72 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
            <XAxis dataKey="step" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
            />
            <Legend />
            <Line type="monotone" dataKey="Real" stroke="#4f46e5" strokeWidth={2.5} dot={{ r: 3 }} />
            <Line type="monotone" dataKey="Synthetic" stroke="#06b6d4" strokeWidth={2.5} strokeDasharray="4 4" dot={{ r: 3 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // 3. DISTRIBUTION -> Population Histogram Comparison
  if (kind === 'distribution') {
    const realArr = Array.isArray(realValue) ? realValue : [];
    const synthArr = Array.isArray(synthValue) ? synthValue : [];
    const maxLen = Math.max(realArr.length, synthArr.length);

    const data = Array.from({ length: maxLen }, (_, i) => ({
      bin: `Bin ${i + 1}`,
      Real: realArr[i] ?? 0,
      Synthetic: synthArr[i] ?? 0,
    }));

    return (
      <div className="w-full h-72 bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
            <XAxis dataKey="bin" stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', color: '#fff' }}
            />
            <Legend />
            <Bar dataKey="Real" fill="#4f46e5" radius={[4, 4, 0, 0]} />
            <Bar dataKey="Synthetic" fill="#06b6d4" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  // 4. MATRIX -> Side-by-Side Numerical Heatmap Grid
  if (kind === 'matrix') {
    const realMat = Array.isArray(realValue) ? realValue : [[1, 0], [0, 1]];
    const synthMat = Array.isArray(synthValue) ? synthValue : [[1, 0], [0, 1]];

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
          <span className="text-xs font-bold text-indigo-600 uppercase">Real Correlation Matrix</span>
          <div className="space-y-1">
            {realMat.map((row, rIdx) => (
              <div key={rIdx} className="flex gap-1">
                {Array.isArray(row) &&
                  row.map((cell, cIdx) => (
                    <div
                      key={cIdx}
                      className="flex-1 py-2 text-center text-xs font-mono rounded bg-indigo-50 dark:bg-indigo-950/40 text-indigo-700 dark:text-indigo-300"
                    >
                      {Number(cell).toFixed(2)}
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>

        <div className="p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
          <span className="text-xs font-bold text-cyan-600 uppercase">Synthetic Correlation Matrix</span>
          <div className="space-y-1">
            {synthMat.map((row, rIdx) => (
              <div key={rIdx} className="flex gap-1">
                {Array.isArray(row) &&
                  row.map((cell, cIdx) => (
                    <div
                      key={cIdx}
                      className="flex-1 py-2 text-center text-xs font-mono rounded bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-300"
                    >
                      {Number(cell).toFixed(2)}
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return <div className="text-sm text-slate-400 p-4">No visual comparison available for this format.</div>;
}