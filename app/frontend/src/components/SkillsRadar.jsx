import {
  RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend, CartesianGrid
} from 'recharts'

function categorizeSkill(skill) {
  const s = skill.toLowerCase()
  if (['python','java','javascript','typescript','c++','c#','golang','rust','scala'].some(k => s.includes(k))) return 'Programming'
  if (['react','vue','angular','node','django','flask','fastapi','spring'].some(k => s.includes(k))) return 'Frameworks'
  if (['aws','azure','gcp','docker','kubernetes','terraform','ansible','linux','ci/cd'].some(k => s.includes(k))) return 'DevOps/Cloud'
  if (['sql','postgresql','mysql','mongodb','redis','elasticsearch','kafka'].some(k => s.includes(k))) return 'Data/DB'
  if (['management','leadership','communication','agile','scrum'].some(k => s.includes(k))) return 'Soft Skills'
  return 'Domain'
}

export default function SkillsRadar({ matchedSkills = [], missingSkills = [] }) {
  if (!matchedSkills.length && !missingSkills.length) return null

  // Build category totals
  const categories = ['Programming', 'Frameworks', 'DevOps/Cloud', 'Data/DB', 'Soft Skills', 'Domain']
  const matched = {}
  const missing = {}
  categories.forEach(c => { matched[c] = 0; missing[c] = 0 })

  matchedSkills.forEach(s => { const c = categorizeSkill(s); matched[c]++ })
  missingSkills.forEach(s => { const c = categorizeSkill(s); missing[c]++ })

  const radarData = categories.map(c => ({
    category: c,
    Has: matched[c],
    Needs: missing[c],
    fullMark: Math.max(...categories.map(cat => matched[cat] + missing[cat]), 1),
  })).filter(d => d.Has > 0 || d.Needs > 0)

  const barData = categories.map(c => ({
    name: c,
    Has: matched[c],
    Needs: missing[c],
  })).filter(d => d.Has > 0 || d.Needs > 0)

  return (
    <div className="bg-slate-50 rounded-lg p-5 border border-slate-200">
      <h3 className="text-sm font-semibold text-slate-700 uppercase tracking-wide mb-4">
        Skills Gap Visualization
      </h3>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Radar chart */}
        <div>
          <p className="text-xs text-slate-500 mb-2 text-center">Skills Coverage Radar</p>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="category" tick={{ fontSize: 10 }} />
              <Radar name="Has" dataKey="Has" stroke="#22c55e" fill="#22c55e" fillOpacity={0.4} />
              <Radar name="Needs" dataKey="Needs" stroke="#ef4444" fill="#ef4444" fillOpacity={0.2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Bar chart */}
        <div>
          <p className="text-xs text-slate-500 mb-2 text-center">Has vs. Needs by Category</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 10 }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 10 }} width={70} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Bar dataKey="Has" fill="#22c55e" radius={[0, 3, 3, 0]} />
              <Bar dataKey="Needs" fill="#ef4444" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
