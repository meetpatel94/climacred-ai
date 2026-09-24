import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  UploadCloud,
  FileSpreadsheet,
  File as FileIcon,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Loader2,
  Database,
  Building2,
  History,
  Play,
  Trash2,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import {
  ImportFileResult,
  ImportStatus,
  PageId,
} from '../types';
import {
  activateImportedBusiness,
  getImportStatus,
  importDataFiles,
  previewImport,
  resetAllStoredData,
} from '../services/api';
import { EmptyState } from '../components/common/EmptyState';

interface DataImportPageProps {
  onNavigate: (page: PageId) => void;
  /** Called after a successful import so the app can reload every stored dataset. */
  onDataImported: () => void;
  notify: (type: 'success' | 'info' | 'warning' | 'error', title: string, message?: string) => void;
}

type Stage = 'idle' | 'previewing' | 'ready' | 'importing' | 'completed' | 'error';

const STAGES: Array<{ key: Stage; label: string }> = [
  { key: 'previewing', label: 'Uploading' },
  { key: 'ready', label: 'Validating' },
  { key: 'importing', label: 'Importing' },
  { key: 'completed', label: 'Completed' },
];

const ACCEPTED = '.xlsx,.xls,.csv';

const formatBytes = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(2)} MB`;
};

const fileKind = (name: string): string => {
  const ext = name.split('.').pop()?.toLowerCase();
  if (ext === 'xlsx') return 'Excel Workbook';
  if (ext === 'xls') return 'Excel 97-2003';
  if (ext === 'csv') return 'CSV';
  return 'Unsupported';
};

const isAccepted = (name: string): boolean => {
  const ext = name.split('.').pop()?.toLowerCase();
  return ext === 'xlsx' || ext === 'xls' || ext === 'csv';
};

export const DataImportPage: React.FC<DataImportPageProps> = ({ onNavigate, onDataImported, notify }) => {
  const [files, setFiles] = useState<File[]>([]);
  const [stage, setStage] = useState<Stage>('idle');
  const [previews, setPreviews] = useState<ImportFileResult[] | null>(null);
  const [results, setResults] = useState<ImportFileResult[] | null>(null);
  const [summaryText, setSummaryText] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [status, setStatus] = useState<ImportStatus | null>(null);
  const [dragging, setDragging] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  const refreshStatus = useCallback(async () => {
    try {
      setStatus(await getImportStatus());
    } catch (err: any) {
      setFailure(err?.message || 'Could not reach the ClimaCred backend.');
    }
  }, []);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const list = Array.from(incoming);
    const accepted = list.filter((file) => isAccepted(file.name));
    const rejected = list.filter((file) => !isAccepted(file.name));
    if (rejected.length) {
      notify('warning', 'Unsupported file type', `${rejected.map((f) => f.name).join(', ')} - use .xlsx, .xls or .csv.`);
    }
    if (!accepted.length) return;
    setFiles((prev) => {
      const byName = new Map(prev.map((file) => [file.name, file]));
      accepted.forEach((file) => byName.set(file.name, file));
      return Array.from(byName.values());
    });
    setStage('idle');
    setPreviews(null);
    setResults(null);
    setSummaryText(null);
    setFailure(null);
  }, [notify]);

  const preview = useCallback(async () => {
    if (!files.length) return;
    setStage('previewing');
    setFailure(null);
    setResults(null);
    setSummaryText(null);
    try {
      const response = await previewImport(files);
      setPreviews(response.results);
      setStage('ready');
    } catch (err: any) {
      setStage('error');
      setFailure(err?.message || 'Could not read the selected files.');
    }
  }, [files]);

  const runImport = useCallback(async () => {
    if (!files.length) return;
    setStage('importing');
    setFailure(null);
    try {
      const response = await importDataFiles(files);
      setResults(response.results);
      setSummaryText(response.message);
      setStage(response.success ? 'completed' : 'error');
      if (!response.success) {
        setFailure(`${response.datasets_failed} file(s) could not be imported.`);
      }
      if (response.assessment?.synced) {
        notify(
          'success',
          'Climate Assessment recalculated',
          `${response.assessment.business_id} scored ${response.assessment.overall_score}/100 (${response.assessment.score_label}).`
        );
      }
      await refreshStatus();
      onDataImported();
    } catch (err: any) {
      setStage('error');
      setFailure(err?.message || 'Import failed.');
    }
  }, [files, notify, onDataImported, refreshStatus]);

  const clear = () => {
    setFiles([]);
    setPreviews(null);
    setResults(null);
    setSummaryText(null);
    setFailure(null);
    setStage('idle');
    if (inputRef.current) inputRef.current.value = '';
  };

  const previewFor = (name: string): ImportFileResult | undefined => previews?.find((r) => r.filename === name);

  const busy = stage === 'previewing' || stage === 'importing';
  const stageIndex = STAGES.findIndex((s) => s.key === stage);

  const totalRows = useMemo(() => previews?.reduce((sum, r) => sum + r.rows_received, 0) ?? 0, [previews]);
  const invalidRows = useMemo(() => previews?.reduce((sum, r) => sum + r.rows_rejected, 0) ?? 0, [previews]);

  return (
    <div className="space-y-6 max-w-6xl pb-16">
      {/* Header */}
      <div className="bg-white border border-slate-200/90 rounded-3xl p-6 sm:p-8 shadow-xs space-y-3">
        <div className="flex items-center gap-2">
          <span className="p-2 rounded-xl bg-emerald-50 text-emerald-700">
            <UploadCloud className="w-5 h-5" />
          </span>
          <span className="text-xs font-bold uppercase tracking-wider text-emerald-800">Excel / CSV</span>
        </div>
        <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">Import Business Data</h2>
        <p className="text-sm text-slate-600 max-w-3xl leading-relaxed">
          Upload your ClimaCred business datasets to build your climate profile, assessment and
          historical intelligence.
        </p>
        <div className="flex flex-wrap gap-2 pt-1">
          {(status?.supported_formats || ['.xlsx', '.xls', '.csv']).map((fmt) => (
            <span key={fmt} className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-700 text-[11px] font-bold font-mono">
              {fmt}
            </span>
          ))}
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 text-[11px] font-semibold">
            up to {status?.max_file_mb ?? 25} MB per file
          </span>
          <span className="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-600 text-[11px] font-semibold">
            multiple files at once
          </span>
        </div>
        <p className="text-[11px] text-slate-500">
          Files are parsed and stored by the ClimaCred backend - they are never sent to Gemini.
          {status?.recommended_import_order?.length
            ? ` Import ${status.recommended_import_order[0]} first so the other datasets can be linked by business id.`
            : ''}
        </p>
      </div>

      {/* Dropzone */}
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => {
          event.preventDefault();
          setDragging(false);
          if (event.dataTransfer?.files?.length) addFiles(event.dataTransfer.files);
        }}
        className={`rounded-3xl border-2 border-dashed p-8 sm:p-10 text-center transition-colors ${
          dragging ? 'border-emerald-500 bg-emerald-50/60' : 'border-slate-300 bg-white'
        }`}
      >
        <span className="inline-flex w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-700 items-center justify-center mb-3">
          <UploadCloud className="w-6 h-6" />
        </span>
        <p className="text-sm font-bold text-slate-800">Drag &amp; drop your datasets here</p>
        <p className="text-xs text-slate-600 mt-1">or</p>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="mt-3 inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors"
        >
          <FileSpreadsheet className="w-4 h-4" />
          Select Files
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED}
          className="hidden"
          onChange={(event) => {
            if (event.target.files?.length) addFiles(event.target.files);
            event.target.value = '';
          }}
        />
      </div>

      {/* Selected files */}
      {files.length > 0 && (
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
              Selected files ({files.length})
            </h3>
            <button
              type="button"
              onClick={clear}
              className="inline-flex items-center gap-1 text-[11px] font-bold text-slate-500 hover:text-rose-600"
            >
              <Trash2 className="w-3.5 h-3.5" /> Clear
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100">
                  <th className="px-5 py-2.5">Filename</th>
                  <th className="px-3 py-2.5">File type</th>
                  <th className="px-3 py-2.5">Size</th>
                  <th className="px-3 py-2.5">Detected dataset</th>
                  <th className="px-3 py-2.5 text-right">Rows</th>
                  <th className="px-5 py-2.5">Validation</th>
                </tr>
              </thead>
              <tbody>
                {files.map((file) => {
                  const info = previewFor(file.name);
                  const invalid = isAccepted(file.name) ? false : true;
                  const rowErrors = info?.validation_errors?.length ?? 0;
                  const ok = info ? info.success && rowErrors === 0 : null;
                  return (
                    <React.Fragment key={file.name}>
                      <tr className="border-b border-slate-50 text-xs">
                        <td className="px-5 py-2.5 font-semibold text-slate-800">
                          <div className="flex items-center gap-2">
                            <FileIcon className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                            <span className="truncate max-w-[16rem]">{file.name}</span>
                          </div>
                        </td>
                        <td className="px-3 py-2.5 text-slate-600 whitespace-nowrap">{fileKind(file.name)}</td>
                        <td className="px-3 py-2.5 text-slate-600 whitespace-nowrap">{formatBytes(file.size)}</td>
                        <td className="px-3 py-2.5 text-slate-700 whitespace-nowrap">
                          {invalid ? (
                            <span className="text-rose-600 font-semibold">Unsupported format</span>
                          ) : info ? (
                            info.dataset_label || <span className="text-rose-600 font-semibold">Not recognised</span>
                          ) : (
                            <span className="text-slate-400">—</span>
                          )}
                        </td>
                        <td className="px-3 py-2.5 text-right font-mono text-slate-700">
                          {info ? info.rows_received : '—'}
                        </td>
                        <td className="px-5 py-2.5 whitespace-nowrap">
                          {invalid ? (
                            <span className="inline-flex items-center gap-1 text-rose-600 font-semibold">
                              <XCircle className="w-3.5 h-3.5" /> Rejected
                            </span>
                          ) : !info ? (
                            <span className="text-slate-400 text-[11px]">Not checked yet</span>
                          ) : ok ? (
                            <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Valid
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() => setExpanded(expanded === file.name ? null : file.name)}
                              className="inline-flex items-center gap-1 text-amber-700 font-semibold"
                            >
                              <AlertTriangle className="w-3.5 h-3.5" />
                              {info.rows_rejected || rowErrors} row(s) rejected
                              {expanded === file.name ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            </button>
                          )}
                        </td>
                      </tr>
                      {expanded === file.name && info && info.validation_errors?.length > 0 && (
                        <tr>
                          <td colSpan={6} className="px-5 py-3 bg-amber-50/60 border-b border-amber-100">
                            <ul className="space-y-1">
                              {info.validation_errors.slice(0, 25).map((error, index) => (
                                <li key={index} className="text-[11px] text-amber-900 font-medium">
                                  {error.row ? `Row ${error.row}: ` : ''}
                                  {error.column ? <span className="font-mono">{error.column}</span> : null}{' '}
                                  {error.message}
                                </li>
                              ))}
                              {info.validation_errors.length > 25 && (
                                <li className="text-[11px] text-amber-800">
                                  …and {info.validation_errors.length - 25} more.
                                </li>
                              )}
                            </ul>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Actions */}
          <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="text-[11px] text-slate-600">
              {previews ? (
                <>
                  <span className="font-bold text-slate-800">{totalRows.toLocaleString()}</span> rows detected
                  {invalidRows > 0 && (
                    <>
                      {' '}· <span className="font-bold text-amber-700">{invalidRows.toLocaleString()}</span> would be rejected
                    </>
                  )}
                </>
              ) : (
                'Validate first to see the detected dataset, row count and any problems.'
              )}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={preview}
                disabled={busy}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 hover:bg-white text-xs font-bold transition-colors disabled:opacity-50"
              >
                {stage === 'previewing' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileSpreadsheet className="w-3.5 h-3.5" />}
                Validate
              </button>
              <button
                type="button"
                onClick={runImport}
                disabled={busy}
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition-colors disabled:opacity-50"
              >
                {stage === 'importing' ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                Import Data
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Progress */}
      {(busy || stage === 'completed' || stage === 'error') && (
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-xs">
          <div className="flex flex-wrap items-center gap-2">
            {STAGES.map((step, index) => {
              const done = stageIndex > index || stage === 'completed';
              const active = stageIndex === index && busy;
              return (
                <React.Fragment key={step.key}>
                  <span
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold ${
                      done
                        ? 'bg-emerald-100 text-emerald-800'
                        : active
                        ? 'bg-slate-900 text-white'
                        : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {active ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : done ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : null}
                    {step.label}
                  </span>
                  {index < STAGES.length - 1 && <span className="text-slate-300">→</span>}
                </React.Fragment>
              );
            })}
          </div>

          {summaryText && (
            <p
              className={`mt-3 text-sm font-bold ${
                stage === 'completed' ? 'text-emerald-700' : 'text-slate-800'
              }`}
            >
              {summaryText}
            </p>
          )}
          {failure && <p className="mt-2 text-xs font-semibold text-rose-700">{failure}</p>}

          {results && (
            <ul className="mt-3 space-y-1.5">
              {results.map((result) => (
                <li key={`${result.filename}-${result.import_id}`} className="flex items-start gap-2 text-[11px]">
                  {result.success ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 mt-0.5 shrink-0" />
                  ) : (
                    <XCircle className="w-3.5 h-3.5 text-rose-600 mt-0.5 shrink-0" />
                  )}
                  <span className="text-slate-700">
                    <span className="font-semibold">{result.filename}</span>
                    {result.dataset_label ? ` — ${result.dataset_label}` : ''}
                    {result.rows_imported > 0 ? ` — ${result.rows_imported} rows stored` : ''}
                    {result.rows_rejected > 0 ? ` — ${result.rows_rejected} rejected` : ''}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Imported businesses */}
      {status && status.businesses.length > 0 && (
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
          <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-emerald-700" />
            <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">
              Imported businesses ({status.businesses.length})
            </h3>
          </div>
          <div className="divide-y divide-slate-50">
            {status.businesses.map((business) => (
              <div key={business.business_id} className="px-5 py-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="min-w-0">
                  <p className="text-xs font-bold text-slate-800 truncate">
                    {business.business_name || business.business_id}
                    {business.active && (
                      <span className="ml-2 text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-emerald-100 text-emerald-800 uppercase">
                        Active
                      </span>
                    )}
                  </p>
                  <p className="text-[11px] text-slate-600">
                    <span className="font-mono">{business.business_id}</span>
                    {business.industry ? ` · ${business.industry}` : ''}
                    {business.business_size ? ` · ${business.business_size}` : ''}
                    {` · ${business.total_rows.toLocaleString()} linked rows`}
                  </p>
                </div>
                {!business.active && (
                  <button
                    type="button"
                    onClick={async () => {
                      try {
                        const res = await activateImportedBusiness(business.business_id);
                        notify('success', 'Business switched', `Now analysing ${business.business_name || business.business_id}.`);
                        if (res.assessment_synced?.synced) {
                          notify('info', 'Climate Assessment recalculated', `Score ${res.assessment_synced.overall_score}/100.`);
                        }
                        await refreshStatus();
                        onDataImported();
                      } catch (err: any) {
                        notify('error', 'Could not switch business', err?.message);
                      }
                    }}
                    className="self-start sm:self-auto text-[11px] font-bold px-3 py-1.5 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50"
                  >
                    Make active
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent imports */}
      <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
          <History className="w-4 h-4 text-emerald-700" />
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">Recent Imports</h3>
        </div>
        {status && status.recent_imports.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-100">
                  <th className="px-5 py-2.5">Filename</th>
                  <th className="px-3 py-2.5">Dataset</th>
                  <th className="px-3 py-2.5 text-right">Rows</th>
                  <th className="px-3 py-2.5">Status</th>
                  <th className="px-5 py-2.5">Imported at</th>
                </tr>
              </thead>
              <tbody>
                {status.recent_imports.map((entry, index) => (
                  <tr key={`${entry.import_id}-${index}`} className="border-b border-slate-50 text-xs">
                    <td className="px-5 py-2.5 font-semibold text-slate-800 truncate max-w-[16rem]">{entry.filename}</td>
                    <td className="px-3 py-2.5 text-slate-600 whitespace-nowrap">{entry.dataset_label || '—'}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-700">{entry.rows_imported}</td>
                    <td className="px-3 py-2.5 whitespace-nowrap">
                      {entry.success ? (
                        <span className="inline-flex items-center gap-1 text-emerald-700 font-semibold">
                          <CheckCircle2 className="w-3.5 h-3.5" /> Imported
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-rose-600 font-semibold" title={entry.message}>
                          <XCircle className="w-3.5 h-3.5" /> Failed
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-2.5 text-slate-600 whitespace-nowrap">
                      {entry.started_at ? new Date(entry.started_at).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={History}
            title="No imports yet"
            message="Uploaded files and their validation results are listed here."
            variant="inline"
          />
        )}
      </div>

      {/* Stored data & reset */}
      <div className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
        <div className="px-5 py-3 border-b border-slate-100 flex items-center gap-2">
          <Database className="w-4 h-4 text-emerald-700" />
          <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700">Stored data</h3>
        </div>
        <div className="px-5 py-4 space-y-3">
          <p className="text-[11px] text-slate-600">
            Document counts per MongoDB collection. An empty database really is empty - nothing is
            seeded or faked.
          </p>
          <div className="flex flex-wrap gap-1.5">
            {status &&
              Object.entries(status.collections)
                .filter(([, count]) => count > 0)
                .map(([name, count]) => (
                  <span key={name} className="px-2 py-1 rounded-lg bg-slate-100 text-slate-700 text-[10px] font-mono font-semibold">
                    {name}: {count}
                  </span>
                ))}
            {status && Object.values(status.collections).every((count) => count === 0) && (
              <span className="text-[11px] font-semibold text-slate-500">No documents stored.</span>
            )}
          </div>
          {status?.active_business && (
            <p className="text-[11px] text-slate-600">
              Active business:{' '}
              <span className="font-semibold text-slate-800">{status.active_business.name || '—'}</span>
              {status.active_business.business_id ? ` (${status.active_business.business_id})` : ''}
              {' · source: '}
              <span className="font-mono">{status.active_business.source || 'unknown'}</span>
            </p>
          )}
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button
              type="button"
              onClick={async () => {
                try {
                  const result = await resetAllStoredData();
                  notify('success', 'All data cleared', 'The database is empty again.');
                  clear();
                  await refreshStatus();
                  onDataImported();
                  return result;
                } catch (err: any) {
                  notify('error', 'Reset failed', err?.message);
                }
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 text-[11px] font-bold"
            >
              <Trash2 className="w-3.5 h-3.5" /> Delete all stored data
            </button>
            <button
              type="button"
              onClick={() => onNavigate('profile')}
              className="text-[11px] font-bold text-emerald-700 hover:text-emerald-800"
            >
              Or enter a business profile manually →
            </button>
          </div>
        </div>
      </div>

      {/* Supported datasets */}
      {status && (
        <details className="bg-white border border-slate-200/90 rounded-2xl shadow-xs overflow-hidden">
          <summary className="px-5 py-3 cursor-pointer text-xs font-extrabold uppercase tracking-wider text-slate-700 flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-emerald-700" />
            Supported datasets ({status.datasets.length})
          </summary>
          <div className="px-5 pb-5 grid grid-cols-1 md:grid-cols-2 gap-3">
            {status.datasets.map((dataset) => (
              <div key={dataset.dataset_type} className="p-3 rounded-xl border border-slate-200 bg-slate-50/60">
                <p className="text-xs font-bold text-slate-800">{dataset.label}</p>
                <p className="text-[10px] font-mono text-slate-500">{dataset.dataset_type} → {dataset.collection}</p>
                <p className="text-[11px] text-slate-600 mt-1">{dataset.description}</p>
                <p className="text-[10px] text-slate-500 mt-1.5">
                  <span className="font-bold uppercase">Required:</span> {dataset.required_columns.join(', ')}
                </p>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
};

export default DataImportPage;
