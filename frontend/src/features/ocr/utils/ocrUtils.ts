// Extract rectangular boxes from OCR data
export const extractBlockBoxes = (ocrData: any) => {
    const blocks: { x: number; y: number; width: number; height: number }[] = [];
    try {
        const list = ocrData?.blocks || [];
        for (const block of list) {
            const v = block.boundingBox?.vertices || [];
            if (v.length === 4) {
                const xs = v.map((p: { x: any; }) => p.x ?? 0);
                const ys = v.map((p: { y: any; }) => p.y ?? 0);
                const x = Math.min(...xs);
                const y = Math.min(...ys);
                blocks.push({x, y, width: Math.max(...xs) - x, height: Math.max(...ys) - y});
            }
        }
    } catch (e) {
        console.warn('Failed to parse OCR block boxes', e);
    }
    return blocks;
};

// Determine if OCR block is inside a segmentation box
export const isBoxInside = (
    block: { x: number; y: number; width: number; height: number },
    seg: { x: number; y: number; width: number; height: number }
) =>
    block.x >= seg.x * 0.9 &&
    block.y >= seg.y * 0.9 &&
    block.x + block.width <= (seg.x + seg.width) * 1.1 &&
    block.y + block.height <= (seg.y + seg.height) * 1.1;
