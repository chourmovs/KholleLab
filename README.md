# Khollelab

Khollelab est le socle d'une salle de colle numérique : une interface sobre pour réfléchir, démontrer et, bientôt, recevoir l'intervention d'un professeur au bon moment.

## Architecture

```text
Browser
  ↓
Next.js (UI et proxy `/api/health`)
  ↓
FastAPI
  ↓
PostgreSQL 17
```

Seul Next.js publie un port. Le route handler Next.js relaie le healthcheck au backend sur le réseau Docker ; FastAPI vérifie réellement PostgreSQL avec `SELECT 1`. Une indisponibilité est transformée en état « Offline » sans faire tomber l'interface. Le backend est structuré pour recevoir ultérieurement modèles, schémas et services métier, sans anticiper leurs schémas.

## Développement local

Prérequis : Docker avec Docker Compose v2.

```bash
cp .env.example .env
# Remplacez au minimum POSTGRES_PASSWORD et le mot de passe dans DATABASE_URL
docker compose up --build
```

Une fois les trois services `healthy` :

- application : <http://localhost:3000> ;
- API (interne à Docker par défaut) : `http://backend:8000/api/health` ;
- documentation API (interne) : `http://backend:8000/docs`.

Pour arrêter l'application : `docker compose down`. Ajoutez `-v` uniquement si vous souhaitez aussi supprimer les données PostgreSQL.

## Configuration

| Variable | Rôle | Exemple local |
| --- | --- | --- |
| `APP_ENV` | Environnement de l'API | `development` |
| `POSTGRES_DB` | Base créée par PostgreSQL | `khollelab` |
| `POSTGRES_USER` | Utilisateur PostgreSQL | `khollelab` |
| `POSTGRES_PASSWORD` | Secret PostgreSQL (à remplacer) | aucune valeur réelle versionnée |
| `DATABASE_URL` | URL SQLAlchemy avec driver psycopg | `postgresql+psycopg://…@postgres:5432/khollelab` |
| `CORS_ORIGINS` | Origines autorisées, séparées par des virgules | `http://localhost:3000` |
| `BACKEND_URL` | Adresse interne utilisée par Next.js | `http://backend:8000` |
| `FRONTEND_PORT` | Port hôte local optionnel | `3000` |

`.env.example` ne contient que des valeurs de développement. Ne commitez jamais `.env` ni un secret de production. Les migrations futures pourront être créées et appliquées via `alembic revision --autogenerate` puis `alembic upgrade head` dans `backend/`.

## Déploiement Coolify

1. Créez une ressource **Docker Compose** et connectez ce dépôt Git.
2. Définissez `POSTGRES_DB`, `POSTGRES_USER`, un `POSTGRES_PASSWORD` fort et `DATABASE_URL` avec les mêmes identifiants et l'hôte `postgres`.
3. Définissez `APP_ENV=production`, `BACKEND_URL=http://backend:8000` et `CORS_ORIGINS=https://votre-domaine`.
4. Exposez uniquement le service `frontend` sur le port `3000`, puis associez-lui votre domaine et TLS dans Coolify.
5. Laissez `backend` et `postgres` sans domaine : ils communiquent sur le réseau Compose interne. Le volume nommé `postgres_data` assure la persistance.

Le fichier Compose n'utilise ni chemin absolu, ni bind mount local, ni `localhost` entre conteneurs.

## Contrôles qualité

```bash
cd frontend && npm run lint && npm run build
cd backend && python -m compileall app && pytest
docker compose config
```

## Périmètre PR1

Cette version fournit l'UI responsive, KaTeX, la connectivité et l'infrastructure. Elle n'inclut volontairement ni authentification, ni banque d'exercices réelle, ni correction, ni évaluation LLM.

## Corpus PR2

Les exercices sont des fichiers YAML versionnés sous `problems/`, validés strictement au démarrage puis chargés une seule fois en mémoire. PostgreSQL est réservé aux futures données utilisateur. L'API publique fournit le catalogue (`GET /api/problems`) et le détail (`GET /api/problems/{id}`), mais ne transmet jamais `reference_solution`.

Commandes utiles :

```bash
make test              # tests backend et frontend
make validate-corpus   # validation des YAML avec le chargeur de production
make build             # construction Compose
make smoke             # pile complète et assertions HTTP
```
