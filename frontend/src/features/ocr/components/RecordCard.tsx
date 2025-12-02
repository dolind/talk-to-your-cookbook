import React from 'react';
import {Box, Button, Card, CardContent, IconButton, Typography,} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import {ClassificationRecordRead} from '../../../lib/model';
import {approveRecord, redoRecord} from '../api/recordsApi';
import {useSnackbar} from "notistack";

const BASE_URL = import.meta.env.VITE_MEDIA_BASE_URL;

type Props = {
    record: ClassificationRecordRead;
    isSelected: boolean;
    onToggle: (id: string) => void;
    onDelete: (id: string) => void;
    onInspect: (id: string) => void;
    onRefresh: () => void;
};

export const RecordCard: React.FC<Props> = ({
                                                record,
                                                isSelected,
                                                onToggle,
                                                onDelete,
                                                onInspect,
                                                onRefresh,
                                            }) => {
    const {enqueueSnackbar} = useSnackbar();
    const handleApprove = async (e: React.MouseEvent) => {
        e.stopPropagation();
        try {
            if (record.status === 'NEEDS_TAXONOMY') {
                await approveRecord(record.id, 'taxonomy', {categories: null, tags: null});
                enqueueSnackbar('Labels approved', {variant: 'success'});
            } else {
                await approveRecord(record.id, 'recipe');
                enqueueSnackbar('Classification approved', {variant: 'success'});
            }
            onRefresh();

        } catch {
            enqueueSnackbar('Approve failed', {variant: 'error'});
        }
    };

    const handleRedo = async (e: React.MouseEvent) => {
        e.stopPropagation();
        await redoRecord(record.id);
    };

    return (
        <Card
            onClick={() => onToggle(record.id)}
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
                    src={`${BASE_URL}/scanner_images/${record.thumbnail_path}`}
                    alt={record.title ?? record.id}
                    style={{
                        width: '100%',
                        maxHeight: 200,
                        objectFit: 'cover',
                        borderRadius: 4,
                        marginBottom: 8,
                    }}
                />

                <Typography variant="subtitle1">
                    {record.title ?? `Record ${record.id.slice(0, 6)}`}
                </Typography>

                <Typography variant="caption" color="text.secondary">
                    Pages:{' '}
                    {record.image_pages?.map(p => p.page_number ?? '?').join(', ')}{' '}
                    {record.text_pages?.map(p => p.page_number ?? '?').join(', ')} • Status: {record.status}
                </Typography>

                <Box mt={1}>
                    {(record.status === 'NEEDS_REVIEW' || record.status === 'NEEDS_TAXONOMY') && (
                        <Button size="small" variant="outlined" color="success" onClick={handleApprove}>
                            {record.status === 'NEEDS_TAXONOMY' ? 'Refetch & Approve' : 'Approve'}
                        </Button>
                    )}

                    {record.status === 'APPROVED' && (
                        <Button size="small" variant="outlined" color="success" onClick={handleRedo}>
                            Redo Record
                        </Button>
                    )}

                    <Button size="small" sx={{ml: 1}} onClick={e => {
                        e.stopPropagation();
                        onInspect(record.id);
                    }}>
                        Inspect
                    </Button>

                    <IconButton
                        onClick={e => {
                            e.stopPropagation();
                            onDelete(record.id);
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
