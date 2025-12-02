import React from 'react';
import {Box, Button, Card, CardContent, IconButton, Typography,} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import {PageScanRecord, SegmentationApproval} from '../../../lib/model';
import {approveImage, redoOCR, redoSegmentation} from '../api/ocrApi';
import {useSnackbar} from 'notistack';
import {useOCRStore} from "../../../store/useOCRStore.ts";

const BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;

type Props = {
    page: PageScanRecord;
    isSelected: boolean;
    onToggle: (id: string) => void;
    onDelete: (id: string) => void;
    onInspect: (id: string) => void;
    onRefresh: () => void;
};

export const ImageCard: React.FC<Props> = ({
                                               page,
                                               isSelected,
                                               onToggle,
                                               onDelete,
                                               onInspect,
                                               onRefresh,
                                           }) => {
    const {enqueueSnackbar} = useSnackbar();
    const {tempSegments} = useOCRStore();
    const handleApprove = async (e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            const segments = tempSegments[page.id] || [];
            const approval: SegmentationApproval = {
                approved: true,
                segmentation: {
                    segmentation_done: segments.length > 0,
                    page_segments: segments,
                },
            };

            await approveImage(page.id, approval);
            enqueueSnackbar('Segmentation approved', {variant: 'success'});
            onRefresh();
        } catch {
            enqueueSnackbar('Approve failed', {variant: 'error'});
        }
    };

    const handleRedoOCR = async (e: React.MouseEvent) => {
        e.stopPropagation();
        await redoOCR(page.id);
    };
    const handleRedoSegmentation = async (e: React.MouseEvent) => {
        e.stopPropagation();
        await redoSegmentation(page.id);
    };
    return (
        <Card
            onClick={() => onToggle(page.id)}
            sx={{
                position: 'relative',
                border: isSelected ? '2px solid #1976d2' : '1px solid #e0e0e0',
                cursor: 'pointer',
                height: 350,
            }}
        >
            {isSelected && (
                <Box
                    sx={{
                        position: 'absolute',
                        top: 8,
                        right: 8,
                        bgcolor: 'white',
                        borderRadius: '50%',
                        px: 1,
                        py: 0.5,
                        fontSize: '0.8rem',
                        fontWeight: 'bold',
                        boxShadow: 1,
                        zIndex: 10,
                    }}
                >
                    ✅
                </Box>
            )}
            <CardContent>
                <img
                    src={`${BASE_URL}/scanner_images/${page.filename}`}
                    alt={page.filename}
                    style={{width: '100%', maxHeight: 200, objectFit: 'cover', borderRadius: 4, marginBottom: 8,}}
                />

                <Typography variant="subtitle1" display="block">Page {page.page_number}</Typography>

                <Typography variant="caption" color="text.secondary" display="block">
                    Status: {page.status || '—'}
                </Typography>

                <Typography variant="caption" display="block">{page.filename}</Typography>

                <Box mt={1}>
                    {page.status === 'NEEDS_REVIEW' && page.page_type == 'text' && (
                        <Button size="small" variant="outlined" color="success" onClick={handleApprove}>
                            Approve
                        </Button>
                    )}
                    {page.status === 'APPROVED' && page.page_type == 'text' && (
                        <Button size="small" variant="outlined" color="success" onClick={handleRedoOCR}>
                            Redo OCR
                        </Button>
                    )}
                    {page.status === 'OCR_DONE' && page.page_type == 'text' && (
                        <Button size="small" variant="outlined" color="success" onClick={handleRedoSegmentation}>
                            Redo Segmentation
                        </Button>
                    )}
                    {page.page_type == 'text' && (
                        <Button size="small" onClick={(e) => {
                            e.stopPropagation();
                            onInspect(page.id);
                        }}>
                            Inspect
                        </Button>
                    )}
                    <IconButton
                        onClick={(e) => {
                            e.stopPropagation();
                            onDelete(page.id);
                        }}
                        size="small"
                        color={isSelected ? 'primary' : 'default'}
                        sx={{
                            position: 'absolute',
                            bottom: 8,
                            right: 8,
                            boxShadow: 1,
                        }}
                    >
                        <DeleteIcon fontSize="small"/>
                    </IconButton>
                </Box>
            </CardContent>
        </Card>
    );
};
