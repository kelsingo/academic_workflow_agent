# Fulbright Frontend — Developer Guide

## File Structure
```
frontend/
├── web.html          - HTML
├── css/
│   └── styles.css      - CSS
└── js/
    ├── config.js       - API URL, constants            
    ├── state.js        - Global STATE object
    ├── storage.js      - localStorage helpers          
    ├── api.js          - All fetch() calls to backend  
    ├── ui.js           - DOM helpers, tracker, toasts  
    ├── polling.js      - Status polling + push notifs  
    └── chat.js         - Chat flow & routing logic    
```

---

## STATE.step Values

| Value | Meaning |
|-------|---------|
| `idle` | No active flow |
| `collecting` | Waiting for student to enter course IDs/reason/plan |
| `checking` | Eligibility animation running (automated) |
| `advisor_wait` | Request submitted, polling for advisor reply |
| `registrar_wait` | Advisor approved, polling for registrar reply |
| `done` | Final outcome shown |

---

## Script Load Order
Scripts must load in this exact order:
```
config.js → state.js → storage.js → api.js → ui.js → polling.js → chat.js
```
Each file depends on the ones before it.
