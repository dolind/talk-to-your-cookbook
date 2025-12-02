import React, {useEffect, useRef} from 'react';
import {Image as KonvaImage, Layer, Rect, Stage, Text, Transformer} from 'react-konva';
import useImage from 'use-image';
import Konva from 'konva';
import {boundingBoxToRect, rectToBoundingBox} from '../utils/geometry';
import {extractBlockBoxes, isBoxInside} from '../utils/ocrUtils';
import {SegmentationSegment} from '../../../lib/model';
import {useSegmentDrawing} from '../hooks/useSegmentDrawing';
import {useSegmentTransformer} from '../hooks/useSegmentTransformer';
import {useSegmentKeyboardShortcuts} from "../hooks/useSegmentKeybordShortcuts.ts";

const BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;

interface SegmentCanvasProps {
    image: { id: string; filename: string };
    ocrData?: any;
    segments: SegmentationSegment[];
    drawMode: boolean;
    selectedId: { segId: number; boxIdx: number } | null;
    setSelectedId: (sel: { segId: number; boxIdx: number } | null) => void;

    setTempSegments: (imageId: string, segs: SegmentationSegment[]) => void;
    showOCR: boolean;
    showSegments: boolean;
    drawingRect: number[] | null;
    setDrawingRect: (v: number[] | null) => void;
}

export const SegmentCanvas = React.memo(
    ({
         image,
         ocrData,
         segments,
         drawMode,
         selectedId,
         setSelectedId,
         setTempSegments,
         showOCR,
         showSegments,
         drawingRect,
         setDrawingRect,
     }: SegmentCanvasProps) => {
        const [bg] = useImage(`${BASE_URL}/scanner_images/${image.filename}`);
        const transformerRef = useRef<Konva.Transformer>(null);
        const shapeRefs = useRef<Record<number, Konva.Rect[]>>({});
        const stageRef = useRef<Konva.Stage>(null);
        const scale = bg ? 500 / bg.width : 1;
        const blockBoxes = showOCR && ocrData ? extractBlockBoxes(ocrData) : [];
        const bgLayerRef = useRef<Konva.Layer>(null);
        const ocrLayerRef = useRef<Konva.Layer>(null);
        // Attach hooks
        useSegmentTransformer({transformerRef, shapeRefs, selectedId, segments});
        useSegmentKeyboardShortcuts({selectedId, segments, setSelectedId, setTempSegments, imageId: image.id});

        const {handleMouseDown, handleMouseMove, handleMouseUp} = useSegmentDrawing({
            stageRef,
            drawMode,
            drawingRect,
            setDrawingRect,
            segments,
            imageId: image.id,
            setTempSegments,
            scale,
        });

        useEffect(() => {
            const next: Record<number, Konva.Rect[]> = {};
            segments.forEach((s) => {
                next[s.id] = [];
            });
            shapeRefs.current = next;
        }, [segments]);


        useEffect(() => {
            const bgLayer = bgLayerRef.current;
            const ocrLayer = ocrLayerRef.current;

            // only cache once the image is fully loaded and has dimensions
            if (bg && bg.width > 0 && bg.height > 0 && bgLayer) {
                bgLayer.cache();
            }

            if (blockBoxes.length > 0 && ocrLayer) {
                ocrLayer.cache();
            }
        }, [bg, blockBoxes]);

        return (
            <Stage
                ref={stageRef}
                width={bg ? bg.width * scale : 500}
                height={bg ? bg.height * scale : 500}
                scale={{x: scale, y: scale}}
                style={{border: '1px solid #ccc'}}
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                draggable={false}
                perfectDrawEnabled={false}
                dragBoundFunc={(pos) => pos}
                hitStrokeWidth={8}
                listening={true}
            >
                {/* Background image */}
                <Layer listening={!drawMode} ref={bgLayerRef}>{bg && <KonvaImage image={bg}/>}</Layer>


                {/* OCR overlay */}
                {showOCR && (
                    <Layer ref={ocrLayerRef}>
                        {blockBoxes.map((b, i) => (
                            <Rect
                                key={`ocr-${i}`}
                                x={b.x}
                                y={b.y}
                                width={b.width}
                                height={b.height}
                                stroke="red"
                                dash={[4, 2]}
                                strokeWidth={2 / scale}
                            />
                        ))}
                    </Layer>
                )}

                {/* Segments */}
                <Layer>
                    {showSegments && segments.length > 1 &&
                        segments.map((seg, idx) =>
                                seg.bounding_boxes.map((bb, bIdx) => {
                                    const {x, y, width, height} = boundingBoxToRect(bb);
                                    const containedBlocks = blockBoxes.filter(b =>
                                        isBoxInside(b, {x, y, width, height})
                                    );
                                    const isSelected =
                                        selectedId != null &&
                                        selectedId.segId === seg.id &&
                                        selectedId.boxIdx === bIdx;

                                    return (
                                        <React.Fragment key={`${seg.id}-${bIdx}`}>
                                            <Rect
                                                id={`${seg.id}-${bIdx}`}
                                                name={`seg-${seg.id}-box-${bIdx}`}
                                                ref={(node) => {
                                                    if (!node) return;
                                                    if (!shapeRefs.current[seg.id]) {
                                                        shapeRefs.current[seg.id] = [];
                                                    }

                                                    // Avoid duplicates (re-render safety)
                                                    shapeRefs.current[seg.id][bIdx] = node;
                                                }}
                                                x={x}
                                                y={y}
                                                width={width}
                                                height={height}
                                                fill="rgba(0,255,0,0.2)"
                                                stroke={isSelected ? 'red' : 'lime'}
                                                strokeWidth={10}
                                                draggable={drawMode}
                                                onClick={() => drawMode && setSelectedId({segId: seg.id, boxIdx: bIdx})}
                                                onDragEnd={(e) => {
                                                    if (!drawMode) return;
                                                    const node = e.target as Konva.Rect;

                                                    const newBox = rectToBoundingBox(
                                                        node.x(),
                                                        node.y(),
                                                        Math.max(5, node.width()),
                                                        Math.max(5, node.height())
                                                    );

                                                    const updated = segments.map((s) => {
                                                        if (s.id !== seg.id) return s;

                                                        // update only this box (bIdx)
                                                        const newBoxes = s.bounding_boxes.map((bb, i) =>
                                                            i === bIdx ? newBox : bb
                                                        );

                                                        return {...s, bounding_boxes: newBoxes};
                                                    });

                                                    setTempSegments(image.id, updated);
                                                }}

                                                onTransformEnd={(e) => {
                                                    const node = e.target as Konva.Rect;
                                                    const sx = node.scaleX();
                                                    const sy = node.scaleY();
                                                    node.scaleX(1);
                                                    node.scaleY(1);
                                                    const newBox = rectToBoundingBox(
                                                        node.x(),
                                                        node.y(),
                                                        Math.max(5, node.width() * sx),
                                                        Math.max(5, node.height() * sy)
                                                    );


                                                    const updated = segments.map((s) => {
                                                        if (s.id !== seg.id) return s;
                                                        const newBoxes = s.bounding_boxes.map((orig, i) => (i === bIdx ? newBox : orig));
                                                        return {...s, bounding_boxes: newBoxes};
                                                    });
                                                    setTempSegments(image.id, updated);


// Force a redraw to keep Transformer aligned
                                                    transformerRef.current?.getLayer()?.batchDraw();
                                                    transformerRef.current?.getStage()?.batchDraw();
                                                }}

                                            />
                                            <Text
                                                x={x + 4}
                                                y={y + 2}
                                                text={
                                                    seg.bounding_boxes.length === 1
                                                        ? `${idx + 1}`
                                                        : `${idx + 1}.${bIdx + 1}`
                                                }
                                                fontSize={16 / scale}
                                                fontStyle="bold"
                                                fill="black"
                                            />
                                            {containedBlocks.map((b, i) => (
                                                <Rect
                                                    key={`ocr-${seg.id}-${i}`}
                                                    x={b.x}
                                                    y={b.y}
                                                    width={b.width}
                                                    height={b.height}
                                                    stroke="blue"
                                                    fill="rgba(0,0,255,0.2)"
                                                    dash={[3, 3]}
                                                />
                                            ))}
                                        </React.Fragment>
                                    );
                                })
                        )}

                    {/* Live drawing preview */}
                    {drawMode && drawingRect && (
                        <Rect
                            x={drawingRect[0]}
                            y={drawingRect[1]}
                            width={drawingRect[2]}
                            height={drawingRect[3]}
                            stroke="orange"
                            dash={[10, 10]}
                            fill="rgba(255,165,0,0.1)"
                        />
                    )}

                    <Transformer ref={transformerRef} rotateEnabled={false}/>
                </Layer>
            </Stage>
        );
    });
