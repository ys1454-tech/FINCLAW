# ArmorClaw Frontend

This is the FINCLAW static frontend bundle.

## Default backend
The frontend reads the API base from:
1. `window.FINCLAW_API_BASE` from `config.js`
2. `localStorage.FINCLAW_API_BASE`
3. fallback: `http://127.0.0.1:8000`

## Local run
```powershell
cd "ArmorClawFrontend-main\Armorclaw frontend"
python -m http.server 3000
```

Open:
- `http://127.0.0.1:3000`

If your backend runs elsewhere, edit `config.js` or set in browser console:
```js
localStorage.setItem('FINCLAW_API_BASE', 'http://127.0.0.1:8000')
location.reload()
```
