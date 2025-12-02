import {FC} from 'react';
import {Box, Button} from '@mui/material';

interface ShoppingListControlsProps {
    showChecked: boolean;
    onToggleFilter: () => void;
    onClearAll: () => void;
}

export const ShoppingListControls: FC<ShoppingListControlsProps> = ({
                                                                        showChecked,
                                                                        onToggleFilter,
                                                                        onClearAll,
                                                                    }) => (
    <Box sx={{display: 'flex', gap: 2, mt: 3}}>
        <Button variant="outlined" onClick={onToggleFilter}>
            {showChecked ? 'Hide Checked' : 'Show All'}
        </Button>
        <Button variant="outlined" color="error" onClick={onClearAll}>
            Clear All
        </Button>
    </Box>
);
