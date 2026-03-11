import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Component as LoginPage } from "@/components/ui/animated-characters-login-page"
// @ts-ignore
import { Chat } from "@/views/Chat"

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const token = localStorage.getItem('token');
    if (!token) {
        return <Navigate to="/login" replace />;
    }
    return <>{children}</>;
}

// The UI has been ported to `Chat.tsx`

function App() {
    return (
        <div className="min-h-screen bg-background text-foreground">
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route
                        path="/"
                        element={
                            <ProtectedRoute>
                                <Chat />
                            </ProtectedRoute>
                        }
                    />
                </Routes>
            </BrowserRouter>
        </div>
    )
}

export default App
