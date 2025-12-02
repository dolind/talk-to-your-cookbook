import {Navigate, Route, Routes} from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import Chat from './pages/Chat';
import Recipes from './pages/Recipes';
import MealPlans from './pages/MealPlans';
import RecipeDetail from './pages/RecipeDetail';
import Login from './pages/Login';
import Register from './pages/Register';
import Profile from './pages/Profile';
import {AuthProvider, useAuth} from './context/AuthContext';
import ShoppingList from "./pages/ShoppingList.tsx";
import OCRExplorer from "./pages/OCR/OCRExplorer";


// @ts-ignore
function PrivateRoute({children}) {
    // @ts-ignore
    const {user} = useAuth();
    return user ? children : <Navigate to="/login"/>;
}

function App() {
    return (
        <AuthProvider>
            <Routes>
                <Route path="/" element={<Layout/>}>
                    <Route index element={<Home/>}/>
                    <Route path="login" element={<Login/>}/>
                    <Route path="register" element={<Register/>}/>

                    {/* Protected Routes */}
                    <Route
                        path="chat"
                        element={
                            <PrivateRoute>
                                <Chat/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="recipes"
                        element={
                            <PrivateRoute>
                                <Recipes/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="meal-plans"
                        element={
                            <PrivateRoute>
                                <MealPlans/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="recipes/new"
                        element={
                            <PrivateRoute>
                                <RecipeDetail/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="recipes/:id"
                        element={
                            <PrivateRoute>
                                <RecipeDetail/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="profile"
                        element={
                            <PrivateRoute>
                                <Profile/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="shoppinglist"
                        element={
                            <PrivateRoute>
                                <ShoppingList/>
                            </PrivateRoute>
                        }
                    />
                    <Route
                        path="ocr"
                        element={
                            <PrivateRoute>
                                <OCRExplorer/>
                            </PrivateRoute>
                        }
                    />
                    <Route path="/ocr/:bookId?" element={
                        <PrivateRoute>
                            <OCRExplorer/>
                        </PrivateRoute>
                    }
                    />
                </Route>


            </Routes>
        </AuthProvider>
    );
}

export default App;
