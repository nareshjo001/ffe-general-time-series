'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

export default function HomePage() {
  const router = useRouter();

  const [evalMode, setEvalMode] = useState('comparison');
  const [realFile, setRealFile] = useState(null);
  const [syntheticFile, setSyntheticFile] = useState(null);
  const [specFile, setSpecFile] = useState(null);

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState('');

  const backendUrl =
    process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const handleSubmit = async (e) => {
    e.preventDefault();

    // -----------------------------------------
    // Validate files
    // -----------------------------------------

    if (!realFile) {
      alert('Please upload the Real Dataset CSV.');
      return;
    }

    if (evalMode === 'comparison' && !syntheticFile) {
      alert('Please upload the Synthetic Dataset CSV.');
      return;
    }

    if (!specFile) {
      alert('Please upload the YAML specification file.');
      return;
    }

    setLoading(true);
    setStatus('Creating evaluation job...');

    try {
      // -----------------------------------------
      // 1. CREATE JOB
      // -----------------------------------------

      const createResponse = await fetch(
        `${backendUrl}/create-job`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            mode:
              evalMode === 'comparison'
                ? 'real_synthetic'
                : 'real_only',
          }),
        }
      );

      if (!createResponse.ok) {
        const error = await createResponse
          .json()
          .catch(() => ({}));

        throw new Error(
          error.detail || 'Failed to create evaluation job.'
        );
      }

      const jobData = await createResponse.json();
      const jobId = jobData.job_id;

      console.log('Created job:', jobId);

      // -----------------------------------------
      // 2. UPLOAD REAL CSV
      // -----------------------------------------

      setStatus('Uploading real dataset...');

      const realForm = new FormData();
      realForm.append('file', realFile);

      const realResponse = await fetch(
        `${backendUrl}/upload-real/${jobId}`,
        {
          method: 'POST',
          body: realForm,
        }
      );

      if (!realResponse.ok) {
        const error = await realResponse
          .json()
          .catch(() => ({}));

        throw new Error(
          error.detail || 'Real CSV upload failed.'
        );
      }

      // -----------------------------------------
      // 3. UPLOAD SYNTHETIC CSV
      // -----------------------------------------

      if (evalMode === 'comparison') {
        setStatus('Uploading synthetic dataset...');

        const syntheticForm = new FormData();
        syntheticForm.append('file', syntheticFile);

        const syntheticResponse = await fetch(
          `${backendUrl}/upload-synthetic/${jobId}`,
          {
            method: 'POST',
            body: syntheticForm,
          }
        );

        if (!syntheticResponse.ok) {
          const error = await syntheticResponse
            .json()
            .catch(() => ({}));

          throw new Error(
            error.detail || 'Synthetic CSV upload failed.'
          );
        }
      }

      // -----------------------------------------
      // 4. UPLOAD YAML
      // -----------------------------------------

      setStatus('Uploading YAML specification...');

      const specForm = new FormData();
      specForm.append('file', specFile);

      const specResponse = await fetch(
        `${backendUrl}/upload-spec/${jobId}`,
        {
          method: 'POST',
          body: specForm,
        }
      );

      if (!specResponse.ok) {
        const error = await specResponse
          .json()
          .catch(() => ({}));

        throw new Error(
          error.detail || 'YAML specification upload failed.'
        );
      }

      // -----------------------------------------
      // 5. START EVALUATION
      // -----------------------------------------

      setStatus('Starting evaluation...');

      const evalResponse = await fetch(
        `${backendUrl}/evaluate/${jobId}`,
        {
          method: 'POST',
        }
      );

      if (!evalResponse.ok) {
        const error = await evalResponse
          .json()
          .catch(() => ({}));

        throw new Error(
          error.detail || 'Failed to start evaluation.'
        );
      }

      // -----------------------------------------
      // 6. SAVE JOB ID
      // -----------------------------------------

      localStorage.setItem('job_id', jobId);
      localStorage.setItem('evalMode', evalMode);

      // -----------------------------------------
      // 7. POLL JOB STATUS
      // -----------------------------------------

      setStatus('Running analytical models...');

      const startTime = Date.now();

      while (true) {
        if (Date.now() - startTime > POLL_TIMEOUT_MS) {
          throw new Error(
            'Evaluation timed out. Please try again.'
          );
        }

        await new Promise((resolve) =>
          setTimeout(resolve, POLL_INTERVAL_MS)
        );

        const statusResponse = await fetch(
          `${backendUrl}/jobs/${jobId}/status`
        );

        if (!statusResponse.ok) {
          throw new Error(
            'Unable to check evaluation status.'
          );
        }

        const statusData = await statusResponse.json();

        console.log('Job status:', statusData.status);

        if (statusData.status === 'queued') {
          setStatus('Evaluation queued...');
        } else if (statusData.status === 'running') {
          setStatus('Running analytical models...');
        } else if (statusData.status === 'done') {
          setStatus('Evaluation completed!');
          break;
        } else if (statusData.status === 'failed') {
          throw new Error(
            statusData.error || 'Evaluation failed.'
          );
        }
      }

      // -----------------------------------------
      // 8. GET ACTUAL RESULT
      // -----------------------------------------

      setStatus('Loading real scores...');

      const resultResponse = await fetch(
        `${backendUrl}/jobs/${jobId}/result`
      );

      if (!resultResponse.ok) {
        const error = await resultResponse
          .json()
          .catch(() => ({}));

        throw new Error(
          error.detail ||
            'Evaluation completed but result could not be retrieved.'
        );
      }

      const result = await resultResponse.json();

      console.log('Evaluation result:', result);

      // -----------------------------------------
      // 9. STORE RESULT
      // -----------------------------------------

      localStorage.setItem(
        'syntheticEvalData',
        JSON.stringify(result)
      );

      localStorage.setItem(
        'evaluationResult',
        JSON.stringify(result)
      );

      // -----------------------------------------
      // 10. GO TO DASHBOARD
      // -----------------------------------------

      setStatus('Opening results...');

      router.push('/dashboard');

    } catch (error) {
      console.error('Evaluation error:', error);

      alert(
        error.message ||
          'Something went wrong while running the evaluation.'
      );

      setStatus('');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-[75vh] text-center max-w-3xl mx-auto space-y-8 px-4 py-8">

      {/* Header */}
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

      {/* Form */}
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-2xl space-y-6 bg-white p-8 rounded-2xl shadow-sm border border-slate-200 dark:bg-slate-900 dark:border-slate-800 text-left"
      >

        {/* Evaluation Mode */}
        <div className="space-y-2">

          <label className="block text-xs font-bold uppercase tracking-wider text-slate-500">
            Evaluation Mode
          </label>

          <div className="grid grid-cols-2 gap-3 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">

            <button
              type="button"
              disabled={loading}
              onClick={() => setEvalMode('comparison')}
              className={`py-2 px-3 rounded-lg text-sm font-semibold transition-all ${
                evalMode === 'comparison'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 shadow-xs'
                  : 'text-slate-500'
              }`}
            >
              Function 2: Real vs. Synthetic
            </button>

            <button
              type="button"
              disabled={loading}
              onClick={() => setEvalMode('real_only')}
              className={`py-2 px-3 rounded-lg text-sm font-semibold transition-all ${
                evalMode === 'real_only'
                  ? 'bg-white dark:bg-slate-900 text-indigo-600 shadow-xs'
                  : 'text-slate-500'
              }`}
            >
              Function 1: Profile Real Data
            </button>

          </div>
        </div>

        {/* YAML Upload */}
        <div className="space-y-2">

          <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
            Query Specification (YAML)
          </label>

          <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-indigo-500 transition-colors dark:border-slate-700">

            <input
              type="file"
              accept=".yaml,.yml"
              disabled={loading}
              onChange={(e) =>
                setSpecFile(
                  e.target.files?.[0] || null
                )
              }
              className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
            />

            <span className="text-sm text-slate-500">
              {specFile
                ? `✅ ${specFile.name}`
                : 'Select Query Specification (.yaml / .yml)'}
            </span>

          </div>
        </div>

        {/* CSV Uploads */}
        <div
          className={`grid gap-6 ${
            evalMode === 'comparison'
              ? 'grid-cols-1 md:grid-cols-2'
              : 'grid-cols-1'
          }`}
        >

          {/* Real Dataset */}
          <div className="space-y-2">

            <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
              Real Dataset CSV
            </label>

            <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-indigo-500 transition-colors dark:border-slate-700">

              <input
                type="file"
                accept=".csv"
                disabled={loading}
                onChange={(e) =>
                  setRealFile(
                    e.target.files?.[0] || null
                  )
                }
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />

              <span className="text-sm text-slate-500">
                {realFile
                  ? `✅ ${realFile.name}`
                  : 'Select Real Panel (.csv)'}
              </span>

            </div>
          </div>

          {/* Synthetic Dataset */}
          {evalMode === 'comparison' && (
            <div className="space-y-2">

              <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300">
                Synthetic Dataset CSV
              </label>

              <div className="relative flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl p-6 text-center hover:border-indigo-500 transition-colors dark:border-slate-700">

                <input
                  type="file"
                  accept=".csv"
                  disabled={loading}
                  onChange={(e) =>
                    setSyntheticFile(
                      e.target.files?.[0] || null
                    )
                  }
                  className="absolute inset-0 w-full h-full cursor-pointer opacity-0"
                />

                <span className="text-sm text-slate-500">
                  {syntheticFile
                    ? `✅ ${syntheticFile.name}`
                    : 'Select Synthetic Panel (.csv)'}
                </span>

              </div>
            </div>
          )}

        </div>

        {/* Status */}
        {loading && (
          <div className="rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800 p-4 text-center">

            <div className="flex items-center justify-center gap-3">

              <svg
                className="animate-spin h-5 w-5 text-indigo-600"
                viewBox="0 0 24 24"
                fill="none"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />

                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>

              <span className="text-sm font-medium text-indigo-700 dark:text-indigo-300">
                {status || 'Processing...'}
              </span>

            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={
            loading ||
            !realFile ||
            !specFile ||
            (evalMode === 'comparison' &&
              !syntheticFile)
          }
          className="w-full py-3 px-4 rounded-xl text-white font-medium bg-indigo-600 hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading
            ? status || 'Evaluating Query Battery...'
            : evalMode === 'comparison'
              ? 'Run Fidelity Benchmark'
              : 'Extract Real Query Profiles'}
        </button>

      </form>
    </div>
  );
}