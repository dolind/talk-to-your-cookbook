import {Box, Button, Checkbox, FormControlLabel, IconButton, ToggleButton, ToggleButtonGroup,} from '@mui/material';
import LinkIcon from '@mui/icons-material/Link';
import CallSplitIcon from '@mui/icons-material/CallSplit';
import {SegmentationSegment} from '../../../lib/model';
import {useOCRStore} from '../../../store/useOCRStore';

interface Props {
    imageId: string;
    drawMode: boolean;
    setDrawMode: (v: boolean) => void;
    showOCR: boolean;
    setShowOCR: (v: boolean) => void;
    showSegments: boolean;
    setShowSegments: (v: boolean) => void;
    selectedId: number | null;
    setSelectedId: (id: { segId: number; boxIdx: number } | null) => void;
    segments: SegmentationSegment[];
    setTempSegments: (imageId: string, segs: SegmentationSegment[]) => void;
}

export const SegmentToolbar = ({
                                   imageId,
                                   drawMode,
                                   setDrawMode,
                                   showOCR,
                                   setShowOCR,
                                   showSegments,
                                   setShowSegments,
                                   selectedId,
                                   setSelectedId,
                                   segments,
                                   setTempSegments,
                               }: Props) => {

    const {manualSegmentation, setManualSegmentation, pages} = useOCRStore();
    const page = pages.find(p => p.id === imageId);
    const isApproved = page?.status === 'APPROVED';
    return (
        <Box display="flex" gap={2} mb={1}>
            <FormControlLabel
                control={<Checkbox checked={showOCR} onChange={() => setShowOCR(!showOCR)}/>}
                label="Show OCR"
            />
            <FormControlLabel
                control={
                    <Checkbox
                        checked={showSegments}
                        onChange={() => setShowSegments(!showSegments)}
                    />
                }
                label="Show Segments"
            />

            <ToggleButtonGroup exclusive value={drawMode ? 'draw' : 'view'}>
                <ToggleButton value="view" onClick={() => setDrawMode(false)}>
                    View
                </ToggleButton>
                <ToggleButton
                    value="draw"
                    disabled={isApproved}
                    onClick={() => {
                        setDrawMode(true);
                        setManualSegmentation(imageId, true);
                    }}
                >
                    Draw
                </ToggleButton>
            </ToggleButtonGroup>

            {selectedId != null && (
                <Button
                    variant="outlined"
                    color="error"
                    onClick={() => {
                        setTempSegments(imageId, segments.filter(s => s.id !== selectedId));
                        setSelectedId(null);
                    }}
                >
                    Delete
                </Button>
            )}

            {manualSegmentation && (
                <Button
                    variant="outlined"
                    size="small"
                    color="warning"
                    disabled={isApproved}
                    onClick={() => {
                        setTempSegments(imageId, []);
                        setManualSegmentation(imageId, false);
                        setDrawMode(false);
                        setSelectedId(null);
                    }}
                >
                    Reset to Full Page
                </Button>
            )}

            {selectedId != null && (
                <>
                    <IconButton
                        title="Merge with previous"
                        size="small"
                        onClick={() => {
                            const idx = segments.findIndex(s => String(s.id) === String(selectedId));
                            if (idx > 0) {
                                const prev = segments[idx - 1];
                                const curr = segments[idx];
                                const merged: SegmentationSegment = {
                                    ...prev,
                                    bounding_boxes: [...prev.bounding_boxes, ...curr.bounding_boxes],
                                    associated_ocr_blocks: [
                                        ...prev.associated_ocr_blocks,
                                        ...curr.associated_ocr_blocks,
                                    ],
                                };
                                const newSegs = [...segments];
                                newSegs.splice(idx - 1, 2, merged);
                                setTempSegments(imageId, newSegs);
                                setSelectedId(drawMode ? {segId: merged.id, boxIdx: 0} : null);
                            }
                        }}
                    >
                        <LinkIcon fontSize="small"/>
                    </IconButton>

                    <IconButton
                        title="Split boxes"
                        size="small"
                        onClick={() => {
                            const seg = segments.find(s => String(s.id) === String(selectedId));
                            if (!seg) return;
                            const splitSegs = seg.bounding_boxes.map((bb, i) => ({
                                id: i,
                                title: seg.title,
                                bounding_boxes: [bb],
                                associated_ocr_blocks: seg.associated_ocr_blocks,
                            }));
                            const newSegs = segments
                                .filter(s => s.id !== selectedId)
                                .concat(splitSegs);
                            setTempSegments(imageId, newSegs);
                            setSelectedId(null);
                        }}
                    >
                        <CallSplitIcon fontSize="small"/>
                    </IconButton>
                </>
            )}
        </Box>
    );
};
