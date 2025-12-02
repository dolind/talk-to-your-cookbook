import {FC} from 'react';
import {Box, Button} from '@mui/material';
import ShoppingCartIcon from '@mui/icons-material/ShoppingCart';

interface MealPlanActionsProps {
    onImportToList: () => void;
    onDeletePlan: () => void;
}

export const MealPlanActions: FC<MealPlanActionsProps> = ({onImportToList, onDeletePlan}) => (
    <Box sx={{display: 'flex', gap: 2, mt: 3}}>
        <Button variant="outlined" startIcon={<ShoppingCartIcon/>} onClick={onImportToList}>
            Add to Cart
        </Button>
        <Button variant="outlined" color="error" onClick={onDeletePlan}>
            Delete Meal Plan
        </Button>
    </Box>
);
