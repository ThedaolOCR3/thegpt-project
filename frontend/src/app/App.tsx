import { RouterProvider } from 'react-router-dom';
import { AuthProvider } from '../features/auth/AuthProvider';
import { router } from './router';
import { ThemeProvider } from '../components/Theme/ThemeContext';
import { AuthProvider } from '../components/Auth/AuthContext';
import { ModelSelectProvider } from '../components/Chat/ModelSelectContext';
import { CursorFxProvider } from '../components/CursorFx/CursorFxContext';
import { CursorFxLayer } from '../components/CursorFx/CursorFxLayer';

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <ModelSelectProvider>
          <CursorFxProvider>
            <RouterProvider router={router} />
            <CursorFxLayer />
          </CursorFxProvider>
        </ModelSelectProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
