import {FC} from 'react';
import {Box, Button} from '@mui/material';

interface RecipeFormActionsProps {
    onSave: () => void;
    onCancel: () => void;
}

export const RecipeFormActions: FC<RecipeFormActionsProps> = ({onSave, onCancel}) => (
    <Box sx={{mt: 3, display: 'flex', gap: 2}}>
        <Button variant="contained" onClick={onSave}>
            Save
        </Button>
        <Button variant="outlined" onClick={onCancel}>
            Cancel
        </Button>
    </Box>
);
