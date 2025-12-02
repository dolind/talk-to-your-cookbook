import {FC} from 'react';
import {Checkbox, Chip, IconButton, List, ListItem, ListItemText} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import {ShoppingListItem} from '../types';

interface ShoppingListItemsProps {
    items: ShoppingListItem[];
    showChecked: boolean;
    recipeTitleMap: Record<string, string>;
    onToggleChecked: (itemId: string) => void;
    onDeleteItem: (itemId: string) => void;
}

export const ShoppingListItems: FC<ShoppingListItemsProps> = ({
                                                                  items,
                                                                  showChecked,
                                                                  recipeTitleMap,
                                                                  onToggleChecked,
                                                                  onDeleteItem,
                                                              }) => {
    const visibleItems = showChecked ? items : items.filter(item => !item.checked);

    return (
        <List>
            {visibleItems.map(item => (
                <ListItem
                    key={item.id}
                    secondaryAction={
                        <IconButton edge="end" onClick={() => onDeleteItem(item.id)}>
                            <DeleteIcon/>
                        </IconButton>
                    }
                >
                    <Checkbox checked={item.checked ?? false} onChange={() => onToggleChecked(item.id)}/>
                    <ListItemText
                        primary={
                            <span
                                style={{
                                    textDecoration: item.checked ? 'line-through' : 'none',
                                    color: item.checked ? 'gray' : 'inherit',
                                }}
                            >
                {item.ingredient_name}
                                {item.quantity ? ` – ${item.quantity} ${item.unit || ''}` : ''}
              </span>
                        }
                        secondary={
                            item.recipe_id
                                ? `from: ${recipeTitleMap[item.recipe_id] || 'Unknown Recipe'}`
                                : item.note || undefined
                        }
                    />
                    {item.recipe_id && <Chip label="From Recipe" size="small" sx={{ml: 1}}/>}
                    {item.note && !item.recipe_id && <Chip label="note" size="small" sx={{ml: 1}}/>}
                </ListItem>
            ))}
        </List>
    );
};
