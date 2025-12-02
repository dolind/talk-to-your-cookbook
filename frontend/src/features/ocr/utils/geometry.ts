export const boundingBoxToRect = (box: { [p: string]: number }[]) => {
    const xs = box.map(v => v.x);
    const ys = box.map(v => v.y);
    const x = Math.min(...xs);
    const y = Math.min(...ys);
    const width = Math.max(...xs) - x;
    const height = Math.max(...ys) - y;
    return {x, y, width, height};
};

export const rectToBoundingBox = (x: number, y: number, w: number, h: number) => [
    {x: Math.round(x), y: Math.round(y)},
    {x: Math.round(x + w), y: Math.round(y)},
    {x: Math.round(x + w), y: Math.round(y + h)},
    {x: Math.round(x), y: Math.round(y + h)},
];
