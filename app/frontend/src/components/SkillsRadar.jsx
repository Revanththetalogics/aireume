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
    <div className="bg-brand-50/60 rounded-2xl p-5 ring-1 ring-brand-100">
      <h3 className="text-sm font-bold text-brand-900 uppercase tracking-wide mb-4">
        Skills Gap Visualization
      </h3>

      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <p className="text-xs text-slate-500 mb-2 text-center font-medium">Skills Coverage Radar</p>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#DDD6FE" />
              <PolarAngleAxis dataKey="category" tick={{ fontSize: 10, fill: '#6B7280' }} />
              <Radar name="Has"   dataKey="Has"   stroke="#7C3AED" fill="#7C3AED" fillOpacity={0.35} />
              <Radar name="Needs" dataKey="Needs" stroke="#F43F5E" fill="#F43F5E" fillOpacity={0.2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div>
          <p className="text-xs text-slate-500 mb-2 text-center font-medium">Has vs. Needs by Category</p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={barData} layout="vertical" margin={{ left: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EDE9FE" />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#6B7280' }} />
              <YAxis dataKey="name" type="category" tick={{ fontSize: 10, fill: '#6B7280' }} width={70} />
              <Tooltip
                contentStyle={{ borderRadius: '12px', border: '1px solid #EDE9FE', boxShadow: '0 4px 16px rgba(124,58,237,0.12)' }}
              />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              <Bar dataKey="Has"   fill="#7C3AED" radius={[0, 4, 4, 0]} />
              <Bar dataKey="Needs" fill="#F43F5E" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
