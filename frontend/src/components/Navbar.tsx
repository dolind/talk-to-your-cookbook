import {useState} from 'react';
import {Link as RouterLink} from 'react-router-dom';
import {AppBar, Avatar, Box, Button, IconButton, Menu, MenuItem, Toolbar, Tooltip, Typography} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import RestaurantIcon from '@mui/icons-material/Restaurant';
import {useAuth} from '../context/AuthContext';

interface NavbarProps {
    toggleSidebar: () => void;
}

const Navbar = ({toggleSidebar}: NavbarProps) => {
    const [anchorElUser, setAnchorElUser] = useState<null | HTMLElement>(null);
    const {user, logout} = useAuth();

    const handleLogout = async () => {
        await logout();
        handleCloseUserMenu();
    };
    const handleOpenUserMenu = (event: React.MouseEvent<HTMLElement>) => {
        setAnchorElUser(event.currentTarget);
    };

    const handleCloseUserMenu = () => {
        setAnchorElUser(null);
    };

    return (
        <AppBar position="fixed" color="primary" elevation={0}>
            <Toolbar>
                <IconButton
                    color="inherit"
                    aria-label="open drawer"
                    edge="start"
                    onClick={toggleSidebar}
                    sx={{mr: 2}}
                >
                    <MenuIcon/>
                </IconButton>

                <Box sx={{display: 'flex', alignItems: 'center'}}>
                    <RestaurantIcon sx={{mr: 1}}/>
                    <Typography
                        variant="h6"
                        component={RouterLink}
                        to="/"
                        sx={{
                            color: 'white',
                            textDecoration: 'none',
                            fontWeight: 'bold'
                        }}
                    >
                        Talk To Your Cookbook
                    </Typography>
                </Box>

                <Box sx={{flexGrow: 1}}/>

                <Box sx={{display: {xs: 'none', md: 'flex'}, alignItems: 'center', gap: 2}}>
                    <Button color="inherit" component={RouterLink} to="/chat">Chat</Button>
                    <Button color="inherit" component={RouterLink} to="/recipes">Recipes</Button>
                    <Button color="inherit" component={RouterLink} to="/meal-plans">Meal Plans</Button>
                </Box>

                <Box sx={{flexGrow: 0, ml: 2}}>
                    <Tooltip title="Open settings">
                        <IconButton onClick={handleOpenUserMenu} sx={{p: 0}}>
                            <Avatar alt={user?.first_name || 'User'}/>
                        </IconButton>
                    </Tooltip>
                    <Menu
                        sx={{mt: '45px'}}
                        id="menu-appbar"
                        anchorEl={anchorElUser}
                        anchorOrigin={{
                            vertical: 'top',
                            horizontal: 'right',
                        }}
                        keepMounted
                        transformOrigin={{
                            vertical: 'top',
                            horizontal: 'right',
                        }}
                        open={Boolean(anchorElUser)}
                        onClose={handleCloseUserMenu}
                    >
                        <MenuItem component={RouterLink} to="/profile" onClick={handleCloseUserMenu}>
                            <Typography textAlign="center">Profile</Typography>
                        </MenuItem>
                        <MenuItem onClick={handleCloseUserMenu}>
                            <Typography textAlign="center">Settings</Typography>
                        </MenuItem>
                        <MenuItem onClick={handleLogout}>
                            <Typography textAlign="center">Logout</Typography>
                        </MenuItem>
                    </Menu>
                </Box>
            </Toolbar>
        </AppBar>
    );
};

export default Navbar;
