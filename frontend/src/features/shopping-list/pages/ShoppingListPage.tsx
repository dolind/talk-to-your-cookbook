import {useState} from 'react';
import {Box, CircularProgress, Typography} from '@mui/material';
import {ShoppingListInputBar} from '../components/ShoppingListInputBar';
import {ShoppingListItems} from '../components/ShoppingListItems';
import {ShoppingListControls} from '../components/ShoppingListControls';
import {ShoppingListImports} from '../components/ShoppingListImports';
import {useShoppingList} from '../hooks/useShoppingList';

const ShoppingListPage = () => {
    const [newIngredient, setNewIngredient] = useState('');
    const [showChecked, setShowChecked] = useState(true);
    const {
        shoppingList,
        loading,
        recipeTitleMap,
        addItem,
        toggleChecked,
        deleteItem,
        clearAll,
        removeRecipe,
        removeMealPlan,
    } = useShoppingList();

    const handleSubmit = async () => {
        await addItem(newIngredient);
        setNewIngredient('');
    };

    if (loading && !shoppingList) {
        return (
            <Box sx={{display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh'}}>
                <CircularProgress/>
            </Box>
        );
    }

    if (!shoppingList) {
        return <Typography>Unable to load shopping list.</Typography>;
    }

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Shopping List
            </Typography>

            <ShoppingListInputBar
                value={newIngredient}
                onChange={setNewIngredient}
                onSubmit={handleSubmit}
            />

            <ShoppingListItems
                items={shoppingList.items}
                showChecked={showChecked}
                recipeTitleMap={recipeTitleMap}
                onToggleChecked={toggleChecked}
                onDeleteItem={deleteItem}
            />

            <ShoppingListControls
                showChecked={showChecked}
                onToggleFilter={() => setShowChecked(prev => !prev)}
                onClearAll={clearAll}
            />

            <ShoppingListImports
                recipes={shoppingList.imported_recipes}
                mealPlans={shoppingList.imported_meal_plans || []}
                onRemoveRecipe={removeRecipe}
                onRemoveMealPlan={removeMealPlan}
            />
        </Box>
    );
};

export default ShoppingListPage;
