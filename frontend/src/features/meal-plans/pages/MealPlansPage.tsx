import {useMemo, useState} from 'react';
import {Box, CircularProgress, Typography} from '@mui/material';
import {MealPlanHeader} from '../components/MealPlanHeader';
import {MealPlanDayView} from '../components/MealPlanDayView';
import {MealPlanWeekView} from '../components/MealPlanWeekView';
import {MealPlanActions} from '../components/MealPlanActions';
import {MealEditDialog} from '../components/MealEditDialog';
import {MealType} from '../constants';
import {Recipe} from '../types';
import {useMealPlan} from '../hooks/useMealPlan';
import {useRecipeSearch} from '../hooks/useRecipeSearch';

interface EditInfo {
    dayIndex: number;
    mealType: MealType;
}

const MealPlansPage = () => {
    const [currentDate, setCurrentDate] = useState(() => new Date());
    const [viewMode, setViewMode] = useState<'day' | 'week'>('day');
    const [activeDayIndex, setActiveDayIndex] = useState(0);
    const [editInfo, setEditInfo] = useState<EditInfo | null>(null);

    const {
        mealPlan,
        loading,
        weekStart,
        weekEnd,
        deleteMealPlan,
        assignRecipeToMeal,
        updateMealNotes,
        removeMeal,
        importToShoppingList,
    } = useMealPlan(currentDate);
    const {query, results, search} = useRecipeSearch();

    const weekRangeLabel = useMemo(
        () => `${weekStart.toDateString()} – ${weekEnd.toDateString()}`,
        [weekEnd, weekStart],
    );

    const changeWeek = (direction: 'prev' | 'next') => {
        const next = new Date(currentDate);
        next.setDate(next.getDate() + (direction === 'prev' ? -7 : 7));
        setCurrentDate(next);
    };

    const handleSelectRecipe = async (recipe: Recipe) => {
        if (!editInfo) return;
        await assignRecipeToMeal(editInfo.dayIndex, editInfo.mealType, recipe);
        setEditInfo(null);
    };

    const handleUpdateNotes = (notes: string) => {
        if (!editInfo) return;
        void updateMealNotes(editInfo.dayIndex, editInfo.mealType, notes);
    };

    const handleDeleteMeal = () => {
        if (!editInfo) return;
        void removeMeal(editInfo.dayIndex, editInfo.mealType).then(() => setEditInfo(null));
    };

    const handleDeletePlan = async () => {
        if (!mealPlan) return;
        const confirmed = window.confirm('Are you sure you want to delete this meal plan?');
        if (!confirmed) return;
        try {
            await deleteMealPlan();
            setCurrentDate(new Date());
        } catch (error) {
            console.error('Failed to delete meal plan', error);
            alert('Could not delete meal plan. It is on the Shopping List!');
        }
    };

    const handleImportToList = async () => {
        try {
            await importToShoppingList();
        } catch (error) {
            console.error('Failed to add to cart', error);
            alert('Failed to add to cart.');
        }
    };

    if (loading && !mealPlan) {
        return (
            <Box sx={{display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '40vh'}}>
                <CircularProgress/>
            </Box>
        );
    }

    if (!mealPlan) {
        return <Typography>Unable to load meal plan.</Typography>;
    }

    return (
        <Box>
            <Typography variant="h4" gutterBottom>
                Meal Plans
            </Typography>

            <MealPlanHeader
                weekRangeLabel={weekRangeLabel}
                onPrevWeek={() => changeWeek('prev')}
                onNextWeek={() => changeWeek('next')}
                viewMode={viewMode}
                onToggleView={() => setViewMode(prev => (prev === 'day' ? 'week' : 'day'))}
            />

            {viewMode === 'day' ? (
                <MealPlanDayView
                    mealPlan={mealPlan}
                    activeDayIndex={activeDayIndex}
                    onDayChange={setActiveDayIndex}
                    onEditMeal={(dayIndex, mealType) => setEditInfo({dayIndex, mealType})}
                />
            ) : (
                <MealPlanWeekView
                    mealPlan={mealPlan}
                    onEditMeal={(dayIndex, mealType) => setEditInfo({dayIndex, mealType})}
                />
            )}

            <MealPlanActions onImportToList={handleImportToList} onDeletePlan={handleDeletePlan}/>

            {editInfo && (
                <MealEditDialog
                    open={Boolean(editInfo)}
                    dayIndex={editInfo.dayIndex}
                    mealType={editInfo.mealType}
                    mealPlan={mealPlan}
                    searchQuery={query}
                    searchResults={results}
                    onSearch={search}
                    onSelectRecipe={handleSelectRecipe}
                    onUpdateNotes={handleUpdateNotes}
                    onDelete={handleDeleteMeal}
                    onClose={() => setEditInfo(null)}
                />
            )}
        </Box>
    );
};

export default MealPlansPage;
