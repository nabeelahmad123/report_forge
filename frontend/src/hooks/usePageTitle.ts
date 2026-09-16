import { useEffect } from 'react'

const SITE_NAME = 'ReportForge'

/** index.html's <title> is static, so without this every route shows the
 * same browser-tab title regardless of which page is actually open. */
export function usePageTitle(pageTitle: string) {
  useEffect(() => {
    document.title = `${pageTitle} — ${SITE_NAME}`
  }, [pageTitle])
}
