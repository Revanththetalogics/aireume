import { useState, useEffect } from 'react'
import { Card, Skeleton } from '../components/ui'
import { getAnalyticsMetrics, getBiExportManifest } from '../lib/api'
import { ANALYTICS } from '../lib/uxLabels'

export default function AnalyticsDocsPage() {
  const [metrics, setMetrics] = useState(null)
  const [manifest, setManifest] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getAnalyticsMetrics(),
      getBiExportManifest(),
    ])
      .then(([m, man]) => {
        setMetrics(m)
        setManifest(man)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Skeleton className="h-64 rounded-2xl" />

  return (
    <div className="space-y-6">
      <p className="text-sm text-slate-600">{ANALYTICS.docsSubtitle}</p>

      <Card className="p-4">
        <h2 className="text-lg font-bold text-brand-900 mb-4">{ANALYTICS.glossaryTitle}</h2>
        <div className="space-y-4">
          {(metrics?.metrics || []).map((m) => (
            <div key={m.key} className="border-b border-slate-100 pb-3 last:border-0">
              <p className="font-semibold text-brand-800">{m.label}</p>
              <p className="text-sm text-slate-600 mt-1">{m.definition}</p>
              {m.formula && (
                <p className="text-xs text-slate-500 mt-1 font-mono">{m.formula}</p>
              )}
              {m.caveats && (
                <p className="text-xs text-amber-700 mt-1">{m.caveats}</p>
              )}
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-4">
        <h2 className="text-lg font-bold text-brand-900 mb-2">{ANALYTICS.biManifestTitle}</h2>
        <p className="text-sm text-slate-600 mb-4">{manifest?.description || ANALYTICS.biManifestHint}</p>
        {manifest?.entities && (
          <div className="grid sm:grid-cols-2 gap-4 mb-4">
            {Object.entries(manifest.entities).map(([name, fields]) => (
              <div key={name} className="rounded-xl bg-slate-50 p-3">
                <p className="text-xs font-bold uppercase text-slate-500">{name}</p>
                <p className="text-xs text-slate-600 mt-1">{(fields || []).join(', ')}</p>
              </div>
            ))}
          </div>
        )}
        {manifest?.export_endpoints && (
          <ul className="text-sm space-y-1">
            {Object.entries(manifest.export_endpoints).map(([k, v]) => (
              <li key={k}><span className="font-semibold">{k}:</span> <code className="text-xs bg-slate-100 px-1 rounded">{v}</code></li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
