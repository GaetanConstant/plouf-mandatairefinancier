
import React, { useState } from 'react';
import axios from 'axios';
import { Eye, EyeOff } from 'lucide-react';
import parrot from '../assets/parrot.webp';
import scopaLogo from '../assets/scopa-logo.png';
import { API_URL } from '../lib/api';


export function LoginPage({ onLogin }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [showPw, setShowPw] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            const response = await axios.post(`${API_URL}/login`, { username, password }, { withCredentials: true });
            if (response.status === 200) onLogin(response.data.user);
        } catch (err) {
            setError(err.response?.data?.detail || "Erreur de connexion");
        } finally {
            setLoading(false);
        }
    };

    const inputStyle = {
        width: '100%', padding: '11px 16px', borderRadius: '10px',
        border: '1px solid #ccc8c4', background: '#fafaf9', fontSize: '14px',
        fontFamily: 'inherit', outline: 'none',
    };

    return (
        <div
            style={{
                fontFamily: "'Work Sans', 'Helvetica Neue', Arial, sans-serif",
                minHeight: '100vh', position: 'relative', overflow: 'hidden',
                backgroundImage: `url(${parrot})`, backgroundSize: '115%',
                backgroundPosition: 'right 40%', backgroundRepeat: 'no-repeat',
            }}
        >
            {/* Panneau verre dépoli à gauche */}
            <aside
                className="login-panel"
                style={{
                    position: 'absolute', top: 0, bottom: 0, left: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem',
                    WebkitBackdropFilter: 'blur(12px)', backdropFilter: 'blur(12px)',
                    background: 'rgba(237, 236, 234, 0.4)', borderRight: '1px solid rgba(255,255,255,0.1)',
                }}
            >
                <div
                    style={{
                        width: '100%', maxWidth: '420px', background: 'rgba(255,255,255,0.88)',
                        borderRadius: '20px', boxShadow: '0 20px 40px -8px rgba(0,0,0,0.18)',
                        padding: '2.5rem', WebkitBackdropFilter: 'blur(4px)', backdropFilter: 'blur(4px)',
                    }}
                >
                    <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                        <h1 style={{ margin: 0, fontSize: '34px', fontWeight: 700, color: '#3547af', letterSpacing: '-0.5px' }}>Plouf</h1>
                        <p style={{ margin: '6px 0 0', fontSize: '13px', color: '#6b7280' }}>Compte mandataire financier</p>
                    </div>

                    {error && (
                        <div style={{ background: '#fef2f2', border: '1px solid #fca5a5', color: '#dc2626', borderRadius: '8px', padding: '10px 14px', fontSize: '13px', marginBottom: '1rem' }}>
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleSubmit}>
                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Identifiant</label>
                            <input type="text" placeholder="gconstant" required autoComplete="username"
                                value={username} onChange={(e) => setUsername(e.target.value)}
                                style={inputStyle} onFocus={focusOn} onBlur={focusOff} />
                        </div>

                        <div style={{ marginBottom: '1.25rem' }}>
                            <label style={labelStyle}>Mot de passe</label>
                            <div style={{ position: 'relative' }}>
                                <input type={showPw ? 'text' : 'password'} placeholder="••••••••" required autoComplete="current-password"
                                    value={password} onChange={(e) => setPassword(e.target.value)}
                                    style={{ ...inputStyle, paddingRight: '3rem' }} onFocus={focusOn} onBlur={focusOff} />
                                <button type="button" onClick={() => setShowPw(!showPw)}
                                    aria-label={showPw ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
                                    style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', padding: '4px', color: '#9ca3af', display: 'flex', alignItems: 'center' }}>
                                    {showPw ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <button type="submit" disabled={loading}
                            style={{
                                width: '100%', padding: '13px', background: '#3547af', color: '#fff',
                                fontSize: '14px', fontWeight: 600, fontFamily: 'inherit', border: 'none',
                                borderRadius: '50px', cursor: loading ? 'not-allowed' : 'pointer',
                                marginTop: '0.5rem', opacity: loading ? 0.6 : 1, transition: 'opacity .2s, transform .1s',
                            }}>
                            {loading ? 'Connexion…' : 'Se connecter'}
                        </button>
                    </form>
                </div>
            </aside>

            {/* Logo SCOPA en bas à gauche */}
            <footer style={{ position: 'fixed', bottom: '16px', left: '20px', zIndex: 10 }}>
                <a href="https://scopa.co" target="_blank" rel="noopener noreferrer" style={{ display: 'inline-block' }}>
                    <img src={scopaLogo} alt="SCOPA" style={{ height: '56px', width: 'auto', opacity: 0.65 }} />
                </a>
            </footer>

            <style>{`
                .login-panel { width: 33.333%; }
                @media (max-width: 640px) { .login-panel { width: 100% !important; border-right: none !important; } }
            `}</style>
        </div>
    );
}

const labelStyle = {
    display: 'block', fontSize: '11px', fontWeight: 600, color: '#6b7280',
    textTransform: 'uppercase', letterSpacing: '0.6px', marginBottom: '6px',
};

function focusOn(e) {
    e.target.style.borderColor = '#3547af';
    e.target.style.boxShadow = '0 0 0 3px rgba(53,71,175,0.15)';
    e.target.style.background = '#fff';
}
function focusOff(e) {
    e.target.style.borderColor = '#ccc8c4';
    e.target.style.boxShadow = 'none';
    e.target.style.background = '#fafaf9';
}
