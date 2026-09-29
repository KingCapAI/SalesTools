import { Header } from '../components/layout/Header';
import calendarHtml from '../content/marketing-calendar-2027.html?raw';

/**
 * 2027 Marketing Calendar.
 * The calendar itself is a self-contained HTML page (its own styles and script) kept in
 * src/content/marketing-calendar-2027.html. It is bundled into the app as a raw string and
 * rendered in a sandboxed iframe so its styles never collide with Tailwind, and so the page
 * stays behind login rather than sitting in /public.
 */
export function MarketingCalendar() {
  return (
    <div className="min-h-screen bg-black flex flex-col">
      <Header />
      <iframe
        title="2027 Marketing Calendar"
        srcDoc={calendarHtml}
        sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox"
        className="flex-1 w-full border-0"
        style={{ minHeight: 'calc(100vh - 4rem)' }}
      />
    </div>
  );
}
