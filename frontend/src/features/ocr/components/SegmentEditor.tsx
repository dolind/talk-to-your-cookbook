import {useEffect, useState} from 'react';
import {Box} from '@mui/material';
import {useOCRStore} from '../../../store/useOCRStore';
import {SegmentToolbar} from './SegmentToolbar';
import {SegmentCanvas} from './SegmentCanvas';

export const SegmentEditor = ({image, ocrData}: any) => {
    const {tempSegments, setTempSegments, editingImageId} = useOCRStore();
    const segments = tempSegments[image.id] || [];

    // Local to this page/canvas only
    const [selectedId, setSelectedId] = useState<{ segId: number; boxIdx: number } | null>(null);
    const [drawMode, setDrawMode] = useState(false);
    const [showOCR, setShowOCR] = useState(true);
    const [showSegments, setShowSegments] = useState(true);
    const [drawingRect, setDrawingRect] = useState<number[] | null>(null);

    // Reset selection when switching to a different image
    useEffect(() => {
        setSelectedId(null);
    }, [editingImageId]);

    return (
        <>
            <SegmentToolbar
                imageId={image.id}
                drawMode={drawMode}
                setDrawMode={setDrawMode}
                showOCR={showOCR}
                setShowOCR={setShowOCR}
                showSegments={showSegments}
                setShowSegments={setShowSegments}
                selectedId={selectedId?.segId ?? null}
                setSelectedId={setSelectedId}
                segments={segments}
                setTempSegments={setTempSegments}
            />
            <Box>
                <SegmentCanvas
                    image={image}
                    ocrData={ocrData}
                    segments={segments}
                    drawMode={drawMode}
                    selectedId={selectedId}
                    setSelectedId={setSelectedId}
                    setTempSegments={setTempSegments}
                    showOCR={showOCR}
                    showSegments={showSegments}
                    drawingRect={drawingRect}
                    setDrawingRect={setDrawingRect}
                />
            </Box>
        </>
    );
};
