import { NavLink, Outlet } from 'react-router-dom'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-1.5 text-sm font-medium transition ${
    isActive
      ? 'bg-teal-600 text-white'
      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
  }`

export function Layout() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-300">
        Unsolicited demo by a candidate for Cloud & Data Engineering — not affiliated with PFASuiki.
      </div>

      <nav className="border-b border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        <div className="mx-auto flex max-w-5xl items-center justify-between">
          <span className="text-sm font-semibold tracking-tight">ReportForge</span>
          <div className="flex gap-2">
            <NavLink to="/" end className={navLinkClass}>
              Lab Report
            </NavLink>
            <NavLink to="/regwatch" className={navLinkClass}>
              RegWatch
            </NavLink>
          </div>
        </div>
      </nav>

      <div className="flex-1">
        <Outlet />
      </div>

      <footer className="border-t border-slate-200 px-4 py-6 text-center text-xs text-slate-500 dark:border-slate-800 dark:text-slate-500">
        Built with TypeScript, Python, LLMs, and GCP-ready architecture. Not affiliated with PFASuiki.
      </footer>
    </div>
  )
}
