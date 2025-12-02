import {Box, Button, Drawer, Typography} from '@mui/material';
import {useOCRStore} from '../../../store/useOCRStore';
import {useOcrData} from '../hooks/useOcrData';
import {SegmentEditor} from './SegmentEditor';
import {approveImage, redoOCR, redoSegmentation, updatePageNumber} from '../api/ocrApi';
import {SegmentationApproval, SegmentationResult} from '../../../lib/model';

interface OCRImageInspectorProps {
    onRefresh?: () => void;
}

export const OCRImageInspector = ({onRefresh}: OCRImageInspectorProps) => {
    const {pages, editingImageId, stopEditing, startEditing, tempSegments, manualSegmentation} = useOCRStore();

    const {ocrData} = useOcrData();

    if (!editingImageId) return null;
    const current = pages.find((img) => img.id === editingImageId);
    if (!current) return null;

    // Find adjacent images for navigation
    const listInBook = pages.filter((img) => img.bookScanID === current.bookScanID);
    const idx = listInBook.findIndex((img) => img.id === current.id);

    const handleApprove = async () => {
        try {
            const segments = tempSegments[current.id] || [];
            const result: SegmentationResult = {
                segmentation_done: segments.length > 0,
                page_segments: segments,
            };
            const approval: SegmentationApproval = {
                approved: true,
                segmentation: result,
            };
            await approveImage(current.id, approval);
            stopEditing();
        } catch (err) {
            console.error(err);
        }
    };

    const handleRedoOCR = async () => {
        await redoOCR(current.id);
    };

    const handleRedoSegmentation = async () => {
        await redoSegmentation(current.id);
    };

    const handleChangePageNumber = async () => {
        const input = window.prompt('Enter the new page number:');
        if (!input) return; // user cancelled

        const target = parseInt(input, 10);
        if (isNaN(target) || target <= 0) {
            alert('Please enter a valid positive page number.');
            return;
        }

        try {
            await updatePageNumber(current.id, target);
            alert(`Page number updated to ${target}`);
            onRefresh?.();
            // Optionally: refresh list or reorder pages
        } catch (err: any) {
            console.error(err);
            alert(err.response?.data?.detail || 'Failed to update page number');
        }
    };
    return (
        <>
            <Drawer
                anchor="right"
                open
                onClose={stopEditing}
                sx={{
                    zIndex: 1300,
                    '& .MuiDrawer-paper': {width: {xs: '100vw', md: 800}},
                }}
            >
                <Box p={2} width={{xs: '100vw', md: 540}}>
                    <Typography variant="h6">
                        {(() => {

                            const segs = tempSegments[current.id] || [];
                            console.log(segs);
                            const hasOneWithTitle = segs.length === 1 && segs[0].title && segs[0].title.trim() !== '';
                            return hasOneWithTitle ? segs[0].title : current.filename;
                        })()}
                    </Typography>

                    {!manualSegmentation[current.id] && (
                        <Typography variant="body2" color="text.secondary" sx={{mb: 1, fontStyle: 'italic'}}>
                            Full-page recipe mode: no segmentation used.
                        </Typography>
                    )}

                    <Typography variant="caption" color="text.secondary">
                        Status: {current.status}
                    </Typography>

                    {ocrData ? (
                        <SegmentEditor image={current} ocrData={ocrData}/>
                    ) : (
                        <Typography variant="body2" color="text.secondary">
                            Loading OCR…
                        </Typography>
                    )}

                    <Box mt={2} display="flex" justifyContent="space-between">
                        <Button
                            variant="outlined"
                            onClick={() => {
                                const prevText = [...listInBook]
                                    .slice(0, idx)
                                    .reverse()
                                    .find((img) => img.page_type === 'text');
                                if (prevText) startEditing(prevText.id);
                            }}
                            disabled={![...listInBook].slice(0, idx).some((img) => img.page_type === 'text')}
                        >
                            ← Previous
                        </Button>

                        <Button
                            variant="outlined"
                            onClick={() => {
                                const nextText = [...listInBook]
                                    .slice(idx + 1)
                                    .find((img) => img.page_type === 'text');
                                if (nextText) startEditing(nextText.id);
                            }}
                            disabled={![...listInBook].slice(idx + 1).some((img) => img.page_type === 'text')}
                        >
                            Next →
                        </Button>

                    </Box>

                    <Box mt={3}>
                        {current.status === 'NEEDS_REVIEW' && (
                            <>
                                <Button
                                    size="small"
                                    variant="outlined"
                                    color="success"
                                    disabled={!ocrData}
                                    sx={{mr: 1}}
                                    onClick={handleApprove}
                                >
                                    Approve
                                </Button>
                            </>
                        )}
                        <Button
                            size="small"
                            variant="outlined"
                            color="success"
                            disabled={!ocrData}
                            sx={{mr: 1}}
                            onClick={handleRedoSegmentation}
                        >
                            Redo Segmentation
                        </Button>


                        {current.status === 'APPROVED' && (
                            <Button
                                size="small"
                                variant="outlined"
                                color="success"
                                disabled={!ocrData}
                                sx={{mr: 1}}
                                onClick={handleRedoOCR}
                            >
                                Redo OCR
                            </Button>
                        )}
                        <Button
                            size="small"
                            variant="outlined"
                            color="primary"
                            sx={{mr: 1}}
                            onClick={handleChangePageNumber}
                        >
                            Change Page Number
                        </Button>
                    </Box>
                </Box>
            </Drawer>

        </>
    );
};

export default OCRImageInspector;
