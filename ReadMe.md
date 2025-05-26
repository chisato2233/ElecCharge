# ⚡ Elecharge – Full-Stack Demo

A learning-oriented full-stack project that simulates an electric-vehicle charging
station workflow:

* **Backend** — Django 4 + Django REST Framework  
* **Frontend** — Next.js 14 (App Router) + Tailwind CSS + shadcn/ui  
* **Database** — MySQL (Railway plugin)  
* **Deployment** — Railway (Asia-Southeast 1 region)  
* **CI/CD** — Push to GitHub → Railway autodeploy for both services

---

## 🌐 Live URLs

| Layer      | URL | Notes |
|------------|-----|-------|
| **Frontend (Next.js)** | <https://elecharge.up.railway.app> | User / admin dashboards |
| **Backend API (Django)** | <https://elecharge-backend.up.railway.app> | `/api/` for REST, `/admin/` for Django Admin |
| **Backend Swagger** *(optional)* | `<backend>/api/docs/` | If drf-spectacular enabled |
| **MySQL** | Internal only → `mysql.railway.internal:3306` | Accessible from backend via ENV |

---


---

## 🚀 Quick Start ( Local )

```bash
# 1. spin up DB + backend
docker compose up -d        # visits http://localhost:8000/

# 2. frontend
cd frontend
npm install
npm run dev                 # http://localhost:3000/
````

---


## 📜 License

MIT – free to learn, fork, and extend.
