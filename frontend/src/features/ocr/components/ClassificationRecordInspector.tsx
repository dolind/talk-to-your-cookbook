import {Alert, Autocomplete, Box, Button, Chip, Drawer, Stack, TextField, Typography,} from '@mui/material';
import {useOCRStore} from '../../../store/useOCRStore';
import {approveRecord, redoRecord} from '../api/recordsApi';
import {useRecordDetail} from '../hooks/useRecordDetail';
import {useState} from "react";

const ALLOWED_CATEGORIES = ['Breakfast', 'Lunch', 'Dinner', 'Snacks', 'Dessert'];
const ALLOWED_TAGS = ['scanned', 'vegetarian', 'vegan', 'low-carb'];

export const ClassificationRecordInspector = () => {
    const {
        records,
        editingRecordId,
        stopRecordEditing,
        startRecordEditing,
    } = useOCRStore();
    const [categories, setCategories] = useState<string[]>([]);
    const [tags, setTags] = useState<string[]>(['scanned']);
    const {jsonText, originalText, parseError, handleChange} =
        useRecordDetail(editingRecordId);

    if (!editingRecordId) return null;
    const current = records.find(r => r.id === editingRecordId);
    if (!current) return null;

    const sameBook = records.filter(r => r.book_scan_id === current.book_scan_id);
    const idx = sameBook.findIndex(r => r.id === current.id);
    const prevRec = sameBook[idx - 1];
    const nextRec = sameBook[idx + 1];

    const needsReview = current.status === 'NEEDS_REVIEW';
    const needsTaxonomy = current.status === 'NEEDS_TAXONOMY';
    const hasChanged = jsonText.trim() !== originalText.trim();

    const sourceValue = current.validation_result?.source;


    const handleApprove = async () => {
        try {

            if (current.status === 'NEEDS_TAXONOMY') {
                await approveRecord(current.id, 'taxonomy', {
                    categories,
                    tags,
                    sourceValue
                });
            } else {
                const parsed = JSON.parse(jsonText);
                await approveRecord(
                    current.id,
                    'recipe',
                    hasChanged ? parsed : undefined
                );
            }
            stopRecordEditing();
        } catch (err) {
            console.error('Approve failed:', err);
        }
    };

    return (
        <Drawer
            anchor="right"
            open
            onClose={stopRecordEditing}
            sx={{
                zIndex: 1300,
                '& .MuiDrawer-paper': {width: {xs: '100vw', md: 800}},
            }}
        >
            <Box p={2}>
                <Typography variant="h6">{current.title ?? 'UNKNOWN'}</Typography>

                {/* Mode instructions */}
                {needsReview && (
                    <Alert severity="info" sx={{mt: 2, mb: 2}}>
                        Review the extracted recipe. You may edit the entire JSON.
                    </Alert>
                )}

                {needsTaxonomy && (
                    <Alert severity="info" sx={{mt: 2, mb: 2}}>
                        The recipe text is already approved.
                        Add categories, tags, and source metadata.
                    </Alert>
                )}

                <Box
                    display="flex"
                    flexDirection={{xs: 'column', md: 'row'}}
                    gap={2}
                    mb={2}
                >
                    {/* Thumbnail */}
                    <Box flex={1}>
                        <img
                            src={`${import.meta.env.VITE_MEDIA_BASE_URL}/scanner_images/${current.thumbnail_path}`}
                            alt={current.id}
                            style={{
                                width: '100%',
                                borderRadius: 4,
                                maxHeight: 700,
                                objectFit: 'contain',
                            }}
                        />
                    </Box>

                    {/* JSON Editor */}
                    <Box flex={1} display="flex" flexDirection="column">
                        {needsReview && (
                            <>
                                <Typography variant="subtitle2" gutterBottom>
                                    Validation Result (Editable JSON)
                                </Typography>

                                <textarea
                                    value={jsonText}
                                    onChange={e => handleChange(e.target.value)}
                                    style={{
                                        flex: 1,
                                        width: '100%',
                                        minHeight: 700,
                                        fontFamily: 'monospace',
                                        fontSize: '0.875rem',
                                        padding: '0.5rem',
                                        borderColor: parseError ? 'red' : '#ccc',
                                        borderWidth: 1,
                                        borderStyle: 'solid',
                                        borderRadius: 4,
                                    }}
                                />

                                {parseError && (
                                    <Typography color="error" variant="caption" mt={1}>
                                        Invalid JSON: {parseError}
                                    </Typography>
                                )}
                            </>
                        )}

                        {needsTaxonomy && (
                            <>
                                <Typography variant="subtitle2" gutterBottom>
                                    Recipe Metadata
                                </Typography>

                                {/* Source (read-only) */}
                                <TextField
                                    label="Source"
                                    value={sourceValue}
                                    InputProps={{readOnly: true}}
                                    fullWidth
                                    sx={{mb: 2}}
                                />

                                {/* Categories: freeSolo (user may add new ones) */}
                                <Autocomplete
                                    multiple
                                    freeSolo
                                    options={ALLOWED_CATEGORIES}
                                    value={categories}
                                    onChange={(e, val) => setCategories(val)}
                                    renderInput={params => (
                                        <TextField
                                            {...params}
                                            label="Categories (add your own or choose suggestions)"
                                        />
                                    )}
                                    sx={{mb: 2}}
                                />

                                {/* Tags: freeSolo (user may add new ones) */}
                                <Autocomplete
                                    multiple
                                    freeSolo
                                    options={ALLOWED_TAGS}
                                    value={tags}
                                    onChange={(e, val) => setTags(val)}
                                    renderInput={params => (
                                        <TextField
                                            {...params}
                                            label="Tags (add your own or choose suggestions)"
                                        />
                                    )}
                                />
                            </>
                        )}
                    </Box>
                </Box>

                {/* Related pages */}
                <Typography variant="subtitle2" gutterBottom>
                    Pages used for Recipe
                </Typography>
                <Stack direction="row" spacing={1} flexWrap="wrap">
                    {[...current.text_pages, ...current.image_pages].map(p => (
                        <Chip key={p.id} label={`Page ${p.page_number ?? '?'}`} size="small"/>
                    ))}
                </Stack>

                {/* Navigation */}
                <Box mt={3} display="flex" justifyContent="space-between">
                    <Button
                        variant="outlined"
                        disabled={!prevRec}
                        onClick={() => prevRec && startRecordEditing(prevRec.id)}
                    >
                        ← Previous
                    </Button>
                    <Button
                        variant="outlined"
                        disabled={!nextRec}
                        onClick={() => nextRec && startRecordEditing(nextRec.id)}
                    >
                        Next →
                    </Button>
                </Box>

                {/* Actions */}
                <Box mt={3}>
                    {(current.status === 'NEEDS_REVIEW' ||
                        current.status === 'NEEDS_TAXONOMY') && (
                        <Button variant="outlined" color="success" onClick={handleApprove}>
                            {current.status === 'NEEDS_TAXONOMY'
                                ? 'Approve Metadata'
                                : 'Approve'}
                        </Button>
                    )}
                    <Button
                        variant="outlined"
                        color="warning"
                        sx={{ml: 1}}
                        onClick={async () => {
                            await redoRecord(current.id);
                            stopRecordEditing();
                        }}
                    >
                        Redo
                    </Button>
                </Box>
            </Box>
        </Drawer>
    );
};

export default ClassificationRecordInspector;
