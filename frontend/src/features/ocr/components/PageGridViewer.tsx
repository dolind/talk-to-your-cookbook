import {useState} from 'react';
import {Box, Button, Grid} from '@mui/material';
import {useOCRStore} from '../../../store/useOCRStore';
import {useSnackbar} from 'notistack';
import {usePages} from '../hooks/usePages.ts';
import {ImageCard} from './ImageCard';
import {approveImage, deletePage, redoSegmentation, uploadImages} from '../api/ocrApi';
import {SegmentationApproval} from "../../../lib/model.ts";
import OCRImageInspector from "./OCRImageInspector.tsx";


export const PageGridViewer = () => {
    const {selectedBookId, pages, setImages, startEditing, tempSegments} = useOCRStore();
    const {enqueueSnackbar} = useSnackbar();
    const {fetchPages} = usePages();
    const [selectedPageIds, setSelectedPageIds] = useState<Set<string>>(new Set());

    const toggle = (id: string) => {
        setSelectedPageIds((prev) => {
            const updated = new Set(prev);
            updated.has(id) ? updated.delete(id) : updated.add(id);
            return updated;
        });
    };

    const handleSelectAll = () => setSelectedPageIds(new Set(pages.map(r => r.id)));
    const handleDeselectAll = () => setSelectedPageIds(new Set());

    const handleApproveSelected = async () => {
        const idsToApprove = [...selectedPageIds].filter(
            (id) => pages.find((p) => p.id === id)?.status === 'NEEDS_REVIEW'
        );

        await Promise.all(
            idsToApprove.map(async (id) => {
                const segments = tempSegments[id] || [];
                const approval: SegmentationApproval = {
                    approved: true,
                    segmentation: {
                        segmentation_done: segments.length > 0,
                        page_segments: segments,
                    },
                };
                await approveImage(id, approval);
            })
        );

        enqueueSnackbar(`${idsToApprove.length} approved`, {variant: 'success'});
        fetchPages()
        setSelectedPageIds(new Set());
    };

    const handleRedoSelected = async () => {
        await Promise.all([...selectedPageIds].map(id => redoSegmentation(id)));
        enqueueSnackbar(`${selectedPageIds.size} re-queued`, {variant: 'info'});
        setSelectedPageIds(new Set());
    };
    const handleDeleteSelected = async () => {
        await Promise.all([...selectedPageIds].map((id) => deletePage(id)));
        enqueueSnackbar('Deleted Page ${selectedPageIds.size}', {variant: 'info'});
        setImages(pages.filter((p) => !selectedPageIds.has(p.id)));
        setSelectedPageIds(new Set());
    };

    const handleAddImages = async () => {
        if (!selectedBookId) return;
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = 'image/*';
        input.onchange = async (e: any) => {
            const files = Array.from(e.target.files) as File[];
            if (!files.length) return;
            try {
                const res = await uploadImages(selectedBookId, files);
                enqueueSnackbar(`Uploaded ${res.data.length} images`, {variant: 'success'});
                fetchPages();
            } catch {
                enqueueSnackbar('Upload failed', {variant: 'error'});
            }
        };
        input.click();
    };
    const handleDeleteOne = async (id: string) => {
        await deletePage(id);
        enqueueSnackbar(`Page deleted`, {variant: 'info'});
        setImages(pages.filter(r => r.id !== id));
        setSelectedPageIds(prev => {
            const next = new Set(prev);
            next.delete(id);
            return next;
        });
    };
    const isAllSelectedNeedsReview = [...selectedPageIds].every(
        (id) => pages.find((img) => img.id === id)?.status === 'NEEDS_REVIEW'
    );
    return (
        <Box>
            <Box sx={{display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2}}>
                <Button variant="contained" onClick={handleAddImages}>Add Images</Button>
                <Button onClick={handleSelectAll}>Select All</Button>
                <Button onClick={handleDeselectAll}>Deselect All</Button>
                <Button color="success" disabled={!selectedPageIds.size || !isAllSelectedNeedsReview}
                        onClick={handleApproveSelected}>
                    Approve Selected
                </Button>
                <Button color="warning" disabled={!selectedPageIds.size} onClick={handleRedoSelected}>
                    Redo Selected
                </Button>
                <Button color="error" disabled={!selectedPageIds.size} onClick={handleDeleteSelected}>
                    Delete Selected
                </Button>
            </Box>

            <Grid container spacing={2}>
                {pages.map((img) => (
                    <Grid item xs={12} md={6} key={img.id}>
                        <ImageCard
                            page={img}
                            isSelected={selectedPageIds.has(img.id)}
                            onToggle={toggle}
                            onInspect={startEditing}
                            onDelete={() => handleDeleteOne(img.id)}
                            onRefresh={fetchPages}
                        />
                    </Grid>
                ))}
            </Grid>
            <OCRImageInspector onRefresh={fetchPages}/>
        </Box>
    );
};
