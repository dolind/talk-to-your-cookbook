import {FC} from 'react';
import {
    Box,
    Card,
    CardContent,
    Dialog,
    DialogContent,
    DialogTitle,
    IconButton,
    List,
    ListItemButton,
    ListItemText,
    TextField,
    Typography,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import SearchIcon from '@mui/icons-material/Search';
import {MealPlan, Recipe} from '../types';
import {MealType} from '../constants';

interface MealEditDialogProps {
    open: boolean;
    dayIndex: number;
    mealType: MealType;
    mealPlan: MealPlan;
    searchQuery: string;
    searchResults: Recipe[];
    onSearch: (term: string) => void;
    onSelectRecipe: (recipe: Recipe) => void;
    onUpdateNotes: (notes: string) => void;
    onDelete: () => void;
    onClose: () => void;
}

export const MealEditDialog: FC<MealEditDialogProps> = ({
                                                            open,
                                                            dayIndex,
                                                            mealType,
                                                            mealPlan,
                                                            searchQuery,
                                                            searchResults,
                                                            onSearch,
                                                            onSelectRecipe,
                                                            onUpdateNotes,
                                                            onDelete,
                                                            onClose,
                                                        }) => {
    const day = mealPlan.days[dayIndex];
    const item = day.items.find(entry => entry.meal_type === mealType);

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
            <DialogTitle>Edit Meal</DialogTitle>
            <DialogContent>
                {item?.recipe && (
                    <Box sx={{mb: 2}}>
                        <Typography variant="subtitle2" gutterBottom>
                            Currently Selected Recipe:
                        </Typography>
                        <Card variant="outlined" sx={{mb: 1}}>
                            <CardContent>
                                <Typography variant="body1">{item.recipe.title}</Typography>
                                <Typography variant="body2" color="text.secondary">
                                    {item.recipe.description}
                                </Typography>
                            </CardContent>
                        </Card>
                    </Box>
                )}

                <TextField
                    fullWidth
                    placeholder="Search recipes"
                    value={searchQuery}
                    onChange={event => onSearch(event.target.value)}
                    InputProps={{endAdornment: <SearchIcon/>}}
                    sx={{mb: 2}}
                />

                <Box sx={{maxHeight: 300, overflowY: 'auto', mb: 2}}>
                    <List>
                        {searchResults.map(recipe => (
                            <ListItemButton key={recipe.id} onClick={() => onSelectRecipe(recipe)}>
                                <ListItemText primary={recipe.title} secondary={recipe.description}/>
                            </ListItemButton>
                        ))}
                    </List>
                </Box>

                <TextField
                    fullWidth
                    label="Meal Notes"
                    multiline
                    rows={2}
                    value={item?.notes ?? ''}
                    onChange={event => onUpdateNotes(event.target.value)}
                    sx={{mb: 2}}
                />

                <Box sx={{display: 'flex', justifyContent: 'flex-end'}}>
                    <IconButton color="error" onClick={onDelete}>
                        <DeleteIcon/>
                    </IconButton>
                </Box>
            </DialogContent>
        </Dialog>
    );
};
