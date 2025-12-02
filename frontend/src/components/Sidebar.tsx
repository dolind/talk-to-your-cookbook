import {useNavigate} from 'react-router-dom';
import {
    Box,
    Divider,
    Drawer,
    List,
    ListItem,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Typography
} from '@mui/material';
import ChatIcon from '@mui/icons-material/Chat';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import HomeIcon from '@mui/icons-material/Home';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import {Scanner, ShoppingBag} from "@mui/icons-material";

interface SidebarProps {
    open: boolean;
    onClose: () => void;
}

const Sidebar = ({open, onClose}: SidebarProps) => {
    const navigate = useNavigate();

    const menuItems = [
        {text: 'Home', icon: <HomeIcon/>, path: '/'},
        {text: 'AI Chat Assistant', icon: <ChatIcon/>, path: '/chat'},
        {text: 'Recipe Scanner', icon: <Scanner/>, path: '/ocr'},
        {text: 'Recipe Collection', icon: <MenuBookIcon/>, path: '/recipes'},
        {text: 'Meal Planning', icon: <CalendarTodayIcon/>, path: '/meal-plans'},
        {text: 'Shopping List', icon: <ShoppingBag/>, path: '/shoppinglist'},

    ];

    const handleNavigate = (path: string) => {
        navigate(path);
        onClose();
    };

    return (
        <Drawer
            anchor="left"
            open={open}
            onClose={onClose}
            sx={{
                '& .MuiDrawer-paper': {
                    width: {xs: 280, sm: 320},
                    boxSizing: 'border-box',
                },
            }}
        >
            <Box sx={{p: 2, display: 'flex', alignItems: 'center', gap: 1}}>
                <RestaurantIcon color="primary"/>
                <Typography variant="h6" color="primary" fontWeight="bold">
                    Talk To Your Cookbook
                </Typography>
            </Box>

            <Divider/>

            <Box sx={{overflow: 'auto', flexGrow: 1, pt: 2}}>
                <List>
                    {menuItems.map((item) => (
                        <ListItem key={item.text} disablePadding>
                            <ListItemButton onClick={() => handleNavigate(item.path)}>
                                <ListItemIcon>
                                    {item.icon}
                                </ListItemIcon>
                                <ListItemText primary={item.text}/>
                            </ListItemButton>
                        </ListItem>
                    ))}
                </List>
            </Box>
        </Drawer>
    );
};

export default Sidebar;
