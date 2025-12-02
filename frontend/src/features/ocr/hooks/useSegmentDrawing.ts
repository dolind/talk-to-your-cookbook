import {useCallback} from 'react';
import {rectToBoundingBox} from '../utils/geometry';
import {SegmentationSegment} from '../../../lib/model';

export function useSegmentDrawing({
                                      stageRef,
                                      drawMode,
                                      drawingRect,
                                      setDrawingRect,
                                      segments,
                                      imageId,
                                      setTempSegments,
                                      scale,
                                  }: any) {
    const handleMouseDown = useCallback(
        (e: any) => {

            if (!drawMode) return;

            // Allow drawing over background image or empty canvas
            const className = e.target?.getClassName?.();
            const isEmpty =
                !e.target ||
                e.target === stageRef.current ||
                e.target === stageRef.current.getStage() ||
                className === 'Stage' ||
                className === 'Layer' ||
                className === 'Image';

            if (isEmpty) {
                const pos = stageRef.current.getPointerPosition();
                if (pos) {
                    setDrawingRect([pos.x / scale, pos.y / scale, 1, 1]);
                }
            }
        },
        [drawMode, stageRef, scale, setDrawingRect]
    );


    const handleMouseMove = useCallback(() => {
        if (!drawMode || !drawingRect) return;
        const pos = stageRef.current.getPointerPosition();
        if (pos) {
            setDrawingRect((prev: number[] | null) =>
                prev
                    ? [
                        Math.min(pos.x / scale, prev[0]),
                        Math.min(pos.y / scale, prev[1]),
                        Math.abs(pos.x / scale - prev[0]),
                        Math.abs(pos.y / scale - prev[1]),
                    ]
                    : null
            );
        }
    }, [drawMode, drawingRect, scale, stageRef, setDrawingRect]);

    const handleMouseUp = useCallback(() => {
        if (drawMode && drawingRect && drawingRect[2] > 5 && drawingRect[3] > 5) {
            const newBox = rectToBoundingBox(
                drawingRect[0],
                drawingRect[1],
                drawingRect[2],
                drawingRect[3]
            );

            // 🧮 Sequential numeric IDs
            const newId =
                segments.length > 0
                    ? Math.max(...segments.map((s: SegmentationSegment) => Number(s.id) || 0)) + 1
                    : 0;

            const newSeg: SegmentationSegment = {
                id: newId,
                title: '',
                bounding_boxes: [newBox],
                associated_ocr_blocks: [],
            };

            setTempSegments(imageId, [...segments, newSeg]);
        }
        setDrawingRect(null);
    }, [drawMode, drawingRect, segments, imageId, scale, setTempSegments]);

    return {handleMouseDown, handleMouseMove, handleMouseUp};
}
