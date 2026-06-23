import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiFetch } from '../api/client';


/**
 * Pantalla de acceso de WorkaTrack.
 *
 * Ahora SÍ habla con el backend:
 *  - En modo "login" llama a POST /api/login.
 *  - En modo "register" llama a POST /api/users.
 * Si la respuesta es correcta:
 *  - Guarda el token JWT en localStorage ("workatrack_token").
 *  - Guarda el usuario en localStorage ("workatrack_user").
 *  - Redirige a /projects.
 */
function AuthPage() {
  const [mode, setMode] = useState('login'); // 'login' o 'register'
  const [emailOrUsername, setEmailOrUsername] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [nombre, setNombre] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (!emailOrUsername || !password) {
        setError('Rellena usuario/correo y contraseña.');
        setLoading(false);
        return;
      }

      if (mode === 'login') {
        // -------- LOGIN --------
        const data = await apiFetch('/login', {
          method: 'POST',
          body: JSON.stringify({
            username: emailOrUsername,
            password,
          }),
        });       

        const token = data.access_token;
        const user = data.user;

        if (!token) {
          throw new Error('La API no ha devuelto token.');
        }

        localStorage.setItem('workatrack_token', token);
        if (user) {
          localStorage.setItem('workatrack_user', JSON.stringify(user));
        }

        navigate('/projects');
      } else {
        // -------- REGISTRO --------
        if (!username) {
          setError('El nombre de usuario es obligatorio para registrarse.');
          setLoading(false);
          return;
        }

        const data = await apiFetch('/users', {
          method: 'POST',
          body: JSON.stringify({
            username,
            email: emailOrUsername,
            password,
            nombre: nombre || null,
          }),
        });

        // Después de registrar, hacemos login automático
        const loginData = await apiFetch('/login', {
          method: 'POST',
          body: JSON.stringify({
            username,
            password,
          }),
        });
        const token = loginData.access_token;
        const user = loginData.user;

        if (!token) {
          throw new Error('La API no ha devuelto token tras el registro.');
        }

        localStorage.setItem('workatrack_token', token);
        if (user) {
          localStorage.setItem('workatrack_user', JSON.stringify(user));
        }

        navigate('/projects');
      }
    } catch (err) {
      console.error('Error en autenticación:', err);
      setError(err.message || 'Ha ocurrido un error.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-container">
      <div className="auth-card">
        <h1>WorkaTrack</h1>
        <p className="auth-subtitle">Organiza tus proyectos y sesiones</p>

        {/* Botones para cambiar entre Login y Registro */}
        <div className="auth-toggle">
          <button
            type="button"
            className={mode === 'login' ? 'active' : ''}
            onClick={() => {
              setMode('login');
              setError('');
            }}
          >
            Login
          </button>

          <button
            type="button"
            className={mode === 'register' ? 'active' : ''}
            onClick={() => {
              setMode('register');
              setError('');
            }}
          >
            Registro
          </button>
        </div>

        {/* Formulario principal */}
        <form onSubmit={handleSubmit} className="auth-form">
          {mode === 'register' && (
            <>
              <div className="form-group">
                <label htmlFor="username">Nombre de usuario</label>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Tu nombre de usuario"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="nombre">Nombre (opcional)</label>
                <input
                  id="nombre"
                  type="text"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Tu nombre real o alias"
                />
              </div>
            </>
          )}

          <div className="form-group">
            <label htmlFor="email">
              {mode === 'login' ? 'Usuario (por ahora)' : 'Correo electrónico'}
            </label>
            <input
              id="email"
              type={mode === 'login' ? 'text' : 'email'}
              value={emailOrUsername}
              onChange={(e) => setEmailOrUsername(e.target.value)}
              placeholder={
                mode === 'login' ? 'Ej: gcrespo' : 'tucorreo@example.com'
              }
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Contraseña</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button type="submit" className="auth-submit" disabled={loading}>
            {loading
              ? mode === 'login'
                ? 'Entrando...'
                : 'Creando cuenta...'
              : mode === 'login'
              ? 'Entrar'
              : 'Crear cuenta'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default AuthPage;
