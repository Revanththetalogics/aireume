import { createContext, useContext, useMemo, useState } from 'react'

const LiveScreenModeContext = createContext({
  active: false,
  setActive: () => {},
})

export function LiveScreenModeProvider({ children }) {
  const [active, setActive] = useState(false)
  const value = useMemo(() => ({ active, setActive }), [active])
  return (
    <LiveScreenModeContext.Provider value={value}>
      {children}
    </LiveScreenModeContext.Provider>
  )
}

export function useLiveScreenMode() {
  return useContext(LiveScreenModeContext)
}
