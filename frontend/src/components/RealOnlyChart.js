// // 'use client';

// // function flattenNumbers(value, result = []) {
// //   if (typeof value === 'number') {
// //     if (Number.isFinite(value)) {
// //       result.push(value);
// //     }
// //     return result;
// //   }

// //   if (Array.isArray(value)) {
// //     value.forEach((item) => {
// //       flattenNumbers(item, result);
// //     });

// //     return result;
// //   }

// //   if (value && typeof value === 'object') {
// //     Object.values(value).forEach((item) => {
// //       flattenNumbers(item, result);
// //     });
// //   }

// //   return result;
// // }

// // function formatNumber(value) {
// //   if (typeof value !== 'number' || !Number.isFinite(value)) {
// //     return '—';
// //   }

// //   if (Math.abs(value) >= 1000) {
// //     return value.toLocaleString();
// //   }

// //   return Number(value.toFixed(4)).toString();
// // }

// // export default function RealOnlyChart({
// //   kind,
// //   realValue,
// //   qid,
// // }) {
// //   const values = flattenNumbers(realValue);

// //   /*
// //    * Scalar query.
// //    *
// //    * Example:
// //    * mean
// //    * variance
// //    * linear_trend
// //    */

// //   if (values.length === 1) {
// //     return (
// //       <div className="min-h-[300px] flex flex-col items-center justify-center">

// //         <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
// //           Real Value
// //         </div>

// //         <div className="mt-4 text-4xl font-black text-indigo-600 dark:text-indigo-400">
// //           {formatNumber(values[0])}
// //         </div>

// //         <div className="mt-2 text-xs font-mono text-slate-400">
// //           {qid}
// //         </div>

// //         <div className="mt-1 text-[11px] uppercase text-slate-400">
// //           {kind}
// //         </div>

// //       </div>
// //     );
// //   }

// //   /*
// //    * No numeric values.
// //    *
// //    * Useful for object/string outputs.
// //    */

// //   if (values.length === 0) {
// //     return (
// //       <div className="min-h-[300px] flex flex-col items-center justify-center">

// //         <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
// //           Real Output
// //         </div>

// //         <pre className="mt-4 w-full p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 text-xs font-mono text-indigo-700 dark:text-indigo-300 whitespace-pre-wrap break-words overflow-auto">
// //           {JSON.stringify(realValue, null, 2)}
// //         </pre>

// //       </div>
// //     );
// //   }

// //   /*
// //    * Vector / array output.
// //    *
// //    * Create a simple real-only line graph.
// //    */

// //   const width = 700;
// //   const height = 300;
// //   const padding = 35;

// //   const min =
// //     Math.min(...values);

// //   const max =
// //     Math.max(...values);

// //   const range =
// //     max - min || 1;

// //   const points = values
// //     .map((value, index) => {
// //       const x =
// //         padding +
// //         (index /
// //           Math.max(values.length - 1, 1)) *
// //           (width - padding * 2);

// //       const y =
// //         height -
// //         padding -
// //         ((value - min) / range) *
// //           (height - padding * 2);

// //       return `${x},${y}`;
// //     })
// //     .join(' ');

// //   return (
// //     <div className="w-full">

// //       <div className="flex items-center justify-between mb-3">

// //         <div>
// //           <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
// //             Real Values
// //           </h3>

// //           <p className="text-xs text-slate-400 font-mono">
// //             {qid}
// //           </p>
// //         </div>

// //         <div className="text-xs text-slate-400">
// //           {values.length} values
// //         </div>

// //       </div>

// //       <div className="w-full overflow-x-auto">

// //         <svg
// //           viewBox={`0 0 ${width} ${height}`}
// //           className="w-full min-w-[500px] h-[300px]"
// //           role="img"
// //           aria-label={`Real values for ${qid}`}
// //         >

// //           {/* Horizontal guide lines */}

// //           <line
// //             x1={padding}
// //             y1={padding}
// //             x2={width - padding}
// //             y2={padding}
// //             stroke="currentColor"
// //             className="text-slate-200 dark:text-slate-700"
// //             strokeDasharray="4 4"
// //           />

// //           <line
// //             x1={padding}
// //             y1={height / 2}
// //             x2={width - padding}
// //             y2={height / 2}
// //             stroke="currentColor"
// //             className="text-slate-200 dark:text-slate-700"
// //             strokeDasharray="4 4"
// //           />

// //           <line
// //             x1={padding}
// //             y1={height - padding}
// //             x2={width - padding}
// //             y2={height - padding}
// //             stroke="currentColor"
// //             className="text-slate-200 dark:text-slate-700"
// //             strokeDasharray="4 4"
// //           />

// //           {/* Y axis */}

// //           <line
// //             x1={padding}
// //             y1={padding}
// //             x2={padding}
// //             y2={height - padding}
// //             stroke="currentColor"
// //             className="text-slate-400 dark:text-slate-600"
// //           />

// //           {/* X axis */}

// //           <line
// //             x1={padding}
// //             y1={height - padding}
// //             x2={width - padding}
// //             y2={height - padding}
// //             stroke="currentColor"
// //             className="text-slate-400 dark:text-slate-600"
// //           />

// //           {/* Real data line */}

// //           <polyline
// //             points={points}
// //             fill="none"
// //             stroke="currentColor"
// //             className="text-indigo-600 dark:text-indigo-400"
// //             strokeWidth="3"
// //             strokeLinecap="round"
// //             strokeLinejoin="round"
// //           />

// //           {/* Data points */}

// //           {values.map((value, index) => {
// //             const x =
// //               padding +
// //               (index /
// //                 Math.max(values.length - 1, 1)) *
// //                 (width - padding * 2);

// //             const y =
// //               height -
// //               padding -
// //               ((value - min) / range) *
// //                 (height - padding * 2);

// //             return (
// //               <circle
// //                 key={index}
// //                 cx={x}
// //                 cy={y}
// //                 r="3"
// //                 fill="currentColor"
// //                 className="text-indigo-600 dark:text-indigo-400"
// //               />
// //             );
// //           })}

// //         </svg>

// //       </div>

// //       {/* Min / Max */}

// //       <div className="flex justify-between mt-2 text-[11px] font-mono text-slate-400">

// //         <span>
// //           Min: {formatNumber(min)}
// //         </span>

// //         <span>
// //           Max: {formatNumber(max)}
// //         </span>

// //       </div>

// //     </div>
// //   );
// // }



// 'use client';

// function flattenNumbers(value, result = []) {
//   if (typeof value === 'number') {
//     if (Number.isFinite(value)) {
//       result.push(value);
//     }
//     return result;
//   }

//   if (Array.isArray(value)) {
//     value.forEach((item) => {
//       flattenNumbers(item, result);
//     });

//     return result;
//   }

//   if (value && typeof value === 'object') {
//     Object.values(value).forEach((item) => {
//       flattenNumbers(item, result);
//     });
//   }

//   return result;
// }

// function formatNumber(value) {
//   if (
//     typeof value !== 'number' ||
//     !Number.isFinite(value)
//   ) {
//     return '—';
//   }

//   if (Math.abs(value) >= 1000) {
//     return value.toLocaleString();
//   }

//   return Number(value.toFixed(4)).toString();
// }

// function formatOutput(value) {
//   if (value === null || value === undefined) {
//     return '—';
//   }

//   if (typeof value === 'number') {
//     return formatNumber(value);
//   }

//   if (typeof value === 'string') {
//     return value;
//   }

//   try {
//     return JSON.stringify(value, null, 2);
//   } catch {
//     return String(value);
//   }
// }

// export default function RealOnlyChart({
//   kind,
//   realValue,
//   qid,
// }) {
//   /*
//    * No result
//    */
//   if (
//     realValue === null ||
//     realValue === undefined
//   ) {
//     return (
//       <div className="min-h-[300px] flex flex-col items-center justify-center">

//         <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
//           Real Output
//         </div>

//         <div className="mt-4 text-sm font-mono text-slate-400">
//           No value returned
//         </div>

//       </div>
//     );
//   }

//   /*
//    * ========================================================
//    * SCALAR
//    * ========================================================
//    *
//    * Examples:
//    * mean
//    * variance
//    * linear_trend
//    * acf_lag1
//    * seasonal_strength_stl
//    */

//   if (
//     typeof realValue === 'number' &&
//     Number.isFinite(realValue)
//   ) {
//     return (
//       <div className="min-h-[300px] flex flex-col items-center justify-center">

//         <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
//           Real Value
//         </div>

//         <div className="mt-4 text-4xl font-black text-indigo-600 dark:text-indigo-400">
//           {formatNumber(realValue)}
//         </div>

//         <div className="mt-2 text-xs font-mono text-slate-400">
//           {qid}
//         </div>

//         <div className="mt-1 text-[11px] uppercase text-slate-400">
//           {kind}
//         </div>

//       </div>
//     );
//   }

//   /*
//    * ========================================================
//    * STRING / NON-NUMERIC OBJECT
//    * ========================================================
//    */

//   const numericValues = flattenNumbers(realValue);

//   if (numericValues.length === 0) {
//     return (
//       <div className="min-h-[300px] flex flex-col">

//         <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
//           Real Output
//         </div>

//         <pre className="mt-4 w-full p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 text-xs font-mono text-indigo-700 dark:text-indigo-300 whitespace-pre-wrap break-words overflow-auto max-h-[400px]">
//           {formatOutput(realValue)}
//         </pre>

//       </div>
//     );
//   }

//   /*
//    * ========================================================
//    * NUMERIC VECTOR
//    * ========================================================
//    *
//    * Used for things like:
//    *
//    * acf_profile
//    *
//    * If the backend returns a simple numeric array:
//    *
//    * [0.82, 0.61, 0.48, ...]
//    *
//    * we render it as a real-only line graph.
//    */

//   const values = Array.isArray(realValue)
//     ? numericValues
//     : null;

//   /*
//    * If the result is a structured object containing
//    * multiple arrays/fields, don't incorrectly flatten it
//    * into a fake time-series graph.
//    */

//   if (!values) {
//     return (
//       <div className="min-h-[300px] flex flex-col">

//         <div className="flex items-center justify-between">

//           <div>
//             <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
//               Real Output
//             </h3>

//             <p className="text-xs text-slate-400 font-mono">
//               {qid}
//             </p>
//           </div>

//           <span className="text-[11px] uppercase text-slate-400">
//             {kind}
//           </span>

//         </div>

//         <pre className="mt-4 w-full p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 text-xs font-mono text-indigo-700 dark:text-indigo-300 whitespace-pre-wrap break-words overflow-auto max-h-[400px]">
//           {formatOutput(realValue)}
//         </pre>

//       </div>
//     );
//   }

//   /*
//    * Empty array
//    */

//   if (values.length === 0) {
//     return (
//       <div className="min-h-[300px] flex items-center justify-center text-sm text-slate-400">
//         No numeric values returned.
//       </div>
//     );
//   }

//   /*
//    * ========================================================
//    * LINE GRAPH
//    * ========================================================
//    */

//   const width = 700;
//   const height = 300;
//   const padding = 40;

//   const min = Math.min(...values);
//   const max = Math.max(...values);

//   const range = max - min || 1;

//   const getX = (index) => {
//     if (values.length === 1) {
//       return width / 2;
//     }

//     return (
//       padding +
//       (index / (values.length - 1)) *
//         (width - padding * 2)
//     );
//   };

//   const getY = (value) => {
//     return (
//       height -
//       padding -
//       ((value - min) / range) *
//         (height - padding * 2)
//     );
//   };

//   const points = values
//     .map((value, index) => {
//       return `${getX(index)},${getY(value)}`;
//     })
//     .join(' ');

//   return (
//     <div className="w-full">

//       {/* Header */}

//       <div className="flex items-center justify-between mb-3">

//         <div>

//           <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
//             Real Values
//           </h3>

//           <p className="text-xs text-slate-400 font-mono">
//             {qid}
//           </p>

//         </div>

//         <div className="text-xs text-slate-400">
//           {values.length} values
//         </div>

//       </div>

//       {/* Graph */}

//       <div className="w-full overflow-x-auto">

//         <svg
//           viewBox={`0 0 ${width} ${height}`}
//           className="w-full min-w-[500px] h-[300px]"
//           role="img"
//           aria-label={`Real values for ${qid}`}
//         >

//           {/* Top guide */}

//           <line
//             x1={padding}
//             y1={padding}
//             x2={width - padding}
//             y2={padding}
//             stroke="currentColor"
//             className="text-slate-200 dark:text-slate-700"
//             strokeDasharray="4 4"
//           />

//           {/* Middle guide */}

//           <line
//             x1={padding}
//             y1={height / 2}
//             x2={width - padding}
//             y2={height / 2}
//             stroke="currentColor"
//             className="text-slate-200 dark:text-slate-700"
//             strokeDasharray="4 4"
//           />

//           {/* Bottom guide */}

//           <line
//             x1={padding}
//             y1={height - padding}
//             x2={width - padding}
//             y2={height - padding}
//             stroke="currentColor"
//             className="text-slate-200 dark:text-slate-700"
//             strokeDasharray="4 4"
//           />

//           {/* Y axis */}

//           <line
//             x1={padding}
//             y1={padding}
//             x2={padding}
//             y2={height - padding}
//             stroke="currentColor"
//             className="text-slate-400 dark:text-slate-600"
//           />

//           {/* X axis */}

//           <line
//             x1={padding}
//             y1={height - padding}
//             x2={width - padding}
//             y2={height - padding}
//             stroke="currentColor"
//             className="text-slate-400 dark:text-slate-600"
//           />

//           {/* Real line */}

//           <polyline
//             points={points}
//             fill="none"
//             stroke="currentColor"
//             className="text-indigo-600 dark:text-indigo-400"
//             strokeWidth="3"
//             strokeLinecap="round"
//             strokeLinejoin="round"
//           />

//           {/* Points */}

//           {values.map((value, index) => (
//             <circle
//               key={index}
//               cx={getX(index)}
//               cy={getY(value)}
//               r="3"
//               fill="currentColor"
//               className="text-indigo-600 dark:text-indigo-400"
//             />
//           ))}

//         </svg>

//       </div>

//       {/* Min / Max */}

//       <div className="flex justify-between mt-2 text-[11px] font-mono text-slate-400">

//         <span>
//           Min: {formatNumber(min)}
//         </span>

//         <span>
//           Max: {formatNumber(max)}
//         </span>

//       </div>

//     </div>
//   );
// }



'use client';

import { useMemo, useState } from 'react';

/* =========================================================
   Helpers
   ========================================================= */

function isFiniteNumber(value) {
  return (
    typeof value === 'number' &&
    Number.isFinite(value)
  );
}

function formatNumber(value) {
  if (!isFiniteNumber(value)) {
    return '—';
  }

  if (Math.abs(value) >= 1000) {
    return value.toLocaleString();
  }

  return Number(value.toFixed(6)).toString();
}

function formatDisplayValue(value) {
  if (value === null || value === undefined) {
    return '—';
  }

  if (isFiniteNumber(value)) {
    return formatNumber(value);
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
 * Check whether value is a simple numeric vector.
 *
 * Example:
 *
 * [0.81, 0.72, 0.64, 0.55]
 */
function isNumericVector(value) {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every(isFiniteNumber)
  );
}

/*
 * Check whether value is a numeric matrix.
 *
 * Example:
 *
 * [
 *   [1, 0.5, 0.2],
 *   [0.5, 1, 0.7],
 *   [0.2, 0.7, 1]
 * ]
 */
function isNumericMatrix(value) {
  if (
    !Array.isArray(value) ||
    value.length === 0
  ) {
    return false;
  }

  if (
    !value.every(
      (row) =>
        Array.isArray(row) &&
        row.length > 0
    )
  ) {
    return false;
  }

  const columnCount = value[0].length;

  if (
    !value.every(
      (row) =>
        row.length === columnCount
    )
  ) {
    return false;
  }

  return value.every((row) =>
    row.every(isFiniteNumber)
  );
}

/*
 * Some backend matrix outputs may be objects.
 *
 * For example:
 *
 * {
 *   matrix: [
 *     [1, 0.5],
 *     [0.5, 1]
 *   ]
 * }
 *
 * or:
 *
 * {
 *   values: [
 *     [1, 0.5],
 *     [0.5, 1]
 *   ]
 * }
 */
function extractMatrix(value) {
  if (isNumericMatrix(value)) {
    return value;
  }

  if (
    value &&
    typeof value === 'object'
  ) {
    const candidates = [
      value.matrix,
      value.values,
      value.data,
      value.correlation_matrix,
      value.corr_matrix,
    ];

    for (const candidate of candidates) {
      if (isNumericMatrix(candidate)) {
        return candidate;
      }
    }
  }

  return null;
}

/*
 * Some vector outputs may be objects:
 *
 * {
 *   values: [...]
 * }
 */
function extractVector(value) {
  if (isNumericVector(value)) {
    return value;
  }

  if (
    value &&
    typeof value === 'object'
  ) {
    const candidates = [
      value.values,
      value.data,
      value.profile,
      value.acf,
    ];

    for (const candidate of candidates) {
      if (isNumericVector(candidate)) {
        return candidate;
      }
    }
  }

  return null;
}

/* =========================================================
   Scalar
   ========================================================= */

function ScalarView({
  value,
  qid,
  kind,
}) {
  return (
    <div className="min-h-[300px] flex flex-col items-center justify-center">

      <div className="text-xs font-bold uppercase tracking-wider text-slate-400">
        Real Value
      </div>

      <div className="mt-4 text-4xl font-black text-indigo-600 dark:text-indigo-400">
        {formatNumber(value)}
      </div>

      <div className="mt-2 text-xs font-mono text-slate-400">
        {qid}
      </div>

      <div className="mt-1 text-[11px] uppercase text-slate-400">
        {kind}
      </div>

    </div>
  );
}

/* =========================================================
   Vector
   ========================================================= */

function VectorView({
  values,
  qid,
  kind,
}) {
  const [selectedIndex, setSelectedIndex] =
    useState(null);

  const width = 760;
  const height = 320;
  const padding = 45;

  const min = Math.min(...values);
  const max = Math.max(...values);

  const range = max - min || 1;

  const getX = (index) => {
    if (values.length <= 1) {
      return width / 2;
    }

    return (
      padding +
      (index / (values.length - 1)) *
        (width - padding * 2)
    );
  };

  const getY = (value) => {
    return (
      height -
      padding -
      ((value - min) / range) *
        (height - padding * 2)
    );
  };

  const points = values
    .map(
      (value, index) =>
        `${getX(index)},${getY(value)}`
    )
    .join(' ');

  return (
    <div className="w-full">

      {/* Header */}

      <div className="flex items-center justify-between mb-4">

        <div>

          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            Real Values
          </h3>

          <p className="text-xs text-slate-400 font-mono">
            {qid}
          </p>

        </div>

        <div className="text-xs text-slate-400">
          {values.length} values
        </div>

      </div>


      {/* Graph */}

      <div className="w-full overflow-x-auto">

        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full min-w-[600px] h-[320px]"
          role="img"
          aria-label={`Real values for ${qid}`}
        >

          {/* Grid */}

          <line
            x1={padding}
            y1={padding}
            x2={width - padding}
            y2={padding}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-700"
            strokeDasharray="4 4"
          />

          <line
            x1={padding}
            y1={height / 2}
            x2={width - padding}
            y2={height / 2}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-700"
            strokeDasharray="4 4"
          />

          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="currentColor"
            className="text-slate-200 dark:text-slate-700"
            strokeDasharray="4 4"
          />


          {/* Axis */}

          <line
            x1={padding}
            y1={padding}
            x2={padding}
            y2={height - padding}
            stroke="currentColor"
            className="text-slate-400 dark:text-slate-600"
          />

          <line
            x1={padding}
            y1={height - padding}
            x2={width - padding}
            y2={height - padding}
            stroke="currentColor"
            className="text-slate-400 dark:text-slate-600"
          />


          {/* Real line */}

          <polyline
            points={points}
            fill="none"
            stroke="currentColor"
            className="text-indigo-600 dark:text-indigo-400"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />


          {/* Points */}

          {values.map(
            (value, index) => {
              const x = getX(index);
              const y = getY(value);

              const selected =
                selectedIndex === index;

              return (
                <g key={index}>

                  <circle
                    cx={x}
                    cy={y}
                    r={selected ? 6 : 4}
                    fill="currentColor"
                    className="text-indigo-600 dark:text-indigo-400 cursor-pointer"
                    onMouseEnter={() =>
                      setSelectedIndex(index)
                    }
                    onMouseLeave={() =>
                      setSelectedIndex(null)
                    }
                    onClick={() =>
                      setSelectedIndex(
                        selected
                          ? null
                          : index
                      )
                    }
                  />

                  {selected && (
                    <g>
                      <rect
                        x={Math.min(
                          x + 10,
                          width - 150
                        )}
                        y={Math.max(
                          y - 50,
                          5
                        )}
                        width="140"
                        height="45"
                        rx="6"
                        fill="white"
                        stroke="#cbd5e1"
                      />

                      <text
                        x={Math.min(
                          x + 20,
                          width - 140
                        )}
                        y={Math.max(
                          y - 30,
                          25
                        )}
                        fontSize="11"
                        fill="#475569"
                      >
                        Index: {index}
                      </text>

                      <text
                        x={Math.min(
                          x + 20,
                          width - 140
                        )}
                        y={Math.max(
                          y - 13,
                          42
                        )}
                        fontSize="11"
                        fontWeight="bold"
                        fill="#4f46e5"
                      >
                        Value: {formatNumber(value)}
                      </text>
                    </g>
                  )}

                </g>
              );
            }
          )}

        </svg>

      </div>


      {/* Min / Max */}

      <div className="flex justify-between mt-2 text-[11px] font-mono text-slate-400">

        <span>
          Min: {formatNumber(min)}
        </span>

        <span>
          Max: {formatNumber(max)}
        </span>

      </div>


      {/* ===================================================
          ACTUAL VECTOR VALUES
          =================================================== */}

      <div className="mt-6">

        <div className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">
          Values
        </div>

        <div className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">

          <div className="max-h-[220px] overflow-auto">

            <table className="w-full text-xs">

              <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800">
                <tr>

                  <th className="px-4 py-2 text-left text-slate-500">
                    Index
                  </th>

                  <th className="px-4 py-2 text-right text-slate-500">
                    Real Value
                  </th>

                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">

                {values.map(
                  (value, index) => (
                    <tr
                      key={index}
                      className={`cursor-pointer hover:bg-indigo-50 dark:hover:bg-indigo-950/30 ${
                        selectedIndex === index
                          ? 'bg-indigo-50 dark:bg-indigo-950/30'
                          : ''
                      }`}
                      onMouseEnter={() =>
                        setSelectedIndex(index)
                      }
                    >

                      <td className="px-4 py-2 font-mono text-slate-500">
                        {index}
                      </td>

                      <td className="px-4 py-2 text-right font-mono font-semibold text-indigo-600 dark:text-indigo-400">
                        {formatNumber(value)}
                      </td>

                    </tr>
                  )
                )}

              </tbody>

            </table>

          </div>

        </div>

      </div>

    </div>
  );
}

/* =========================================================
   Matrix
   ========================================================= */

function MatrixView({
  matrix,
  qid,
}) {
  const [selectedCell, setSelectedCell] =
    useState(null);

  const flat = matrix.flat();

  const min = Math.min(...flat);
  const max = Math.max(...flat);

  const range = max - min || 1;

  const getIntensity = (value) => {
    return (value - min) / range;
  };

  return (
    <div className="w-full">

      {/* Header */}

      <div className="flex items-center justify-between mb-4">

        <div>

          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            Real Matrix
          </h3>

          <p className="text-xs text-slate-400 font-mono">
            {qid}
          </p>

        </div>

        <div className="text-xs text-slate-400">
          {matrix.length} × {matrix[0].length}
        </div>

      </div>


      {/* Matrix */}

      <div className="overflow-auto border border-slate-200 dark:border-slate-800 rounded-xl">

        <table className="border-collapse">

          <tbody>

            {matrix.map(
              (row, rowIndex) => (
                <tr key={rowIndex}>

                  {row.map(
                    (value, colIndex) => {

                      const selected =
                        selectedCell?.row ===
                          rowIndex &&
                        selectedCell?.col ===
                          colIndex;

                      const intensity =
                        getIntensity(value);

                      /*
                       * Use CSS opacity rather than
                       * hard-coding a color.
                       */

                      return (
                        <td
                          key={colIndex}
                          className={`relative min-w-[70px] h-[55px] border border-white dark:border-slate-900 text-center font-mono text-xs cursor-pointer transition-all ${
                            selected
                              ? 'ring-2 ring-indigo-500 z-10'
                              : ''
                          }`}
                          style={{
                            backgroundColor:
                              `rgb(99 102 241 / ${0.08 + intensity * 0.65})`,
                          }}
                          onMouseEnter={() =>
                            setSelectedCell({
                              row: rowIndex,
                              col: colIndex,
                            })
                          }
                          onMouseLeave={() =>
                            setSelectedCell(null)
                          }
                        >

                          {formatNumber(value)}

                          {selected && (
                            <div className="absolute z-20 left-1/2 -translate-x-1/2 -top-12 bg-slate-900 text-white px-2 py-1 rounded text-[10px] whitespace-nowrap shadow-lg">

                              Row {rowIndex},
                              Col {colIndex}
                              {' • '}
                              {formatNumber(value)}

                            </div>
                          )}

                        </td>
                      );
                    }
                  )}

                </tr>
              )
            )}

          </tbody>

        </table>

      </div>


      {/* Min / Max */}

      <div className="flex justify-between mt-3 text-[11px] font-mono text-slate-400">

        <span>
          Min: {formatNumber(min)}
        </span>

        <span>
          Max: {formatNumber(max)}
        </span>

      </div>


      {/* Full matrix values */}

      <details className="mt-5">

        <summary className="cursor-pointer text-xs font-semibold text-indigo-600 dark:text-indigo-400">
          View raw matrix values
        </summary>

        <pre className="mt-3 p-4 rounded-xl bg-slate-50 dark:bg-slate-800 text-xs font-mono overflow-auto max-h-[300px]">
          {JSON.stringify(matrix, null, 2)}
        </pre>

      </details>

    </div>
  );
}

/* =========================================================
   Structured Output
   ========================================================= */

function StructuredOutput({
  value,
  qid,
  kind,
}) {
  return (
    <div className="w-full">

      <div className="flex items-center justify-between mb-3">

        <div>

          <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200">
            Real Output
          </h3>

          <p className="text-xs text-slate-400 font-mono">
            {qid}
          </p>

        </div>

        <span className="text-[11px] uppercase text-slate-400">
          {kind}
        </span>

      </div>

      <pre className="w-full p-4 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 text-xs font-mono text-indigo-700 dark:text-indigo-300 whitespace-pre-wrap break-words overflow-auto max-h-[450px]">
        {formatDisplayValue(value)}
      </pre>

    </div>
  );
}

/* =========================================================
   Main Component
   ========================================================= */

export default function RealOnlyChart({
  kind,
  realValue,
  qid,
}) {
  /*
   * -------------------------------------------------------
   * 1. Scalar
   * -------------------------------------------------------
   */

  if (isFiniteNumber(realValue)) {
    return (
      <ScalarView
        value={realValue}
        qid={qid}
        kind={kind}
      />
    );
  }

  /*
   * -------------------------------------------------------
   * 2. Matrix
   * -------------------------------------------------------
   */

  const matrix =
    extractMatrix(realValue);

  if (matrix) {
    return (
      <MatrixView
        matrix={matrix}
        qid={qid}
      />
    );
  }

  /*
   * -------------------------------------------------------
   * 3. Vector
   * -------------------------------------------------------
   */

  const vector =
    extractVector(realValue);

  if (vector) {
    return (
      <VectorView
        values={vector}
        qid={qid}
        kind={kind}
      />
    );
  }

  /*
   * -------------------------------------------------------
   * 4. Everything else
   * -------------------------------------------------------
   */

  return (
    <StructuredOutput
      value={realValue}
      qid={qid}
      kind={kind}
    />
  );
}