import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { flushSync } from 'react-dom';
import { Link } from 'react-router-dom';
import { Caption } from '../components/design-system';
import { exportRegistrationDeckToPdf } from './exportRegistrationDeckToPdf';
import { registrationSlides } from './registrationDeckContent';
import { RegistrationDeckSlide } from './RegistrationDeckSlide';

export default function RegistrationDeck() {
  const [index, setIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const slideCaptureRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  const [pdfExporting, setPdfExporting] = useState(false);
  const [pdfProgress, setPdfProgress] = useState<{ current: number; total: number } | null>(null);

  const total = registrationSlides.length;

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const w = el.clientWidth;
      const pad = 32;
      setScale(Math.min(1, Math.max(0.2, (w - pad) / 1920)));
    };

    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const go = useCallback(
    (delta: number) => {
      setIndex((i) => Math.max(0, Math.min(total - 1, i + delta)));
    },
    [total],
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault();
        go(1);
      }
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        go(-1);
      }
      if (e.key === 'Home') {
        e.preventDefault();
        setIndex(0);
      }
      if (e.key === 'End') {
        e.preventDefault();
        setIndex(total - 1);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go, total]);

  const handleDownloadPdf = useCallback(async () => {
    if (pdfExporting) return;

    const previousIndex = index;
    setPdfExporting(true);
    setPdfProgress(null);
    flushSync(() => {});

    // Laisser la slide de capture passer en overlay visible (voir JSX) avant html2canvas.
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
    await new Promise((r) => setTimeout(r, 200));

    const root = slideCaptureRef.current;
    if (!root) {
      setPdfExporting(false);
      return;
    }

    try {
      await exportRegistrationDeckToPdf({
        captureRoot: root,
        slideCount: total,
        prepareSlide: (i) => {
          flushSync(() => setIndex(i));
        },
        fileName: 'vancelian-registration-deck.pdf',
        onProgress: setPdfProgress,
        settleMs: 120,
      });
    } catch (e) {
      console.error(e);
      alert(
        e instanceof Error
          ? `Export PDF impossible : ${e.message}`
          : 'Export PDF impossible.',
      );
    } finally {
      flushSync(() => setIndex(previousIndex));
      setPdfExporting(false);
      setPdfProgress(null);
    }
  }, [index, pdfExporting, total]);

  return (
    <div className="flex min-h-screen flex-col bg-[#e5e5e5]">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-300 bg-white px-6 py-3">
        <Caption className="text-[#1e1c1b]">
          Flèches, espace, Page préc./suiv., Début / Fin — slide {index + 1} / {total}
          {pdfProgress ? (
            <span className="ml-2 text-[#4F46E5]">
              · PDF {pdfProgress.current}/{pdfProgress.total}
            </span>
          ) : null}
        </Caption>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => void handleDownloadPdf()}
            disabled={pdfExporting}
            className="rounded-md bg-[#4F46E5] px-4 py-2 text-sm font-medium text-white hover:bg-[#4338ca] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {pdfExporting ? 'Génération du PDF…' : 'Télécharger en PDF'}
          </button>
          <Link
            to="/templates"
            className="text-sm font-medium text-[#4F46E5] hover:underline"
          >
            Templates de slides
          </Link>
          <Link
            to="/design-system"
            className="text-sm font-medium text-[#4F46E5] hover:underline"
          >
            Design system
          </Link>
        </div>
      </header>

      <main
        ref={containerRef}
        className={`flex flex-1 justify-center overflow-auto px-4 py-8 ${pdfExporting ? 'invisible' : ''}`}
        aria-hidden={pdfExporting}
      >
        <div
          className="relative shrink-0 overflow-hidden rounded-sm shadow-lg"
          style={{
            width: 1920 * scale,
            height: 1080 * scale,
          }}
        >
          <div
            className="absolute left-0 top-0 origin-top-left"
            style={{
              width: 1920,
              height: 1080,
              transform: `scale(${scale})`,
            }}
          >
            <RegistrationDeckSlide
              slide={registrationSlides[index]}
              index={index}
              total={total}
            />
          </div>
        </div>
      </main>

      <footer className="border-t border-gray-300 bg-white px-6 py-4">
        <div className="mx-auto flex max-w-3xl flex-wrap items-center justify-center gap-4">
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={index <= 0 || pdfExporting}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-[#1e1c1b] disabled:opacity-40"
          >
            Précédent
          </button>
          <div className="flex flex-wrap justify-center gap-2">
            {registrationSlides.map((_, j) => (
              <button
                key={j}
                type="button"
                onClick={() => !pdfExporting && setIndex(j)}
                className={`h-2.5 w-2.5 rounded-full transition-colors ${
                  j === index ? 'bg-[#4F46E5]' : 'bg-gray-300 hover:bg-gray-400'
                }`}
                aria-label={`Aller à la slide ${j + 1}`}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={() => go(1)}
            disabled={index >= total - 1 || pdfExporting}
            className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-[#1e1c1b] disabled:opacity-40"
          >
            Suivant
          </button>
        </div>
      </footer>

      {/* Overlay + slide : pas de flex center (évite left négatif → crop gauche avec html2canvas / foreignObject). */}
      {pdfExporting ? (
        <div
          className="fixed inset-0 z-[99998] bg-[rgba(0,0,0,0.5)]"
          aria-hidden
        />
      ) : null}
      <div
        ref={slideCaptureRef}
        className={
          pdfExporting
            ? 'fixed left-0 top-0 z-[99999] shadow-2xl [box-shadow:0_0_0_1px_rgba(255,255,255,0.25)]'
            : 'pointer-events-none fixed left-[-12000px] top-0 z-0 overflow-hidden'
        }
        style={{ width: 1920, height: 1080 }}
      >
        <RegistrationDeckSlide
          slide={registrationSlides[index]}
          index={index}
          total={total}
        />
      </div>
      {pdfExporting ? (
        <p className="fixed left-1/2 top-6 z-[100000] -translate-x-1/2 rounded-md bg-white/95 px-4 py-2 text-sm font-medium text-[#1e1c1b] shadow-md">
          Génération du PDF…
        </p>
      ) : null}
    </div>
  );
}
