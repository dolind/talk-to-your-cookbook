import {FC} from 'react';
import {IconButton, List, ListItem, ListItemText, Typography} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import {ImportedMealPlan, ImportedRecipe} from '../types';

interface ShoppingListImportsProps {
    recipes: ImportedRecipe[];
    mealPlans: ImportedMealPlan[];
    onRemoveRecipe: (recipeId: string) => void;
    onRemoveMealPlan: (mealPlanId: string) => void;
}

export const ShoppingListImports: FC<ShoppingListImportsProps> = ({
                                                                      recipes,
                                                                      mealPlans,
                                                                      onRemoveRecipe,
                                                                      onRemoveMealPlan,
                                                                  }) => (
    <>
        <Typography variant="h6" gutterBottom sx={{mt: 4}}>
            Recipes on Shopping List
        </Typography>
        <List dense>
            {recipes.map(recipe => (
                <ListItem
                    key={recipe.recipe_id}
                    secondaryAction={
                        <IconButton edge="end" onClick={() => onRemoveRecipe(recipe.recipe_id)}>
                            <DeleteIcon/>
                        </IconButton>
                    }
                >
                    <ListItemText primary={recipe.title}/>
                </ListItem>
            ))}
        </List>

        {!!mealPlans.length && (
            <>
                <Typography variant="h6" gutterBottom sx={{mt: 4}}>
                    Meal Plans Imported
                </Typography>
                <List dense>
                    {mealPlans.map(plan => (
                        <ListItem
                            key={plan.meal_plan_id}
                            secondaryAction={
                                <IconButton edge="end" onClick={() => onRemoveMealPlan(plan.meal_plan_id)}>
                                    <DeleteIcon/>
                                </IconButton>
                            }
                        >
                            <ListItemText primary={plan.name}/>
                        </ListItem>
                    ))}
                </List>
            </>
        )}
    </>
);
