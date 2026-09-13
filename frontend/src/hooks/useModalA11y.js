import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

/**
 * Standard modal keyboard behavior, shared by every dialog/modal component:
 * focus moves into the dialog when it opens, Tab/Shift+Tab cycle within it
 * instead of escaping to the page behind it, and Escape closes it.
 *
 * @param {boolean} isOpen
 * @param {() => void} onClose
 * @returns {import('react').RefObject<HTMLElement>} Attach to the dialog's outermost element.
 */
function useModalA11y(isOpen, onClose) {
  const containerRef = useRef(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    onCloseRef.current = onClose
  })

  useEffect(() => {
    if (!isOpen) return undefined

    const container = containerRef.current
    const focusable = container?.querySelectorAll(FOCUSABLE_SELECTOR)
    focusable?.[0]?.focus()

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        onCloseRef.current()
        return
      }
      if (event.key !== 'Tab' || !container) return

      const nodes = container.querySelectorAll(FOCUSABLE_SELECTOR)
      if (nodes.length === 0) return
      const first = nodes[0]
      const last = nodes[nodes.length - 1]

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  return containerRef
}

export default useModalA11y
