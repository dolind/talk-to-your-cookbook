import {Box, Button} from '@mui/material';

interface RecipeBulkDeleteProps {
    deleteMode: boolean;
    selectedCount: number;
    onEnterDeleteMode: () => void;
    onConfirmDelete: () => void;
    onCancelDelete: () => void;
}

const RecipeBulkDelete = ({
                              deleteMode,
                              selectedCount,
                              onEnterDeleteMode,
                              onConfirmDelete,
                              onCancelDelete,
                          }: RecipeBulkDeleteProps) => {
    if (!deleteMode) {
        return (
            <Button variant="outlined" color="error" onClick={onEnterDeleteMode}>
                Delete Recipes
            </Button>
        );
    }

    return (
        <Box sx={{display: 'flex', gap: 1}}>
            <Button
                variant="contained"
                color="error"
                onClick={onConfirmDelete}
                disabled={selectedCount === 0}
            >
                Confirm Deletion ({selectedCount})
            </Button>
            <Button variant="outlined" onClick={onCancelDelete}>
                Cancel
            </Button>
        </Box>
    );
};

export default RecipeBulkDelete;
