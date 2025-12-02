import {useState} from 'react';
import {Box, Button, Grid} from '@mui/material';
import {useOCRStore} from '../../../store/useOCRStore';
import {useSnackbar} from 'notistack';
import {useRecords} from '../hooks/useRecords';
import {approveRecord, classifyRecipes, deleteRecord, redoRecord} from '../api/recordsApi';
import {RecordCard} from './RecordCard';
import {GroupingCard} from "./GroupingCard";

export const RecordGridViewer = () => {
    const {selectedBookId, records, setRecords, startRecordEditing} = useOCRStore();
    const {enqueueSnackbar} = useSnackbar();
    const {fetchRecords} = useRecords();
    const [selectedRecordIds, setSelectedRecordIds] = useState<Set<string>>(new Set());

    const toggle = (id: string) => {
        const next = new Set(selectedRecordIds);
        next.has(id) ? next.delete(id) : next.add(id);
        setSelectedRecordIds(next);
    };

    const handleSelectAll = () => setSelectedRecordIds(new Set(records.map(r => r.id)));
    const handleDeselectAll = () => setSelectedRecordIds(new Set());

    const handleApproveSelected = async () => {
        await Promise.all([...selectedRecordIds].map(async id => {
            const rec = records.find(r => r.id === id);
            if (!rec) return;
            if (rec.status === 'NEEDS_TAXONOMY') {
                await approveRecord(rec.id, 'taxonomy', {categories: null, tags: null});
            } else if (rec.status === 'NEEDS_REVIEW') {
                await approveRecord(rec.id, 'recipe');
            }
        }));
        enqueueSnackbar(`${selectedRecordIds.size} approved`, {variant: 'success'});
        fetchRecords();
        setSelectedRecordIds(new Set());
    };

    const handleRedoSelected = async () => {
        await Promise.all([...selectedRecordIds].map(id => redoRecord(id)));
        enqueueSnackbar(`${selectedRecordIds.size} re-queued`, {variant: 'info'});
        setSelectedRecordIds(new Set());
    };

    const handleDeleteSelected = async () => {
        await Promise.all([...selectedRecordIds].map(id => deleteRecord(id)));
        enqueueSnackbar(`Deleted Record ${selectedRecordIds.size}`, {variant: 'info'});
        setRecords(records.filter(r => !selectedRecordIds.has(r.id)));
        setSelectedRecordIds(new Set());
    };

    const handleDeleteOne = async (id: string) => {
        await deleteRecord(id);
        enqueueSnackbar(`Record deleted`, {variant: 'info'});
        setRecords(records.filter(r => r.id !== id));
        setSelectedRecordIds(prev => {
            const next = new Set(prev);
            next.delete(id);
            return next;
        });
    };
    const isAllSelectedNeedsReview = [...selectedRecordIds].every(
        (id) => records.find((record) => record.id === id)?.status === 'NEEDS_REVIEW'
    );
    return (
        <Box>
            {/* Toolbar */}
            <Box sx={{display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2}}>
                <Button variant="contained" onClick={() => {
                    classifyRecipes(selectedBookId);
                }}>
                    Identify Recipes
                </Button>
                <Button onClick={handleSelectAll}>Select All</Button>
                <Button onClick={handleDeselectAll}>Deselect All</Button>
                <Button color="success" disabled={!selectedRecordIds.size || !isAllSelectedNeedsReview}
                        onClick={handleApproveSelected}>
                    Approve Selected
                </Button>
                <Button color="warning" disabled={!selectedRecordIds.size} onClick={handleRedoSelected}>
                    Redo Selected
                </Button>
                <Button color="error" disabled={!selectedRecordIds.size} onClick={handleDeleteSelected}>
                    Delete Selected
                </Button>
            </Box>

            {/* Grid */}
            <Grid container spacing={2}>
                {records.map(rec => (
                    <Grid item xs={12} md={6} key={rec.id}>
                        {rec.status === 'REVIEW_GROUPING' ? (
                            <GroupingCard
                                record={rec}
                                onRefresh={fetchRecords}
                                onDelete={() => handleDeleteOne(rec.id)}/>
                        ) : (
                            <RecordCard
                                record={rec}
                                isSelected={selectedRecordIds.has(rec.id)}
                                onToggle={toggle}
                                onDelete={() => handleDeleteOne(rec.id)}
                                onInspect={startRecordEditing}
                                onRefresh={fetchRecords}
                            />
                        )}
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
};
