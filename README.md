# Khollelab

Khollelab est le socle d'une salle de colle numérique : une interface sobre pour réfléchir, démontrer et, bientôt, recevoir l'intervention d'un professeur au bon moment.

## Architecture

```text
Browser
  ↓
Next.js (UI et proxy `/api/*`)
  ↓
FastAPI
  ↓
PostgreSQL 17
```

Coolify route le domaine public uniquement vers le port interne `3000` de Next.js. Aucun service ne publie de port hôte. Next.js relaie les URL relatives `/api/*` au backend sur le réseau Docker ; FastAPI vérifie réellement PostgreSQL avec `SELECT 1`. Le backend est structuré pour recevoir ultérieurement modèles, schémas et services métier, sans anticiper leurs schémas.

## Développement local

Prérequis : Docker avec Docker Compose v2.

```bash
cp .env.example .env
# Remplacez au minimum POSTGRES_PASSWORD et le mot de passe dans DATABASE_URL
docker compose up --build
```

Une fois les trois services `healthy`, l'application n'est volontairement liée à aucun port hôte. Pour un accès local ponctuel, utilisez par exemple `docker compose exec frontend wget -qO- http://localhost:3000/`. En déploiement :

- application : le domaine Coolify affecté au service `frontend`, port interne `3000` ;
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
| `INTERNAL_API_URL` | Adresse privée utilisée uniquement par le proxy Next.js | `http://backend:8000` |

`.env.example` ne contient que des valeurs de développement. Ne commitez jamais `.env` ni un secret de production. Les migrations futures pourront être créées et appliquées via `alembic revision --autogenerate` puis `alembic upgrade head` dans `backend/`.

## Déploiement Coolify

1. Créez une ressource **Docker Compose** et connectez ce dépôt Git.
2. Définissez `POSTGRES_DB`, `POSTGRES_USER`, un `POSTGRES_PASSWORD` fort et `DATABASE_URL` avec les mêmes identifiants et l'hôte `postgres`.
3. Définissez `APP_ENV=production`, `INTERNAL_API_URL=http://backend:8000` et `CORS_ORIGINS=https://votre-domaine`.
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

## LLM examiner runtime configuration
The backend-only examiner uses runtime variables `LLM_PROVIDER`, `LLM_MODEL`,
`OPENAI_API_KEY`, and `LLM_TIMEOUT_SECONDS` (default 90). CI and smoke tests use
`LLM_PROVIDER=fake`. Never expose the key as a build-time or `NEXT_PUBLIC_` variable.

## Inférence locale

Le backend FastAPI appelle exclusivement, sur le réseau Compose privé, l'API compatible OpenAI de **llama.cpp**, qui charge par défaut `Qwen/Qwen3-4B-GGUF` en `Q4_K_M` (Apache-2.0, environ 2,5 Go). L'image serveur est épinglée à `ghcr.io/ggml-org/llama.cpp:server-b5350`; aucun port hôte ni domaine Coolify ne doit être attribué à `inference`.

Au premier démarrage, llama.cpp résout nativement `Qwen/Qwen3-4B-GGUF:Q4_K_M` avec `-hf`. `LLAMA_CACHE=/models/cache` place le GGUF téléchargé dans le volume nommé `llm_models`; les redémarrages et redéploiements réutilisent donc ce cache (ne lancez pas `docker compose down -v`). `HF_TOKEN` reste facultatif pour les dépôts restreints. L'acquisition et le chargement apparaissent dans `docker compose logs -f inference` (dépôt et quantification demandés, cache manquant/téléchargement, chargement du modèle, puis serveur HTTP prêt). L'application ne déduit jamais l'état depuis ces logs : le backend interroge `/health`.

La configuration backend comprend `LLM_PROVIDER` (`fake`, `openai` ou `local`), `LOCAL_LLM_BASE_URL`, `LOCAL_LLM_MODEL`, `LOCAL_LLM_HF_REPO`, `LOCAL_LLM_QUANT`, `LOCAL_LLM_CONTEXT_SIZE` (8192), `LOCAL_LLM_THREADS` (6), `LOCAL_LLM_BATCH_SIZE`, `LOCAL_LLM_PARALLEL` (1) et `LOCAL_LLM_TIMEOUT_SECONDS`. **Coolify/production doit définir `LLM_PROVIDER=local`** (valeur recommandée et valeur Compose par défaut). Utilisez `LLM_PROVIDER=fake` explicitement en CI uniquement afin de ne jamais télécharger le modèle.

Pour vérifier la persistance après le premier chargement :

```bash
docker compose exec inference find /models -maxdepth 4 -type f -ls
docker compose restart inference
```

Le redémarrage doit charger le fichier déjà présent sous `/models/cache` sans nouveau téléchargement. Le service `inference` démarre en parallèle : ni `backend` ni `frontend` n'en dépendent, et `/api/health` reste opérationnel pendant le téléchargement. `/api/inference/status` expose `starting` jusqu'à ce que `/health` réponde 200, puis `ready`.

Diagnostics manuels depuis un environnement capable de joindre les noms Compose :

```bash
make inference-status
make inference-test
make inference-bench
```

Le benchmark couvre calcul, équation, contre-exemple et question tutorale. Il affiche latence, tokens et tokens/s lorsque l'usage est fourni, sans seuil de performance CI.

### Examiner providers and runtime diagnostics

Before PR7, `LLM_PROVIDER=fake` was deterministic examiner plumbing, not mathematical
inference. Its fixed fixture produced approximately `16/20` / `mostly_correct` so
persistence, UX, and the evaluation workflow could be exercised without an LLM.
Production now explicitly uses `LLM_PROVIDER=local`; CI and offline unit tests must
explicitly select `fake`. The UI labels every fake result **Évaluation simulée**.

Runtime diagnostics are disabled by default. Operators set
`DIAGNOSTICS_ENABLED=true` and a strong `DIAGNOSTICS_TOKEN`, then use **LOGS** in the
header. The token is entered by the operator, retained only in browser
`sessionStorage`, and sent as `X-Diagnostics-Token`. Application and llama.cpp logs
are separate, bounded views backed by the private `runtime_logs` volume; no Docker
socket or arbitrary file access is used.

The proposed `server-b10516` image tag was checked against GHCR on 2026-09-05 and
returned `404`, so it has deliberately not been committed. The currently pinned
`server-b5350` remains until a replacement can be pulled and its `-hf`, logging,
Qwen model load, health, models, and completion paths can all be exercised on a
Docker-capable runner. This prevents an unverified production runtime upgrade.
