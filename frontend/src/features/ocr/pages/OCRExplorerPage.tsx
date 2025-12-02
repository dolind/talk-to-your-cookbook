import {useCallback, useEffect} from 'react';
import {Box, Grid, ToggleButton, ToggleButtonGroup, Typography} from '@mui/material';
import {useNavigate, useParams} from 'react-router-dom';
import {useOCRStore} from '../../../store/useOCRStore';
import {useWebSocket} from '../../../utils/useWebSocket';
import {GraphBroadCast} from '../../../lib/model';
import OCRImageInspector from '../components/OCRImageInspector';
import ClassificationRecordInspector from '../components/ClassificationRecordInspector';
import {BookScanList} from '../components/BookScanList';
import {PageGridViewer} from '../components/PageGridViewer.tsx';
import {RecordGridViewer} from '../components/RecordGridViewer';

const OCRExplorerPage = () => {
    const {bookId} = useParams();
    const navigate = useNavigate();
    const {
        setSelectedBookId,
        selectedBookId,
        updatePageStatus,
        viewMode,
        setViewMode,
        updateRecordStatus,
    } = useOCRStore();

    useEffect(() => {
        if (!bookId) return;
        setSelectedBookId(bookId);
    }, [bookId, setSelectedBookId]);

    useEffect(() => {
        if (selectedBookId && selectedBookId !== bookId) {
            navigate(`/ocr/${selectedBookId}`);
        }
    }, [bookId, navigate, selectedBookId]);

    const handleStatusMessage = useCallback(
        (statusMessage: GraphBroadCast) => {
            if (statusMessage.type === 'record') {
                updateRecordStatus(statusMessage.id, statusMessage.status);
            } else {
                updatePageStatus(statusMessage.id, statusMessage.status);
            }
        },
        [updatePageStatus, updateRecordStatus],
    );

    useWebSocket('/api/v1/ws/status', handleStatusMessage);

    return (
        <Box>
            <OCRImageInspector/>
            <ClassificationRecordInspector/>

            <Typography variant="h4" gutterBottom>
                Recipe Scanner
            </Typography>

            <ToggleButtonGroup
                exclusive
                size="small"
                value={viewMode}
                onChange={(_, value) => value && setViewMode(value)}
                sx={{mb: 2}}
            >
                <ToggleButton value="scans">Page Scans</ToggleButton>
                <ToggleButton value="records">Records</ToggleButton>
            </ToggleButtonGroup>

            <Grid container spacing={2}>
                <Grid item xs={12} md={3}>
                    <BookScanList/>
                </Grid>
                <Grid item xs={12} md={9}>
                    {viewMode === 'scans' ? <PageGridViewer/> : <RecordGridViewer/>}
                </Grid>
            </Grid>
        </Box>
    );
};

export default OCRExplorerPage;
