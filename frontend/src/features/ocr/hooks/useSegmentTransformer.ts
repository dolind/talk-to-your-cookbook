import {useEffect} from 'react';
import Konva from 'konva';
import {SegmentationSegment} from '../../../lib/model';

interface UseSegmentTransformerProps {
    transformerRef: React.RefObject<Konva.Transformer>;
    shapeRefs: React.MutableRefObject<Record<number, Konva.Rect[]>>;
    selectedId: { segId: number; boxIdx: number } | null;
    segments: SegmentationSegment[];
}

export function useSegmentTransformer({
                                          transformerRef,
                                          shapeRefs,
                                          selectedId,
                                          segments,
                                      }: UseSegmentTransformerProps) {
    useEffect(() => {
        const transformer = transformerRef.current;
        if (!transformer) return;

        if (!selectedId) {
            transformer.nodes([]);
            transformer.getLayer()?.batchDraw();

            return;
        }

        const node = shapeRefs.current[selectedId.segId]?.[selectedId.boxIdx];
        if (node) {
            transformer.nodes([node]);
        } else {
            transformer.nodes([]);
        }
        transformer.getLayer()?.batchDraw();
        transformer.getStage()?.batchDraw();
    }, [selectedId, segments, transformerRef, shapeRefs]);
}
