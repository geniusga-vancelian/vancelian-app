export const SLIDE_PDF_WIDTH = 1920;
export const SLIDE_PDF_HEIGHT = 1080;

function waitNextPaint(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(() => resolve());
    });
  });
}

const HTML2CANVAS_OPTS = {
  foreignObjectRendering: true,
  scale: 1.5,
  width: SLIDE_PDF_WIDTH,
  height: SLIDE_PDF_HEIGHT,
  scrollX: 0,
  scrollY: 0,
  useCORS: true,
  allowTaint: false,
  backgroundColor: '#ffffff',
  logging: false,
} as const;

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const fr = new FileReader();
    fr.onload = () => resolve(fr.result as string);
    fr.onerror = () => reject(fr.error);
    fr.readAsDataURL(blob);
  });
}

/** http(s) absolu ou résolu ; pas data:/blob: (déjà exploitables par le canvas). */
function isInlinableHttpUrl(src: string, baseHref: string): boolean {
  if (!src || src.startsWith('data:') || src.startsWith('blob:')) return false;
  try {
    const u = new URL(src, baseHref);
    return u.protocol === 'http:' || u.protocol === 'https:';
  } catch {
    return false;
  }
}

function waitForImg(img: HTMLImageElement): Promise<void> {
  if (img.complete && img.naturalHeight > 0) {
    return (img.decode?.() ?? Promise.resolve()).catch(() => undefined);
  }
  return new Promise((resolve) => {
    const done = () => resolve();
    img.addEventListener('load', done, { once: true });
    img.addEventListener('error', done, { once: true });
    setTimeout(done, 12_000);
  });
}

function waitForSvgImage(el: SVGImageElement): Promise<void> {
  return new Promise((resolve) => {
    const done = () => resolve();
    el.addEventListener('load', done, { once: true });
    el.addEventListener('error', done, { once: true });
    setTimeout(done, 12_000);
    try {
      if ((el as SVGImageElement & { complete?: boolean }).complete) done();
    } catch {
      /* ignore */
    }
  });
}

/**
 * Remplace temporairement les `src` / `href` http(s) par des data URLs pour que html2canvas
 * peigne les pixels (sinon `<img>` / `<image>` externes ou CORS → zones vides dans le PDF).
 * Retourne une fonction pour restaurer le DOM.
 */
export async function inlineHttpRastersForPdfCapture(root: HTMLElement): Promise<() => void> {
  const undos: Array<() => void> = [];
  const base = typeof window !== 'undefined' ? window.location.href : 'http://localhost/';

  const fetchAsDataUrl = async (absoluteUrl: string): Promise<string | null> => {
    try {
      const res = await fetch(absoluteUrl, { mode: 'cors', credentials: 'omit' });
      if (!res.ok) return null;
      const blob = await res.blob();
      return await blobToDataUrl(blob);
    } catch {
      return null;
    }
  };

  for (const el of root.querySelectorAll('img')) {
    const img = el as HTMLImageElement;
    const src = img.currentSrc || img.src;
    if (!isInlinableHttpUrl(src, base)) continue;
    let absolute: string;
    try {
      absolute = new URL(src, base).href;
    } catch {
      continue;
    }
    const dataUrl = await fetchAsDataUrl(absolute);
    if (!dataUrl) continue;
    const prev = img.src;
    img.src = dataUrl;
    undos.push(() => {
      img.src = prev;
    });
    await waitForImg(img);
  }

  for (const el of root.querySelectorAll('image')) {
    const svgImg = el as SVGImageElement;
    const hrefRaw =
      svgImg.getAttribute('href') ||
      svgImg.getAttributeNS('http://www.w3.org/1999/xlink', 'href');
    if (!hrefRaw || !isInlinableHttpUrl(hrefRaw, base)) continue;
    let absolute: string;
    try {
      absolute = new URL(hrefRaw, base).href;
    } catch {
      continue;
    }
    const dataUrl = await fetchAsDataUrl(absolute);
    if (!dataUrl) continue;
    const prevHref = svgImg.getAttribute('href');
    const prevXlink = svgImg.getAttributeNS('http://www.w3.org/1999/xlink', 'href');
    svgImg.setAttribute('href', dataUrl);
    if (prevXlink) {
      svgImg.removeAttributeNS('http://www.w3.org/1999/xlink', 'href');
    }
    undos.push(() => {
      if (prevHref != null) svgImg.setAttribute('href', prevHref);
      else svgImg.removeAttribute('href');
      if (prevXlink != null) {
        svgImg.setAttributeNS('http://www.w3.org/1999/xlink', 'href', prevXlink);
      }
    });
    await waitForSvgImage(svgImg);
  }

  await waitNextPaint();

  return () => {
    for (const u of undos.reverse()) {
      try {
        u();
      } catch {
        /* ignore */
      }
    }
  };
}

/**
 * Capture un nœud racine slide (1920×1080) — réutilisable pour un PDF multi-pages.
 */
export async function renderSlideElementToCanvas(
  element: HTMLElement,
  options?: { settleMs?: number },
): Promise<HTMLCanvasElement> {
  const settleMs = options?.settleMs ?? 120;

  if (typeof document !== 'undefined' && document.fonts?.ready) {
    await document.fonts.ready;
  }
  if (typeof window !== 'undefined') {
    window.scrollTo(0, 0);
  }

  const { default: html2canvas } = await import('html2canvas');

  await waitNextPaint();
  if (settleMs > 0) {
    await new Promise((r) => setTimeout(r, settleMs));
  }
  if (typeof window !== 'undefined') {
    window.scrollTo(0, 0);
  }

  let restoreDom: (() => void) | undefined;
  try {
    restoreDom = await inlineHttpRastersForPdfCapture(element);
    await waitNextPaint();
    await new Promise((r) => setTimeout(r, 60));

    return await html2canvas(element, HTML2CANVAS_OPTS);
  } finally {
    restoreDom?.();
  }
}

/**
 * Capture un nœud racine de slide et produit un PDF paysage une page.
 */
export async function exportSlideElementToPdf(
  element: HTMLElement,
  fileName = 'slide.pdf',
  options?: { settleMs?: number },
): Promise<void> {
  const canvas = await renderSlideElementToCanvas(element, options);
  const { jsPDF } = await import('jspdf');
  const pdf = new jsPDF({
    orientation: 'landscape',
    unit: 'px',
    format: [SLIDE_PDF_WIDTH, SLIDE_PDF_HEIGHT],
    compress: true,
  });
  const imgData = canvas.toDataURL('image/jpeg', 0.92);
  pdf.addImage(imgData, 'JPEG', 0, 0, SLIDE_PDF_WIDTH, SLIDE_PDF_HEIGHT);
  pdf.save(fileName);
}
