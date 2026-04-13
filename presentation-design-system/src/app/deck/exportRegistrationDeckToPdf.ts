import { renderSlideElementToCanvas } from '../templates/exportSlideToPdf';

const SLIDE_WIDTH = 1920;
const SLIDE_HEIGHT = 1080;

function waitNextPaint(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}

export type ExportPdfProgress = { current: number; total: number };

/**
 * Capture un conteneur slide (1920×1080) pour chaque index, après `prepareSlide`,
 * puis assemble un PDF paysage une page par slide.
 */
export async function exportRegistrationDeckToPdf(options: {
  captureRoot: HTMLElement;
  slideCount: number;
  /** Doit mettre à jour le DOM pour afficher la slide `index` (ex. flushSync + setState). */
  prepareSlide: (index: number) => void | Promise<void>;
  fileName?: string;
  onProgress?: (p: ExportPdfProgress) => void;
  /** Délai après chaque changement de slide pour polices / layout (ms). */
  settleMs?: number;
}): Promise<void> {
  const {
    captureRoot,
    slideCount,
    prepareSlide,
    fileName = 'vancelian-registration-deck.pdf',
    onProgress,
    settleMs = 80,
  } = options;

  if (slideCount <= 0) return;

  const { jsPDF } = await import('jspdf');

  if (typeof document !== 'undefined' && document.fonts?.ready) {
    await document.fonts.ready;
  }

  if (typeof window !== 'undefined') {
    window.scrollTo(0, 0);
  }

  const pdf = new jsPDF({
    orientation: 'landscape',
    unit: 'px',
    format: [SLIDE_WIDTH, SLIDE_HEIGHT],
    compress: true,
  });

  for (let i = 0; i < slideCount; i++) {
    await prepareSlide(i);
    await waitNextPaint();
    if (settleMs > 0) {
      await new Promise((r) => setTimeout(r, settleMs));
    }

    // foreignObject : oklab OK. Slide en fixed left-0 top-0 pendant l’export pour éviter left < 0 (crop gauche).
    // Ne pas forcer windowWidth/Height : ils décalent le repère par rapport au viewport réel et rognent la capture.
    if (typeof window !== 'undefined') {
      window.scrollTo(0, 0);
    }

    const canvas = await renderSlideElementToCanvas(captureRoot, { settleMs: 0 });

    const imgData = canvas.toDataURL('image/jpeg', 0.92);

    if (i > 0) {
      pdf.addPage([SLIDE_WIDTH, SLIDE_HEIGHT], 'landscape');
    }

    pdf.addImage(imgData, 'JPEG', 0, 0, SLIDE_WIDTH, SLIDE_HEIGHT);

    onProgress?.({ current: i + 1, total: slideCount });
  }

  pdf.save(fileName);
}
